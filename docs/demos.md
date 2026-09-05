# Demos

Every entry point below is a console script defined in `backend/pyproject.toml` (`[project.scripts]`) and run through `uv run <name>` from `backend/`.

## CLI reference

| CLI entry | What it does |
| --- | --- |
| `uv run arxiv-demo` | Harvest papers from the arXiv API (abstracts); `--fulltext` downloads the PDFs and parses them with docling |
| `uv run citation-demo --seed <id>` | Production pipeline: seed bibliography → Qwen3 taxonomy → per-document GLiNER extraction → classification (core / seed-only / refs-only); exports `output/citation_kg.json` by default |
| `uv run graph-viz output/citation_kg.json` | Renders a graph JSON into a standalone interactive HTML (vis-network), colored by `entity_type` with a legend |
| `uv run qwen-demo` | Utility — runs Qwen3 concept extraction with structured output (requires Ollama) |
| `uv run gliner-demo` | Utility — builds a graph with GLiNER using the **static** taxonomy in `params.yaml` and runs a retrieval query |

## Typical commands

**arXiv harvester** (abstracts, full text, or both):

```sh
uv run arxiv-demo                              # 5 CoT/RL papers, abstracts only
uv run arxiv-demo --query '"LLM agents"' --max-results 10
uv run arxiv-demo --fulltext --max-results 2   # download PDFs + docling full text
```

`--fulltext` downloads each PDF to `data/arxiv_pdfs/` (default) and writes the parsed markdown next to it as `<arxiv_id>.md`. That folder can be re-fed to the pipeline with a `data_source` of `local_files` and `file_type: md`.

**Citation (production):**

```sh
uv run citation-demo --seed 2404.16130                        # primary pipeline
uv run citation-demo --seed 2404.16130 --output out/cit.json  # custom export path
uv run citation-demo --seed 2404.16130 --max-refs 10          # limit references resolved
```

**Visualize:**

```sh
uv run graph-viz output/citation_kg.json   # writes output/citation_kg.json.html
```

## Behind the scenes

Each demo maps to a module under `backend/src/kgraph/cli/`:

| Entry point | Module |
| --- | --- |
| `arxiv-demo` | `cli/arxiv_demo.py` |
| `citation-demo` | `cli/citation_demo.py` |
| `graph-viz` | `cli/graph_viz.py` |
| `qwen-demo` | `cli/qwen_demo.py` |
| `gliner-demo` | `cli/gliner_graph_demo.py` |

The legacy stack (topic-guided discovery, full-assembly pipeline, and multi-document corpus graph, driven by KeyBERT / spaCy) was **removed** in the model cleanup — `discovery-demo`, `assembly-demo`, `segmented-demo`, `corpus-demo`, and `kbert-demo` no longer exist as entry points. Their modules were deleted from `backend/src/kgraph/` (see [Discovery](architecture/discovery.md) and [Assembly](architecture/assembly.md) for why).