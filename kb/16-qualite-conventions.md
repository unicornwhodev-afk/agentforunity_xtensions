# 16. Règles de Qualité & Conventions

## 16.1 Règles de Code C#

- Toujours utiliser des namespaces : `namespace ProjectName.SystemName { }`
- Régions pour organiser les gros scripts : `#region Variables`, `#region Unity Callbacks`, `#region Public Methods`, `#region Private Methods`
- Documentation XML sur toutes les méthodes publiques : `/// <summary>`
- `[Header("Section")]` et `[Tooltip("Description")]` sur tous les champs exposés dans l'inspecteur
- `[SerializeField] private` au lieu de `public` pour l'encapsulation
- Pas de magic numbers : utiliser des constantes ou des ScriptableObjects
- Observer pattern via EventBus pour la communication inter-systèmes
- Object Pooling pour tout objet instancié fréquemment (projectiles, VFX, ennemis)
- Coroutines pour les séquences temporelles, async/await pour le I/O
- Jamais de `Find()`, `FindObjectOfType()` en runtime : utiliser DI ou ServiceLocator

## 16.2 Règles de Performance

| **Règle** | **Impact** | **Solution** |
| --- | --- | --- |
| Pas d'allocation dans Update/FixedUpdate | GC spikes | Cache des références, struct, NativeArrays |
| Object Pooling obligatoire | GC + instanciation | Pool générique avec warm-up |
| LOD sur tous les meshes | Draw calls, vertices | 3 niveaux minimum + cull |
| Occlusion Culling activé | Overdraw | Bake en pré-production |
| Batching SRP | Draw calls | SRP Batcher compatible shaders |
| Physics layers séparés | Collision checks | Matrix définie dans KB |
| Texture streaming | VRAM | Mipmap streaming activé |
| Audio compression | Mémoire | Vorbis pour musique, ADPCM pour SFX |

## 16.3 Matrice de Collision (Physics Layers)

| **Layer** | **Index** | **Collide avec** |
| --- | --- | --- |
| Default | 0 | Tout |
| Player | 8 | Default, Enemy, Projectile, Pickup, Trigger |
| Enemy | 9 | Default, Player, PlayerProjectile, Trigger |
| PlayerProjectile | 10 | Default, Enemy, Destructible |
| EnemyProjectile | 11 | Default, Player, Destructible |
| Pickup | 12 | Player uniquement |
| Trigger | 13 | Player, Enemy |
| Destructible | 14 | Tous les projectiles, Default |
| IgnoreRaycast | 2 | Rien (helpers visuels) |
| NavMeshObstacle | 15 | NavMesh system uniquement |
