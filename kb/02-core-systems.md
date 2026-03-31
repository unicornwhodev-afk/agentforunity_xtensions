# 2. Base de Connaissances — Core Systems

## 2.1 Structure des Fichiers de Connaissances

Chaque fichier de la KB suit un format standardisé : **Métadonnées YAML** en en-tête, **contenu technique** en corps, et **exemples de code** validés.

### 2.1.1 Arborescence de la Knowledge Base

| **Chemin** | **Contenu** | **Format** |
| --- | --- | --- |
| /kb/core/unity-conventions.md | Règles de nommage, structure projet, best practices | Markdown |
| /kb/core/csharp-patterns.md | Design patterns Unity : Singleton, Observer, Command, State | Markdown |
| /kb/core/performance-rules.md | Règles d'optimisation : pooling, batching, LOD, culling | Markdown |
| /kb/core/physics-config.md | Configuration Rigidbody, colliders, layers, Physics Matrix | YAML+MD |
| /kb/core/input-system.md | New Input System : Actions Maps, Bindings, Processeurs | Markdown |
| /kb/core/project-structure.md | Arborescence type d'un projet FPS Unity | YAML |
| /kb/core/scriptable-objects.md | Catalogue de SO : armes, ennemis, items, niveaux | Markdown |
| /kb/core/event-bus.md | Système d'événements global : GameEvents, channels | Markdown |
| /kb/core/save-system.md | Serialisation JSON/Binary, PlayerPrefs, slots de sauvegarde | Markdown |
| /kb/core/networking-basics.md | Netcode for GameObjects, synchronisation, RPCs | Markdown |

## 2.2 Règles Fondamentales du Projet

### Conventions de Nommage

| **Élément** | **Convention** | **Exemple** |
| --- | --- | --- |
| Scripts C# | PascalCase | PlayerController.cs |
| Variables privées | _camelCase avec préfixe | _currentHealth |
| Variables publiques | camelCase | moveSpeed |
| Constantes | UPPER_SNAKE_CASE | MAX_HEALTH |
| Prefabs | PFB_PascalCase | PFB_EnemySoldier |
| Materials | MAT_PascalCase | MAT_MetalFloor |
| Textures | TEX_PascalCase_type | TEX_Wall_Normal |
| Animations | ANIM_Action_State | ANIM_Rifle_Reload |
| ScriptableObjects | SO_PascalCase | SO_AK47_Data |
| Scènes | SCN_PascalCase | SCN_Level01_Factory |
| Audio Clips | SFX_/MUS_ + nom | SFX_Gunshot_Rifle |
| Layers | PascalCase | PlayerProjectile |
| Tags | PascalCase | EnemyAI |

### Structure Projet Type

| **Dossier** | **Contenu** |
| --- | --- |
| Assets/_Project/Scripts/ | Tous les scripts C# organisés par système |
| Assets/_Project/Scripts/Player/ | Controller, Camera, Input, Interaction |
| Assets/_Project/Scripts/AI/ | BehaviourTree, GOAP, Sensors, Navigation |
| Assets/_Project/Scripts/Combat/ | WeaponSystem, DamageSystem, Projectiles, Hitboxes |
| Assets/_Project/Scripts/Economy/ | Inventory, Shop, Currency, Loot Tables |
| Assets/_Project/Scripts/UI/ | HUD, Menus, Widgets, Notifications |
| Assets/_Project/Scripts/MapBuilder/ | GridSystem, PrefabPlacer, RoomGenerator |
| Assets/_Project/Scripts/Core/ | GameManager, EventBus, SaveSystem, ObjectPool |
| Assets/_Project/Prefabs/ | Prefabs organisés par catégorie |
| Assets/_Project/ScriptableObjects/ | SO de configuration (armes, stats, waves…) |
| Assets/_Project/Art/ | Textures, Materials, Models, Sprites |
| Assets/_Project/Audio/ | SFX, Music, Mixers, Snapshots |
| Assets/_Project/Scenes/ | Scènes de jeu et scènes d'édition |
| Assets/_Project/Animations/ | Controllers, Clips, Avatar Masks |
| Assets/_Project/Settings/ | Render Pipeline, Quality, Input Actions |
