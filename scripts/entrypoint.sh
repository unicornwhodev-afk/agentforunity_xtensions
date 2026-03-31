#!/usr/bin/env bash
set -euo pipefail

# ── AgentUnity entrypoint — runs on pod start ────────────────────────

echo "╔══════════════════════════════════════════╗"
echo "║         AgentUnity — Starting...         ║"
echo "╚══════════════════════════════════════════╝"

# ── 1. Install heavy Python deps (first boot) + lock versions ───────

HEAVY_LOCK_DIR="/workspace/pip-lock"
HEAVY_LOCK_FILE="$HEAVY_LOCK_DIR/requirements-heavy.lock"
mkdir -p "$HEAVY_LOCK_DIR"

have_heavy_deps() {
    python - <<'PY'
import importlib.util
import sys

required = ["vllm", "sentence_transformers", "FlagEmbedding", "peft"]
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    print("Missing Python modules:", ", ".join(missing))
    sys.exit(1)
PY
}

if have_heavy_deps; then
    echo "[1/5] Heavy deps already installed"
    if [ ! -s "$HEAVY_LOCK_FILE" ]; then
        echo "      Creating dependency lock at $HEAVY_LOCK_FILE"
        pip freeze > "$HEAVY_LOCK_FILE"
    fi
else
    if [ -s "$HEAVY_LOCK_FILE" ]; then
        echo "[1/5] Installing heavy deps from lock..."
        pip install --no-cache-dir -r "$HEAVY_LOCK_FILE"
    else
        echo "[1/5] Installing heavy deps (vLLM, embeddings)..."
        echo "      This takes a few minutes on first boot."
        pip install --no-cache-dir -r /app/requirements-heavy.txt
        echo "      Saving dependency lock to $HEAVY_LOCK_FILE"
        pip freeze > "$HEAVY_LOCK_FILE"
    fi
fi

if ! have_heavy_deps; then
    echo "  ✗ ERROR: heavy dependencies are not importable after install"
    exit 1
fi

# ── 2. Download models (first boot only, persisted in /workspace) ────

echo "[2/5] Checking & downloading models..."
MODELS_DIR="/workspace/models"
mkdir -p "$MODELS_DIR"

if [ -z "${HF_TOKEN:-}" ]; then
    echo "  ⚠ Warning: HF_TOKEN is not set. Public models may still download."
fi

if [ ! -f "$MODELS_DIR/Qwen2.5-Coder-32B-Instruct-AWQ/config.json" ]; then
    echo "  ▶ Downloading Qwen2.5-Coder-32B-Instruct-AWQ (~18 GB)..."
    huggingface-cli download Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \
        --local-dir "$MODELS_DIR/Qwen2.5-Coder-32B-Instruct-AWQ" \
        --local-dir-use-symlinks False
    if [ $? -ne 0 ] || [ ! -f "$MODELS_DIR/Qwen2.5-Coder-32B-Instruct-AWQ/config.json" ]; then
        echo "  ✗ ERROR: LLM model download failed!"
        exit 1
    fi
    echo "  ✓ LLM model downloaded"
else
    echo "  ✓ LLM model already present"
fi

if [ ! -f "$MODELS_DIR/Qwen2-VL-7B-Instruct/config.json" ]; then
    echo "  ▶ Downloading Qwen2-VL-7B-Instruct (~14 GB)..."
    huggingface-cli download Qwen/Qwen2-VL-7B-Instruct \
        --local-dir "$MODELS_DIR/Qwen2-VL-7B-Instruct" \
        --local-dir-use-symlinks False
    if [ $? -ne 0 ] || [ ! -f "$MODELS_DIR/Qwen2-VL-7B-Instruct/config.json" ]; then
        echo "  ✗ ERROR: Vision model download failed!"
        exit 1
    fi
    echo "  ✓ Vision model downloaded"
else
    echo "  ✓ Vision model already present"
fi

if [ ! -f "$MODELS_DIR/bge-m3/config.json" ]; then
    echo "  ▶ Downloading BGE-M3 (~1.3 GB)..."
    huggingface-cli download BAAI/bge-m3 \
        --local-dir "$MODELS_DIR/bge-m3" \
        --local-dir-use-symlinks False
    if [ $? -ne 0 ] || [ ! -f "$MODELS_DIR/bge-m3/config.json" ]; then
        echo "  ✗ ERROR: Embedding model download failed!"
        exit 1
    fi
    echo "  ✓ Embedding model downloaded"
else
    echo "  ✓ Embedding model already present"
fi

if [ ! -f "$MODELS_DIR/bge-reranker-v2-m3/config.json" ]; then
    echo "  ▶ Downloading BGE-Reranker-v2-M3 (~1.3 GB)..."
    huggingface-cli download BAAI/bge-reranker-v2-m3 \
        --local-dir "$MODELS_DIR/bge-reranker-v2-m3" \
        --local-dir-use-symlinks False
    if [ $? -ne 0 ] || [ ! -f "$MODELS_DIR/bge-reranker-v2-m3/config.json" ]; then
        echo "  ✗ ERROR: Reranker model download failed!"
        exit 1
    fi
    echo "  ✓ Reranker model downloaded"
else
    echo "  ✓ Reranker model already present"
fi

# ── 3. Qdrant data dir ──────────────────────────────────────────────

echo "[3/5] Preparing Qdrant storage..."
mkdir -p /workspace/qdrant_data

# ── 4. MCP-Unity connectivity ───────────────────────────────────────

echo "[4/5] MCP-Unity URL: ${MCP_UNITY_WS_URL:-ws://localhost:8090/McpUnity}"

# ── 5. Launch all services via supervisord ───────────────────────────

echo "[5/5] Starting services via supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/agentunity.conf
