# KG Builder Lab

## Introduction

A tool to know the **state of the art of any topic** from the research sources that matter (arXiv, IEEE, ...) and to act on it:

- **Map the field** — an accumulated knowledge graph per topic shows the concepts and how they relate, with confidence and frequency.
- **Spot originality** — a new paper or idea compared against the accumulated graph reveals novel nodes, edges, and combinations even when the wording overlaps with prior work.
- **Find the gaps** — rare or absent concepts/relations are inspiration for unexplored directions.
- **Check an idea instantly** — because GLiNER is zero-shot, any topic the user thinks of becomes a label, and we can ask whether it appears in the corpus and how it connects.

---

## Approaches

-  Adaptive KeyBERT + Topic Discovery
-  Assembly pipeline: discovery-driven GLiNER taxonomy (current, `ft/assembly_gliner`)

### The assembled pipeline

- **Discovery → GLiNER closed loop** (`DiscoveryAssembly`): the topic graph discovered by stages 1–3 provides the entity/relation taxonomy handed to GLiNER — no hand-written labels.
- **GLiNER-compatible labels**: multi-word taxonomy is underscore-joined (`dumping papers` → `dumping_papers`) because GLiNER tokenizes labels on whitespace.
- **Entity normalization & merging** (`kgraph/extractors/normalization.py`): `canonical()` strips case/whitespace/leading articles and `EntityMerger` collapses token-subset near-duplicates (`model` ⊆ `reasoning model`) when `entity_merging.enabled` is set in `params.yaml`.
- **Mention dedup fix**: the same entity extracted multiple times no longer double-counts its mentions.
- **Tooling**: `assembly-demo --output` exports `kg_final.json`; `graph-viz` renders it as an interactive HTML (vis-network).
- **Known caveat**: GLiNER truncates documents longer than its 1024-token context (warning at `processor.py`); chunking is the planned fix.

### The vision (this branch)

`ft/state_of_the_art` frames the tool around the state-of-the-art use case:

- **Sources**: arXiv and IEEE harvesters that fetch documents for a topic query (planned; the current pipeline reads a local folder).
- **Accumulated topic graph**: one graph per topic that grows as documents are added, instead of a fresh graph per run.
- **Originality signal**: compare a new paper/idea against the accumulated graph (WL-kernel / embeddings).
- **Gap discovery**: rare/absent concepts and relations become candidate unexplored directions.
- **GLiNER idea check**: a user-proposed idea, used as a GLiNER label, is tested against the corpus to see if it exists and how it connects.

---

## Installation

```bash
uv add mkdocs-material
uv run mkdocs serve
```

Open `http://127.0.0.1:8000` in your browser and you'll see the site running locally with live reload.

---

## Project structure

```
doc/
├── mkdocs.yml
└── docs/
    └── index.md
```

!!! tip "Adding more pages"
    Create new `.md` files inside `docs/` and register them in the `nav:` section of `mkdocs.yml`.