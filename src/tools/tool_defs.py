"""LangChain tool wrappers around the MCP-Unity client.

Each tool is a @tool-decorated async function that LangGraph agents
can invoke via the standard tool-calling interface.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from src.tools import mcp_unity


# ── Code tools ───────────────────────────────────────────────────────


@tool
async def unity_list_scripts() -> str:
    """List all C# script paths in the Unity project."""
    result = await mcp_unity.list_scripts()
    return json.dumps(result, indent=2)


@tool
async def unity_get_script(path: str) -> str:
    """Get the content of a C# script at the given path."""
    result = await mcp_unity.get_script_content(path)
    return json.dumps(result, indent=2)


@tool
async def unity_apply_patch(path: str, diff: str) -> str:
    """Apply a unified diff patch to a C# script.

    Args:
        path: Asset path of the script (e.g. Assets/Scripts/Player.cs)
        diff: Unified diff content to apply
    """
    result = await mcp_unity.apply_patch(path, diff)
    return json.dumps(result, indent=2)


@tool
async def unity_create_script(name: str, content: str) -> str:
    """Create a new C# script in the Unity project.

    Args:
        name: Script name (without .cs extension)
        content: Full C# source code
    """
    result = await mcp_unity.create_script(name, content)
    return json.dumps(result, indent=2)


# ── Scene tools ──────────────────────────────────────────────────────


@tool
async def unity_get_scene_info() -> str:
    """Get information about the currently active scene(s)."""
    result = await mcp_unity.get_scene_info()
    return json.dumps(result, indent=2)


@tool
async def unity_load_scene(scene_path: str, additive: bool = False) -> str:
    """Load a scene by path. Use additive=true for multi-scene setups."""
    result = await mcp_unity.load_scene(scene_path, additive)
    return json.dumps(result, indent=2)


@tool
async def unity_get_gameobject(name: str = "", path: str = "") -> str:
    """Get a GameObject by name or hierarchical path (e.g. 'Canvas/Panel/Button').

    Provide either name or path.
    """
    kwargs: dict[str, Any] = {}
    if name:
        kwargs["name"] = name
    if path:
        kwargs["path"] = path
    result = await mcp_unity.get_gameobject(**kwargs)
    return json.dumps(result, indent=2)


@tool
async def unity_update_gameobject(name: str, **properties: Any) -> str:
    """Update a GameObject's properties (tag, layer, active, static, etc.)."""
    result = await mcp_unity.update_gameobject(name=name, **properties)
    return json.dumps(result, indent=2)


@tool
async def unity_update_component(
    game_object: str,
    component_type: str,
    properties: str,
) -> str:
    """Add or update a component on a GameObject.

    Args:
        game_object: Name or path of the target GameObject
        component_type: Full type name (e.g. UnityEngine.BoxCollider)
        properties: JSON string of property key-value pairs
    """
    props = json.loads(properties)
    result = await mcp_unity.update_component(game_object, component_type, props)
    return json.dumps(result, indent=2)


@tool
async def unity_delete_gameobject(path: str) -> str:
    """Delete a GameObject by hierarchical path."""
    result = await mcp_unity.delete_gameobject(path=path)
    return json.dumps(result, indent=2)


@tool
async def unity_duplicate_gameobject(path: str) -> str:
    """Duplicate a GameObject by hierarchical path."""
    result = await mcp_unity.duplicate_gameobject(path=path)
    return json.dumps(result, indent=2)


# ── Material tools ───────────────────────────────────────────────────


@tool
async def unity_create_material(name: str, shader: str = "Standard") -> str:
    """Create a new material with the given shader."""
    result = await mcp_unity.create_material(name, shader)
    return json.dumps(result, indent=2)


@tool
async def unity_assign_material(game_object: str, material_path: str) -> str:
    """Assign a material to a GameObject's renderer."""
    result = await mcp_unity.assign_material(game_object, material_path)
    return json.dumps(result, indent=2)


@tool
async def unity_modify_material(material_path: str, properties: str) -> str:
    """Modify properties of an existing material.

    Args:
        material_path: Path to the material asset
        properties: JSON string of property key-value pairs to update
    """
    props = json.loads(properties)
    result = await mcp_unity.modify_material(material_path, props)
    return json.dumps(result, indent=2)


@tool
async def unity_get_material_info(material_path: str) -> str:
    """Get detailed information about a material (shader, properties, textures)."""
    result = await mcp_unity.get_material_info(material_path)
    return json.dumps(result, indent=2)


@tool
async def unity_reparent_gameobject(instance_id: int, new_parent_id: int = -1) -> str:
    """Move a GameObject to a new parent in the hierarchy.

    Args:
        instance_id: Instance ID of the GameObject to move
        new_parent_id: Instance ID of the new parent (-1 for root)
    """
    parent = new_parent_id if new_parent_id >= 0 else None
    result = await mcp_unity.reparent_gameobject(instance_id, parent)
    return json.dumps(result, indent=2)


