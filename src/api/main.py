ur """FastAPI server — exposes the LangGraph agent as a REST/WebSocket API.

Features:
- SSE streaming for real-time agent responses
- Prometheus metrics endpoint
- Rate limiting per API key
- Structured logging with correlation IDs
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from src.agents.graph import app as agent_app
from src.config import settings
from src.rag.indexer import index_kb_documents, index_project_code
from src.tools.mcp_unity import get_client

logger = logging.getLogger(__name__)


# ── Metrics ──────────────────────────────────────────────────────────


class Metrics:
    """Simple in-memory metrics collector."""

    def __init__(self) -> None:
        self.requests_total: int = 0
        self.requests_by_route: dict[str, int] = defaultdict(int)
        self.requests_by_status: dict[int, int] = defaultdict(int)
        self.latency_sum_ms: float = 0.0
        self.latency_count: int = 0
        self.errors_total: int = 0
        self.active_connections: int = 0
        self.ws_connections_total: int = 0
        self.agent_calls_total: int = 0
        self.agent_calls_by_route: dict[str, int] = defaultdict(int)

    def record_request(self, route: str, status_code: int, duration_ms: float) -> None:
        self.requests_total += 1
        self.requests_by_route[route] += 1
        self.requests_by_status[status_code] += 1
        self.latency_sum_ms += duration_ms
        self.latency_count += 1
        if status_code >= 400:
            self.errors_total += 1

    def record_agent_call(self, route: str) -> None:
        self.agent_calls_total += 1
        self.agent_calls_by_route[route] += 1

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = [
            "# HELP agentunity_requests_total Total HTTP requests",
            "# TYPE agentunity_requests_total counter",
            f"agentunity_requests_total {self.requests_total}",
            "",
            "# HELP agentunity_requests_by_route HTTP requests by route",
            "# TYPE agentunity_requests_by_route counter",
        ]
        for route, count in self.requests_by_route.items():
            lines.append(f'agentunity_requests_by_route{{route="{route}"}} {count}')

        lines.extend([
            "",
            "# HELP agentunity_requests_by_status HTTP requests by status code",
            "# TYPE agentunity_requests_by_status counter",
        ])
        for status, count in self.requests_by_status.items():
            lines.append(f"agentunity_requests_by_status{{status=\"{status}\"}} {count}")

        avg_latency = self.latency_sum_ms / self.latency_count if self.latency_count else 0
        lines.extend([
            "",
            "# HELP agentunity_latency_avg_ms Average request latency in ms",
            "# TYPE agentunity_latency_avg_ms gauge",
            f"agentunity_latency_avg_ms {avg_latency:.2f}",
            "",
            "# HELP agentunity_errors_total Total HTTP errors (4xx/5xx)",
            "# TYPE agentunity_errors_total counter",
            f"agentunity_errors_total {self.errors_total}",
            "",
            "# HELP agentunity_active_connections Current active connections",
            "# TYPE agentunity_active_connections gauge",
            f"agentunity_active_connections {self.active_connections}",
            "",
            "# HELP agentunity_ws_connections_total Total WebSocket connections",
            "# TYPE agentunity_ws_connections_total counter",
            f"agentunity_ws_connections_total {self.ws_connections_total}",
            "",
            "# HELP agentunity_agent_calls_total Total agent invocations",
            "# TYPE agentunity_agent_calls_total counter",
            f"agentunity_agent_calls_total {self.agent_calls_total}",
        ])

        for route, count in self.agent_calls_by_route.items():
            lines.append(f'agentunity_agent_calls_by_route{{route="{route}"}} {count}')

        return "\n".join(lines)


metrics = Metrics()


# ── Rate Limiter ─────────────────────────────────────────────────────


class RateLimiter:
    """Simple in-memory rate limiter per API key."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if t > window_start]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.time()
        window_start = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        return max(0, self.max_requests - len(self._requests[key]))


rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


# ── Lifespan ─────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("AgentUnity server starting on %s:%s", settings.api_host, settings.api_port)
    # Auto-index KB documents on startup
    try:
        from src.rag.indexer import index_kb_documents
        count = await index_kb_documents()
        logger.info("KB auto-indexed: %d chunks", count)
    except Exception as exc:
        logger.warning("KB auto-indexing failed (non-fatal): %s", exc)
    yield
    # cleanup
    client = get_client()
    await client.close()
    logger.info("AgentUnity server stopped")


