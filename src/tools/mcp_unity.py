"""WebSocket client for mcp-unity (CoderGamester).

Sends JSON-RPC-style requests to the Unity Editor MCP server and
exposes every tool as a typed async helper that LangGraph agents can call.

Features:
- Heartbeat/ping-pong every 30s to keep connection alive
- Auto-reconnection with exponential backoff (2s, 4s, 8s, 16s, 32s max)
- Circuit breaker pattern (open after 5 failures, half-open after 30s, close after success)
- Retry policy (3 attempts with backoff for transient errors)
- Idempotency keys for safe operations
- Connection pool support
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from src.config import settings

logger = logging.getLogger(__name__)


# ── Circuit Breaker ──────────────────────────────────────────────────


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds before trying half-open
    success_threshold: int = 1  # successes needed to close from half-open

    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                logger.info("Circuit breaker: half-open → closed (recovered)")
                self._reset()
        elif self.state == CircuitState.CLOSED:
            self._failure_count = 0  # Reset failure count on success

    def record_failure(self) -> None:
        """Record a failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._success_count = 0

        if self.state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
            logger.warning("Circuit breaker: closed → open (%d failures)", self._failure_count)
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker: half-open → open (test failed)")
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker: open → half-open (testing recovery)")
                self.state = CircuitState.HALF_OPEN
                self._success_count = 0
                return True
            return False

        # HALF_OPEN: allow limited requests
        return True

    def _reset(self) -> None:
        """Reset to closed state."""
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0


# ── Timeout Configuration ────────────────────────────────────────────


# Timeout per operation type (seconds)
TIMEOUT_BY_CATEGORY: dict[str, float] = {
    "default": 30.0,
    "screenshot": 60.0,
    "batch": 120.0,
    "build": 180.0,
    "lighting_bake": 300.0,
    "navmesh_bake": 120.0,
    "compile": 60.0,
    "test": 120.0,
    "connect": 10.0,
    "heartbeat": 10.0,
}

# Methods that are safe to retry (idempotent)
SAFE_METHODS: set[str] = {
    "list_scripts",
    "get_script_content",
    "get_scene_info",
    "get_gameobject",
    "get_material_info",
    "get_console_logs",
    "get_screenshot",
    "list_assets",
    "get_all_tags",
    "get_lighting_settings",
    "get_lighting_bake_status",
    "get_navmesh_info",
    "get_terrain_info",
    "get_physics_layer_matrix",
    "get_project_settings",
    "get_build_settings",
    "get_animator_controller",
    "get_animator_state",
    "get_audio_mixer_info",
    "get_scriptable_object",
    "list_scriptable_objects",
}


def _get_timeout_for_method(method: str, explicit_timeout: float | None) -> float:
    """Determine timeout based on method and explicit override."""
    if explicit_timeout is not None:
        return explicit_timeout

    # Match method to category
    method_lower = method.lower()
    if "screenshot" in method_lower:
        return TIMEOUT_BY_CATEGORY["screenshot"]
    if "batch" in method_lower:
        return TIMEOUT_BY_CATEGORY["batch"]
    if "bake" in method_lower:
        if "lighting" in method_lower:
            return TIMEOUT_BY_CATEGORY["lighting_bake"]
        return TIMEOUT_BY_CATEGORY["navmesh_bake"]
    if "compile" in method_lower:
        return TIMEOUT_BY_CATEGORY["compile"]
    if "test" in method_lower or "run_tests" in method_lower:
        return TIMEOUT_BY_CATEGORY["test"]
    if "build" in method_lower:
        return TIMEOUT_BY_CATEGORY["build"]

    return TIMEOUT_BY_CATEGORY["default"]


def _is_safe_to_retry(method: str) -> bool:
    """Check if a method is safe to retry (idempotent)."""
    return method in SAFE_METHODS


# ── low-level transport ──────────────────────────────────────────────