@tool
async def unity_send_console_log(message: str, log_type: str = "Log") -> str:
    """Send a message to the Unity console. log_type: Log, Warning, Error."""
    result = await mcp_unity.send_console_log(message, log_type)
    return json.dumps(result, indent=2)


@tool
async def unity_create_prefab(game_object: str, save_path: str) -> str:
    """Create a prefab from an existing GameObject.

    Args:
        game_object: Name or path of the source GameObject
        save_path: Asset path to save the prefab (e.g. Assets/Prefabs/PFB_MyPrefab.prefab)
    """
    result = await mcp_unity.create_prefab(game_object, save_path)
    return json.dumps(result, indent=2)


@tool
async def unity_add_asset_to_scene(asset_path: str) -> str:
    """Instantiate an asset (prefab, model, etc.) into the active scene."""
    result = await mcp_unity.add_asset_to_scene(asset_path)
    return json.dumps(result, indent=2)


@tool
async def unity_set_transform(
    instance_id: int,
    position: str = "",
    rotation: str = "",
    scale: str = "",
) -> str:
    """Set the transform of a GameObject.

    Args:
        instance_id: Instance ID of the GameObject
        position: JSON string like {"x":0,"y":1,"z":0} (optional)
        rotation: JSON string like {"x":0,"y":90,"z":0} (optional)
        scale: JSON string like {"x":1,"y":1,"z":1} (optional)
    """
    pos = json.loads(position) if position else None
    rot = json.loads(rotation) if rotation else None
    scl = json.loads(scale) if scale else None
    result = await mcp_unity.set_transform(instance_id, pos, rot, scl)
    return json.dumps(result, indent=2)


# ── Editor / Build tools ────────────────────────────────────────────


@tool
async def unity_execute_menu_item(menu_path: str) -> str:
    """Execute a Unity Editor menu item by its path (e.g. 'File/Save')."""
    result = await mcp_unity.execute_menu_item(menu_path)
    return json.dumps(result, indent=2)


@tool
async def unity_recompile_scripts() -> str:
    """Force Unity to recompile all scripts."""
    result = await mcp_unity.recompile_scripts()
    return json.dumps(result, indent=2)


@tool
async def unity_get_console_logs(
    log_type: str = "All",
    limit: int = 50,
    include_stacktrace: bool = False,
) -> str:
    """Get Unity console logs. log_type: All, Error, Warning, Log."""
    result = await mcp_unity.get_console_logs(log_type, limit=limit, include_stacktrace=include_stacktrace)
    return json.dumps(result, indent=2)


@tool
async def unity_run_tests(test_mode: str = "EditMode", name_filter: str = "") -> str:
    """Run Unity Test Runner tests. test_mode: EditMode or PlayMode."""
    result = await mcp_unity.run_tests(test_mode, name_filter or None)
    return json.dumps(result, indent=2)


@tool
async def unity_add_package(package_id: str) -> str:
    """Install a Unity package by name (e.g. com.unity.inputsystem)."""
    result = await mcp_unity.add_package(package_id)
    return json.dumps(result, indent=2)


# ── Vision ───────────────────────────────────────────────────────────


@tool
async def unity_get_screenshot() -> str:
    """Capture a screenshot of the Unity Editor (returns base64 image)."""
    result = await mcp_unity.get_screenshot()
    return json.dumps(result, indent=2)


# ── Batch ────────────────────────────────────────────────────────────


@tool
async def unity_batch_execute(operations_json: str) -> str:
    """Execute multiple MCP operations atomically for 10-100× performance.

    Args:
        operations_json: JSON array of operations, each with 'method' and 'params' keys
    """
    operations = json.loads(operations_json)
    result = await mcp_unity.batch_execute(operations)
    return json.dumps(result, indent=2)


# ── Animation tools ──────────────────────────────────────────────────


@tool
async def unity_get_animator_controller(game_object: str) -> str:
    """Get the AnimatorController parameters and state machine info for a GameObject.

    Args:
        game_object: Name or path of the GameObject with an Animator component
    """
    result = await mcp_unity.get_animator_controller(game_object)
    return json.dumps(result, indent=2)


@tool
async def unity_set_animator_parameter(
    game_object: str,
    param_name: str,
    value: str,
) -> str:
    """Set an Animator parameter (float, int, bool, or trigger).

    Args:
        game_object: Name or path of the GameObject with an Animator
        param_name: Name of the parameter to set
        value: Value to set (will be auto-parsed to correct type)
    """
    # Try to parse value to appropriate type
    parsed_value: Any = value
    if value.lower() == "true":
        parsed_value = True
    elif value.lower() == "false":
        parsed_value = False
    elif value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        parsed_value = int(value)
    else:
        try:
            parsed_value = float(value)
        except ValueError:
            pass  # Keep as string

    result = await mcp_unity.set_animator_parameter(game_object, param_name, parsed_value)
    return json.dumps(result, indent=2)


