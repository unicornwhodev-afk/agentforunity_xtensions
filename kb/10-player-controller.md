# 10. Player Controller

## 10.1 Mouvements de Base

| **Action** | **Vitesse (m/s)** | **Conditions** | **Input** |
| --- | --- | --- | --- |
| Walk | 3.5 | Défaut, au sol | WASD / Left Stick |
| Run | 5.5 | Stamina > 0, au sol, avant uniquement | Shift (toggle/hold) |
| Sprint | 7.0 | Stamina > 20%, au sol, avant strict | Double Shift / L3 |
| Crouch Walk | 2.0 | Accroupi, au sol | Ctrl + WASD |
| Crouch Idle | 0 | Accroupi, immobile | Ctrl |
| Slide | 8.0 → 3.0 | Depuis sprint, durée 0.8s, cooldown 1.5s | Ctrl pendant Sprint |
| Jump | 5.0 (vert.) | Au sol, coyote time 0.15s | Space / A Button |
| Air Strafe | 1.5 (lat.) | En l'air, accélération réduite | WASD en l'air |
| Wall Run | 6.0 | Contact mur + vitesse > 4.0, durée max 1.5s | Vers le mur + avant |
| Ledge Grab | 0 → mantle | Bord détecté à portée + input vers le haut | Auto / Jump |
| Lean | 0 (statique) | Immobile ou crouch, angles 15° | Q/E |

## 10.2 Physique du Controller

| **Paramètre** | **Valeur** | **Notes** |
| --- | --- | --- |
| Gravity | -20 m/s² | Plus fort que réel (-9.81) pour meilleur game feel |
| Ground Check | SphereCast radius 0.3 | Depuis le bas du collider, dist 0.15 |
| Slope Limit | 45° | Au-delà, le joueur glisse |
| Step Offset | 0.35m | Hauteur max de marche franchissable |
| Capsule Height | 1.8m (debout) / 1.0m (crouch) | Transition smooth 0.2s |
| Capsule Radius | 0.35m | Collider joueur |
| Air Control | 0.3 (30%) | Réduction de contrôle en l'air |
| Coyote Time | 0.15s | Fenêtre de saut après quitter le sol |
| Jump Buffer | 0.1s | Input jump mémorisé avant atterrissage |
| Terminal Velocity | -30 m/s | Vitesse de chute max |

## 10.3 Règles KB du Controller

- Utiliser CharacterController.Move() (pas Rigidbody) pour un contrôle précis et prévisible
- Appliquer la gravité manuellement : velocity.y += gravity * Time.deltaTime chaque frame
- Le ground check doit utiliser SphereCast, pas un simple Raycast (gestion des bords)
- Implémenter Coyote Time ET Jump Buffer pour un gameplay réactif et satisfaisant
- Les transitions crouch/stand doivent vérifier l'espace au-dessus (SphereCast) avant de se relever
- Séparer la logique de mouvement (FixedUpdate) de l'application du mouvement (Update pour CharacterController)
- Le slide doit hériter de la direction du sprint avec décélération progressive (AnimationCurve)
- Prévoir un système de state machine pour les états du joueur (Grounded, Airborne, Sliding, WallRunning, Climbing)
