# Troubleshooting

## Model setup

### `models/` missing or a demo fails at model load

The `models/` directory is git-ignored — download the models once (see [Quickstart](quickstart.md)). Paths are configured in `backend/configs/params.yaml` (`ner.name`, `keyword_extractor.name`, `discovery.spacy_model`).

### docling can't convert PDFs / tries to reach the Hub

`parsers.py` pins `HF_HUB_OFFLINE=1` and `HUGGINGFACE_HUB_CACHE=models/hub` on purpose. If parsing fails, the docling models are not cached: run

```bash
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-layout-heron
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-models
```

### GLiNER emits `Sentence of length N has been truncated to 1024`

You hit the whole-document path (or `--no-segmentation`). The segmented extractor fixes this — make sure `segmentation.enabled: true` in `params.yaml` or run `uv run segmented-demo`.

## Running the demos

### `uv run <demo>` fails with "command not found" / module errors

Make sure you are in `backend/` (the console scripts and `.venv` live there) and that `uv sync` was run. For `qwen-demo` you also need Ollama running with `qwen3:0.6b` pulled.

### `graph-viz` needs a graph JSON first

`graph-viz` renders an existing export. Run `uv run assembly-demo` (writes `output/kg_final.json`) or `uv run corpus-demo --output-json out/g.json` first.

## CodeGraph / development tooling

| Symptom | Fix |
| --- | --- |
| `codegraph: command not found` | Make sure `~/.local/bin` is in `PATH`; verify with `which codegraph`. If missing, ensure the `export PATH="$HOME/.local/bin:$PATH"` line is in `~/.zshenv` (and `~/.zshrc`), then open a **new** shell. |
| opencode MCP shows CodeGraph as unavailable | The relative `codegraph` command couldn't be resolved when opencode spawned it — opencode inherited a stale `PATH` (e.g. from a long-lived shell started before the export was added). Relaunch opencode from a **new** shell/terminal. |
| `codegraph status` reports a stale/incomplete index | Run `codegraph sync`; if that doesn't help, `codegraph index`. |
| A stale lock blocks indexing | `codegraph unlock` |

Full setup: [Development / Tooling](development.md).

## Known limitations (by design)

| Limitation | Where | Workaround / plan |
| --- | --- | --- |
| Threads share one GLiNER model; `workers > 1` pins torch intra-op threads to 1 | [Segmentation](architecture/segmentation.md) | process-per-worker (one model copy each) for very large corpora |
| Cached `.md` files have no `DoclingDocument` → markdown-heading fallback | [Segmentation](architecture/segmentation.md) | re-parse the PDF to get section-aware chunks |
| Cross-document entity matching is lexical → inflates the novelty view | [Corpus](architecture/corpus.md) | semantic entity alignment is future work |
| `TopicGraph.build` accumulates state → must be fresh per document | [Corpus](architecture/corpus.md) | `CorpusGraphBuilder` builds one per document |
| CSV parsing not implemented | [Ingestion](architecture/ingestion.md) | `parse_csv` raises `NotImplementedError` |
| GLiNER truncates long documents on the whole-document path | [Assembly](architecture/assembly.md) | use the segmented extractor (default) |
