# 9. HUD & Interface Utilisateur

## 9.1 Layout HUD Standard FPS

| **Élément** | **Position Écran** | **Priorité Visuelle** | **Mise à jour** |
| --- | --- | --- | --- |
| Crosshair | Centre exact | Maximale | Chaque frame |
| Barre de Santé | Bas-gauche | Haute | Sur dommage / heal |
| Barre d'Armure | Sous la santé | Haute | Sur modification |
| Munitions | Bas-droite | Haute | Sur tir / reload |
| Minimap | Haut-droite | Moyenne | Chaque frame |
| Indicateurs de Dégâts | Autour du crosshair | Haute (flash) | Sur hit reçu |
| Kill Feed | Haut-droite (sous minimap) | Basse | Sur kill |
| Objectifs | Haut-gauche | Moyenne | Événementiel |
| Grenade Indicator | Bas-centre / côté arme | Moyenne | Sur changement |
| Interaction Prompt | Centre-bas | Contextuelle | Proximité objet |
| Stamina Bar | Sous crosshair ou bas-gauche | Contextuelle | Sprint/action |
| Hit Marker | Centre (overlay crosshair) | Flash haute | Sur hit confirmé |
| Score/Timer | Haut-centre | Basse | Chaque seconde |

## 9.2 Règles UI/HUD de la KB

- Utiliser UI Toolkit (UXML + USS) pour les menus, Canvas + World Space pour le HUD in-game si performance critique
- Le crosshair doit répondre en temps réel au spread, au mouvement et au tir
- Les animations UI doivent utiliser DOTween ou des coroutines, pas l'Animator
- Toutes les couleurs doivent être définies dans un SO (ThemeConfig) pour permettre le theming et le daltonisme
- Le HUD doit pouvoir être masqué complètement (mode cinématique) et individuellement (chaque élément)
- Respecter les safe areas sur toutes les plateformes (mobile notch, TV overscan)
- Police par défaut en SDF (TextMeshPro) pour netteté à toutes les résolutions
- Les éléments de HUD critiques (santé, ammo) doivent avoir un feedback audio en plus du visuel
