# Continue.dev — Configuration pour AgentUnity

## Installation

1. Installer l'extension **Continue** dans VS Code (`continue.continue`)
2. Copier `config.json` vers `~/.continue/config.json` (ou le fusionner avec ta config existante)
3. Remplacer les placeholders :
   - `RUNPOD_ID` → le Pod ID de ton pod RunPod (ex: `abc123def`)
   - `YOUR_API_SECRET_KEY` → la même clé que dans les env vars du serveur

   Ou utiliser le script automatique : `setup-local.ps1`

## Modèles configurés

| Modèle | Usage | Port |
|--------|-------|------|
| Qwen2.5-Coder-32B-AWQ | Chat principal, inline edit, autocomplete | 8000 |
| Qwen2-VL-7B | Analyse d'images/screenshots | 8001 |
| BGE-M3 | Embeddings pour `@codebase` | 8002 |
| BGE-Reranker | Reranking RAG | 8003 |

## Commandes custom

- `/unity-scene` — Inspecter ou modifier la scène Unity active
- `/unity-fix` — Corriger toutes les erreurs de compilation
- `/unity-test` — Lancer les tests et analyser les résultats

## Usage

- **Chat** : directement dans le panneau Continue (Ctrl+L)
- **Inline edit** : sélectionne du code → Ctrl+I → décris la modification
- **Autocomplete** : tape du code, l'autocomplétion inline se déclenche automatiquement
- **RAG codebase** : utilise `@codebase` dans le chat pour chercher dans le code indexé
