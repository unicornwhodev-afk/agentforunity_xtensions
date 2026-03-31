FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# ── System deps ──────────────────────────────────────────────────────

RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor curl wget gnupg2 lsb-release ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── Qdrant binary ───────────────────────────────────────────────────

RUN curl -fsSL https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-unknown-linux-musl.tar.gz \
    | tar -xz -C /usr/local/bin

# ── Python deps (lightweight — heavy deps install at pod startup) ───

WORKDIR /app
COPY requirements-light.txt .
COPY requirements-heavy.txt .
RUN pip install --no-cache-dir -r requirements-light.txt

# ── App code ─────────────────────────────────────────────────────────

COPY src/ src/
COPY scripts/ scripts/
COPY kb/ kb/
COPY supervisord.conf /etc/supervisor/conf.d/agentunity.conf

RUN chmod +x scripts/*.sh scripts/*.py

# ── Volumes ──────────────────────────────────────────────────────────

# /workspace is the RunPod persistent volume — models + qdrant data live here
VOLUME ["/workspace"]

# ── Ports ────────────────────────────────────────────────────────────

EXPOSE 8000 8001 8002 8003 8080 6333

# ── Entrypoint ───────────────────────────────────────────────────────

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
