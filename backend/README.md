# Knowledge Graph Builder Graph

## Overview

Experimenting with multiple approaches to knowledge graph construction from documents_

- Approach 1: spaCy/AutoPhrase + BERTopic + GLiNER
- Approach 2: LLM...
- Assembly pipeline (current): Adaptive KeyBERT seeds → LLM-free topic-guided discovery (spaCy) → GLiNER with the discovered taxonomy

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
│   └── gliner-relex-large-v0.5
├── pyproject.toml
├── src
│   └── kgraph
│       ├── cli
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
│       └── retriever
└── uv.loc
```

`output/` (assembly exports) is git-ignored.

## Usage

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