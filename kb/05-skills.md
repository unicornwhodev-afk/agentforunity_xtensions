# 5. Skills de l'Agent

## 5.1 Skills Techniques

Les skills sont les capacités opérationnelles de l'agent. Chaque skill définit une action concrète que l'agent peut exécuter avec des entrées/sorties définies.

| **ID Skill** | **Nom** | **Entrée** | **Sortie** | **Description** |
| --- | --- | --- | --- | --- |
| SK-001 | generate_script | Spécification fonctionnelle | Script C# validé | Génère un script complet, testé, documenté |
| SK-002 | edit_script | Script + instructions | Script modifié + diff | Modifie un script existant avec changelog |
| SK-003 | analyze_script | Script C# | Rapport d'analyse | Audit qualité, perfs, bugs potentiels |
| SK-004 | place_prefabs | Layout + règles | Liste de placements | Calcule les positions optimales des prefabs |
| SK-005 | build_room | Dimensions + type | Room data JSON | Génère une salle complète avec props |
| SK-006 | balance_weapon | Stats brutes | Stats équilibrées | Ajuste les paramètres pour l'équilibre |
| SK-007 | create_bt | Type ennemi | BT JSON/Asset | Construit un Behaviour Tree complet |
| SK-008 | audit_scene | Scene file | Rapport d'audit | Analyse une scène pour problèmes |
| SK-009 | generate_ui | Spéc UI | UXML + USS + script | Crée composant UI Toolkit complet |
| SK-010 | optimize_build | Project settings | Recommandations | Optimise les settings de build |

## 5.2 Skills de Workflow

| **ID Skill** | **Nom** | **Description** |
| --- | --- | --- |
| SK-W01 | project_init | Initialise un projet Unity FPS complet avec arborescence, packages, settings |
| SK-W02 | system_integration | Intègre un nouveau système dans le projet existant (wiring, events, tests) |
| SK-W03 | playtest_analysis | Analyse des métriques de playtest et suggère des ajustements |
| SK-W04 | version_migration | Aide à la migration entre versions de Unity |
| SK-W05 | asset_pipeline | Gère l'import, le traitement et l'optimisation des assets |
| SK-W06 | documentation_gen | Génère la documentation technique du projet automatiquement |
| SK-W07 | code_review | Review complète d'un ensemble de scripts avec scoring qualité |
| SK-W08 | deploy_build | Prépare et valide un build pour la plateforme cible |
