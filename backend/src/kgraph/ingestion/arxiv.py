from __future__ import annotations

import urllib.request
from pathlib import Path

import arxiv
from arxiv import SortCriterion

from kgraph.graph.models import RawDocument
from kgraph.ingestion.base import DataSource
from kgraph.ingestion.parsers.parsers import parse_pdf

_SORT_BY = {
    "relevance": SortCriterion.Relevance,
    "submitted_date": SortCriterion.SubmittedDate,
    "last_updated_date": SortCriterion.LastUpdatedDate,
}

_USER_AGENT = "kgraph/0.1 (arxiv-retriever; python urllib)"


class ArxivSource(DataSource):
    """Harvest papers from the arXiv API.

    ``fetch`` returns one ``RawDocument`` per result, with the abstract as the
    content and the paper metadata (title, authors, dates, IDs, URLs) in
    ``metadata``.

    The API only exposes abstracts. For full-text analysis the PDF must be
    downloaded first: :meth:`download_pdfs` saves them to a local folder so the
    existing local pipeline (docling) can parse them, or :meth:`fetch_fulltext`
    does download + parse in one step and returns ``RawDocument``s with the
    full text as content.
    """

    def __init__(
        self,
        query: str,
        max_results: int = 100,
        sort_by: str = "relevance",
        client: arxiv.Client | None = None,
    ):
        self.query = query
        self.max_results = max_results
        if sort_by not in _SORT_BY:
            raise ValueError(
                f"Unknown sort_by: {sort_by}. Available: {list(_SORT_BY)}"
            )
        self.sort_by = _SORT_BY[sort_by]
        self.client = client or arxiv.Client()

    def search(self) -> list[arxiv.Result]:
        """Run the query against the arXiv API and return the raw results."""
        search = arxiv.Search(
            query=self.query,
            max_results=self.max_results,
            sort_by=self.sort_by,
        )
        return list(self.client.results(search))

    def fetch(self) -> list[RawDocument]:
        """Return one abstract-level document per arXiv result."""
        return [self._to_document(result) for result in self.search()]

    def download_pdfs(
        self, download_dir: str | Path = "data/arxiv_pdfs"
    ) -> list[Path]:
        """Download the PDF of every result into ``download_dir``.

        Skips results without a PDF and files that already exist, so the call is
        idempotent and safe to re-run. Returns the paths of the saved PDFs.
        """
        out_dir = Path(download_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for result in self.search():
            path = self._download_pdf(result, out_dir)
            if path is not None:
                paths.append(path)
        return paths

    def fetch_fulltext(
        self, download_dir: str | Path = "data/arxiv_pdfs"
    ) -> list[RawDocument]:
        """Download the PDFs, parse them (docling) and persist the text.

        Each parsed document is written next to its PDF as
        ``<arxiv_id>.md`` (skipped on failure), so the corpus can be re-fed to
        the pipeline with a ``LocalFileSource(folder=..., file_type="md")``.
        Returns the ``RawDocument``s in memory.
        """
        out_dir = Path(download_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        parsed = []
        for result in self.search():
            path = self._download_pdf(result, out_dir)
            if path is None:
                continue
            text_path = path.with_suffix(".md")
            if not text_path.exists():
                try:
                    text, _ = parse_pdf(path)
                except Exception:
                    continue
                text_path.write_text(text, encoding="utf-8")
            else:
                text = text_path.read_text(encoding="utf-8")
            parsed.append(
                RawDocument(
                    id=f"arxiv:{result.get_short_id()}",
                    content=text,
                    source="arxiv_fulltext",
                    metadata=self._metadata(result),
                )
            )
        return parsed

    def _download_pdf(self, result: arxiv.Result, out_dir: Path) -> Path | None:
        if not result.pdf_url:
            return None
        path = out_dir / f"{self._safe_id(result.get_short_id())}.pdf"
        if path.exists():
            return path
        request = urllib.request.Request(
            result.pdf_url, headers={"User-Agent": _USER_AGENT}
        )
        with urllib.request.urlopen(request) as response, open(path, "wb") as f:
            f.write(response.read())
        return path

    @staticmethod
    def _to_document(result: arxiv.Result) -> RawDocument:
        return RawDocument(
            id=f"arxiv:{result.get_short_id()}",
            content=result.summary,
            source="arxiv",
            metadata=ArxivSource._metadata(result),
        )

    @staticmethod
    def _metadata(result: arxiv.Result) -> dict:
        return {
            "arxiv_id": result.get_short_id(),
            "title": result.title,
            "authors": [author.name for author in result.authors],
            "published": result.published.isoformat(),
            "updated": result.updated.isoformat(),
            "primary_category": result.primary_category,
            "categories": result.categories,
            "url": result.entry_id,
            "pdf_url": result.pdf_url,
        }

    @staticmethod
    def _safe_id(arxiv_id: str) -> str:
        return arxiv_id.replace("/", "_")
