# Astrolabe — backend

> **Full technical docs** (architecture, config reference, demos, experiments, roadmap, troubleshooting) live in the repo's documentation site — a standalone docs project at the repo root (`pyproject.toml`, own venv). Build it with `uv sync && uv run mkdocs serve` from the repo root, or read the sources under [`docs/`](../docs/). This README covers backend setup and the CLI demos.

## Overview

A state-of-the-art explorer for any research topic. Papers from sources like arXiv and IEEE are turned into an accumulated knowledge graph that maps the field, exposes originality, and surfaces unexplored gaps.

- Assembly pipeline (current): citation-guided discovery (Qwen3 taxonomy) → per-document GLiNER extraction → canonicalization → classification (core / seed-only / refs-only)

### What you can do with it

| Question | How |
| --- | --- |
| What does the field look like? | `uv run citation-demo --seed <id>` builds the graph from a paper's references (writes `output/citation_kg.json`); `uv run graph-viz` renders it as an interactive HTML |
| Is my idea already published? | Any idea you think of becomes a GLiNER label (zero-shot) — run it against the corpus and see if it appears and how it connects (planned) |
| What is original? | Compare a new paper against the accumulated topic graph: novel nodes/edges stand out structurally (planned) |
| What hasn't been explored? | Rare/absent concepts and relations in the graph are candidate gaps (planned) |

> The arXiv harvester is implemented; IEEE and the accumulated/originality layers are designed but not yet implemented — the pipeline can also read a local corpus folder.

## Installation

### Install dependencies

```bash
uv sync
```

### Download the models

Run this once (or whenever you need to refresh the local cache):

#### NER + relation extraction

```bash
uv run hf download urchade/gliner_multi-v2.1 --local-dir models/gliner-relex-large-v0.5
```

#### Citation discovery (Qwen3 via Ollama)

```bash
brew install --cask ollama
ollama pull qwen3:0.6b
```

> `models/` is git-ignored; the paths are configured in `configs/params.yaml` (`ner.name`, `citation.ollama_model`).

#### Docling (PDF parsing)

docling parses PDFs with ML models (layout + table structure) that are pulled
from HuggingFace Hub. They are cached under `models/hub/` so parsing is fully
offline (`HF_HUB_OFFLINE=1`); the cache path is set in `parsers.py` via
`HUGGINGFACE_HUB_CACHE`. Download them once:

```bash
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-layout-heron
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-models
```

> These two downloads populate `models/hub/models--docling-project--...` with
> the Hub cache layout (refs/snapshots). Without them docling cannot convert
> PDFs, and it must never be pointed at a live Hub — `HF_HUB_OFFLINE=1` is set
> in `parsers.py` on purpose.

#### LLM

Install Ollama (macOS):

```bash
brew install --cask ollama
```

Download model (Qwen 0.6b)

```bash
ollama pull qwen3:0.6b
```

> The LLM is **required** for the citation pipeline: Qwen3 builds the taxonomy
> from the seed's references (API and `citation-demo`), canonicalizes entities,
> and classifies nodes (core / seed-only / refs-only). GLiNER and docling run
> fully locally. `qwen-demo` also uses it.

## Project Structure

```text
├── README.md
├── configs
│   └── params.yaml
├── data
│   └── case_2
│       └── medium.txt
├── experiments
│   ├── exp_01_explore_docling.ipynb
│   └── exp_02_qwen_versus_keybert.ipynb
├── models
│   ├── gliner-relex-large-v0.5
│   └── hub                 # docling models (HF cache layout, offline)
├── pyproject.toml
├── src
│   └── kgraph
│       ├── cli
│       │   ├── arxiv_demo.py        # arxiv-demo (search arXiv, download PDFs, full-text)
│       │   ├── citation_demo.py     # citation-demo (seed → references → Qwen taxonomy)
│       │   ├── gliner_graph_demo.py # gliner-demo
│       │   ├── graph_viz.py         # graph-viz
│       │   └── qwen_demo.py         # qwen-demo
│       ├── discovery
│       │   ├── bibliography.py      # parse References → entries (arXiv IDs, author–year)
│       │   ├── citation_assembly.py # CitationAssembly (citation → GLiNER → classification)
│       │   └── citation_graph.py    # Qwen discovery + taxonomy aggregation (ensure_ollama)
│       ├── extractors
│       │   ├── gliner.py            # GLiNERGraph, add_entity/add_relation/find_entity
│       │   └── normalization.py     # canonical(), EntityMerger
│       ├── graph
│       │   └── config.py            # PipelineConfig, EntityMergingConfig
│       ├── ingestion
│       │   ├── arxiv.py             # ArxivSource (arXiv API → RawDocument + PDF download)
│       │   ├── base.py              # DataSource interface
│       │   ├── factory.py           # build_data_source() (local_files | arxiv)
│       │   └── local_files.py
│       └── retriever
└── uv.loc
```

`output/` (pipeline exports) is git-ignored.

## Usage

### Arxiv demo

Harvest papers from the arXiv API (abstracts) and optionally download + parse the full text:

```sh
uv run arxiv-demo                          # 5 CoT/RL papers, abstracts only
uv run arxiv-demo --query '"LLM agents"' --max-results 10
uv run arxiv-demo --fulltext --max-results 2   # download PDFs + docling full text
```

`--fulltext` downloads each PDF to `data/arxiv_pdfs/` (default) and writes the parsed markdown next to it as `<arxiv_id>.md` — that folder can be re-fed to the pipeline with a `data_source` of `local_files` and `file_type: md`.

### Citation demo (production)

Builds the knowledge graph from a seed paper and its references (Qwen taxonomy → per-document GLiNER → classification):

```sh
uv run citation-demo --seed 2404.16130                       # writes output/citation_kg.json
uv run citation-demo --seed 2404.16130 --output out/cit.json
uv run citation-demo --seed 2404.16130 --max-refs 10
```

### QWEN demo

```sh
uv run qwen-demo
```

### Visualize the graph

```sh
uv run graph-viz output/citation_kg.json   # writes output/citation_kg.json.html
```

### Gliner + KnowledgeGraph + Retrieval

```sh
uv run gliner-demo
```