app = FastAPI(title="AgentUnity", version="0.1.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rate Limiting Middleware ─────────────────────────────────────────


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting based on API key."""
    # Skip rate limiting for health/ping/metrics
    if request.url.path in ("/api/v1/health", "/api/v1/ping", "/metrics"):
        return await call_next(request)

    # Get API key from header
    api_key = request.headers.get("x-api-key", "")

    if not rate_limiter.is_allowed(api_key):
        remaining = rate_limiter.remaining(api_key)
        return HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again later.",
            headers={"X-RateLimit-Remaining": str(remaining)},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(rate_limiter.remaining(api_key))
    return response


# ── Auth ─────────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key")


async def verify_api_key(api_key: str = Depends(_api_key_header)) -> str:
    if api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


# ── Models ───────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []  # [{"role": "user"|"assistant", "content": "..."}]


class ChatResponse(BaseModel):
    reply: str
    route: str
    duration_ms: int


class IndexResponse(BaseModel):
    chunks_indexed: int
    duration_ms: int


class HealthStatus(BaseModel):
    status: str
    mcp_unity: str
    vllm_llm: str
    qdrant: str
    embeddings: str
    reranker: str


# ── Endpoints ────────────────────────────────────────────────────────


@app.post("/api/v1/agent/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _: str = Depends(verify_api_key)) -> ChatResponse:
    """Send a message to the multi-agent system."""
    t0 = time.monotonic()

    messages: list[Any] = []
    for h in req.history:
        role = h.get("role", "")
        content = h.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=req.message))

    result = await agent_app.ainvoke(
        {"messages": messages, "rag_context": "", "route": "", "iteration": 0}
    )

    last_ai = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            last_ai = msg.content
            break

    duration = int((time.monotonic() - t0) * 1000)
    return ChatResponse(reply=last_ai, route=result.get("route", "unknown"), duration_ms=duration)


@app.post("/api/v1/rag/index", response_model=IndexResponse)
async def rag_index(_: str = Depends(verify_api_key)) -> IndexResponse:
    """Trigger re-indexation of the Unity project codebase via MCP-Unity + KB docs."""
    t0 = time.monotonic()
    code_count = await index_project_code()
    kb_count = await index_kb_documents()
    duration = int((time.monotonic() - t0) * 1000)
    return IndexResponse(chunks_indexed=code_count + kb_count, duration_ms=duration)


@app.post("/api/v1/rag/index-kb", response_model=IndexResponse)
async def rag_index_kb(_: str = Depends(verify_api_key)) -> IndexResponse:
    """Index only the local KB markdown files (no MCP-Unity required)."""
    t0 = time.monotonic()
    count = await index_kb_documents()
    duration = int((time.monotonic() - t0) * 1000)
    return IndexResponse(chunks_indexed=count, duration_ms=duration)


@app.get("/api/v1/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    """Check connectivity to all backend services."""
    import asyncio

    import httpx

    mcp_status = "unknown"
    vllm_status = "unknown"
    qdrant_status = "unknown"
    embed_status = "unknown"
    rerank_status = "unknown"

    async with httpx.AsyncClient(timeout=5) as http:
        # MCP-Unity — non-blocking check (just report last known state)
        try:
            client = get_client()
            if client._ws and not client._ws.closed:
                mcp_status = "ok"
            else:
                # Try to connect with a short timeout
                try:
                    await asyncio.wait_for(client._ensure_connected(), timeout=3)
                    mcp_status = "ok"
                except asyncio.TimeoutError:
                    mcp_status = "timeout"
                except Exception as exc:
                    mcp_status = f"error: {exc}"
        except Exception as exc:
            mcp_status = f"error: {exc}"

        # vLLM
        try:
            r = await http.get(f"{settings.vllm_llm_url}/models")
            vllm_status = "ok" if r.status_code in (200, 401) else f"http {r.status_code}"
        except Exception as exc:
            vllm_status = f"error: {exc}"

        # Qdrant
        try:
            r = await http.get(f"{settings.qdrant_url}/collections")
            qdrant_status = "ok" if r.status_code == 200 else f"http {r.status_code}"
        except Exception as exc:
            qdrant_status = f"error: {exc}"

        # Embeddings
        try:
            r = await http.get(f"{settings.embedding_url}/health")
            embed_status = "ok" if r.status_code == 200 else f"http {r.status_code}"
        except Exception as exc:
            embed_status = f"error: {exc}"

        # Reranker
        try:
            r = await http.get(f"{settings.reranker_url}/health")
            rerank_status = "ok" if r.status_code == 200 else f"http {r.status_code}"
        except Exception as exc:
            rerank_status = f"error: {exc}"

    # MCP-Unity is remote via tunnel — timeout is acceptable, not a degradation
    core_statuses = [vllm_status, qdrant_status, embed_status, rerank_status]
    overall = "ok" if all(s == "ok" for s in core_statuses) else "degraded"
    return HealthStatus(
        status=overall, mcp_unity=mcp_status, vllm_llm=vllm_status,
        qdrant=qdrant_status, embeddings=embed_status, reranker=rerank_status,
    )


@app.get("/api/v1/ping")
async def ping():
    """Lightweight ping endpoint for quick connectivity checks."""
    return {"status": "ok"}


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    return StreamingResponse(
        iter([metrics.to_prometheus()]),
        media_type="text/plain",
    )


@app.get("/api/v1/metrics")
async def get_metrics():
    """Get metrics in JSON format."""
    avg_latency = metrics.latency_sum_ms / metrics.latency_count if metrics.latency_count else 0
    return {
        "requests_total": metrics.requests_total,
        "requests_by_route": dict(metrics.requests_by_route),
        "requests_by_status": dict(metrics.requests_by_status),
        "latency_avg_ms": round(avg_latency, 2),
        "errors_total": metrics.errors_total,
        "active_connections": metrics.active_connections,
        "ws_connections_total": metrics.ws_connections_total,
        "agent_calls_total": metrics.agent_calls_total,
        "agent_calls_by_route": dict(metrics.agent_calls_by_route),
    }


# ── SSE Streaming ────────────────────────────────────────────────────


async def _stream_agent_response(
    messages: list[Any],
    conversation_id: str = "",
) -> Any:
    """Generator that yields SSE events for agent responses."""
    import json

    # Send planning event
    yield f"data: {json.dumps({'type': 'planning', 'message': 'Analyzing request...'})}\n\n"

    try:
        result = await agent_app.ainvoke(
            {
                "messages": messages,
                "rag_context": "",
                "route": "",
                "iteration": 0,
            }
        )

        # Send route event
        route = result.get("route", "unknown")
        yield f"data: {json.dumps({'type': 'route', 'route': route})}\n\n"

        # Send tool events if any
        for msg in result.get("messages", []):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_call.get('name', 'unknown')})}\n\n"

        # Send final response
        last_ai = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                last_ai = msg.content
                break

        yield f"data: {json.dumps({'type': 'response', 'content': last_ai, 'route': route})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as exc:
        logger.error("Streaming agent error: %s", exc, exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


@app.post("/api/v1/agent/stream")
async def stream_chat(req: ChatRequest, api_key: str = Depends(verify_api_key)):
    """SSE streaming endpoint for real-time agent responses."""
    messages: list[Any] = []
    for h in req.history:
        role = h.get("role", "")
        content = h.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=req.message))

    return StreamingResponse(
        _stream_agent_response(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── WebSocket (streaming) ───────────────────────────────────────────


@app.websocket("/api/v1/agent/ws")
async def ws_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming agent responses."""
    await websocket.accept()

    # auth check
    try:
        init = await websocket.receive_json()
        if init.get("api_key") != settings.api_secret_key:
            await websocket.send_json({"error": "Invalid API key"})
            await websocket.close()
            return
    except Exception:
        await websocket.close()
        return

    # Conversation memory for the WS session
    ws_messages: list[Any] = []

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            if not message:
                continue

            ws_messages.append(HumanMessage(content=message))

            try:
                result = await agent_app.ainvoke(
                    {
                        "messages": list(ws_messages),
                        "rag_context": "",
                        "route": "",
                        "iteration": 0,
                    }
                )

                last_ai = ""
                for msg in reversed(result["messages"]):
                    if isinstance(msg, AIMessage) and msg.content:
                        last_ai = msg.content
                        break

                ws_messages.append(AIMessage(content=last_ai))
                await websocket.send_json({"reply": last_ai, "route": result.get("route", "unknown")})
            except Exception as exc:
                logger.error("Agent error during WS call: %s", exc, exc_info=True)
                await websocket.send_json({"error": str(exc)})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
