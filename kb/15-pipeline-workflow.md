# 15. Pipeline d'Intégration & Workflow

## 15.1 Workflow de l'Agent

| **Phase** | **Étape** | **Actions** | **Output** |
| --- | --- | --- | --- |
| 1. Analyse | Compréhension de la demande | Parse la requête, identifie les systèmes impliqués | Task plan structuré |
| 2. Recherche KB | Consultation de la base de connaissances | Charge les règles, patterns, templates pertinents | Contexte enrichi |
| 3. Génération | Création de code/assets | Génère scripts, configs, layouts selon les règles KB | Fichiers bruts |
| 4. Validation | Tests et vérification | Lint C#, tests unitaires, règles de nommage, perf check | Rapport de validation |
| 5. Intégration | Insertion dans le projet | Wiring events, dépendances, registration dans les managers | Projet mis à jour |
| 6. Review | Audit final | Code review, playtest simulation, balance check | Rapport final |

## 15.2 Checklist de Qualité par Système

| **Système** | **Checks Obligatoires** |
| --- | --- |
| Scripts | Conventions nommage ✓ · Pas de GetComponent dans Update ✓ · [SerializeField] sur privés ✓ · Events découplés ✓ · Documentation XML ✓ |
| Caméra | LateUpdate ✓ · Clamp vertical ✓ · No raw euler accumulé ✓ · Head bob désactivable ✓ · Weapon cam séparée ✓ |
| Controller | Coyote time ✓ · Jump buffer ✓ · Ceiling check crouch ✓ · Ground SphereCast ✓ · State machine ✓ |
| IA | Perception validée ✓ · NavMesh coverage ✓ · Squad comm ✓ · Difficulty scaling ✓ · Fallback states ✓ |
| Combat | TTK dans range ✓ · Hitbox alignment ✓ · Recoil pattern ✓ · Damage falloff ✓ · No instakill auto ✓ |
| UI/HUD | Safe areas ✓ · TMP fonts ✓ · Theme SO ✓ · Toggle chaque élément ✓ · Audio feedback ✓ |
| Économie | Source/Sink ratio ✓ · Pity system ✓ · No pay-to-win ✓ · Simulation 1000 runs ✓ |
| Map Builder | 3 chemins règle ✓ · NavMesh 100% ✓ · Spawn LOS check ✓ · Cover density ✓ · Vertical variety ✓ |
