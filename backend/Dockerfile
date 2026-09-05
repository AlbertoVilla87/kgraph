# ── Backend Dockerfile ──────────────────────────────────────────────
# Bake the GLiNER model into the image at build time.
# HF_HUB_OFFLINE=1 at runtime — no network needed for model loads.
# spaCy/MiniLM are NOT included (no longer used in the pipeline).
# ───────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 1. Install dependencies (layer cache — changes rarely)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. Copy code + config so `uv run` can resolve the project
COPY backend/src/ src/
COPY backend/configs/ configs/
RUN uv sync --frozen --no-dev

# 3. Bake the GLiNER model (needs `uv run` from the project venv)
RUN mkdir -p models && \
    uv run hf download urchade/gliner_multi-v2.1 \
        --local-dir models/gliner-relex-large-v0.5

# ── Runtime stage ──────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY --from=builder /app/models models
COPY --from=builder /app/src src
COPY --from=builder /app/configs configs

ENV PATH="/app/.venv/bin:$PATH"
ENV HF_HUB_OFFLINE=1
ENV DOCLING_INFERENCE_COMPILE_TORCH_MODELS=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "kgraph.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
