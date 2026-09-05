# Quickstart

All commands run from `backend/` unless noted otherwise.

## 1. Install dependencies

```bash
cd backend
uv sync
```

## 2. Download the models (one time)

The pipeline is fully local. The `models/` directory is git-ignored; the paths are configured in `configs/params.yaml`.

**NER + relation extraction** (GLiNER):

```bash
uv run hf download urchade/gliner_multi-v2.1 --local-dir models/gliner-relex-large-v0.5
```

**Citation discovery** (Qwen3 via Ollama) — required for the concept/relation taxonomy that feeds GLiNER:

```bash
brew install --cask ollama
ollama pull qwen3:0.6b
```

**Docling** (PDF parsing) — pulls the layout/table models into `models/hub/` so parsing works offline (`HF_HUB_OFFLINE=1`):

```bash
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-layout-heron
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-models
```

> The LLM (Ollama + Qwen3 0.6b) is **required**: citation discovery (the API, `citation-demo`, `qwen-demo`) uses it to extract and canonicalize the taxonomy from the seed's references. GLiNER and docling run fully locally; there are no paid per-token API calls.

## 3. Build your first graph

With Ollama running and Qwen3 pulled, run the **citation pipeline** (the production path — Qwen builds the taxonomy from a seed paper's references, GLiNER extracts, nodes get classified and canonicalized):

```bash
uv run citation-demo --seed 2404.16130
# writes output/citation_kg.json (use --output for a custom path)
```

Render the result as an interactive HTML:

```bash
uv run graph-viz output/kg_final.json
# writes output/kg_final.json.html
```

## 4. Frontend (ArXiv Graph Explorer)

The React frontend visualizes the knowledge graph interactively.

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend connects to the FastAPI backend at `localhost:8000`.

To start the backend API:

```bash
cd backend
uv run uvicorn kgraph.api.main:app --reload --port 8000
```

## 5. Next steps

| Goal | Command |
| --- | --- |
| Harvest papers from arXiv | `uv run arxiv-demo --query '"LLM agents"' --max-results 10` |
| See the production pipeline on a seed paper | `uv run citation-demo --seed 2404.16130` |
| See every CLI entry point | [Demos](demos.md) |

Full setup and usage details: [Architecture](architecture/index.md), [Data model & configuration](architecture/data-model.md).
