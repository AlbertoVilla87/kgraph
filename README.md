# Downloading models locally

This project uses two Hugging Face models that are **not** checked into
the repo (they're large binary files and don't belong in git history).
Download them once to a local `models/` folder before running anything
that depends on the chunker or the GLiNER extraction pipeline.

## What gets downloaded

| Model | Purpose |
|---|---|
| `microsoft/mdeberta-v3-base` | Tokenizer backbone used by `MarkdownChunker` to measure real token counts |
| `urchade/gliner_multi-v2.1` | Multilingual GLiNER checkpoint used for entity extraction |

## 1. Install dependencies

With `uv`:

```bash
uv add huggingface_hub transformers torch gliner
```

With plain `pip`:

```bash
pip install huggingface_hub transformers torch gliner
```

## 2. Download the models

Run this once (or whenever you need to refresh the local cache):

```bash
uv run python scripts/download_models.py
```

Or with plain Python:

```bash
python scripts/download_models.py
```

`scripts/download_models.py`:

```python
from huggingface_hub import snapshot_download

MODELS = [
    "microsoft/mdeberta-v3-base",
    "urchade/gliner_multi-v2.1",
]

for repo_id in MODELS:
    local_dir = f"models/{repo_id.split('/')[-1]}"
    print(f"Downloading {repo_id} -> {local_dir}")
    snapshot_download(repo_id=repo_id, local_dir=local_dir)

print("Done.")
```

Alternatively, using the `huggingface-cli`:

```bash
uv run huggingface-cli download microsoft/mdeberta-v3-base --local-dir models/mdeberta-v3-base
uv run huggingface-cli download urchade/gliner_multi-v2.1 --local-dir models/gliner_multi-v2.1
```

## 3. Keep `models/` out of git

Add this to `.gitignore`:

```
models/
```

Everyone on the team runs the download script once locally instead of
pulling model weights through git.

## 4. Point the code at the local folder

Once downloaded, load everything from the local path instead of the
Hugging Face repo id — this also means the code works offline after
the first download.

```python
from markdown_chunker_gliner import MarkdownChunker

chunker = MarkdownChunker(
    tokenizer_name="models/mdeberta-v3-base",
    max_tokens=350,
    overlap_tokens=30,
)
```

```python
from gliner import GLiNER

model = GLiNER.from_pretrained("models/gliner_multi-v2.1")
```

## Notes

- `AutoTokenizer.from_pretrained` and `GLiNER.from_pretrained` both
  accept a local folder path transparently — no code changes needed
  beyond swapping the repo id for the local path.
- If `models/` doesn't exist yet, `transformers`/`gliner` will try to
  hit the network and fail in offline environments — run the download
  script first.
- If you're on a machine with no network access at all (e.g. an air-gapped
  server), download the models elsewhere and copy the `models/` folder
  over manually — the folder is self-contained.
