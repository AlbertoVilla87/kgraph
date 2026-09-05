# Astrolabe

> **Astrolabe** — the instrument that mapped the heavens and guided exploration. This tool does the same for the state of the art of any research topic: it maps the field as a knowledge graph, lets you navigate it, and points at what is original and what is missing.

![ArXiv Graph Explorer — frontend skeleton](assets/app_skeleton.png)

A tool to know the **state of the art of any topic** from the research sources that matter (arXiv, IEEE, ...) and to act on it:

- **Map the field** — an accumulated knowledge graph per topic shows the concepts and how they relate, with confidence and frequency.
- **Spot originality** — a new paper or idea compared against the accumulated graph reveals novel nodes, edges, and combinations even when the wording overlaps with prior work.
- **Find the gaps** — rare or absent concepts/relations are inspiration for unexplored directions.
- **Check an idea instantly** — because GLiNER is zero-shot, any topic the user thinks of becomes a label, and we can ask whether it appears in the corpus and how it connects.

The current pipeline is the **citation-guided GLiNER assembly**: Qwen3 (a small local model) reads the seed paper's references and derives the concept/relation taxonomy, GLiNER extracts the final knowledge graph using exactly those labels, and nodes are canonicalized and classified core / seed-only / refs-only — no hand-written labels.

## Status

Implemented:

- **arXiv harvester** — topic query → seed paper + references full text (ar5iv HTML, or PDF download + docling parsing)
- **Citation-guided discovery** — bibliography parsing, citing-context matching, Qwen3 taxonomy (concepts, types, relations)
- **Per-document GLiNER assembly with canonicalization** — each reference gets its own labels; entities canonicalized and merged
- **Node classification** — core / seed-only / refs-only as an originality proxy
- **Segmentation** — section-aware, token-bounded segments beat the 1024-token GLiNER window

Planned / designed:

- **Accumulated topic graph** — one graph per topic that grows as documents are added (today each run builds a fresh graph)
- **Originality / gap signals** — WL-kernel / embedding comparison against the accumulated graph
- **GLiNER idea check** — ask the accumulated graph whether a user idea exists and how it connects
- **IEEE harvester** (and similar sources) — arXiv is implemented, others plug in as `DataSource` implementations

See the [roadmap](roadmap.md) for the full picture.

## Where to start

| If you want to... | Go to |
| --- | --- |
| Understand the problem and the idea | [Overview](overview.md) |
| Install and run the pipeline on a document | [Quickstart](quickstart.md) |
| See the pipeline end to end | [Architecture](architecture/index.md) |
| Run each CLI demo | [Demos](demos.md) |
| Know what works and what's missing | [Roadmap](roadmap.md) |
| Fix a problem | [Troubleshooting](troubleshooting.md) |

## Repository layout

```
kgraph/
├── mkdocs.yml                 # this documentation site
├── docs/                      # documentation sources (what you are reading)
├── backend/                   # Python package, demos, experiments, models, data
│   ├── src/kgraph/            # the pipeline (ingestion, discovery, extractors, ...)
│   ├── src/kgraph/api/        # FastAPI REST API for frontend integration
│   ├── experiments/           # Jupyter notebooks
│   ├── configs/params.yaml    # pipeline configuration
│   ├── data/                  # data: case_1/, case_2/, arxiv_pdfs/
│   └── models/                # local models (git-ignored)
└── frontend/                  # React + TypeScript frontend (ArXiv Graph Explorer)
    └── src/
        ├── components/        # Layout, KnowledgeGraph (Cytoscape.js)
        └── pages/             # Overview, Graph Explorer, Shared Insights, ...
```

Build and preview the docs locally (docs have their own environment at the repo root, decoupled from `backend/`):

```bash
uv sync
uv run mkdocs serve
```

Open `http://127.0.0.1:8000`. To deploy elsewhere, `uv sync && uv run mkdocs build` produces a static site in `site/`.
