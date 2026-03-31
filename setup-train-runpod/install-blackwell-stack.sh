#!/usr/bin/env bash
set -euo pipefail

PYTORCH_INDEX_URL="${PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_FLASH_ATTN="${SKIP_FLASH_ATTN:-0}"

python -m pip install --upgrade pip setuptools wheel

python -m pip install --index-url "${PYTORCH_INDEX_URL}" \
    torch \
    torchvision \
    torchaudio

python -m pip install --prefer-binary -r "${SCRIPT_DIR}/requirements-train.txt"

if [ "${SKIP_FLASH_ATTN}" != "1" ]; then
    python -m pip install --no-build-isolation "flash-attn>=2.7.0.post2"
fi

python -m pip install --no-build-isolation "nvidia-modelopt[torch]>=0.23.0"

echo "Blackwell training stack installed."