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
└── uv.loc
```

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

```sh
uv run assembly-demo
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