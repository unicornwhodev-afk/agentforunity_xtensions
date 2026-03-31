# 3. Scripts Library — Répertoire Complet

## 3.1 Catalogue des Scripts par Système

Chaque script référencé est accompagné de sa description, de ses dépendances et de son niveau de complexité. L'agent peut générer, modifier ou analyser chacun de ces scripts.

### 3.1.1 Core / Infrastructure

| **Script** | **Rôle** | **Complexité** |
| --- | --- | --- |
| GameManager.cs | Singleton global : game states (Menu, Play, Pause, GameOver), scène loading | ★★★ |
| EventBus.cs | Système d'événements découplé avec génériques typés | ★★★ |
| ObjectPoolManager.cs | Pool générique pour projectiles, VFX, ennemis, débris | ★★★ |
| SaveManager.cs | Sérialisation/Désérialisation JSON + encryption optionnelle | ★★★ |
| AudioManager.cs | Gestion mixeurs, groupes, transitions, musique adaptative | ★★ |
| SceneLoader.cs | Chargement async, loading screen, transition effects | ★★ |
| ServiceLocator.cs | Injection de dépendances légère pour accès aux managers | ★★ |
| TimeManager.cs | Slow-motion, pause, timestep custom, cooldown registry | ★★ |

### 3.1.2 Player Systems

| **Script** | **Rôle** | **Complexité** |
| --- | --- | --- |
| FPSController.cs | CharacterController + physique : walk, run, crouch, slide, wall-run, ledge grab | ★★★★★ |
| FPSCameraController.cs | Rotation caméra, recoil, sway, tilt, headbob, ADS zoom | ★★★★ |
| PlayerInputHandler.cs | Bridge New Input System → actions gameplay | ★★ |
| PlayerStats.cs | Santé, armure, stamina, XP, buffs/debuffs avec timers | ★★★ |
| PlayerInventory.cs | Slots d'inventaire, quick-swap armes, gestion munitions | ★★★ |
| PlayerInteraction.cs | Raycast interaction : portes, switches, pickups, NPCs | ★★ |
| FootstepSystem.cs | Détection surface (Physic Material) + audio contextuel | ★★ |
| PlayerRespawn.cs | Logique de mort, respawn, invulnérabilité temporaire | ★★ |

### 3.1.3 Système de Combat

| **Script** | **Rôle** | **Complexité** |
| --- | --- | --- |
| WeaponBase.cs | Classe abstraite : fire modes, recoil pattern, reload, ammo | ★★★★ |
| WeaponSway.cs | Sway procédural des armes (mouvement + inertie) | ★★★ |
| RecoilSystem.cs | Patterns de recul 2D/3D avec recovery curve | ★★★★ |
| ProjectileSystem.cs | Balles hitscan + physiques, ricochet, pénétration | ★★★★ |
| DamageSystem.cs | Calcul dégâts : zones (head/body/limbs), armure, distance falloff | ★★★ |
| HitboxManager.cs | Colliders par zone corporelle, hit registration | ★★★ |
| MeleeSystem.cs | Attaques CaC : swing, stab, combos, hit detection par overlap | ★★★ |
| GrenadeSystem.cs | Lancer, trajectoire, explosion AOE, fragmentation, flashbang | ★★★ |
| WeaponPickup.cs | Ramassage au sol, swap, drop avec physique | ★★ |
| BulletTracer.cs | VFX traceurs avec line renderer ou particules | ★★ |
| ImpactEffects.cs | VFX/SFX d'impact par matériau (métal, bois, chair…) | ★★ |
| KillFeedManager.cs | Affichage des éliminations en temps réel | ★★ |

### 3.1.4 Intelligence Artificielle

