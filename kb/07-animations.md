# 7. Système d'Animations

## 7.1 Animator Controller Structure

| **Layer** | **Rôle** | **Weight / Masque** |
| --- | --- | --- |
| Base Layer | Locomotion : Idle, Walk, Run, Sprint, Crouch, Slide | 1.0 / Full Body |
| Upper Body | Armes : Idle, ADS, Fire, Reload, Switch, Melee | 1.0 / Upper Body Mask |
| Additive Layer | Breathing, Recoil visual, Hit reactions | 0.3-0.7 / Additive Blend |
| IK Layer | Procedural IK pour mains, pieds, regard | 1.0 / IK Pass enabled |
| Override Layer | Death, Victory, Emotes (override tout) | 1.0 / Full Body Override |

## 7.2 Catalogue d'Animations Requises

| **Catégorie** | **Animations** | **Blend Tree** |
| --- | --- | --- |
| Locomotion | Idle, Walk (4 dir), Run (4 dir), Sprint, Crouch Idle, Crouch Walk | 2D Freeform Directional |
| Armes | Idle, ADS Enter/Exit, Fire, Reload, Switch, Inspect, Empty Click | Direct / 1D |
| Combat CaC | Swing L/R, Stab, Block, Block Hit, Combo 1-2-3 | 1D |
| Grenades | Pull Pin, Throw Overhand, Throw Underhand | Direct |
| Interactions | Use, Pickup, Open Door, Push Button, Ladder Climb | Direct |
| Dommages | Hit Front/Back/Left/Right, Stagger, Knockback | Direct |
| Mort | Death Forward, Backward, Left, Right, Headshot, Explosion | Direct |
| Spéciales | Wall Run, Slide, Ledge Grab, Mantle, Jump, Land Soft/Hard | Direct |

## 7.3 Règles d'Animation KB

- Utiliser des Animation Events pour les moments clés (son de pas, éjection de douille, fin de reload)
- Root Motion désactivé pour le joueur FPS (contrôlé par le CharacterController)
- Root Motion activé pour les ennemis mêlée (meilleur blend mouvement/attaque)
- Procedural IK pour les mains sur l'arme (Two-Bone IK Constraint via Animation Rigging)
- Foot IK pour adaptation au terrain (raycasts pieds + solver IK)
- Blend Trees 2D pour la locomotion directionnelle (Freeform Directional)
- Transitions courtes (0.1-0.15s) pour la réactivité, sauf mort et emotes (0.25s)
- Toujours prévoir des clips de fallback pour éviter les T-pose en cas de state manquant