@tool
async def unity_create_animation_clip(name: str, save_path: str, properties_json: str) -> str:
    """Create a new AnimationClip asset.

    Args:
        name: Clip name
        save_path: Asset path (e.g. Assets/Animations/ANIM_Idle.anim)
        properties_json: JSON string with animation curves data
    """
    properties = json.loads(properties_json)
    result = await mcp_unity.create_animation_clip(name, save_path, properties)
    return json.dumps(result, indent=2)


@tool
async def unity_add_animation_event(
    clip_path: str,
    time: float,
    function_name: str,
    string_param: str = "",
    float_param: float = 0.0,
    int_param: int = 0,
) -> str:
    """Add an AnimationEvent to a clip at a specific time.

    Args:
        clip_path: Path to the AnimationClip asset
        time: Time in seconds when the event triggers
        function_name: Name of the function to call on the GameObject
        string_param: String parameter for the event
        float_param: Float parameter for the event
        int_param: Int parameter for the event
    """
    result = await mcp_unity.add_animation_event(
        clip_path, time, function_name, string_param, float_param, int_param
    )
    return json.dumps(result, indent=2)


@tool
async def unity_set_animator_state(game_object: str, state_name: str, layer: str = "") -> str:
    """Force an Animator to transition to a specific state.

    Args:
        game_object: Name or path of the GameObject with an Animator
        state_name: Name of the target state in the state machine
        layer: Optional layer name (uses base layer if empty)
    """
    result = await mcp_unity.set_animator_state(game_object, state_name, layer)
    return json.dumps(result, indent=2)


@tool
async def unity_get_animator_state(game_object: str) -> str:
    """Get current Animator state info (current state, parameters, transitions).

    Args:
        game_object: Name or path of the GameObject with an Animator
    """
    result = await mcp_unity.get_animator_state(game_object)
    return json.dumps(result, indent=2)


# ── NavMesh tools ────────────────────────────────────────────────────


@tool
async def unity_bake_navmesh() -> str:
    """Bake the NavMesh for the current scene. This rebuilds navigation data."""
    result = await mcp_unity.bake_navmesh()
    return json.dumps(result, indent=2)


@tool
async def unity_get_navmesh_info() -> str:
    """Get information about the baked NavMesh (areas, agents, links)."""
    result = await mcp_unity.get_navmesh_info()
    return json.dumps(result, indent=2)


@tool
async def unity_set_navmesh_area(
    area_index: int,
    name: str,
    cost: float = 1.0,
    walkable: bool = True,
) -> str:
    """Configure a NavMesh area.

    Args:
        area_index: Area index (0-31)
        name: Display name for the area
        cost: Movement cost multiplier
        walkable: Whether agents can walk on this area
    """
    result = await mcp_unity.set_navmesh_area(area_index, name, cost, walkable)
    return json.dumps(result, indent=2)


@tool
async def unity_create_navmesh_link(
    game_object: str,
    start_pos_json: str,
    end_pos_json: str,
    width: float = 1.0,
    bidirectional: bool = True,
) -> str:
    """Create a NavMeshLink between two positions.

    Args:
        game_object: Name or path for the NavMeshLink GameObject
        start_pos_json: JSON position {"x":0,"y":0,"z":0} for start
        end_pos_json: JSON position {"x":5,"y":0,"z":0} for end
        width: Width of the link
        bidirectional: Whether agents can traverse both directions
    """
    start_pos = json.loads(start_pos_json)
    end_pos = json.loads(end_pos_json)
    result = await mcp_unity.create_navmesh_link(game_object, start_pos, end_pos, width, bidirectional)
    return json.dumps(result, indent=2)


@tool
async def unity_set_navmesh_agent_properties(
    game_object: str,
    speed: str = "",
    angular_speed: str = "",
    acceleration: str = "",
    stopping_distance: str = "",
) -> str:
    """Configure NavMeshAgent properties on a GameObject.

    Args:
        game_object: Name or path of the GameObject with NavMeshAgent
        speed: Movement speed (leave empty to skip)
        angular_speed: Turning speed (leave empty to skip)
        acceleration: Acceleration (leave empty to skip)
        stopping_distance: Stopping distance (leave empty to skip)
    """
    kwargs: dict[str, Any] = {}
    if speed:
        kwargs["speed"] = float(speed)
    if angular_speed:
        kwargs["angular_speed"] = float(angular_speed)
    if acceleration:
        kwargs["acceleration"] = float(acceleration)
    if stopping_distance:
        kwargs["stopping_distance"] = float(stopping_distance)
    result = await mcp_unity.set_navmesh_agent_properties(game_object, **kwargs)
    return json.dumps(result, indent=2)