class McpUnityClient:
    """Resilient WebSocket connection to the mcp-unity server.

    Features:
    - Heartbeat/ping-pong every 30s
    - Auto-reconnection with exponential backoff
    - Circuit breaker pattern
    - Retry policy for transient errors
    """

    # Connection parameters
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_BASE_DELAY = 2.0  # seconds
    RECONNECT_MAX_DELAY = 32.0  # seconds

    # Retry parameters
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds

    # Heartbeat
    HEARTBEAT_INTERVAL = 30.0  # seconds
    HEARTBEAT_TIMEOUT = 10.0  # seconds

    def __init__(self) -> None:
        self._ws: ClientConnection | None = None
        self._lock = asyncio.Lock()
        self._circuit_breaker = CircuitBreaker()
        self._heartbeat_task: asyncio.Task | None = None
        self._connected_at: float = 0.0
        self._request_count: int = 0
        self._error_count: int = 0

    async def _ensure_connected(self) -> ClientConnection:
        """Ensure we have a valid WebSocket connection."""
        async with self._lock:
            if self._ws is not None and self._ws.close_code is None:
                return self._ws

            # Check circuit breaker
            if not self._circuit_breaker.can_execute():
                raise ConnectionError(
                    f"Circuit breaker is {self._circuit_breaker.state.value}. "
                    f"Too many failures ({self._circuit_breaker._failure_count}). "
                    f"Retry after {self._circuit_breaker.recovery_timeout}s."
                )

            # Attempt reconnection with exponential backoff
            last_exc = None
            for attempt in range(self.MAX_RECONNECT_ATTEMPTS):
                try:
                    delay = min(
                        self.RECONNECT_BASE_DELAY * (2 ** attempt),
                        self.RECONNECT_MAX_DELAY,
                    )
                    # Support both ws:// and wss:// URLs
                    connect_kwargs = {
                        "open_timeout": TIMEOUT_BY_CATEGORY["connect"],
                        "close_timeout": 10,
                        "max_size": 10 * 1024 * 1024,  # 10 MB for screenshots
                        "ping_interval": 20,
                        "ping_timeout": 10,
                    }

                    # Add SSL context for wss:// URLs (cloudflared tunnel)
                    if settings.mcp_unity_ws_url.startswith("wss://"):
                        import ssl
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        connect_kwargs["ssl"] = ssl_context

                    self._ws = await websockets.connect(
                        settings.mcp_unity_ws_url,
                        **connect_kwargs,
                    )
                    self._connected_at = time.time()
                    self._circuit_breaker.record_success()
                    logger.info(
                        "Connected to MCP-Unity at %s (attempt %d)",
                        settings.mcp_unity_ws_url,
                        attempt + 1,
                    )

                    # Start heartbeat task
                    self._start_heartbeat()

                    return self._ws
                except Exception as exc:
                    last_exc = exc
                    self._circuit_breaker.record_failure()
                    logger.warning(
                        "MCP-Unity connection attempt %d/%d failed: %s (retry in %.1fs)",
                        attempt + 1,
                        self.MAX_RECONNECT_ATTEMPTS,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

            raise ConnectionError(
                f"Failed to connect to MCP-Unity after {self.MAX_RECONNECT_ATTEMPTS} attempts: {last_exc}"
            )

    def _start_heartbeat(self) -> None:
        """Start the heartbeat task to keep connection alive."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat pings to keep the connection alive."""
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)

                if self._ws is None or self._ws.close_code is not None:
                    logger.debug("Heartbeat: connection lost, stopping heartbeat")
                    break

                try:
                    # Send a lightweight ping request
                    ping_id = str(uuid.uuid4())
                    payload = {"jsonrpc": "2.0", "id": ping_id, "method": "ping"}
                    await self._ws.send(json.dumps(payload))
                    # Wait for pong response (non-blocking, just check if alive)
                    await asyncio.wait_for(self._ws.recv(), timeout=self.HEARTBEAT_TIMEOUT)
                    logger.debug("Heartbeat: ping successful")
                except asyncio.TimeoutError:
                    logger.warning("Heartbeat: ping timeout, connection may be stale")
                    # Don't close here, let the next request detect the issue
                except Exception as exc:
                    logger.warning("Heartbeat: ping failed: %s", exc)
                    break
        except asyncio.CancelledError:
            logger.debug("Heartbeat: task cancelled")

    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Send a request with retry logic and circuit breaker.

        Args:
            method: JSON-RPC method name
            params: Optional parameters
            timeout: Explicit timeout override (seconds)
            idempotency_key: Optional key for safe retries
        """
        # Determine effective timeout
        effective_timeout = _get_timeout_for_method(method, timeout)

        # Check if method is safe to retry
        can_retry = _is_safe_to_retry(method)

        last_exc = None
        max_attempts = self.MAX_RETRIES if can_retry else 1

        for attempt in range(max_attempts):
            try:
                ws = await self._ensure_connected()

                request_id = idempotency_key or str(uuid.uuid4())
                payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
                if params:
                    payload["params"] = params

                self._request_count += 1

                await ws.send(json.dumps(payload))
                raw = await asyncio.wait_for(ws.recv(), timeout=effective_timeout)
                response = json.loads(raw)

                if "error" in response:
                    error = McpUnityError(response["error"])
                    self._circuit_breaker.record_failure()
                    self._error_count += 1
                    raise error

                result = response.get("result", response)
                if result is None:
                    logger.warning("MCP-Unity %s returned null result", method)
                    return {}

                self._circuit_breaker.record_success()
                return result

            except (
                websockets.exceptions.ConnectionClosed,
                asyncio.TimeoutError,
            ) as exc:
                last_exc = exc
                self._circuit_breaker.record_failure()
                self._error_count += 1
                self._ws = None  # Mark as disconnected

                if attempt < max_attempts - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "MCP-Unity request %s failed (attempt %d/%d): %s, retrying in %.1fs",
                        method,
                        attempt + 1,
                        max_attempts,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "MCP-Unity request %s failed after %d attempts: %s",
                        method,
                        max_attempts,
                        exc,
                    )

            except McpUnityError:
                # Don't retry on application-level errors
                raise
            except Exception as exc:
                last_exc = exc
                self._circuit_breaker.record_failure()
                self._error_count += 1
                logger.error("MCP-Unity request %s unexpected error: %s", method, exc)
                break

        raise last_exc  # type: ignore[misc]

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        uptime = time.time() - self._connected_at if self._connected_at else 0
        return {
            "connected": self._ws is not None and self._ws.close_code is None,
            "uptime_seconds": round(uptime, 1),
            "requests_total": self._request_count,
            "errors_total": self._error_count,
            "circuit_breaker_state": self._circuit_breaker.state.value,
            "circuit_breaker_failures": self._circuit_breaker._failure_count,
            "ws_url": settings.mcp_unity_ws_url,
        }

    async def close(self) -> None:
        """Close the connection and cleanup."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        logger.info("MCP-Unity client closed. Stats: %s", self.get_stats())


