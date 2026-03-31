# MCP-Unity — Configuration locale pour AgentUnity

## Prérequis

Le package **mcp-unity** (CoderGamester) doit déjà être installé dans ton projet Unity.

## Configuration

1. **Copier** `McpUnitySettings.json` vers ton projet Unity :
   ```
   <ton-projet-unity>/ProjectSettings/McpUnitySettings.json
   ```

2. **Paramètres clés** :
   - `Port: 8090` — port WebSocket du serveur MCP dans l'éditeur Unity
   - `AllowRemoteConnections: true` — **critique** pour que le tunnel cloudflared fonctionne
   - `RequestTimeoutSeconds: 75` — augmenté pour les opérations réseau à travers le tunnel

3. **Redémarrer Unity** après avoir copié le fichier pour que les settings soient pris en compte

## Vérification

Après redémarrage de Unity :
- Ouvre la console Unity → tu devrais voir `MCP Unity Server started on port 8090`
- Le serveur WebSocket écoute sur `ws://0.0.0.0:8090/McpUnity` (toutes interfaces grâce à `AllowRemoteConnections`)

## Tunnel cloudflared

Pour exposer le serveur MCP au pod RunPod :
```powershell
cloudflared tunnel --url ws://localhost:8090
```

Cloudflared génère une URL comme `https://random-words.trycloudflare.com`.
Copier cette URL et la mettre dans la variable d'environnement du pod :
```
MCP_UNITY_WS_URL=wss://random-words.trycloudflare.com/McpUnity
```

> **Note** : L'URL change à chaque relance de cloudflared. Pour une URL fixe, configure un tunnel nommé via le dashboard Cloudflare.

## Test de connectivité depuis le pod RunPod

```bash
# Tester le WebSocket depuis le pod :
python -c "import asyncio, websockets; asyncio.run(websockets.connect('wss://your-tunnel.trycloudflare.com/McpUnity'))"
```