@tool
async def unity_set_navmesh_destination(game_object: str, destination_json: str) -> str:
    """Set a NavMeshAgent destination.

    Args:
        game_object: Name or path of the GameObject with NavMeshAgent
        destination_json: JSON position {"x":0,"y":0,"z":0} for destination
    """
    destination = json.loads(destination_json)
    result = await mcp_unity.set_navmesh_destination(game_object, destination)
    return json.dumps(result, indent=2)


# ── Audio tools ──────────────────────────────────────────────────────


@tool
async def unity_create_audio_source(
    game_object: str,
    clip_path: str = "",
    volume: float = 1.0,
    pitch: float = 1.0,
    loop: bool = False,
    play_on_awake: bool = False,
    spatial_blend: float = 1.0,
) -> str:
    """Add and configure an AudioSource component on a GameObject.

    Args:
        game_object: Target GameObject name or path
        clip_path: Path to the AudioClip asset (optional)
        volume: Volume (0-1)
        pitch: Pitch multiplier
        loop: Whether to loop playback
        play_on_awake: Whether to play automatically on spawn
        spatial_blend: 0=2D, 1=3D
    """
    result = await mcp_unity.create_audio_source(
        game_object, clip_path, volume, pitch, loop, play_on_awake, spatial_blend
    )
    return json.dumps(result, indent=2)


@tool
async def unity_modify_audio_source(game_object: str, properties_json: str) -> str:
    """Modify AudioSource properties (volume, pitch, clip, etc.).

    Args:
        game_object: Name or path of the GameObject with AudioSource
        properties_json: JSON string with properties to update
    """
    properties = json.loads(properties_json)
    result = await mcp_unity.modify_audio_source(game_object, properties)
    return json.dumps(result, indent=2)


@tool
async def unity_play_audio(game_object: str) -> str:
    """Play the AudioSource on a GameObject.

    Args:
        game_object: Name or path of the GameObject with AudioSource
    """
    result = await mcp_unity.play_audio(game_object)
    return json.dumps(result, indent=2)


@tool
async def unity_stop_audio(game_object: str) -> str:
    """Stop the AudioSource on a GameObject.

    Args:
        game_object: Name or path of the GameObject with AudioSource
    """
    result = await mcp_unity.stop_audio(game_object)
    return json.dumps(result, indent=2)


@tool
async def unity_get_audio_mixer_info(mixer_path: str = "") -> str:
    """Get AudioMixer info (groups, snapshots, parameters).

    Args:
        mixer_path: Path to the AudioMixer asset (optional, lists all if empty)
    """
    result = await mcp_unity.get_audio_mixer_info(mixer_path)
    return json.dumps(result, indent=2)


@tool
async def unity_set_audio_mixer_snapshot(
    mixer_path: str,
    snapshot_name: str,
    transition_time: float = 0.5,
) -> str:
    """Transition to an AudioMixer snapshot.

    Args:
        mixer_path: Path to the AudioMixer asset
        snapshot_name: Name of the target snapshot
        transition_time: Transition duration in seconds
    """
    result = await mcp_unity.set_audio_mixer_snapshot(mixer_path, snapshot_name, transition_time)
    return json.dumps(result, indent=2)


# ── ScriptableObject tools ───────────────────────────────────────────


@tool
async def unity_create_scriptable_object(
    type_name: str,
    save_path: str,
    json_data: str,
) -> str:
    """Create a new ScriptableObject asset.

    Args:
        type_name: Full C# type name (e.g. WeaponStats, EnemyConfig)
        save_path: Asset path (e.g. Assets/Data/SO_MyData.asset)
        json_data: JSON string with the SO field values
    """
    result = await mcp_unity.create_scriptable_object(type_name, save_path, json_data)
    return json.dumps(result, indent=2)


@tool
async def unity_modify_scriptable_object(asset_path: str, json_data: str) -> str:
    """Modify an existing ScriptableObject asset.

    Args:
        asset_path: Path to the .asset file
        json_data: JSON string with updated field values
    """
    result = await mcp_unity.modify_scriptable_object(asset_path, json_data)
    return json.dumps(result, indent=2)


@tool
async def unity_get_scriptable_object(asset_path: str) -> str:
    """Get the current values of a ScriptableObject asset.

    Args:
        asset_path: Path to the .asset file
    """
    result = await mcp_unity.get_scriptable_object(asset_path)
    return json.dumps(result, indent=2)