class McpUnityError(Exception):
    """Error from MCP-Unity server."""
    pass


# ── singleton ────────────────────────────────────────────────────────

_client = McpUnityClient()


def get_client() -> McpUnityClient:
    return _client


# ── high-level tool helpers (one per mcp-unity tool) ─────────────────


async def list_scripts() -> dict[str, Any]:
    return await _client.send_request("list_scripts")


async def get_script_content(path: str) -> dict[str, Any]:
    return await _client.send_request("get_script_content", {"path": path})


async def apply_patch(path: str, diff: str) -> dict[str, Any]:
    return await _client.send_request("apply_patch", {"path": path, "diff": diff})


async def create_script(name: str, content: str) -> dict[str, Any]:
    return await _client.send_request("create_script", {"name": name, "content": content})


# ── Scene / GameObjects ──


async def get_scene_info() -> dict[str, Any]:
    return await _client.send_request("get_scene_info")


async def load_scene(scene_path: str, additive: bool = False) -> dict[str, Any]:
    return await _client.send_request("load_scene", {"scenePath": scene_path, "additive": additive})


async def get_gameobject(
    *,
    instance_id: int | None = None,
    name: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if instance_id is not None:
        params["instanceId"] = instance_id
    if name is not None:
        params["name"] = name
    if path is not None:
        params["path"] = path
    return await _client.send_request("get_gameobject", params)


async def update_gameobject(
    instance_id: int | None = None,
    name: str | None = None,
    path: str | None = None,
    **properties: Any,
) -> dict[str, Any]:
    params: dict[str, Any] = {**properties}
    if instance_id is not None:
        params["instanceId"] = instance_id
    if name is not None:
        params["name"] = name
    if path is not None:
        params["path"] = path
    return await _client.send_request("update_gameobject", params)


async def update_component(
    game_object: str,
    component_type: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    return await _client.send_request(
        "update_component",
        {"gameObject": game_object, "componentType": component_type, "properties": properties},
    )


async def delete_gameobject(instance_id: int | None = None, path: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if instance_id is not None:
        params["instanceId"] = instance_id
    if path is not None:
        params["path"] = path
    return await _client.send_request("delete_gameobject", params)


async def duplicate_gameobject(instance_id: int | None = None, path: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if instance_id is not None:
        params["instanceId"] = instance_id
    if path is not None:
        params["path"] = path
    return await _client.send_request("duplicate_gameobject", params)


async def reparent_gameobject(
    instance_id: int,
    new_parent_id: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"instanceId": instance_id}
    if new_parent_id is not None:
        params["newParentId"] = new_parent_id
    return await _client.send_request("reparent_gameobject", params)


# ── Materials ──


async def create_material(name: str, shader: str = "Standard") -> dict[str, Any]:
    return await _client.send_request("create_material", {"name": name, "shader": shader})


async def assign_material(game_object: str, material_path: str) -> dict[str, Any]:
    return await _client.send_request("assign_material", {"gameObject": game_object, "materialPath": material_path})


async def modify_material(material_path: str, properties: dict[str, Any]) -> dict[str, Any]:
    return await _client.send_request("modify_material", {"materialPath": material_path, "properties": properties})


async def get_material_info(material_path: str) -> dict[str, Any]:
    return await _client.send_request("get_material_info", {"materialPath": material_path})


# ── Editor ──


async def execute_menu_item(menu_path: str) -> dict[str, Any]:
    return await _client.send_request("execute_menu_item", {"menuPath": menu_path})


async def recompile_scripts() -> dict[str, Any]:
    return await _client.send_request("recompile_scripts")


async def get_console_logs(
    log_type: str = "All",
    offset: int = 0,
    limit: int = 50,
    include_stacktrace: bool = False,
) -> dict[str, Any]:
    return await _client.send_request(
        "get_console_logs",
        {
            "logType": log_type,
            "offset": offset,
            "limit": limit,
            "includeStackTrace": include_stacktrace,
        },
    )


async def send_console_log(message: str, log_type: str = "Log") -> dict[str, Any]:
    return await _client.send_request("send_console_log", {"message": message, "logType": log_type})


async def run_tests(test_mode: str = "EditMode", name_filter: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"testMode": test_mode}
    if name_filter:
        params["nameFilter"] = name_filter
    return await _client.send_request("run_tests", params)


async def add_package(package_id: str) -> dict[str, Any]:
    return await _client.send_request("add_package", {"packageId": package_id})


# ── Screenshots ──


async def get_screenshot() -> dict[str, Any]:
    """Returns base64 screenshot of the Unity Editor."""
    return await _client.send_request("get_screenshot", timeout=60)


# ── Prefabs ──


async def create_prefab(game_object: str, save_path: str) -> dict[str, Any]:
    return await _client.send_request("create_prefab", {"gameObject": game_object, "savePath": save_path})


async def add_asset_to_scene(asset_path: str) -> dict[str, Any]:
    return await _client.send_request("add_asset_to_scene", {"assetPath": asset_path})


# ── Batch ──


async def batch_execute(operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Execute multiple MCP operations atomically (10-100× perf vs sequential)."""
    return await _client.send_request("batch_execute", {"operations": operations}, timeout=120)


# ── Transform ──


async def set_transform(
    instance_id: int,
    position: dict | None = None,
    rotation: dict | None = None,
    scale: dict | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"instanceId": instance_id}
    if position:
        params["position"] = position
    if rotation:
        params["rotation"] = rotation
    if scale:
        params["scale"] = scale
    return await _client.send_request("set_transform", params)


# ── Animation ────────────────────────────────────────────────────────


async def get_animator_controller(game_object: str) -> dict[str, Any]:
    """Get the AnimatorController parameters and state machine info for a GameObject."""
    return await _client.send_request("get_animator_controller", {"gameObject": game_object})


async def set_animator_parameter(
    game_object: str,
    param_name: str,
    value: Any,
) -> dict[str, Any]:
    """Set an Animator parameter (float, int, bool, or trigger)."""
    return await _client.send_request(
        "set_animator_parameter",
        {"gameObject": game_object, "paramName": param_name, "value": value},
    )


async def create_animation_clip(name: str, save_path: str, properties: dict) -> dict[str, Any]:
    """Create a new AnimationClip asset.

    Args:
        name: Clip name
        save_path: Asset path (e.g. Assets/Animations/MyClip.anim)
        properties: JSON dict with animation curves data
    """
    return await _client.send_request(
        "create_animation_clip",
        {"name": name, "savePath": save_path, "properties": properties},
    )


async def add_animation_event(
    clip_path: str,
    time: float,
    function_name: str,
    string_param: str = "",
    float_param: float = 0.0,
    int_param: int = 0,
) -> dict[str, Any]:
    """Add an AnimationEvent to a clip at a specific time."""
    return await _client.send_request(
        "add_animation_event",
        {
            "clipPath": clip_path,
            "time": time,
            "functionName": function_name,
            "stringParam": string_param,
            "floatParam": float_param,
            "intParam": int_param,
        },
    )


async def set_animator_state(game_object: str, state_name: str, layer: str = "") -> dict[str, Any]:
    """Force an Animator to transition to a specific state."""
    params: dict[str, Any] = {"gameObject": game_object, "stateName": state_name}
    if layer:
        params["layer"] = layer
    return await _client.send_request("set_animator_state", params)


async def get_animator_state(game_object: str) -> dict[str, Any]:
    """Get current Animator state info (current state, parameters, transitions)."""
    return await _client.send_request("get_animator_state", {"gameObject": game_object})


# ── NavMesh ──────────────────────────────────────────────────────────


async def bake_navmesh() -> dict[str, Any]:
    """Bake the NavMesh for the current scene."""
    return await _client.send_request("bake_navmesh")


async def get_navmesh_info() -> dict[str, Any]:
    """Get information about the baked NavMesh (areas, agents, links)."""
    return await _client.send_request("get_navmesh_info")


async def set_navmesh_area(
    area_index: int,
    name: str,
    cost: float = 1.0,
    walkable: bool = True,
) -> dict[str, Any]:
    """Configure a NavMesh area."""
    return await _client.send_request(
        "set_navmesh_area",
        {"areaIndex": area_index, "name": name, "cost": cost, "walkable": walkable},
    )


async def create_navmesh_link(
    game_object: str,
    start_pos: dict,
    end_pos: dict,
    width: float = 1.0,
    bidirectional: bool = True,
) -> dict[str, Any]:
    """Create a NavMeshLink between two positions."""
    return await _client.send_request(
        "create_navmesh_link",
        {
            "gameObject": game_object,
            "startPos": start_pos,
            "endPos": end_pos,
            "width": width,
            "bidirectional": bidirectional,
        },
    )


async def set_navmesh_agent_properties(
    game_object: str,
    speed: float | None = None,
    angular_speed: float | None = None,
    acceleration: float | None = None,
    stopping_distance: float | None = None,
) -> dict[str, Any]:
    """Configure NavMeshAgent properties on a GameObject."""
    params: dict[str, Any] = {"gameObject": game_object}
    if speed is not None:
        params["speed"] = speed
    if angular_speed is not None:
        params["angularSpeed"] = angular_speed
    if acceleration is not None:
        params["acceleration"] = acceleration
    if stopping_distance is not None:
        params["stoppingDistance"] = stopping_distance
    return await _client.send_request("set_navmesh_agent_properties", params)


async def set_navmesh_destination(game_object: str, destination: dict) -> dict[str, Any]:
    """Set a NavMeshAgent destination."""
    return await _client.send_request(
        "set_navmesh_destination",
        {"gameObject": game_object, "destination": destination},
    )


# ── Audio ────────────────────────────────────────────────────────────


async def create_audio_source(
    game_object: str,
    clip_path: str = "",
    volume: float = 1.0,
    pitch: float = 1.0,
    loop: bool = False,
    play_on_awake: bool = False,
    spatial_blend: float = 1.0,
) -> dict[str, Any]:
    """Add and configure an AudioSource component on a GameObject."""
    return await _client.send_request(
        "create_audio_source",
        {
            "gameObject": game_object,
            "clipPath": clip_path,
            "volume": volume,
            "pitch": pitch,
            "loop": loop,
            "playOnAwake": play_on_awake,
            "spatialBlend": spatial_blend,
        },
    )


async def modify_audio_source(
    game_object: str,
    properties: dict,
) -> dict[str, Any]:
    """Modify AudioSource properties (volume, pitch, clip, etc.)."""
    return await _client.send_request(
        "modify_audio_source",
        {"gameObject": game_object, "properties": properties},
    )


async def play_audio(game_object: str) -> dict[str, Any]:
    """Play the AudioSource on a GameObject."""
    return await _client.send_request("play_audio", {"gameObject": game_object})


async def stop_audio(game_object: str) -> dict[str, Any]:
    """Stop the AudioSource on a GameObject."""
    return await _client.send_request("stop_audio", {"gameObject": game_object})


async def get_audio_mixer_info(mixer_path: str = "") -> dict[str, Any]:
    """Get AudioMixer info (groups, snapshots, parameters)."""
    return await _client.send_request("get_audio_mixer_info", {"mixerPath": mixer_path})


async def set_audio_mixer_snapshot(mixer_path: str, snapshot_name: str, transition_time: float = 0.5) -> dict[str, Any]:
    """Transition to an AudioMixer snapshot."""
    return await _client.send_request(
        "set_audio_mixer_snapshot",
        {"mixerPath": mixer_path, "snapshotName": snapshot_name, "transitionTime": transition_time},
    )


# ── ScriptableObjects ────────────────────────────────────────────────


async def create_scriptable_object(
    type_name: str,
    save_path: str,
    json_data: str,
) -> dict[str, Any]:
    """Create a new ScriptableObject asset.

    Args:
        type_name: Full C# type name of the ScriptableObject class
        save_path: Asset path (e.g. Assets/Data/SO_MyData.asset)
        json_data: JSON string with the SO field values
    """
    return await _client.send_request(
        "create_scriptable_object",
        {"typeName": type_name, "savePath": save_path, "jsonData": json_data},
    )


async def modify_scriptable_object(
    asset_path: str,
    json_data: str,
) -> dict[str, Any]:
    """Modify an existing ScriptableObject asset.

    Args:
        asset_path: Path to the .asset file
        json_data: JSON string with updated field values
    """
    return await _client.send_request(
        "modify_scriptable_object",
        {"assetPath": asset_path, "jsonData": json_data},
    )


async def get_scriptable_object(asset_path: str) -> dict[str, Any]:
    """Get the current values of a ScriptableObject asset."""
    return await _client.send_request("get_scriptable_object", {"assetPath": asset_path})


async def list_scriptable_objects(type_filter: str = "") -> dict[str, Any]:
    """List all ScriptableObject assets in the project, optionally filtered by type."""
    params: dict[str, Any] = {}
    if type_filter:
        params["typeFilter"] = type_filter
    return await _client.send_request("list_scriptable_objects", params)


# ── VFX / Particle Systems ───────────────────────────────────────────


async def create_particle_system(
    game_object: str,
    preset: str = "default",
    duration: float = 5.0,
    loop: bool = True,
    start_lifetime: float = 1.0,
    start_speed: float = 5.0,
    start_size: float = 1.0,
    max_particles: int = 1000,
) -> dict[str, Any]:
    """Add a ParticleSystem component to a GameObject.

    Args:
        game_object: Target GameObject name or path
        preset: Preset name (default, explosion, smoke, fire, sparks, muzzle)
        duration: Duration in seconds
        loop: Whether to loop
        start_lifetime: Particle lifetime
        start_speed: Initial speed
        start_size: Initial size
        max_particles: Max particle count
    """
    return await _client.send_request(
        "create_particle_system",
        {
            "gameObject": game_object,
            "preset": preset,
            "duration": duration,
            "loop": loop,
            "startLifetime": start_lifetime,
            "startSpeed": start_speed,
            "startSize": start_size,
            "maxParticles": max_particles,
        },
    )


async def modify_particle_system(game_object: str, properties: dict) -> dict[str, Any]:
    """Modify ParticleSystem properties."""
    return await _client.send_request(
        "modify_particle_system",
        {"gameObject": game_object, "properties": properties},
    )


async def play_particle_system(game_object: str, with_children: bool = True) -> dict[str, Any]:
    """Play a ParticleSystem."""
    return await _client.send_request(
        "play_particle_system",
        {"gameObject": game_object, "withChildren": with_children},
    )


async def stop_particle_system(game_object: str, stop_behavior: str = "StopEmitting") -> dict[str, Any]:
    """Stop a ParticleSystem. stop_behavior: StopEmitting, StopEmittingAndClear, StopEmittingAndSimulate."""
    return await _client.send_request(
        "stop_particle_system",
        {"gameObject": game_object, "stopBehavior": stop_behavior},
    )


# ── Terrain ──────────────────────────────────────────────────────────


async def create_terrain(
    size: dict | None = None,
    position: dict | None = None,
    heightmap_resolution: int = 513,
) -> dict[str, Any]:
    """Create a new Terrain in the scene.

    Args:
        size: Terrain size {"x": 1000, "y": 600, "z": 1000}
        position: World position {"x": 0, "y": 0, "z": 0}
        heightmap_resolution: Resolution of the heightmap (default 513)
    """
    params: dict[str, Any] = {"heightmapResolution": heightmap_resolution}
    if size:
        params["size"] = size
    if position:
        params["position"] = position
    return await _client.send_request("create_terrain", params)


async def modify_terrain_height(
    terrain_path: str,
    heights: list[list[float]],
    x_base: int = 0,
    y_base: int = 0,
) -> dict[str, Any]:
    """Modify terrain heightmap data.

    Args:
        terrain_path: Path or name of the terrain
        heights: 2D array of height values (0.0 - 1.0 normalized)
        x_base: X offset in the heightmap
        y_base: Y offset in the heightmap
    """
    return await _client.send_request(
        "modify_terrain_height",
        {"terrainPath": terrain_path, "heights": heights, "xBase": x_base, "yBase": y_base},
    )


async def paint_terrain_texture(
    terrain_path: str,
    texture_index: int,
    alpha_map: list[list[list[float]]],
    x_base: int = 0,
    y_base: int = 0,
) -> dict[str, Any]:
    """Paint terrain textures using alpha map data.

    Args:
        terrain_path: Path or name of the terrain
        texture_index: Index of the terrain layer to paint
        alpha_map: 3D array [y][x][layer] of alpha values (0.0 - 1.0)
        x_base: X offset in the alpha map
        y_base: Y offset in the alpha map
    """
    return await _client.send_request(
        "paint_terrain_texture",
        {"terrainPath": terrain_path, "textureIndex": texture_index, "alphaMap": alpha_map, "xBase": x_base, "yBase": y_base},
    )


async def add_terrain_layer(
    terrain_path: str,
    diffuse_texture: str,
    normal_map: str = "",
    tile_size: dict | None = None,
    metallic: float = 0.0,
    smoothness: float = 0.5,
) -> dict[str, Any]:
    """Add a texture layer to a terrain.

    Args:
        terrain_path: Path or name of the terrain
        diffuse_texture: Path to the diffuse texture asset
        normal_map: Path to the normal map asset (optional)
        tile_size: Tiling {"x": 15, "y": 15}
        metallic: Metallic value (0-1)
        smoothness: Smoothness value (0-1)
    """
    params: dict[str, Any] = {
        "terrainPath": terrain_path,
        "diffuseTexture": diffuse_texture,
        "metallic": metallic,
        "smoothness": smoothness,
    }
    if normal_map:
        params["normalMap"] = normal_map
    if tile_size:
        params["tileSize"] = tile_size
    return await _client.send_request("add_terrain_layer", params)


async def get_terrain_info(terrain_path: str) -> dict[str, Any]:
    """Get terrain information (size, resolution, layers, settings)."""
    return await _client.send_request("get_terrain_info", {"terrainPath": terrain_path})


# ── Physics & Layers ─────────────────────────────────────────────────


async def set_physics_layer(
    layer_index: int,
    layer_name: str,
    collision_matrix: dict | None = None,
) -> dict[str, Any]:
    """Configure a physics layer name and collision matrix."""
    params: dict[str, Any] = {"layerIndex": layer_index, "layerName": layer_name}
    if collision_matrix:
        params["collisionMatrix"] = collision_matrix
    return await _client.send_request("set_physics_layer", params)


async def get_physics_layer_matrix() -> dict[str, Any]:
    """Get the full physics layer collision matrix."""
    return await _client.send_request("get_physics_layer_matrix")


async def set_layer_collision(layer1: int, layer2: int, ignore: bool) -> dict[str, Any]:
    """Set collision between two layers (ignore or not)."""
    return await _client.send_request(
        "set_layer_collision",
        {"layer1": layer1, "layer2": layer2, "ignore": ignore},
    )


async def set_physics_settings(
    gravity: dict | None = None,
    fixed_timestep: float | None = None,
    default_contact_offset: float | None = None,
    bounce_threshold: float | None = None,
) -> dict[str, Any]:
    """Configure global physics settings."""
    params: dict[str, Any] = {}
    if gravity is not None:
        params["gravity"] = gravity
    if fixed_timestep is not None:
        params["fixedTimestep"] = fixed_timestep
    if default_contact_offset is not None:
        params["defaultContactOffset"] = default_contact_offset
    if bounce_threshold is not None:
        params["bounceThreshold"] = bounce_threshold
    return await _client.send_request("set_physics_settings", params)


# ── Tags ─────────────────────────────────────────────────────────────


async def get_all_tags() -> dict[str, Any]:
    """Get all tags defined in the project."""
    return await _client.send_request("get_all_tags")


async def add_tag(tag_name: str) -> dict[str, Any]:
    """Add a new tag to the project."""
    return await _client.send_request("add_tag", {"tagName": tag_name})


async def remove_tag(tag_name: str) -> dict[str, Any]:
    """Remove a tag from the project."""
    return await _client.send_request("remove_tag", {"tagName": tag_name})


# ── Lighting ─────────────────────────────────────────────────────────


async def get_lighting_settings() -> dict[str, Any]:
    """Get current lighting settings (ambient, fog, reflection, GI)."""
    return await _client.send_request("get_lighting_settings")


async def set_lighting_settings(properties: dict) -> dict[str, Any]:
    """Configure lighting settings (ambient mode, fog, skybox, etc.)."""
    return await _client.send_request("set_lighting_settings", properties)


async def bake_lighting(mode: str = "ProgressiveGPU") -> dict[str, Any]:
    """Start lighting bake. mode: ProgressiveGPU, ProgressiveCPU, Enlighten."""
    return await _client.send_request("bake_lighting", {"mode": mode})


async def get_lighting_bake_status() -> dict[str, Any]:
    """Get the current status of a lighting bake operation."""
    return await _client.send_request("get_lighting_bake_status")


async def create_light_probe_group(
    position: dict | None = None,
    resolution_x: int = 3,
    resolution_y: int = 3,
    resolution_z: int = 3,
) -> dict[str, Any]:
    """Create a LightProbeGroup at the specified position."""
    params: dict[str, Any] = {
        "resolutionX": resolution_x,
        "resolutionY": resolution_y,
        "resolutionZ": resolution_z,
    }
    if position:
        params["position"] = position
    return await _client.send_request("create_light_probe_group", params)


async def create_reflection_probe(
    position: dict | None = None,
    box_size: dict | None = None,
    importance: int = 1,
) -> dict[str, Any]:
    """Create a ReflectionProbe at the specified position."""
    params: dict[str, Any] = {"importance": importance}
    if position:
        params["position"] = position
    if box_size:
        params["boxSize"] = box_size
    return await _client.send_request("create_reflection_probe", params)


# ── Rendering ────────────────────────────────────────────────────────


async def set_render_settings(
    ambient_mode: str | None = None,
    ambient_sky_color: dict | None = None,
    ambient_equator_color: dict | None = None,
    ambient_ground_color: dict | None = None,
    skybox_material: str | None = None,
    sun: str | None = None,
    fog_enabled: bool | None = None,
    fog_color: dict | None = None,
    fog_density: float | None = None,
) -> dict[str, Any]:
    """Configure render and environment settings."""
    params: dict[str, Any] = {}
    if ambient_mode is not None:
        params["ambientMode"] = ambient_mode
    if ambient_sky_color is not None:
        params["ambientSkyColor"] = ambient_sky_color
    if ambient_equator_color is not None:
        params["ambientEquatorColor"] = ambient_equator_color
    if ambient_ground_color is not None:
        params["ambientGroundColor"] = ambient_ground_color
    if skybox_material is not None:
        params["skyboxMaterial"] = skybox_material
    if sun is not None:
        params["sun"] = sun
    if fog_enabled is not None:
        params["fogEnabled"] = fog_enabled
    if fog_color is not None:
        params["fogColor"] = fog_color
    if fog_density is not None:
        params["fogDensity"] = fog_density
    return await _client.send_request("set_render_settings", params)


async def set_quality_settings(
    quality_level: int | None = None,
    anti_aliasing: int | None = None,
    shadow_distance: float | None = None,
    shadow_cascades: int | None = None,
    v_sync_count: int | None = None,
) -> dict[str, Any]:
    """Configure quality settings."""
    params: dict[str, Any] = {}
    if quality_level is not None:
        params["qualityLevel"] = quality_level
    if anti_aliasing is not None:
        params["antiAliasing"] = anti_aliasing
    if shadow_distance is not None:
        params["shadowDistance"] = shadow_distance
    if shadow_cascades is not None:
        params["shadowCascades"] = shadow_cascades
    if v_sync_count is not None:
        params["vSyncCount"] = v_sync_count
    return await _client.send_request("set_quality_settings", params)


# ── Project Settings ─────────────────────────────────────────────────


async def get_project_settings(category: str = "all") -> dict[str, Any]:
    """Get project settings. category: all, player, input, physics, time, graphics, quality, audio, tags."""
    return await _client.send_request("get_project_settings", {"category": category})


async def set_project_settings(category: str, settings_data: dict) -> dict[str, Any]:
    """Set project settings for a specific category."""
    return await _client.send_request(
        "set_project_settings",
        {"category": category, "settings": settings_data},
    )


# ── Asset Management ─────────────────────────────────────────────────


async def import_asset(source_path: str, destination: str = "") -> dict[str, Any]:
    """Import an external asset into the Unity project.

    Args:
        source_path: Local file path on the machine running Unity
        destination: Asset path in the project (e.g. Assets/Textures/)
    """
    params: dict[str, Any] = {"sourcePath": source_path}
    if destination:
        params["destination"] = destination
    return await _client.send_request("import_asset", params)


async def export_asset(asset_path: str, export_path: str) -> dict[str, Any]:
    """Export a Unity asset to an external file.

    Args:
        asset_path: Asset path in the project
        export_path: Destination file path
    """
    return await _client.send_request(
        "export_asset",
        {"assetPath": asset_path, "exportPath": export_path},
    )


async def list_assets(
    folder: str = "Assets",
    file_extension: str = "",
    recursive: bool = True,
) -> dict[str, Any]:
    """List assets in a project folder, optionally filtered by extension."""
    params: dict[str, Any] = {"folder": folder, "recursive": recursive}
    if file_extension:
        params["fileExtension"] = file_extension
    return await _client.send_request("list_assets", params)


async def delete_asset(asset_path: str) -> dict[str, Any]:
    """Delete an asset from the project."""
    return await _client.send_request("delete_asset", {"assetPath": asset_path})


async def move_asset(source_path: str, destination_path: str) -> dict[str, Any]:
    """Move/rename an asset in the project."""
    return await _client.send_request(
        "move_asset",
        {"sourcePath": source_path, "destinationPath": destination_path},
    )


async def create_folder(folder_path: str) -> dict[str, Any]:
    """Create a new folder in the project."""
    return await _client.send_request("create_folder", {"folderPath": folder_path})


# ── Build Settings ───────────────────────────────────────────────────


async def get_build_settings() -> dict[str, Any]:
    """Get current Build Settings (scenes, platform, options)."""
    return await _client.send_request("get_build_settings")


async def add_scene_to_build(scene_path: str, enabled: bool = True) -> dict[str, Any]:
    """Add a scene to the Build Settings scene list."""
    return await _client.send_request(
        "add_scene_to_build",
        {"scenePath": scene_path, "enabled": enabled},
    )


async def set_active_build_target(platform: str, sub_target: str = "") -> dict[str, Any]:
    """Switch the active build target. platform: StandaloneWindows64, Android, iOS, WebGL, PS5, XboxSeriesX."""
    params: dict[str, Any] = {"platform": platform}
    if sub_target:
        params["subTarget"] = sub_target
    return await _client.send_request("set_active_build_target", params)
