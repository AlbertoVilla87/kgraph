# KG Builder Lab

## Introduction

Experimenting with multiple approaches to knowledge graph construction from documents

---

## Approaches

-  Adaptive KeyBERT + Topic Discovery
-  Assembly pipeline: discovery-driven GLiNER taxonomy (current, `ft/assembly_gliner`)

### What's new in the assembly branch

- **Discovery → GLiNER closed loop** (`DiscoveryAssembly`): the topic graph discovered by stages 1–3 provides the entity/relation taxonomy handed to GLiNER — no hand-written labels.
- **GLiNER-compatible labels**: multi-word taxonomy is underscore-joined (`dumping papers` → `dumping_papers`) because GLiNER tokenizes labels on whitespace.
- **Entity normalization & merging** (`kgraph/extractors/normalization.py`): `canonical()` strips case/whitespace/leading articles and `EntityMerger` collapses token-subset near-duplicates (`model` ⊆ `reasoning model`) when `entity_merging.enabled` is set in `params.yaml`.
- **Mention dedup fix**: the same entity extracted multiple times no longer double-counts its mentions.
- **Tooling**: `assembly-demo --output` exports `kg_final.json`; `graph-viz` renders it as an interactive HTML (vis-network).
- **Known caveat**: GLiNER truncates documents longer than its 1024-token context (warning at `processor.py`); chunking is the planned fix.

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