@tool
async def unity_list_scriptable_objects(type_filter: str = "") -> str:
    """List all ScriptableObject assets in the project, optionally filtered by type.

    Args:
        type_filter: Optional type name to filter by (e.g. WeaponStats)
    """
    result = await mcp_unity.list_scriptable_objects(type_filter)
    return json.dumps(result, indent=2)


# ── VFX / Particle System tools ──────────────────────────────────────


@tool
async def unity_create_particle_system(
    game_object: str,
    preset: str = "default",
    duration: float = 5.0,
    loop: bool = True,
    start_lifetime: float = 1.0,
    start_speed: float = 5.0,
    start_size: float = 1.0,
    max_particles: int = 1000,
) -> str:
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
    result = await mcp_unity.create_particle_system(
        game_object, preset, duration, loop, start_lifetime, start_speed, start_size, max_particles
    )
    return json.dumps(result, indent=2)


@tool
async def unity_modify_particle_system(game_object: str, properties_json: str) -> str:
    """Modify ParticleSystem properties.

    Args:
        game_object: Name or path of the GameObject with ParticleSystem
        properties_json: JSON string with properties to update
    """
    properties = json.loads(properties_json)
    result = await mcp_unity.modify_particle_system(game_object, properties)
    return json.dumps(result, indent=2)


@tool
async def unity_play_particle_system(game_object: str, with_children: bool = True) -> str:
    """Play a ParticleSystem.

    Args:
        game_object: Name or path of the GameObject with ParticleSystem
        with_children: Whether to also play child particle systems
    """
    result = await mcp_unity.play_particle_system(game_object, with_children)
    return json.dumps(result, indent=2)


@tool
async def unity_stop_particle_system(
    game_object: str,
    stop_behavior: str = "StopEmitting",
) -> str:
    """Stop a ParticleSystem.

    Args:
        game_object: Name or path of the GameObject with ParticleSystem
        stop_behavior: StopEmitting, StopEmittingAndClear, or StopEmittingAndSimulate
    """
    result = await mcp_unity.stop_particle_system(game_object, stop_behavior)
    return json.dumps(result, indent=2)


# ── Terrain tools ────────────────────────────────────────────────────


@tool
async def unity_create_terrain(
    size_json: str = "",
    position_json: str = "",
    heightmap_resolution: int = 513,
) -> str:
    """Create a new Terrain in the scene.

    Args:
        size_json: Terrain size as JSON {"x":1000,"y":600,"z":1000} (optional)
        position_json: World position as JSON {"x":0,"y":0,"z":0} (optional)
        heightmap_resolution: Resolution of the heightmap (default 513)
    """
    size = json.loads(size_json) if size_json else None
    position = json.loads(position_json) if position_json else None
    result = await mcp_unity.create_terrain(size, position, heightmap_resolution)
    return json.dumps(result, indent=2)


@tool
async def unity_modify_terrain_height(
    terrain_path: str,
    heights_json: str,
    x_base: int = 0,
    y_base: int = 0,
) -> str:
    """Modify terrain heightmap data.

    Args:
        terrain_path: Path or name of the terrain
        heights_json: JSON 2D array of height values (0.0 - 1.0 normalized)
        x_base: X offset in the heightmap
        y_base: Y offset in the heightmap
    """
    heights = json.loads(heights_json)
    result = await mcp_unity.modify_terrain_height(terrain_path, heights, x_base, y_base)
    return json.dumps(result, indent=2)


@tool
async def unity_paint_terrain_texture(
    terrain_path: str,
    texture_index: int,
    alpha_map_json: str,
    x_base: int = 0,
    y_base: int = 0,
) -> str:
    """Paint terrain textures using alpha map data.

    Args:
        terrain_path: Path or name of the terrain
        texture_index: Index of the terrain layer to paint
        alpha_map_json: JSON 3D array [y][x][layer] of alpha values (0.0 - 1.0)
        x_base: X offset in the alpha map
        y_base: Y offset in the alpha map
    """
    alpha_map = json.loads(alpha_map_json)
    result = await mcp_unity.paint_terrain_texture(terrain_path, texture_index, alpha_map, x_base, y_base)
    return json.dumps(result, indent=2)


@tool
async def unity_add_terrain_layer(
    terrain_path: str,
    diffuse_texture: str,
    normal_map: str = "",
    tile_size_json: str = "",
    metallic: float = 0.0,
    smoothness: float = 0.5,
) -> str:
    """Add a texture layer to a terrain.

    Args:
        terrain_path: Path or name of the terrain
        diffuse_texture: Path to the diffuse texture asset
        normal_map: Path to the normal map asset (optional)
        tile_size_json: Tiling as JSON {"x":15,"y":15} (optional)
        metallic: Metallic value (0-1)
        smoothness: Smoothness value (0-1)
    """
    tile_size = json.loads(tile_size_json) if tile_size_json else None
    result = await mcp_unity.add_terrain_layer(
        terrain_path, diffuse_texture, normal_map, tile_size, metallic, smoothness
    )
    return json.dumps(result, indent=2)


