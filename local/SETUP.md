# AgentUnity — Setup complet

## Architecture de connexion

```
┌─────────────────────────────────────────┐
│             PC LOCAL (Windows)          │
│                                         │
│  ┌────────────┐      ┌──────────────┐  │
│  │ Unity Editor│      │  VS Code     │  │
│  │ + MCP-Unity │      │ + Continue   │  │
│  │ + AgentUnity│      │              │  │
│  │   Window    │      │              │  │
│  └──────┬─────┘      └──────┬───────┘  │
│         │                   │           │
│   ws://0.0.0.0:8090         │           │
│         │      https://PODID-8080.proxy │
│  ┌──────┴──────┐            │           │
│  │ cloudflared │  ──────────┘           │
│  │  tunnel     │                        │
│  └──────┬──────┘                        │
└─────────┼───────────────────────────────┘
          │ wss://xxx.trycloudflare.com
          ▼
┌─────────┼───────────────────────────────┐
│         │  RunPod (2× L40S)             │
│         ▼                               │
│  ┌──────────────────────────────────┐   │
│  │  FastAPI (port 8080)             │   │
│  │  LangGraph → MCP_UNITY_WS_URL   │   │
│  └──────────────┬───────────────────┘   │
│        ┌────────┼────────┐              │
│   ┌────┴───┐ ┌──┴──┐ ┌──┴───┐ ┌────┐  │
│   │ vLLM   │ │vLLM │ │Qdrant│ │BGE │  │
│   │ 32B    │ │ VL  │ │      │ │ M3 │  │
│   │GPU0    │ │GPU1 │ │      │ │+RR │  │
│   │:8000   │ │:8001│ │:6333 │ │8002│  │
│   └────────┘ └─────┘ └──────┘ │8003│  │
│                                └────┘  │
│  Proxy: https://PODID-PORT.proxy.runpod│
└─────────────────────────────────────────┘
```

**2 flux de connexion :**
- **Toi → Pod** : via les URLs proxy RunPod (`https://PODID-PORT.proxy.runpod.net`)
- **Pod → Ton Unity** : via un tunnel cloudflared (expose `ws://localhost:8090` en public)

## Étape 1 — Installer cloudflared (PC local)

1. Télécharger depuis https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. Vérifier l'installation :
   ```powershell
   cloudflared --version
   ```

## Étape 2 — Déployer le pod RunPod

1. Build et push l'image Docker :
   ```bash
   docker build -t charlibillabert/agentunity:latest .
   docker push charlibillabert/agentunity:latest
   ```

2. Créer un pod RunPod :
   - Image : `charlibillabert/agentunity:latest`
   - GPU : 2× L40S (48GB chacun)
   - Volume : `/workspace` (persistant entre les sessions)
   - Env vars à configurer :
     | Variable | Valeur | Description |
     |----------|--------|-------------|
     | `API_SECRET_KEY` | `ta-cle-secrete` | Clé d'authentification API |
     | `HF_TOKEN` | `hf_xxx...` | Token HuggingFace (download modèles) |
     | `MCP_UNITY_WS_URL` | `wss://xxx.trycloudflare.com/McpUnity` | URL du tunnel cloudflared (étape 3) |

3. Lancer le pod → le premier démarrage télécharge automatiquement les modèles (~35 GB)
4. Le pod sera accessible via : `https://<POD_ID>-<PORT>.proxy.runpod.net`
5. Récupérer ton **Pod ID** dans le dashboard RunPod (ex: `abc123def`)

## Étape 3 — Lancer le tunnel cloudflared

Ouvre Unity, puis dans un terminal PowerShell :

```powershell
cloudflared tunnel --url ws://localhost:8090
```

Tu obtiens une URL comme `https://random-words.trycloudflare.com`.

→ Va dans les **env vars** du pod RunPod et mets à jour :
```
MCP_UNITY_WS_URL=wss://random-words.trycloudflare.com/McpUnity
```

> **Note** : l'URL change à chaque relance de cloudflared. Il faut mettre à jour `MCP_UNITY_WS_URL` côté pod à chaque fois (ou utiliser un tunnel nommé cloudflared pour une URL fixe).

## Étape 4 — Setup local automatique

```powershell
cd d:\Dev\Projects\agentunity\local\scripts
.\setup-local.ps1 -UnityProjectPath "D:\Dev\MyGame" -RunPodID "abc123def" -ApiKey "ta-cle-secrete"
```

Ce script :
- ✅ Vérifie que cloudflared est installé
- ✅ Copie `McpUnitySettings.json` dans le projet Unity (active les connexions distantes)
- ✅ Ajoute l'extension AgentUnity au `manifest.json` Unity
- ✅ Configure Continue.dev avec les URLs RunPod proxy

