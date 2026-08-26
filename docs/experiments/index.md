# Experiments

Exploratory work lives in `backend/experiments/` as Jupyter notebooks. They are **records of observations and intuition, not final results** — each one documents what was tried, what was measured, and what it suggested for the pipeline.

## Index

| Experiment | Notebook | Question | Outcome |
| --- | --- | --- | --- |
| 01 — Explore docling | `exp_01_explore_docling.ipynb` | How does docling parse PDFs (layout, tables, markdown export)? | Setup stub; docling became the ingestion/parsing layer |
| 02 — Qwen vs KeyBERT | `exp_02_qwen_versus_keybert.ipynb` | Which seed route feeds GLiNER better — document-local keywords or abstract LLM concepts? | KeyBERT stays grounded; Qwen abstracts further but the comparison is not yet conclusive. Led to adaptive KeyBERT + deterministic discovery. → [notebook](exp_02_qwen_versus_keybert.ipynb) |
| 04 — Seed citation graph | `exp_04_seed_citation_graph.ipynb` | Can the seed's own citations define the GLiNER taxonomy? Qwen reads each citing context → `{concepts, relations}` → zero-shot labels over every reference full text → graph split into core / seed-only / refs-only. | **Implemented** as citation-guided discovery in the pipeline. See [Citation-guided discovery](../architecture/discovery.md#citation-guided-discovery-alternative). → [notebook](exp_04_seed_citation_graph.ipynb) |

## Other routes in the repo

Explored earlier and still in the codebase, but **not** part of the discovery pipeline:

- **Qwen3 via LiteLLM** (`kgraph/llms/litellm_client.py`, `uv run qwen-demo`) — asks a local Ollama model for semantic concepts with a strict Pydantic JSON schema. It was the original discovery engine; the experiment showed a small model hallucinates evidence and generic relations, which is why discovery is now deterministic.
- **GLiNER standalone** (`kgraph/extractors/gliner.py`, `uv run gliner-demo`) — builds a `networkx.MultiDiGraph` from the **static** entity/relation types in `params.yaml` and powers `GLiNERRetriever`. In the assembled pipeline the same class is reused, but fed with the taxonomy discovered by stages 1–3.

## Writing a new experiment

1. Create `backend/experiments/exp_NN_<short_name>.ipynb`.
2. Open with the kgraph kernel (`uv run jupyter` from `backend/`).
3. When the outcome informs a pipeline decision, record it here: the question, what was measured, the takeaway, and what it changed in the code.