@tool
async def unity_get_terrain_info(terrain_path: str) -> str:
    """Get terrain information (size, resolution, layers, settings).

    Args:
        terrain_path: Path or name of the terrain
    """
    result = await mcp_unity.get_terrain_info(terrain_path)
    return json.dumps(result, indent=2)


# ── Physics & Layer tools ────────────────────────────────────────────


@tool
async def unity_set_physics_layer(
    layer_index: int,
    layer_name: str,
    collision_matrix_json: str = "",
) -> str:
    """Configure a physics layer name and collision matrix.

    Args:
        layer_index: Layer index (0-31)
        layer_name: Display name for the layer
        collision_matrix_json: Optional JSON collision matrix
    """
    collision_matrix = json.loads(collision_matrix_json) if collision_matrix_json else None
    result = await mcp_unity.set_physics_layer(layer_index, layer_name, collision_matrix)
    return json.dumps(result, indent=2)


@tool
async def unity_get_physics_layer_matrix() -> str:
    """Get the full physics layer collision matrix."""
    result = await mcp_unity.get_physics_layer_matrix()
    return json.dumps(result, indent=2)


@tool
async def unity_set_layer_collision(layer1: int, layer2: int, ignore: bool) -> str:
    """Set collision between two layers (ignore or not).

    Args:
        layer1: First layer index
        layer2: Second layer index
        ignore: True to ignore collisions, False to enable them
    """
    result = await mcp_unity.set_layer_collision(layer1, layer2, ignore)
    return json.dumps(result, indent=2)


@tool
async def unity_set_physics_settings(
    gravity_json: str = "",
    fixed_timestep: str = "",
    default_contact_offset: str = "",
    bounce_threshold: str = "",
) -> str:
    """Configure global physics settings.

    Args:
        gravity_json: Gravity vector as JSON {"x":0,"y":-9.81,"z":0} (optional)
        fixed_timestep: Fixed timestep value (optional)
        default_contact_offset: Contact offset (optional)
        bounce_threshold: Bounce threshold (optional)
    """
    kwargs: dict[str, Any] = {}
    if gravity_json:
        kwargs["gravity"] = json.loads(gravity_json)
    if fixed_timestep:
        kwargs["fixed_timestep"] = float(fixed_timestep)
    if default_contact_offset:
        kwargs["default_contact_offset"] = float(default_contact_offset)
    if bounce_threshold:
        kwargs["bounce_threshold"] = float(bounce_threshold)
    result = await mcp_unity.set_physics_settings(**kwargs)
    return json.dumps(result, indent=2)


# ── Tag tools ────────────────────────────────────────────────────────


@tool
async def unity_get_all_tags() -> str:
    """Get all tags defined in the project."""
    result = await mcp_unity.get_all_tags()
    return json.dumps(result, indent=2)


@tool
async def unity_add_tag(tag_name: str) -> str:
    """Add a new tag to the project.

    Args:
        tag_name: Name of the new tag (e.g. Enemy, Pickup, Cover)
    """
    result = await mcp_unity.add_tag(tag_name)
    return json.dumps(result, indent=2)


@tool
async def unity_remove_tag(tag_name: str) -> str:
    """Remove a tag from the project.

    Args:
        tag_name: Name of the tag to remove
    """
    result = await mcp_unity.remove_tag(tag_name)
    return json.dumps(result, indent=2)


# ── Lighting tools ───────────────────────────────────────────────────


@tool
async def unity_get_lighting_settings() -> str:
    """Get current lighting settings (ambient, fog, reflection, GI)."""
    result = await mcp_unity.get_lighting_settings()
    return json.dumps(result, indent=2)


@tool
async def unity_set_lighting_settings(properties_json: str) -> str:
    """Configure lighting settings (ambient mode, fog, skybox, etc.).

    Args:
        properties_json: JSON string with lighting properties to update
    """
    properties = json.loads(properties_json)
    result = await mcp_unity.set_lighting_settings(properties)
    return json.dumps(result, indent=2)


@tool
async def unity_bake_lighting(mode: str = "ProgressiveGPU") -> str:
    """Start lighting bake.

    Args:
        mode: Bake mode (ProgressiveGPU, ProgressiveCPU, Enlighten)
    """
    result = await mcp_unity.bake_lighting(mode)
    return json.dumps(result, indent=2)


@tool
async def unity_get_lighting_bake_status() -> str:
    """Get the current status of a lighting bake operation."""
    result = await mcp_unity.get_lighting_bake_status()
    return json.dumps(result, indent=2)


