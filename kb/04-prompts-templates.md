# 4. Prompts & Templates de Génération

## 4.1 Catalogue de Prompts par Catégorie

Chaque prompt est conçu pour être injecté dans le contexte de l'agent selon la tâche demandée. Ils incluent des règles, des exemples et des gardes-fous spécifiques au domaine FPS.

### 4.1.1 Prompts de Création de Scripts

| **ID Prompt** | **Nom** | **Description** |
| --- | --- | --- |
| P-SCR-001 | Script Generator | Génère un script C# complet avec namespaces, régions, documentation XML, respect des conventions Unity. Inclut [Header], [Tooltip], [SerializeField]. |
| P-SCR-002 | Script Refactor | Analyse un script existant et propose des refactors : extraction méthodes, patterns, réduction couplage, SOLID principles. |
| P-SCR-003 | MonoBehaviour Audit | Vérifie les erreurs courantes : Update() vide, GetComponent() répété, allocation en boucle, Find() en runtime. |
| P-SCR-004 | SO Creator | Crée un ScriptableObject avec éditeur custom, validation, menu de création contextuel. |
| P-SCR-005 | Editor Script | Génère un CustomEditor ou EditorWindow pour outils d'édition Unity. |
| P-SCR-006 | Test Generator | Crée des tests unitaires (EditMode) et des tests d'intégration (PlayMode) pour un script donné. |

### 4.1.2 Prompts de Level Design

| **ID Prompt** | **Nom** | **Description** |
| --- | --- | --- |
| P-LVL-001 | Room Blueprint | Génère un layout de salle avec dimensions, points d'intérêt, couvertures, lignes de vue. |
| P-LVL-002 | Map Flow Analyzer | Analyse le flow d'une map : choke points, rotations, équilibre spawn, lignes de vue longues. |
| P-LVL-003 | Prefab Placement | Suggère le placement optimal de prefabs selon les règles de level design FPS. |
| P-LVL-004 | Lighting Mood | Définit un setup d'éclairage selon une atmosphère cible : industrial, horror, clean military. |
| P-LVL-005 | Cover Layout | Génère un pattern de couvertures pour une zone de combat donnée. |
| P-LVL-006 | Vertical Design | Plan de verticalité : escaliers, échelles, plateformes, sauts, zip-lines. |

### 4.1.3 Prompts IA & Game Design

| **ID Prompt** | **Nom** | **Description** |
| --- | --- | --- |
| P-AI-001 | Behaviour Tree Builder | Construit un arbre de comportement complet pour un type d'ennemi donné. |
| P-AI-002 | Difficulty Curve | Définit les paramètres de difficulté progressifs par niveau/zone. |
| P-AI-003 | Enemy Archetype | Crée un archétype d'ennemi complet : stats, comportement, visuels, sons. |
| P-AI-004 | Squad Tactics | Définit les tactiques de groupe : flanking, suppression, push coordonné. |
| P-GD-001 | Weapon Balance | Génère un tableau de balance d'armes avec DPS, TTK, range curves. |
| P-GD-002 | Economy Model | Modélise l'économie : sources, sinks, inflation control, progression curve. |
| P-GD-003 | Loot Table | Crée des tables de loot équilibrées avec raretés et pity system. |
| P-GD-004 | Progression System | Définit XP curves, unlocks, prestige, skill trees. |

### 4.1.4 Prompts d'Analyse & Optimisation

| **ID Prompt** | **Nom** | **Description** |
| --- | --- | --- |
| P-OPT-001 | Performance Audit | Analyse complète : draw calls, polygones, memory, GC allocations, frame timing. |
| P-OPT-002 | Memory Profiler | Détection de leaks, textures surdimensionnées, assets non référencés. |
| P-OPT-003 | Shader Optimizer | Analyse et optimise les shaders custom pour mobile/desktop targets. |
| P-OPT-004 | Build Size Audit | Analyse de la taille du build : assets lourds, compression, stripping. |
