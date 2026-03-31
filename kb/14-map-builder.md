# 14. Map Builder & Placement de Prefabs

## 14.1 Architecture du Map Builder

Le système de construction de maps permet la création, l'édition et l'analyse de niveaux FPS. Il combine placement manuel de prefabs sur une grille avec des capacités de génération procédurale.

| **Composant** | **Rôle** | **Interactions** |
| --- | --- | --- |
| GridSystem | Grille 3D : dimensions, multi-floor, snapping | Tous les outils de placement |
| PrefabPalette | Catalogue organisé de prefabs avec previews et tags | MapEditorCore, PropDecorator |
| PlacementTool | Placement, rotation, scale, duplication, multi-select | GridSystem, PrefabPalette |
| EraserTool | Suppression individuelle ou par zone (box select) | GridSystem |
| PaintTool | Application de materials/textures sur surfaces | TerrainPainter |
| ProceduralGen | Génération auto de salles, couloirs, décorations | RoomGenerator, PropDecorator |
| ValidationTool | Vérification : accessibilité, NavMesh, spawn balance | NavMeshBaker, SpawnPointEditor |
| Serializer | Sauvegarde/chargement de maps (JSON, prévisualisation) | MapSerializer |

## 14.2 Catégories de Prefabs

| **Catégorie** | **Exemples** | **Tags** | **Quantité Cible** |
| --- | --- | --- | --- |
| Structures | Murs, sols, plafonds, piliers, escaliers, rampes | structure, blocking | 50-80 |
| Portes & Ouvertures | Porte simple, double, coulissante, barricade | door, passage | 10-15 |
| Couvertures | Murets, caisses, barils, voitures, sacs de sable | cover, combat | 20-30 |
| Props Décoratifs | Mobilier, débris, plantes, signalisation | prop, decoration | 80-120 |
| Éclairage | Lampes, néons, projecteurs, bougies, feux | light, atmosphere | 15-25 |
| Interactifs | Switches, terminaux, échelles, ziplines, ascenseurs | interactive, gameplay | 10-20 |
| Spawns & Zones | Player spawn, enemy spawn, objective marker | spawn, zone, marker | 5-10 |
| Environnement | Rochers, arbres, eau, skybox anchors | environment, terrain | 30-50 |
| VFX Anchors | Points de fumée, étincelles, cascades, fog volumes | vfx, atmosphere | 15-25 |
| Audio Anchors | Ambient zones, reverb triggers, music zones | audio, zone | 10-15 |

## 14.3 Règles de Level Design FPS (KB)

- La règle des 3 chemins : chaque zone de combat doit avoir au minimum 3 accès (prévenir le camping)
- Distance de combat cible : 15-25m pour la majorité des engagements (adapter les couvertures)
- Verticalité : au moins 2 niveaux de hauteur dans chaque zone clé pour la variété tactique
- Ligne de vue maximale : 60m pour éviter la domination sniper (sauf zones dédiées)
- Chaque spawn doit avoir un temps d'immunité ou une zone safe de 3 secondes de course
- Les couvertures doivent offrir une protection partielle (pas de couverture 100% imperméable)
- La symétrie de map n'est pas obligatoire mais l'équilibre de distance aux objectifs est critique
- Le NavMesh doit couvrir 100% de la zone jouable avec des areas tagées (walkable, cover, climb)
- Validation automatique : vérifier qu'aucun spawn n'a de ligne de vue directe sur un autre spawn
