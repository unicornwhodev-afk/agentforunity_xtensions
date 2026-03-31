# 11. Intelligence Artificielle Avancée

## 11.1 Architecture IA Multi-Couches

| **Couche** | **Système** | **Fréquence MAJ** | **Description** |
| --- | --- | --- | --- |
| Stratégique | GOAP / Utility AI | 0.5 – 2.0s | Objectifs haut niveau : capturer, défendre, fuir, héler |
| Tactique | Behaviour Tree | 0.1 – 0.5s | Séquences de combat : tirer, couvrir, flanquer, grenader |
| Réactive | State Machine | Chaque frame | Réactions immédiates : esquive, alerte, flinch |
| Perception | Sensor System | 0.1 – 0.3s | Vision, audition, partage d'information d'équipe |
| Navigation | NavMesh + Custom | 0.05 – 0.2s | Pathfinding, obstacle avoidance, tactical movement |

## 11.2 Système de Perception

| **Sens** | **Méthode** | **Paramètres** | **Détails** |
| --- | --- | --- | --- |
| Vision | FOV Cone + Raycast | Angle: 110°, Range: 30m | Occultation par obstacles, détection partielle (jambes visibles) |
| Audition | Sphere Overlap | Range: 15-50m (selon bruit) | Tirs = 50m, pas = 8m, crouch = 4m, suppressed = 15m |
| Alerte équipe | Event broadcast | Squad range: 40m | Partage de dernière position connue du joueur |
| Mémoire | Timer decay | Durée: 8-15s | Se souvient de la dernière position vue, investigation |
| Suspicion | Score accumulé | Seuil: 0 → 100 | Bruit + ombre + mouvement = alerte progressive |

## 11.3 Archétypes d'Ennemis

| **Archétype** | **Comportement** | **Stats Clés** | **Tactique** |
| --- | --- | --- | --- |
| Grunt | Agressif, avancée directe, couverture basique | HP: 80, Précision: 40% | Rush en groupe, tirs de suppression |
| Soldier | Équilibré, utilise couvertures, flanque | HP: 100, Précision: 60% | Progression tactique, grenades |
| Sniper | Statique, longue portée, fuit si approché | HP: 60, Précision: 85% | Perché en hauteur, relocate après 3 tirs |
| Shotgunner | Ultra agressif, charge, courte portée | HP: 120, Précision: 70% | Flanque pour fermer la distance |
| Heavy | Tank lent, arme lourde, suppression | HP: 300, Précision: 35% | Suppression, avance lente, couvre l'équipe |
| Medic | Support, soigne alliés, combat modéré | HP: 80, Précision: 45% | Reste en arrière, priorise les soins |
| Engineer | Pose pièges/tourelles, combat modéré | HP: 90, Précision: 50% | Déploie des défenses, maintient la position |
| Boss | Patterns uniques, phases, mécaniques spéciales | HP: 1000+, Variable | Multi-phase, invulnérabilité conditionnelle |

## 11.4 Système de Squads

- Chaque squad a un leader qui définit les ordres (avancer, couvrir, flanquer, retraite)
- Formation dynamique : ligne, colonne, éventail, défensif (cercle)
- Communication intra-squad : partage de cibles, appels à l'aide, confirmation de kills
- Si le leader meurt, le membre le plus expérimenté prend le relais
- Les squads peuvent demander du renfort au AIDirector si en difficulté
- Tactical Point System : chaque position est scorée (couverture, visibilité, distance, flanc) pour les décisions
