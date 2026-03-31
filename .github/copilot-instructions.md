## Project: AgentUnity — Medieval Fantasy-Horror FPS

This is a Unity game development project using a multi-agent AI system deployed on RunPod.

### Architecture

- **Game Engine**: Unity 2021.3+
- **Language**: C# (Unity scripting)
- **AI Backend**: RunPod GPU pod with LangGraph orchestrator, vLLM, RAG pipeline
- **MCP-Unity**: WebSocket bridge between VS Code / AI agents and Unity Editor
- **Connection**: cloudflared tunnel (local→pod for MCP) + RunPod proxy (user→pod for API)

### Code Conventions

- **Namespaces**: `namespace ProjectName.SystemName { }` on every script
- **Encapsulation**: `[SerializeField] private` — never expose `public` fields
- **Inspector**: `[Header("Section")]` + `[Tooltip("Description")]` on all serialized fields
- **Documentation**: XML `/// <summary>` on all public methods
- **Regions**: `#region Variables`, `#region Unity Callbacks`, `#region Public Methods`, `#region Private Methods`
- **No magic numbers**: Use `const`, `static readonly`, or ScriptableObjects
- **Communication**: EventBus / Observer pattern — never direct coupling between systems
- **Pooling**: Object Pool for all frequently spawned objects (projectiles, VFX, enemies)
- **Forbidden**: `Find()`, `FindObjectOfType()` at runtime — use DI or ServiceLocator
- **Coroutines** for temporal sequences, **async/await** for I/O only

### Performance Rules

- Zero allocations in `Update()` / `FixedUpdate()` — cache all references
- 3-level LOD minimum on all meshes
- Occlusion Culling baked in pre-production
- SRP Batcher compatible shaders only
- Audio: Vorbis for music, ADPCM for SFX
- Texture streaming enabled with mipmap streaming

### Physics Layer Matrix

| Layer | Index | Collides With |
|-------|-------|---------------|
| Player | 8 | Default, Enemy, Projectile, Pickup, Trigger |
| Enemy | 9 | Default, Player, PlayerProjectile, Trigger |
| PlayerProjectile | 10 | Default, Enemy, Destructible |
| EnemyProjectile | 11 | Default, Player, Destructible |
| Pickup | 12 | Player only |
| Trigger | 13 | Player, Enemy |
| Destructible | 14 | All projectiles, Default |

### Available Tools

When working on this project, the `@agentunity` agent has access to MCP-Unity tools for direct Unity Editor manipulation (scene inspection, object creation, material editing, script management, build/test).
