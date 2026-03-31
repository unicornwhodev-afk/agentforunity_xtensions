# 12. Système Économique

## 12.1 Modèle Économique

| **Composant** | **Type** | **Description** |
| --- | --- | --- |
| Crédits (soft currency) | Source principale | Gagnés en jeu : kills, objectifs, missions, loot |
| Tokens (premium) | Source secondaire | Battle pass, challenges spéciaux, conversion optionnelle |
| Vendors / Shops | Sink principal | Armes, attachments, cosmétiques, consommables |
| Upgrading | Sink secondaire | Amélioration d'armes, armures, compétences |
| Crafting | Sink / Transform | Conversion de matériaux en équipements |
| Repair / Maintenance | Sink récurrent | Durabilité d'équipement (optionnel selon design) |
| Trade | Redistribution | Échanges entre joueurs (si multijoueur) |
| Loot Drops | Source variable | Drops avec tables de probabilité pondérées |

## 12.2 Tables de Rareté

| **Rareté** | **Couleur** | **Drop Rate Base** | **Multiplicateur Stats** | **Sell Value** |
| --- | --- | --- | --- | --- |
| Common | #FFFFFF (Blanc) | 55% | 1.0x | 10 crédits |
| Uncommon | #1EFF00 (Vert) | 25% | 1.15x | 25 crédits |
| Rare | #0070FF (Bleu) | 13% | 1.3x | 75 crédits |
| Epic | #A335EE (Violet) | 5% | 1.5x | 200 crédits |
| Legendary | #FF8000 (Orange) | 1.8% | 1.8x | 500 crédits |
| Mythic | #E6CC80 (Or) | 0.2% | 2.2x | 1500 crédits |

## 12.3 Règles KB Économie

- Inflation control : le ratio sources/sinks doit rester entre 0.9 et 1.1 sur une session type de 2h
- Pity System : après 50 drops sans Epic+, le prochain drop est garanti Epic minimum
- Les prix doivent suivre une progression logarithmique, pas linéaire
- Un nouveau joueur doit pouvoir acheter sa première amélioration significative en 30 minutes de jeu
- Les items cosmétiques n'ont JAMAIS d'impact sur les stats (pay-to-win interdit)
- Le système doit être testable en simulation (1000 sessions) pour vérifier l'équilibre