@tool
async def unity_create_light_probe_group(
    position_json: str = "",
    resolution_x: int = 3,
    resolution_y: int = 3,
    resolution_z: int = 3,
) -> str:
    """Create a LightProbeGroup at the specified position.

    Args:
        position_json: World position as JSON {"x":0,"y":0,"z":0} (optional)
        resolution_x: Number of probes along X
        resolution_y: Number of probes along Y
        resolution_z: Number of probes along Z
    """
    position = json.loads(position_json) if position_json else None
    result = await mcp_unity.create_light_probe_group(position, resolution_x, resolution_y, resolution_z)
    return json.dumps(result, indent=2)


@tool
async def unity_create_reflection_probe(
    position_json: str = "",
    box_size_json: str = "",
    importance: int = 1,
) -> str:
    """Create a ReflectionProbe at the specified position.

    Args:
        position_json: World position as JSON {"x":0,"y":0,"z":0} (optional)
        box_size_json: Box size as JSON {"x":10,"y":10,"z":10} (optional)
        importance: Render priority (higher = more important)
    """
    position = json.loads(position_json) if position_json else None
    box_size = json.loads(box_size_json) if box_size_json else None
    result = await mcp_unity.create_reflection_probe(position, box_size, importance)
    return json.dumps(result, indent=2)


# ── Render & Quality tools ───────────────────────────────────────────


@tool
async def unity_set_render_settings(properties_json: str) -> str:
    """Configure render and environment settings (ambient, fog, skybox).

    Args:
        properties_json: JSON string with render settings to update
    """
    properties = json.loads(properties_json)
    result = await mcp_unity.set_render_settings(**properties)
    return json.dumps(result, indent=2)


@tool
async def unity_set_quality_settings(properties_json: str) -> str:
    """Configure quality settings (AA, shadows, VSync).

    Args:
        properties_json: JSON string with quality settings to update
    """
    properties = json.loads(properties_json)
    result = await mcp_unity.set_quality_settings(**properties)
    return json.dumps(result, indent=2)


# ── Project Settings tools ───────────────────────────────────────────


@tool
async def unity_get_project_settings(category: str = "all") -> str:
    """Get project settings.

    Args:
        category: Settings category (all, player, input, physics, time, graphics, quality, audio, tags)
    """
    result = await mcp_unity.get_project_settings(category)
    return json.dumps(result, indent=2)


@tool
async def unity_set_project_settings(category: str, settings_json: str) -> str:
    """Set project settings for a specific category.

    Args:
        category: Settings category
        settings_json: JSON string with settings to update
    """
    settings_data = json.loads(settings_json)
    result = await mcp_unity.set_project_settings(category, settings_data)
    return json.dumps(result, indent=2)


# ── Asset Management tools ───────────────────────────────────────────


@tool
async def unity_import_asset(source_path: str, destination: str = "") -> str:
    """Import an external asset into the Unity project.

    Args:
        source_path: Local file path on the machine running Unity
        destination: Asset path in the project (e.g. Assets/Textures/)
    """
    result = await mcp_unity.import_asset(source_path, destination)
    return json.dumps(result, indent=2)


@tool
async def unity_export_asset(asset_path: str, export_path: str) -> str:
    """Export a Unity asset to an external file.

    Args:
        asset_path: Asset path in the project
        export_path: Destination file path
    """
    result = await mcp_unity.export_asset(asset_path, export_path)
    return json.dumps(result, indent=2)


@tool
async def unity_list_assets(
    folder: str = "Assets",
    file_extension: str = "",
    recursive: bool = True,
) -> str:
    """List assets in a project folder, optionally filtered by extension.

    Args:
        folder: Folder to list (default: Assets)
        file_extension: Filter by extension (e.g. .cs, .prefab, .shader)
        recursive: Whether to search subdirectories
    """
    result = await mcp_unity.list_assets(folder, file_extension, recursive)
    return json.dumps(result, indent=2)


@tool
async def unity_delete_asset(asset_path: str) -> str:
    """Delete an asset from the project.

    Args:
        asset_path: Path to the asset to delete
    """
    result = await mcp_unity.delete_asset(asset_path)
    return json.dumps(result, indent=2)


@tool
async def unity_move_asset(source_path: str, destination_path: str) -> str:
    """Move/rename an asset in the project.

    Args:
        source_path: Current asset path
        destination_path: New asset path
    """
    result = await mcp_unity.move_asset(source_path, destination_path)
    return json.dumps(result, indent=2)


@tool
async def unity_create_folder(folder_path: str) -> str:
    """Create a new folder in the project.

    Args:
        folder_path: Folder path (e.g. Assets/Scripts/AI)
    """
    result = await mcp_unity.create_folder(folder_path)
    return json.dumps(result, indent=2)


