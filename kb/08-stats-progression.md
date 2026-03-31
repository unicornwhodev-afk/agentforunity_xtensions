# 8. Stats & Progression

## 8.1 Système de Stats du Joueur

| **Stat** | **Type** | **Range** | **Régénération** | **Modifiers** |
| --- | --- | --- | --- | --- |
| Health | float | 0 – 100 | Passive (2/s) après 5s sans dégâts | +/- plat, % multiplicatif |
| Armor | float | 0 – 100 | Aucune (pickup only) | Absorption 50-75% |
| Stamina | float | 0 – 100 | Active (15/s), pause si sprint | +/- coût, % regen |
| Speed | float | 3.5 – 8.0 | N/A (stat de mouvement) | % multiplicatif stack |
| XP | int | 0 – ∞ | N/A (accumulation) | % XP boost |
| Level | int | 1 – max_level | N/A (dérivé de XP) | Curve exponentielle |

## 8.2 Stats des Armes (ScriptableObject)

| **Paramètre** | **Type** | **Description** |
| --- | --- | --- |
| damage | float | Dégâts de base par balle |
| fireRate | float | Cadence de tir (rounds per minute) |
| magazineSize | int | Capacité du chargeur |
| reloadTime | float | Durée de rechargement en secondes |
| spread | Vector2 | Dispersion min/max (hip / ADS) |
| recoilPattern | AnimationCurve[] | Courbes X/Y du pattern de recul |
| range | float | Portée effective maximale |
| damageFalloff | AnimationCurve | Courbe de dégâts en fonction de la distance |
| penetration | float | Valeur de pénétration (murs fins, ennemis alignés) |
| headshotMultiplier | float | Multiplicateur headshot (typ. 1.5 – 4.0) |
| moveSpeedPenalty | float | Réduction de vitesse quand équipé (0.0 – 0.3) |
| adsSpeed | float | Durée de transition vers ADS |
| weaponType | enum | Rifle, SMG, Shotgun, Sniper, Pistol, LMG, Launcher |
| fireMode | enum | Auto, Semi, Burst, BoltAction |

## 8.3 Courbe de Progression XP

Formule de XP requise par niveau : XP(n) = baseXP × n^exponent + (n × linearBonus). Valeurs recommandées : baseXP = 100, exponent = 1.5, linearBonus = 50. Cela produit une courbe douce pour les premiers niveaux qui s'accélère progressivement.

| **Niveau** | **XP Requise** | **XP Cumulée** | **Unlocks Exemple** |
| --- | --- | --- | --- |
| 1 → 2 | 250 | 250 | Première arme secondaire |
| 5 → 6 | 1 368 | 4 950 | Grenade flashbang |
| 10 → 11 | 3 662 | 18 500 | Classe custom |
| 20 → 21 | 9 944 | 72 000 | Prestige des armes |
| 50 → 51 | 36 390 | 620 000 | Prestige global |
