# Knowledge Graph Builder Graph

## Overview

A state-of-the-art explorer for any research topic. Papers from sources like arXiv and IEEE are turned into an accumulated knowledge graph that maps the field, exposes originality, and surfaces unexplored gaps.

- Approach 1: spaCy/AutoPhrase + BERTopic + GLiNER
- Approach 2: LLM...
- Assembly pipeline (current): Adaptive KeyBERT seeds → LLM-free topic-guided discovery (spaCy) → GLiNER with the discovered taxonomy

### What you can do with it

| Question | How |
| --- | --- |
| What does the field look like? | `uv run assembly-demo` builds the topic graph and exports `output/kg_final.json`; `uv run graph-viz` renders it as an interactive HTML |
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

#### Keywords Extractor

```bash
uv run hf download sentence-transformers/all-MiniLM-L6-v2 --local-dir models/all-MiniLM-L6-v2
```

#### NER

```bash
uv run hf download urchade/gliner_multi-v2.1 --local-dir models/gliner-relex-large-v0.5
```

#### SpaCy (topic discovery)

Download `en_core_web_sm` into `models/en_core_web_sm` so the discovery stage
is fully local and self-contained:

```bash
curl -L -o /tmp/en_core_web_sm.whl \
  https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
unzip -o -q /tmp/en_core_web_sm.whl -d /tmp/en_core_web_sm_pkg
mkdir -p models/en_core_web_sm
cp -R /tmp/en_core_web_sm_pkg/en_core_web_sm/en_core_web_sm-3.8.0/. models/en_core_web_sm/
rm -rf /tmp/en_core_web_sm.whl /tmp/en_core_web_sm_pkg
```

`models/` is git-ignored; the path is configured via `discovery.spacy_model`
in `configs/params.yaml`.

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

> The LLM is optional for the assembly pipeline: discovery is deterministic
> (spaCy) and GLiNER runs locally. `qwen-demo` uses Ollama only.

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
│   ├── all-MiniLM-L6-v2
│   ├── en_core_web_sm
│   ├── gliner-relex-large-v0.5
│   └── hub                 # docling models (HF cache layout, offline)
├── pyproject.toml
├── src
│   └── kgraph
│       ├── cli
│       │   ├── arxiv_demo.py        # arxiv-demo (search arXiv, download PDFs, full-text)
│       │   ├── assembly_demo.py     # assembly-demo
│       │   ├── gliner_graph_demo.py # gliner-demo
│       │   ├── graph_viz.py         # graph-viz
│       │   ├── key_bert_demo.py     # kbert-demo
│       │   ├── qwen_demo.py         # qwen-demo
│       │   └── topic_discovery_demo.py # discovery-demo
│       ├── discovery
│       │   ├── assembly.py          # DiscoveryAssembly (discovery → GLiNER taxonomy)
│       │   ├── dependency_relations.py
│       │   └── topic_graph.py
│       ├── extractors
│       │   ├── gliner.py            # GLiNERGraph, add_entity/add_relation/find_entity
│       │   ├── key_bert.py          # AdaptiveKeyBERT
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

`output/` (assembly exports) is git-ignored.

## Usage

### Arxiv demo

Harvest papers from the arXiv API (abstracts) and optionally download + parse the full text:

```sh
uv run arxiv-demo                          # 5 CoT/RL papers, abstracts only
uv run arxiv-demo --query '"LLM agents"' --max-results 10
uv run arxiv-demo --fulltext --max-results 2   # download PDFs + docling full text
```

`--fulltext` downloads each PDF to `data/arxiv_pdfs/` (default) and writes the parsed markdown next to it as `<arxiv_id>.md` — that folder can be re-fed to the pipeline with a `data_source` of `local_files` and `file_type: md`.

### QWEN demo

```sh
uv run qwen-demo
```

### Topic discovery demo

```sh
uv run discovery-demo
```

### Assembly: discovery → GLiNER

Builds the final knowledge graph with the discovered taxonomy and exports it to JSON:

```sh
uv run assembly-demo                       # prints graph + writes output/kg_final.json
uv run assembly-demo --output out/g.json   # custom export path
```

### Visualize the graph

```sh
uv run graph-viz output/kg_final.json      # writes output/kg_final.json.html
```

### Corpus graph: multi-document comparison

Builds a cross-document graph from a folder of PDFs: per-document taxonomies
(Adaptive KeyBERT → spaCy discovery → GLiNER with relations), then merges the
graphs and labels every node/edge as **common** (present in ≥2 documents) or
**unique** to a document (originality view):

```sh
uv run corpus-demo                                        # local data source
uv run corpus-demo --fetch 5 --arxiv-query '"LLM agents"' # download arXiv PDFs first
uv run corpus-demo --workers 4 --max-pages 10             # parallel + drop long PDFs
uv run corpus-demo --output-json out/g.json --output-html out/g.html
```

The interactive HTML (vis-network) colors common nodes/edges in green and
unique ones per document, with a summary/novelty panel and a per-document
filter. Nodes without edges are not rendered. Progress is shown with tqdm
bars for the three stages (docling parsing, taxonomy, GLiNER extraction).

### Gliner + KnowledgeGraph + Retrieval

```sh
uv run gliner-demo
```

### KeyBERT demo

```sh
uv run kbert-demo
```

### QWEN demo

```sh
uv run qwen-demo
```