| **Script** | **Rôle** | **Complexité** |
| --- | --- | --- |
| AIBrain.cs | Orchestrateur IA : sélection de stratégie, mémoire, perception | ★★★★★ |
| BehaviourTreeRunner.cs | Exécuteur d'arbre de comportement avec Blackboard | ★★★★★ |
| GOAPPlanner.cs | Planificateur Goal-Oriented Action Planning | ★★★★★ |
| AISensor.cs | Vision (FOV cone), audition (bruit), alertes partagées | ★★★★ |
| AINavigator.cs | NavMesh + pathfinding avancé, cover points, flanking | ★★★★ |
| AICombatBehaviour.cs | Tir, rechargement, grenades, retraite, suppression | ★★★★ |
| AISquadManager.cs | Coordination d'équipe : formations, ordres, roles | ★★★★★ |
| AIStateManager.cs | FSM : Idle, Patrol, Alert, Engage, Flee, Search, Dead | ★★★ |
| CoverSystem.cs | Détection et évaluation des points de couverture | ★★★★ |
| TacticalPointSystem.cs | Scoring de positions tactiques (visibilité, distance, couverture) | ★★★★★ |
| AISpawner.cs | Spawning par waves, triggers de zone, budget de difficulté | ★★★ |
| AIDialogueAgent.cs | IA NPC : dialogue contextuel, barks, réactions | ★★ |

### 3.1.5 Économie & Inventaire

| **Script** | **Rôle** | **Complexité** |
| --- | --- | --- |
| InventorySystem.cs | Grid/slot inventory, stacking, poids, filtres catégorie | ★★★★ |
| ShopSystem.cs | Achat/vente, prix dynamiques, stock limité, réputation | ★★★ |
| CurrencyManager.cs | Multi-devises : crédits, tokens, monnaie premium | ★★ |
| LootTableManager.cs | Drop tables pondérées, rareté, guaranteed drops, pity system | ★★★★ |
| CraftingSystem.cs | Recettes, matériaux, progression de craft, découverte | ★★★ |
| ItemDatabase.cs | Catalogue ScriptableObject de tous les items du jeu | ★★ |
| QuestRewardSystem.cs | Distribution de récompenses liées aux quêtes/missions | ★★★ |
| TradeSystem.cs | Échange entre joueurs ou avec marchands NPC | ★★★ |

### 3.1.6 UI / HUD

| **Script** | **Rôle** | **Complexité** |
| --- | --- | --- |
| HUDManager.cs | Orchestrateur HUD : santé, ammo, minimap, crosshair, objectifs | ★★★ |
| CrosshairSystem.cs | Crosshair dynamique : spread, hit marker, kill confirm | ★★★ |
| DamageIndicator.cs | Indicateurs directionnels de dégâts reçus | ★★ |
| MinimapController.cs | Minimap temps réel : ennemis, objectifs, zones | ★★★ |
| HealthBarUI.cs | Barre de vie animée avec effet de retard (delayed damage) | ★★ |
| AmmoDisplay.cs | Affichage munitions : current/reserve, reload indicator | ★ |
| NotificationSystem.cs | Pop-ups, achievements, messages système | ★★ |
| MenuManager.cs | Navigation menus : principal, pause, settings, loadout | ★★★ |
| SettingsUI.cs | Options graphiques, audio, contrôles avec persistence | ★★★ |
| ScoreboardUI.cs | Tableau des scores multijoueur temps réel | ★★ |
| LoadoutUI.cs | Écran de sélection d'équipement et de classe | ★★★ |
| DialogueUI.cs | Système de dialogue avec choix, portraits, typing effect | ★★★ |

### 3.1.7 Map Builder & Level Design

| **Script** | **Rôle** | **Complexité** |
| --- | --- | --- |
| MapEditorCore.cs | Système d'édition de map : grid, placement, rotation, snap | ★★★★★ |
| PrefabPalette.cs | Catalogue de prefabs organisé par catégorie avec preview | ★★★ |
| GridSystem.cs | Grille 3D configurable : taille cellule, multi-étages, snapping | ★★★ |
| RoomGenerator.cs | Génération procédurale de salles avec contraintes | ★★★★ |
| ProceduralDungeon.cs | Algorithme BSP/Wave Function Collapse pour donjons | ★★★★★ |
| TerrainPainter.cs | Peinture de terrain : textures, végétation, détails | ★★★ |
| LightingSetup.cs | Placement auto d'éclairage : probes, baked, realtime | ★★★ |
| NavMeshBaker.cs | Bake NavMesh runtime, obstacles dynamiques, areas | ★★★ |
| SpawnPointEditor.cs | Placement et validation de points de spawn | ★★ |
| MapSerializer.cs | Sauvegarde/Chargement de maps custom (JSON/Binary) | ★★★ |
| PropDecorator.cs | Placement auto de props décoratifs selon règles contextuelles | ★★★ |
| ZoneManager.cs | Définition de zones : combat, safe, objective, restricted | ★★ |
