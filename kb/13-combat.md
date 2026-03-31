# 13. Système de Combat

## 13.1 Formules de Dégâts

Le calcul de dégâts suit un pipeline de modificateurs appliqués séquentiellement :

| **Étape** | **Formule** | **Description** |
| --- | --- | --- |
| 1. Dégâts de base | baseDamage = weapon.damage | Valeur brute de l'arme |
| 2. Zone touchée | zoneDmg = baseDamage × zoneMultiplier | Head: 2.5x, Chest: 1.0x, Limbs: 0.75x |
| 3. Distance falloff | distDmg = zoneDmg × falloffCurve(distance) | Courbe définie par arme |
| 4. Armure | armorReduction = distDmg × (1 - armorAbsorb%) | Absorb 50-75% selon type armure |
| 5. Pénétration | penaltyDmg = armorReduced × penFactor | Si le tir traverse un mur/surface |
| 6. Buffs/Debuffs | finalDmg = penaltyDmg × buffMultiplier | Power-ups, skills, états |
| 7. Clamp | clampedDmg = Max(1, finalDmg) | Minimum 1 de dégât garanti |

## 13.2 Balance des Armes

| **Catégorie** | **DPS Théorique** | **TTK (100 HP)** | **Range Efficace** | **Niche** |
| --- | --- | --- | --- | --- |
| Assault Rifle | 180-220 | 0.45-0.55s | 15-40m | Polyvalent, mi-distance |
| SMG | 200-250 | 0.35-0.50s | 5-20m | Courte portée, mobilité |
| Shotgun | 250-350 | 0.3-0.4s | 3-12m | Burst CaC, one-shot potentiel |
| Sniper | 100-150 | 0.5-1.0s | 30-100m+ | One-shot head, lent |
| LMG | 150-200 | 0.5-0.7s | 15-50m | Suppression, gros chargeur |
| Pistol | 120-160 | 0.6-0.8s | 5-25m | Backup, tir rapide |
| Launcher | Variable | Instant (direct) | 10-40m | AOE, anti-véhicule |

## 13.3 Règles KB Combat

- Le TTK doit rester entre 0.3s et 1.0s pour un FPS compétitif satisfaisant
- Chaque arme doit avoir une niche claire : aucune arme ne doit dominer à toutes les distances
- Le headshot multiplier ne doit JAMAIS permettre un one-shot avec une arme automatique (sauf sniper)
- Le recoil doit être learnable : pattern fixe + random spread faible, pas pur random
- Les grenades doivent avoir un temps de fuse visible (indicateur au sol) pour permettre la réaction
- Le système de hit registration doit privilégier le client (client-side prediction) avec validation serveur
