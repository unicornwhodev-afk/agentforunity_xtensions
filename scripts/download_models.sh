#!/usr/bin/env bash
set -euo pipefail

# ── Download models to RunPod persistent volume ─────────────────────
# Run this once after creating the pod, before starting services.

MODELS_DIR="/workspace/models"
mkdir -p "$MODELS_DIR"

echo "╔══════════════════════════════════════════╗"
echo "║     Downloading models to $MODELS_DIR    ║"
echo "╚══════════════════════════════════════════╝"

# Requires: pip install huggingface_hub[cli]
# and HF_TOKEN env var for gated models

# ── GPU 0: LLM ──────────────────────────────────────────────────────

echo ""
echo "▶ [1/4] Qwen2.5-Coder-32B-Instruct-AWQ (LLM principal, ~18 GB)..."
huggingface-cli download Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \
    --local-dir "$MODELS_DIR/Qwen2.5-Coder-32B-Instruct-AWQ" \
    --local-dir-use-symlinks False

# ── GPU 1: Vision ───────────────────────────────────────────────────

echo ""
echo "▶ [2/4] Qwen2-VL-7B-Instruct (Vision, ~14 GB)..."
huggingface-cli download Qwen/Qwen2-VL-7B-Instruct \
    --local-dir "$MODELS_DIR/Qwen2-VL-7B-Instruct" \
    --local-dir-use-symlinks False

# ── GPU 1: Embeddings ───────────────────────────────────────────────

echo ""
echo "▶ [3/4] BGE-M3 (Embeddings, ~1.3 GB)..."
huggingface-cli download BAAI/bge-m3 \
    --local-dir "$MODELS_DIR/bge-m3" \
    --local-dir-use-symlinks False

# ── GPU 1: Reranker ─────────────────────────────────────────────────

echo ""
echo "▶ [4/4] BGE-Reranker-v2-M3 (Reranker, ~1.3 GB)..."
huggingface-cli download BAAI/bge-reranker-v2-m3 \
    --local-dir "$MODELS_DIR/bge-reranker-v2-m3" \
    --local-dir-use-symlinks False

echo ""
echo "✓ All models downloaded to $MODELS_DIR"
du -sh "$MODELS_DIR"/*
