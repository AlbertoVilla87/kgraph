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
uv run hf download urchade/gliner_multi-v2.1 --local-dir models/gliner-relex-large-v0.5
uv run hf download sentence-transformers/all-MiniLM-L6-v2 --local-dir models/all-MiniLM-L6-v2
```

## Project Structure

```text
├── README.md
├── configs
│   └── params.yaml
├── data
│   └── case_1
│       └── mortgage.txt
├── experiments
│   └── exp_01_explore_docling.ipynb
├── models
│   ├── all-MiniLM-L6-v2
│   │   ├── 1_Pooling
│   │   ├── README.md
│   │   ├── config.json
│   │   ├── config_sentence_transformers.json
│   │   ├── data_config.json
│   │   ├── model.safetensors
│   │   ├── modules.json
│   │   ├── onnx
│   │   ├── openvino
│   │   ├── pytorch_model.bin
│   │   ├── rust_model.ot
│   │   ├── sentence_bert_config.json
│   │   ├── special_tokens_map.json
│   │   ├── tf_model.h5
│   │   ├── tokenizer.json
│   │   ├── tokenizer_config.json
│   │   ├── train_script.py
│   │   └── vocab.txt
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

### KeyBERT demo

```sh
uv run gliner-demo
```