## Étape 5 — Vérifier la connectivité

```powershell
.\test-connectivity.ps1 -RunPodID "abc123def"
```

Résultat attendu :
```
  ✓ FastAPI (orchestrator) — https://abc123def-8080.proxy.runpod.net/api/v1/health
  ✓ vLLM LLM (32B)        — https://abc123def-8000.proxy.runpod.net/v1/models
  ✓ vLLM Vision (7B)      — https://abc123def-8001.proxy.runpod.net/v1/models
  ✓ Embeddings (BGE-M3)   — https://abc123def-8002.proxy.runpod.net/health
  ✓ Reranker (BGE)        — https://abc123def-8003.proxy.runpod.net/health
  ✓ Qdrant               — https://abc123def-6333.proxy.runpod.net/collections
  ✓ MCP-Unity server listening on port 8090
```

## Étape 6 — Utiliser

### Dans Unity
- Menu `AgentUnity > Chat Window`
- Entrer le Server URL : `https://abc123def-8080.proxy.runpod.net`
- Entrer l'API key
- Cliquer "Test Connection" → ✓
- Cliquer "Index Project (RAG)" → indexe tout le code C# + KB
- Commencer à chatter !

### Dans VS Code — Copilot (`@agentunity`)
- Ouvrir Copilot Chat : `Ctrl+Shift+I`
- Taper `@agentunity` puis ta demande (ex: "ajoute 3 ennemis dans la scène")
- L'agent a accès aux outils MCP-Unity pour manipuler l'éditeur directement
- Prompts rapides disponibles : `/unity-scene-inspect`, `/unity-fix-errors`, `/unity-create-script`, `/unity-run-tests`

### Dans VS Code — Continue
- Ouvrir le panneau Continue : `Ctrl+L`
- Le modèle "AgentUnity (RunPod)" est déjà configuré
- Utiliser `@codebase` pour chercher dans le code indexé
- Commandes custom : `/unity-scene`, `/unity-fix`, `/unity-test`
- Autocomplete inline activé automatiquement

## Si le pod change de Pod ID

```powershell
.\update-pod-id.ps1 -PodID "nouveau-pod-id" -ApiKey "ta-cle"
```

Puis mettre à jour l'URL dans la fenêtre Unity AgentUnity.

## Si le tunnel cloudflared change

Relancer cloudflared :
```powershell
cloudflared tunnel --url ws://localhost:8090
```
Puis mettre à jour `MCP_UNITY_WS_URL` dans les env vars du pod RunPod.

## Benchmark Q6 local

Piloter le benchmark Q6 depuis Windows avec le repo training séparé :

```powershell
cd d:\Dev\Projects\agentunity\local\scripts
$env:AGENTUNITY_TRAINING_REPO = "D:\path\to\TRAINING-PUBLIC-REPO"
.\run-q6-benchmark.ps1 -TrainingRepoPath $env:AGENTUNITY_TRAINING_REPO -Mode setup
.\run-q6-benchmark.ps1 -TrainingRepoPath $env:AGENTUNITY_TRAINING_REPO -Mode all -CaseLimit 1 -MaxNewTokens 128
```

Le script échoue explicitement si le repo training n'est pas fourni ou ne contient pas le dossier `benchmark/`.

Modes disponibles :
- `setup` : crée un venv Windows, compile `llama.cpp` avec CUDA et installe `llama-cpp-python`
- `prepare` : régénère les cas de benchmark
- `run` : exécute le benchmark Q6
- `visualize` : génère les rapports markdown, JSON et SVG
- `all` : enchaîne `prepare`, `run`, puis `visualize`

## Structure des fichiers Copilot

```
.github/
├── copilot-instructions.md       # Conventions C# chargées automatiquement
├── agents/
│   └── agentunity.agent.md       # Agent @agentunity (MCP-Unity tools)
└── prompts/
    ├── unity-scene-inspect.prompt.md
    ├── unity-fix-errors.prompt.md
    ├── unity-create-script.prompt.md
    └── unity-run-tests.prompt.md
```

## Flux de données

1. **Tu écris** un message dans Unity Chat ou Continue
2. → Envoyé au **FastAPI** sur le pod (port 8080) via le proxy RunPod
3. → **LangGraph** planner analyse et route vers l'agent spécialisé
4. → L'agent appelle **vLLM** (GPU0) pour le raisonnement
5. → Si besoin, l'agent appelle les **tools MCP-Unity** via WebSocket
6. → Le WebSocket traverse le **tunnel cloudflared** vers ton PC
7. → **MCP-Unity** exécute dans l'éditeur Unity (lecture script, patch, screenshot...)
8. → Résultat renvoyé au pod → LLM continue son raisonnement
9. → Réponse finale renvoyée à ton interface