# ── Build Settings tools ─────────────────────────────────────────────


@tool
async def unity_get_build_settings() -> str:
    """Get current Build Settings (scenes, platform, options)."""
    result = await mcp_unity.get_build_settings()
    return json.dumps(result, indent=2)


@tool
async def unity_add_scene_to_build(scene_path: str, enabled: bool = True) -> str:
    """Add a scene to the Build Settings scene list.

    Args:
        scene_path: Path to the scene (e.g. Assets/Scenes/MainMenu.unity)
        enabled: Whether the scene is included in the build
    """
    result = await mcp_unity.add_scene_to_build(scene_path, enabled)
    return json.dumps(result, indent=2)


@tool
async def unity_set_active_build_target(platform: str, sub_target: str = "") -> str:
    """Switch the active build target.

    Args:
        platform: Target platform (StandaloneWindows64, Android, iOS, WebGL, PS5, XboxSeriesX)
        sub_target: Optional sub-target
    """
    result = await mcp_unity.set_active_build_target(platform, sub_target)
    return json.dumps(result, indent=2)


# ── Tool groups for agents ───────────────────────────────────────────

CODE_TOOLS = [
    unity_list_scripts,
    unity_get_script,
    unity_apply_patch,
    unity_create_script,
    unity_recompile_scripts,
    unity_get_console_logs,
    unity_list_assets,
    unity_delete_asset,
    unity_move_asset,
    unity_create_folder,
]

SCENE_TOOLS = [
    unity_get_scene_info,
    unity_load_scene,
    unity_get_gameobject,
    unity_update_gameobject,
    unity_update_component,
    unity_delete_gameobject,
    unity_duplicate_gameobject,
    unity_reparent_gameobject,
    unity_create_material,
    unity_assign_material,
    unity_modify_material,
    unity_get_material_info,
    unity_create_prefab,
    unity_add_asset_to_scene,
    unity_set_transform,
    unity_execute_menu_item,
    unity_batch_execute,
    # NavMesh
    unity_bake_navmesh,
    unity_get_navmesh_info,
    unity_set_navmesh_area,
    unity_create_navmesh_link,
    unity_set_navmesh_agent_properties,
    unity_set_navmesh_destination,
    # Terrain
    unity_create_terrain,
    unity_modify_terrain_height,
    unity_paint_terrain_texture,
    unity_add_terrain_layer,
    unity_get_terrain_info,
    # Lighting
    unity_get_lighting_settings,
    unity_set_lighting_settings,
    unity_bake_lighting,
    unity_create_light_probe_group,
    unity_create_reflection_probe,
    # VFX
    unity_create_particle_system,
    unity_modify_particle_system,
    unity_play_particle_system,
    unity_stop_particle_system,
    # Physics
    unity_set_physics_layer,
    unity_get_physics_layer_matrix,
    unity_set_layer_collision,
    unity_set_physics_settings,
    # Tags
    unity_get_all_tags,
    unity_add_tag,
    unity_remove_tag,
    # Render
    unity_set_render_settings,
    unity_set_quality_settings,
    # Assets
    unity_list_assets,
    unity_create_folder,
    unity_import_asset,
    unity_export_asset,
    unity_delete_asset,
    unity_move_asset,
    # ScriptableObjects
    unity_create_scriptable_object,
    unity_modify_scriptable_object,
    unity_get_scriptable_object,
    unity_list_scriptable_objects,
    # Build
    unity_get_build_settings,
    unity_add_scene_to_build,
]

BUILD_TOOLS = [
    unity_run_tests,
    unity_get_console_logs,
    unity_send_console_log,
    unity_recompile_scripts,
    unity_add_package,
    unity_get_build_settings,
    unity_add_scene_to_build,
    unity_set_active_build_target,
    unity_get_project_settings,
    unity_set_project_settings,
]

VISION_TOOLS = [
    unity_get_screenshot,
]

ANIMATION_TOOLS = [
    unity_get_animator_controller,
    unity_set_animator_parameter,
    unity_create_animation_clip,
    unity_add_animation_event,
    unity_set_animator_state,
    unity_get_animator_state,
]

AUDIO_TOOLS = [
    unity_create_audio_source,
    unity_modify_audio_source,
    unity_play_audio,
    unity_stop_audio,
    unity_get_audio_mixer_info,
    unity_set_audio_mixer_snapshot,
]

# Deduplicate by tool name, preserving order
_seen: set[str] = set()
ALL_TOOLS = []
for _group in [CODE_TOOLS, SCENE_TOOLS, BUILD_TOOLS, VISION_TOOLS, ANIMATION_TOOLS, AUDIO_TOOLS]:
    for _t in _group:
        if _t.name not in _seen:
            _seen.add(_t.name)
            ALL_TOOLS.append(_t)
