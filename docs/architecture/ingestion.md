# Ingestion

Ingestion turns raw files or remote queries into `RawDocument`s. It is the only stage that talks to the outside world; everything downstream consumes plain documents.

## The `DataSource` interface

All sources implement a single abstract method (`ingestion/base.py`):

```python
class DataSource(ABC):
    @abstractmethod
    def fetch(self) -> list[RawDocument]: ...
```

`build_data_source()` (`ingestion/factory.py`) picks the implementation from the `data_source` block in `configs/params.yaml`:

```python
def build_data_source(config: DataSourceConfig) -> DataSource:
    if config.type == "local_files":
        return LocalFileSource(folder=config.folder, file_type=config.file_type)
    if config.type == "arxiv":
        return ArxivSource(query=config.query, max_results=config.max_results)
    raise ValueError(f"Unknown data source type: {config.type}")
```

Adding a new source (IEEE, a database, ...) is just another `DataSource` implementation — the extraction pipeline never changes.

## Local files

`LocalFileSource` reads a folder of documents. Supported types are dispatched by `parsers/parsers.py`:

| Type | Parser | Notes |
| --- | --- | --- |
| `txt` | `parse_txt` | raw text, no metadata |
| `md` | `parse_markdown` | raw text; used to re-feed arXiv full-text exports |
| `json` | `parse_json` | `text` field + remaining keys as metadata |
| `pdf` | `parse_pdf` | docling conversion (see below) |
| `csv` | `parse_csv` | **not implemented yet** (`NotImplementedError`) |

## PDF parsing with docling

`parse_pdf_document` keeps the structured `DoclingDocument` (not just its markdown export) — that is what enables section-aware segmentation downstream.

```python
def parse_pdf_document(path: Path):
    converter = _get_converter()
    result = converter.convert(path)
    return result.document
```

The converter is a process-wide singleton (created once per process) because initialization checks the layout/table/OCR models against HuggingFace Hub. Environment is pinned in `parsers.py` so parsing works fully offline:

- `HUGGINGFACE_HUB_CACHE` → `models/hub` (the Hub cache layout downloaded during setup)
- `HF_HUB_OFFLINE=1` → never reach out to a live Hub
- `DOCLING_INFERENCE_COMPILE_TORCH_MODELS=false` → skips torch compile (faster startup)

## arXiv

`ArxivSource` (`ingestion/arxiv.py`) is the only remote source implemented. Built when `data_source.type` is `arxiv`:

- `fetch()` — one abstract-level `RawDocument` per arXiv API result, with paper metadata (title, authors, dates, `arxiv_id`, URLs) in `metadata`.
- `download_pdfs()` — saves each PDF to a folder (idempotent), so the corpus can be cached for later analysis.
- `fetch_fulltext()` — downloads the PDFs and parses them with docling (the same parser as the local PDF pipeline), writing `<arxiv_id>.md` next to each PDF; those files can be re-fed to the pipeline with `LocalFileSource(folder=..., file_type="md")`.

```sh
uv run arxiv-demo --query '"chain of thought" AND "reinforcement learning"' --max-results 20
uv run arxiv-demo --fulltext --max-results 20 --download-dir data/arxiv_pdfs
```

IEEE and other sources plug in as additional `DataSource` implementations without touching the extraction pipeline (see [Roadmap](../roadmap.md)).

## arXiv full text via ar5iv HTML (fast path)

For the citation-guided pipeline (`api/runner.py::_fetch_arxiv_html`), full text is fetched from **ar5iv** as semantic HTML instead of downloading a PDF and running docling. This is much faster — it skips the PDF parse (docling layout/table/OCR) entirely and needs no locally-downloaded docling models.

```python
url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
resp = _http.get(url)                    # httpx, connection-pooled
soup = BeautifulSoup(resp.text, "html.parser")

# Body: every section before the bibliography
bib_section = soup.find("section", id="bib")

# References: <li class="ltx_bibitem"> items
bib_list = bib_section.find("ul", class_="ltx_biblist")
```

- **Body text** is assembled from the sections preceding the `section#bib` bibliography element; if no bibliography is found it falls back to the whole `<article>`/`<body>`.
- **Reference text** comes from the structured `<li class="ltx_bibitem">` items of `ul.ltx_biblist`, which are then re-prefixed with `- ` so the existing bibliography parser consumes them unchanged.
- Body and refs are truncated to `citation.max_chars` (24 000) per document.
- Requests use a shared `httpx.Client` (connection pooling, retries with exponential backoff on HTTP 429/some request errors).

> **Getting the full text this way is faster than PDF+docling and needs no extra models.** The docling-based path below remains for local files and for sources where ar5iv HTML is unavailable.

## Configuration

```yaml
# configs/params.yaml
data_source:
  type: "local_files"      # local_files | arxiv
  folder: "data/arxiv_pdfs"
  file_type: "pdf"
```

`DataSourceConfig` also carries `query` and `max_results` (used only by the arXiv source).
