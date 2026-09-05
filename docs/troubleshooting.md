# Troubleshooting

## Model setup

### `models/` missing or a demo fails at model load

The `models/` directory is git-ignored — download the models once (see [Quickstart](quickstart.md)). Paths are configured in `backend/configs/params.yaml` (`ner.name`, `citation.ollama_model`, `citation.ollama_api_base`).

### docling can't convert PDFs / tries to reach the Hub

`parsers.py` pins `HF_HUB_OFFLINE=1` and `HUGGINGFACE_HUB_CACHE=models/hub` on purpose. If parsing fails, the docling models are not cached: run

```bash
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-layout-heron
HUGGINGFACE_HUB_CACHE=models/hub uv run hf download docling-project/docling-models
```

### GLiNER emits `Sentence of length N has been truncated to 1024`

You hit the whole-document path (segmentation disabled). The segmented extractor fixes this — make sure `segmentation.enabled: true` in `params.yaml`.

## Running the demos

### `uv run <demo>` fails with "command not found" / module errors

Make sure you are in `backend/` (the console scripts and `.venv` live there) and that `uv sync` was run. Any demo that runs discovery (`citation-demo`, `qwen-demo`) needs Ollama with `qwen3:0.6b` pulled — `ensure_ollama()` auto-launches `ollama serve` when it is not running.

### `graph-viz` needs a graph JSON first

`graph-viz` renders an existing export. Run `uv run citation-demo --seed <id>` (writes `output/citation_kg.json`) first.

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
| CSV parsing not implemented | [Ingestion](architecture/ingestion.md) | `parse_csv` raises `NotImplementedError` |
| GLiNER truncates long documents when segmentation is disabled | [Assembly](architecture/assembly.md) | keep the segmented extractor enabled (default) |
