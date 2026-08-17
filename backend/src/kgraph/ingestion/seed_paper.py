"""Seed-paper data source: start from one paper and expand via references.

Composes a ``DataSource`` (for fetching) with a ``ReferenceExtractor``
(for finding cited papers).  The pipeline never knows which source the
seed came from — it just sees ``RawDocument``s.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from kgraph.graph.models import RawDocument
from kgraph.ingestion.base import DataSource, SourceCapabilities
from kgraph.ingestion.references import ExtractedRef, ReferenceExtractor

_ARXIV_URL_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)"
)
_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")


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

    def fetch(self) -> List[RawDocument]:
        """Download seed paper + references and return as RawDocuments."""
        seed_doc = self._fetch_seed()
        if seed_doc is None:
            return []

        ref_ids = self._discover_references(seed_doc)
        print(
            f"[seed] Found {len(ref_ids)} {self.extractor.reference_format} "
            f"references (max {self.max_references})"
        )

        ref_docs = self._fetch_references(ref_ids)
        print(f"[seed] Downloaded {len(ref_docs)} referenced papers")

        return [seed_doc] + ref_docs

    def _fetch_seed(self) -> RawDocument | None:
        """Download and parse the seed paper via the composed source."""
        # Build a search that returns exactly this paper by ID
        self.source.max_results = 1  # type: ignore[attr-defined]
        if hasattr(self.source, "query"):
            self.source.query = self.seed_id  # type: ignore[attr-defined]

        docs = self.source.fetch_fulltext(self.download_dir)
        if not docs:
            print(f"[seed] Seed paper {self.seed_id} not found")
            return None
        return docs[0]

    def _discover_references(self, seed_doc: RawDocument) -> List[str]:
        """Extract resolvable IDs from the seed paper's references."""
        if not seed_doc.content:
            print("[seed] No content for seed paper, cannot extract references")
            return []

        extracted = self.extractor.extract(seed_doc.content, max_refs=self.max_references)
        for ref in extracted:
            print(f"  [ref] {ref.source_id} (from reference #{ref.reference_index + 1})")

        return [ref.source_id for ref in extracted]

    def _fetch_references(self, ref_ids: List[str]) -> List[RawDocument]:
        """Download and parse referenced papers via the composed source."""
        if not ref_ids:
            return []

        docs: List[RawDocument] = []
        for rid in ref_ids:
            try:
                # Temporarily point the source at this specific ID
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
                    print(f"  [seed] OK: {rid} - {title[:60]}")
                else:
                    print(f"  [seed] Reference {rid} not found, skipping")
            except Exception as e:
                print(f"  [seed] Error fetching {rid}: {e}")
                continue

        return docs
