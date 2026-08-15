# Demos

Every entry point below is a console script defined in `backend/pyproject.toml` (`[project.scripts]`) and run through `uv run <name>` from `backend/`.

## CLI reference

| CLI entry | What it does |
| --- | --- |
| `uv run arxiv-demo` | Harvest papers from the arXiv API (abstracts); `--fulltext` downloads the PDFs and parses them with docling |
| `uv run discovery-demo` | KeyBERT seeds + topic-guided expansion (spaCy), prints the graph by depth |
| `uv run assembly-demo [--output path]` | Full pipeline: discovery then GLiNER with the discovered taxonomy; prints the final graph with scores and occurrence counts and exports it to `output/kg_final.json` by default. **Uses the segmented extractor by default.** |
| `uv run segmented-demo [--output path]` | Same assembled pipeline with explicit controls: `--show-segments` prints the per-document segment boundaries, `--no-segmentation` falls back to the whole-document (truncated) path |
| `uv run corpus-demo` | Multi-document graph: per-document taxonomy → parallel extraction → merged graph with a common/unique originality view |
| `uv run graph-viz output/kg_final.json` | Renders a graph JSON into a standalone interactive HTML (vis-network), colored by `entity_type` with a legend |
| `uv run kbert-demo` | Runs Adaptive KeyBERT over the configured document and prints the chosen keywords |
| `uv run qwen-demo` | Runs Qwen3 concept extraction with structured output (requires Ollama) |
| `uv run gliner-demo` | Builds the graph with GLiNER and runs a retrieval query |

## Typical commands

**arXiv harvester** (abstracts, full text, or both):

```sh
uv run arxiv-demo                              # 5 CoT/RL papers, abstracts only
uv run arxiv-demo --query '"LLM agents"' --max-results 10
uv run arxiv-demo --fulltext --max-results 2   # download PDFs + docling full text
```

`--fulltext` downloads each PDF to `data/arxiv_pdfs/` (default) and writes the parsed markdown next to it as `<arxiv_id>.md`. That folder can be re-fed to the pipeline with a `data_source` of `local_files` and `file_type: md`.

**Assembly:**

```sh
uv run assembly-demo                       # prints graph + writes output/kg_final.json
uv run assembly-demo --output out/g.json   # custom export path
```

**Visualize:**

```sh
uv run graph-viz output/kg_final.json      # writes output/kg_final.json.html
```

**Corpus (multi-document):**

```sh
uv run corpus-demo                                        # local data source
uv run corpus-demo --fetch 5 --arxiv-query '"LLM agents"' # download arXiv PDFs first
uv run corpus-demo --workers 4 --max-pages 10             # parallel + drop long PDFs
uv run corpus-demo --output-json out/g.json --output-html out/g.html
```

**Segmentation controls:**

```sh
uv run segmented-demo --show-segments     # print segment boundaries per document
uv run segmented-demo --no-segmentation   # fall back to the truncated whole-document path
```

## Behind the scenes

Each demo maps to a module under `backend/src/kgraph/cli/`:

| Entry point | Module |
| --- | --- |
| `arxiv-demo` | `cli/arxiv_demo.py` |
| `assembly-demo` | `cli/assembly_demo.py` |
| `segmented-demo` | `cli/segmented_demo.py` |
| `corpus-demo` | `cli/corpus_demo.py` |
| `graph-viz` | `cli/graph_viz.py` |
| `kbert-demo` | `cli/key_bert_demo.py` |
| `qwen-demo` | `cli/qwen_demo.py` |
| `gliner-demo` | `cli/gliner_graph_demo.py` |
| `discovery-demo` | `cli/topic_discovery_demo.py` |
