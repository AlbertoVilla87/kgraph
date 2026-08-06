# Knowledge Graph Builder Graph

## Overview

Experimenting with multiple approaches to knowledge graph construction from documents_

- Approach 1: spaCy/AutoPhrase + BERTopic + GLiNER
- Approach 2: LLM...

## Installation

### Install dependencies

```bash
uv sync
```

### Download the models

Run this once (or whenever you need to refresh the local cache):

```bash
uv run hf download urchade/gliner_multi-v2.1 --local-dir models/gliner_multi-v2.1
```

## Project Structure

```text
.
├── README.md
├── configs
│   └── params.yaml
├── data
│   └── case_1
│       └── mortgage.txt
├── experiments
│   └── exp_01_explore_docling.ipynb
├── models
│   └── gliner-relex-large-v0.5
│       ├── README.md
│       ├── added_tokens.json
│       ├── gliner_config.json
│       ├── model.bf16.safetensors
│       ├── model.fp16.safetensors
│       ├── model.safetensors
│       ├── special_tokens_map.json
│       ├── spm.model
│       ├── tokenizer.json
│       ├── tokenizer_config.json
│       └── trainer_state.json
├── pyproject.toml
├── src
│   └── kgraph
│       ├── __init__.py
│       ├── __pycache__
│       ├── cli
│       ├── extractors
│       ├── graph
│       ├── ingestion
│       └── retriever
└── uv.lock
```

## Usage

### Gliner + KnowledgeGraph + Retrieval

```sh
uv run gliner-demo
```