# 6. Système de Caméra FPS

## 6.1 Règles Fondamentales de Caméra

Le système de caméra est l'élément le plus critique d'un FPS. Il détermine directement le game feel, la précision de visée, et l'immersion du joueur.

| **Paramètre** | **Valeur Recommandée** | **Notes** |
| --- | --- | --- |
| FOV Base | 90° (horizontal) | Ajustable par le joueur : 70° → 120° |
| FOV ADS | 40°-65° | Dépend du type d'optique / scope |
| Sensibilité souris | 1.0 (normalisée) | Pas d'accélération, raw input |
| Clamp vertical | -89° à +89° | Empêcher le retournement |
| Smoothing | 0 (défaut) | Optionnel pour manette uniquement |
| Near Clip Plane | 0.01 – 0.1 | Critique pour éviter le clipping des armes |
| Far Clip Plane | 500 – 1000 | Adapter selon taille de map |
| Head Bob Amplitude | 0.02 – 0.05 | Subtil, désactivable dans les options |
| Recoil Recovery Speed | 5 – 15 | Lerp de retour après recul |
| Camera Shake Max | 0.3 – 0.8 | Intensité max des explosions proches |

## 6.2 Pipeline de Caméra

Le traitement de la caméra suit un pipeline séquentiel strict pour éviter les conflits entre effets :

| **Étape** | **Traitement** | **Priorité** |
| --- | --- | --- |
| 1. Input Brut | Récupération mouse delta / stick input (raw, sans accel) | Maximale |
| 2. Sensibilité | Multiplication par sensibilité utilisateur + ADS multiplier | Haute |
| 3. Recoil | Ajout du vecteur de recul actuel (pattern + random spread) | Haute |
| 4. Sway | Application du sway d'arme basé sur le mouvement | Moyenne |
| 5. Head Bob | Oscillation sinusoïdale liée à la vitesse de déplacement | Moyenne |
| 6. Camera Tilt | Inclinaison lors de wall-run, slide, lean | Moyenne |
| 7. Shake | Secousses procédurales (explosions, impacts lourds) | Basse |
| 8. Clamp | Limitation de la rotation verticale finale | Finale |
| 9. Smooth (opt) | Lissage optionnel pour manette | Post-final |

## 6.3 Règles de KB Caméra

- Toujours utiliser LateUpdate() pour les mouvements de caméra, jamais Update()
- Séparer la rotation X (horizontal, appliquée au player body) de la rotation Y (vertical, appliquée à la caméra)
- Utiliser Quaternion.Euler pour la rotation finale, jamais d'Euler angles accumulés
- Le FOV doit s'adapter au sprint (FOV + 5°) et à l'ADS (FOV spécifique à l'optique)
- Prévoir une caméra d'arme séparée (Weapon Camera) avec FOV fixe pour éviter la déformation
- L'option de désactiver le head bob doit TOUJOURS être présente (accessibilité)
- Le camera shake ne doit JAMAIS affecter la direction de visée réelle (cosmétique uniquement)
