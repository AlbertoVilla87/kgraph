"""Seed-paper data source: start from one paper and expand via references.

Composes a ``DataSource`` (for fetching) with a ``ReferenceExtractor``
(for finding cited papers).  The pipeline never knows which source the
seed came from — it just sees ``RawDocument``s.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Callable, List

from kgraph.graph.models import RawDocument
from kgraph.ingestion.base import DataSource, SourceCapabilities
from kgraph.ingestion.references import ExtractedRef, ReferenceExtractor

log = logging.getLogger(__name__)

_ARXIV_URL_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)"
)
_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")

# Type alias for the progress callback: (current, total, detail_message)
ProgressCallback = Callable[[int, int, str], None]


def _parse_arxiv_id(url_or_id: str) -> str:
    """Extract the arXiv ID from a URL or bare ID string."""
    m = _ARXIV_URL_RE.search(url_or_id)
    if m:
        return m.group(1)
    m = _ARXIV_ID_RE.search(url_or_id)
    if m:
        return m.group(1)
    raise ValueError(
        f"Cannot parse arXiv ID from: {url_or_id!r}. "
        "Expected a URL like https://arxiv.org/abs/2301.12345 or a bare ID."
    )


def _noop_progress(current: int, total: int, detail: str) -> None:
    """Default no-op progress callback."""


class SeedPaperSource(DataSource):
    """Start from one paper and discover its references on the same source.

    Composition:
        - ``source``: a ``DataSource`` used to fetch the seed paper and its
          referenced papers.
        - ``extractor``: a ``ReferenceExtractor`` that finds resolvable IDs
          (arXiv IDs, DOIs, …) in the seed paper's References section.

    The caller wires the correct source + extractor pair.  For example::

        SeedPaperSource(
            source=ArxivSource(query="...", max_results=0),
            extractor=ArxivReferenceExtractor(),
            seed_id="2301.12345",
        )

    This makes ``SeedPaperSource`` source-agnostic: swapping arXiv for IEEE
    means swapping ``ArxivSource`` + ``ArxivReferenceExtractor`` for
    ``IeeeSource`` + ``DoiReferenceExtractor``.
    """

    def __init__(
        self,
        source: DataSource,
        extractor: ReferenceExtractor,
        seed_id: str,
        max_references: int = 15,
        download_dir: str | Path = "data/papers",
    ):
        self.source = source
        self.extractor = extractor
        self.seed_id = seed_id
        self.max_references = max_references
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    @property
    def capabilities(self) -> SourceCapabilities:
        src_cap = self.source.capabilities
        return SourceCapabilities(
            can_search=False,
            can_fetch_fulltext=True,
            can_download_pdf=src_cap.can_download_pdf,
            has_references=True,
            reference_format=self.extractor.reference_format,
        )

    def fetch(self, on_progress: ProgressCallback = _noop_progress) -> List[RawDocument]:
        """Download seed paper + references and return as RawDocuments.

        ``on_progress(current, total, detail)`` is called per paper so the
        caller can update a progress bar with granular status.
        """
        on_progress(0, 1, "Downloading seed paper...")
        seed_doc = self._fetch_seed()
        if seed_doc is None:
            return []

        on_progress(1, 1, "Extracting references...")
        ref_ids = self._discover_references(seed_doc)
        total = len(ref_ids)
        log.info(
            "Found %d %s references (max %d)",
            total,
            self.extractor.reference_format,
            self.max_references,
        )

        ref_docs = self._fetch_references(ref_ids, on_progress)
        log.info("Downloaded %d referenced papers", len(ref_docs))

        return [seed_doc] + ref_docs

    def _fetch_seed(self) -> RawDocument | None:
        """Download and parse the seed paper via the composed source."""
        self.source.max_results = 1  # type: ignore[attr-defined]
        if hasattr(self.source, "query"):
            self.source.query = self.seed_id  # type: ignore[attr-defined]

        docs = self.source.fetch_fulltext(self.download_dir)
        if not docs:
            log.warning("Seed paper %s not found", self.seed_id)
            return None
        return docs[0]

    def _discover_references(self, seed_doc: RawDocument) -> List[str]:
        """Extract resolvable IDs from the seed paper's references."""
        if not seed_doc.content:
            log.warning("No content for seed paper, cannot extract references")
            return []

        extracted = self.extractor.extract(seed_doc.content, max_refs=self.max_references)
        for ref in extracted:
            log.debug(
                "%s (from reference #%d)", ref.source_id, ref.reference_index + 1
            )

        return [ref.source_id for ref in extracted]

    def _fetch_references(
        self,
        ref_ids: List[str],
        on_progress: ProgressCallback = _noop_progress,
    ) -> List[RawDocument]:
        """Download and parse referenced papers via the composed source."""
        if not ref_ids:
            return []

        docs: List[RawDocument] = []
        total = len(ref_ids)

        for i, rid in enumerate(ref_ids, 1):
            on_progress(i, total, f"Downloading paper {i}/{total}: {rid}")
            try:
                original_query = getattr(self.source, "query", None)
                original_max = getattr(self.source, "max_results", None)
                if hasattr(self.source, "query"):
                    self.source.query = rid  # type: ignore[attr-defined]
                self.source.max_results = 1  # type: ignore[attr-defined]

                results = self.source.fetch_fulltext(self.download_dir)

                if original_query is not None and hasattr(self.source, "query"):
                    self.source.query = original_query  # type: ignore[attr-defined]
                if original_max is not None:
                    self.source.max_results = original_max  # type: ignore[attr-defined]

                if results:
                    docs.append(results[0])
                    title = results[0].metadata.get("title", rid)
                    log.info("OK: %s - %s", rid, title[:60])
                else:
                    log.warning("Reference %s not found, skipping", rid)
            except Exception as e:
                log.error("Error fetching %s: %s", rid, e)
                continue

        on_progress(total, total, f"Downloaded {len(docs)}/{total} papers")
        return docs
