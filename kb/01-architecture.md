# 1. Architecture Générale de l'Agent

## 1.1 Rôle et Périmètre

L'agent Unity FPS est un système autonome capable de créer, éditer et analyser un projet Unity complet pour un jeu de type First Person Shooter. Il opère sur l'ensemble du pipeline de développement, de la génération de scripts C# à la construction de niveaux, en passant par le tuning de paramètres de gameplay.

## 1.2 Capacités Fondamentales

| **Capacité** | **Description** | **Priorité** |
| --- | --- | --- |
| Création de Scripts | Génération de scripts C# conformes aux conventions Unity | Critique |
| Édition de Scènes | Modification de scènes, placement d'objets, éclairage | Critique |
| Analyse de Projet | Audit de performance, détection de problèmes, optimisation | Haute |
| Game Design | Balancement des stats, économie, courbes de difficulté | Haute |
| Construction de Maps | Éditeur de niveaux avec placement procédural de prefabs | Haute |
| IA Ennemis | Behaviour Trees, GOAP, navigation avancée | Haute |
| UI/HUD | Systèmes d'interface, menus, éléments in-game | Moyenne |
| Intégration Audio | Mixage, triggers sonores, musique adaptative | Moyenne |

## 1.3 Architecture Modulaire

L'agent est structuré en modules indépendants communiquant via un bus d'événements central. Chaque module possède sa propre base de connaissances, ses scripts référentiels, et ses prompts spécialisés.

| **Module** | **Dossier KB** | **Dépendances** |
| --- | --- | --- |
| Core Engine | /kb/core/ | Aucune |
| Player Systems | /kb/player/ | Core Engine |
| AI Systems | /kb/ai/ | Core Engine, Navigation |
| Combat | /kb/combat/ | Player, AI, Stats |
| Economy | /kb/economy/ | Stats, Inventory |
| Map Builder | /kb/mapbuilder/ | Core Engine, Prefabs |
| UI/HUD | /kb/ui/ | Player, Stats, Combat |
| Audio | /kb/audio/ | Core Engine |
| Camera | /kb/camera/ | Player Systems |
| Animation | /kb/animation/ | Player, AI, Combat |
