# Quickstart

All commands run from `backend/` unless noted otherwise.

## 1. Install dependencies

```bash
cd backend
uv sync
```

## 2. Download the models (one time)

The pipeline is fully local. The `models/` directory is git-ignored; the paths are configured in `configs/params.yaml`.

**Keywords extractor** (KeyBERT / sentence embeddings):

```bash
uv run hf download sentence-transformers/all-MiniLM-L6-v2 --local-dir models/all-MiniLM-L6-v2
```

**NER + relation extraction** (GLiNER):

```bash
uv run hf download urchade/gliner_multi-v2.1 --local-dir models/gliner-relex-large-v0.5
```

**SpaCy** (topic discovery) — download `en_core_web_sm` so the discovery stage is fully local:

```bash
curl -L -o /tmp/en_core_web_sm.whl \
  https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
unzip -o -q /tmp/en_core_web_sm.whl -d /tmp/en_core_web_sm_pkg
mkdir -p models/en_core_web_sm
cp -R /tmp/en_core_web_sm_pkg/en_core_web_sm/en_core_web_sm-3.8.0/. models/en_core_web_sm/
rm -rf /tmp/en_core_web_sm.whl /tmp/en_core_web_sm_pkg
```

**Docling** (PDF parsing) — pulls the layout/table models into `models/hub/` so parsing works offline (`HF_HUB_OFFLINE=1`):

```bash
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-layout-heron
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-models
```

> The LLM (Ollama + Qwen3 0.6b) is **optional** — discovery is deterministic (spaCy) and GLiNER runs locally. Only `qwen-demo` uses it.

## 3. Build your first graph

The default corpus is `data/case_2/medium.txt` (a blog-style document on LLM reasoning):

```bash
uv run assembly-demo
```

This runs discovery → segmented GLiNER extraction and prints the final graph with scores and occurrence counts, writing it to `output/kg_final.json`. Render it as an interactive HTML:

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
| Compare several documents (common vs. unique) | `uv run corpus-demo` |
| Harvest papers from arXiv | `uv run arxiv-demo --query '"LLM agents"' --max-results 10` |
| Control segmentation explicitly | `uv run segmented-demo --show-segments` |
| See every CLI entry point | [Demos](demos.md) |

Full setup and usage details: [Architecture](architecture/index.md), [Data model & configuration](architecture/data-model.md).
