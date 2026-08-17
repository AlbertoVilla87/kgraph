"""Extract references from a parsed document and resolve them to source IDs.

The module provides:
- ``ReferenceExtractor`` ABC — contract for reference extraction per source.
- ``ArxivReferenceExtractor`` — finds arXiv IDs in the References section.
- ``DoiReferenceExtractor``  — finds DOIs (placeholder for future IEEE/ACM).
- ``extract_references`` / ``extract_arxiv_refs`` — standalone helpers kept
  for backward compatibility with existing callers.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")

_REFERENCE_HEADINGS = {
    "references",
    "bibliography",
    "literature cited",
    "cited works",
    "works cited",
}

_NUMBERED_REF_RE = re.compile(
    r"^(?:-\s*)?\[(\d{1,3})\]\s+|^\d{1,3}[\.\)]\s+"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Reference:
    index: int
    raw_text: str


@dataclass
class ExtractedRef:
    """A reference resolved to an identifier in the target source."""
    source_id: str  # arXiv ID, DOI, etc.
    reference_index: int = -1
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Markdown helpers (source-agnostic)
# ---------------------------------------------------------------------------

def _is_reference_heading(heading: str) -> bool:
    return heading.strip().lower() in _REFERENCE_HEADINGS


def _find_reference_section_markdown(markdown_text: str) -> str | None:
    """Find the References section in markdown text and return its content."""
    lines = markdown_text.split("\n")
    in_references = False
    ref_lines: list[str] = []

    for line in lines:
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            heading = heading_match.group(2).strip()
            if _is_reference_heading(heading):
                in_references = True
                continue
            elif in_references:
                break
        if in_references:
            ref_lines.append(line)

    return "\n".join(ref_lines).strip() if ref_lines else None


def split_references(section_text: str) -> List[Reference]:
    """Split a references section into individual Reference entries.

    Handles formats:
      - [1] Author, Title...
      - [1]. Author, Title...
      - 1. Author, Title...
      - Author, Title... (continuation of previous)
    """
    if not section_text:
        return []

    refs: List[Reference] = []
    idx = 0
    current_text: list[str] = []

    for line in section_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        is_new_ref = bool(_NUMBERED_REF_RE.match(line))

        if is_new_ref:
            if current_text:
                refs.append(Reference(index=idx, raw_text=" ".join(current_text)))
                idx += 1
            stripped = _NUMBERED_REF_RE.sub("", line, count=1)
            current_text = [stripped] if stripped else []
        else:
            current_text.append(line)

    if current_text:
        refs.append(Reference(index=idx, raw_text=" ".join(current_text)))

    return refs


# ---------------------------------------------------------------------------
# ReferenceExtractor ABC
# ---------------------------------------------------------------------------

class ReferenceExtractor(ABC):
    """Extract resolvable identifiers from a document's references.

    Each source type (arXiv, DOI, Semantic Scholar, …) provides its own
    implementation that knows how to find identifiers in the reference text.
    """

    @property
    @abstractmethod
    def reference_format(self) -> str:
        """Short tag: ``"arxiv"``, ``"doi"``, etc."""
        ...

    @abstractmethod
    def extract(self, markdown_text: str, max_refs: int = 15) -> List[ExtractedRef]:
        """Return up to *max_refs* resolved references from the document."""
        ...


# ---------------------------------------------------------------------------
# ArXiv reference extractor
# ---------------------------------------------------------------------------

_ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b")
_ARXIV_URL_RE = re.compile(r"arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)")


def _find_arxiv_ids(text: str) -> List[str]:
    """Find arXiv IDs in a text string (bare IDs or in URLs)."""
    ids: set[str] = set()
    for match in _ARXIV_URL_RE.finditer(text):
        ids.add(match.group(1))
    for match in _ARXIV_ID_RE.finditer(text):
        candidate = match.group(1)
        if candidate not in ids:
            ids.add(candidate)
    return sorted(ids)


class ArxivReferenceExtractor(ReferenceExtractor):
    """Find arXiv IDs in a document's References section."""

    @property
    def reference_format(self) -> str:
        return "arxiv"

    def extract(self, markdown_text: str, max_refs: int = 15) -> List[ExtractedRef]:
        section_text = _find_reference_section_markdown(markdown_text)
        if not section_text:
            return []

        references = split_references(section_text)
        seen_ids: set[str] = set()
        result: List[ExtractedRef] = []

        for ref in references:
            if len(result) >= max_refs:
                break
            ids = _find_arxiv_ids(ref.raw_text)
            for aid in ids:
                if aid not in seen_ids and len(result) < max_refs:
                    seen_ids.add(aid)
                    result.append(
                        ExtractedRef(
                            source_id=aid,
                            reference_index=ref.index,
                            raw_text=ref.raw_text,
                        )
                    )
        return result


# ---------------------------------------------------------------------------
# DOI reference extractor (placeholder — ready for IEEE / ACM / etc.)
# ---------------------------------------------------------------------------

_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s,;]+)")


class DoiReferenceExtractor(ReferenceExtractor):
    """Find DOIs in a document's References section.

    This is a placeholder implementation. When IEEE/ACM support is added,
    this extractor can be extended to resolve DOIs via Crossref or
    Semantic Scholar.
    """

    @property
    def reference_format(self) -> str:
        return "doi"

    def extract(self, markdown_text: str, max_refs: int = 15) -> List[ExtractedRef]:
        section_text = _find_reference_section_markdown(markdown_text)
        if not section_text:
            return []

        references = split_references(section_text)
        seen_ids: set[str] = set()
        result: List[ExtractedRef] = []

        for ref in references:
            if len(result) >= max_refs:
                break
            for match in _DOI_RE.finditer(ref.raw_text):
                doi = match.group(1)
                if doi not in seen_ids and len(result) < max_refs:
                    seen_ids.add(doi)
                    result.append(
                        ExtractedRef(
                            source_id=doi,
                            reference_index=ref.index,
                            raw_text=ref.raw_text,
                        )
                    )
        return result


# ---------------------------------------------------------------------------
# Backward-compatible standalone helpers
# ---------------------------------------------------------------------------

def extract_references(
    docling_doc=None, markdown_text: str | None = None
) -> List[Reference]:
    """Parse the References section (backward-compatible helper)."""
    if markdown_text is None and docling_doc is not None:
        try:
            markdown_text = docling_doc.export_to_markdown()
        except Exception:
            return []

    if not markdown_text:
        return []

    section_text = _find_reference_section_markdown(markdown_text)
    if not section_text:
        return []
    return split_references(section_text)


def extract_arxiv_refs(
    docling_doc=None,
    markdown_text: str | None = None,
    max_refs: int = 15,
) -> List[ExtractedRef]:
    """Extract arXiv references (backward-compatible helper)."""
    if markdown_text is None and docling_doc is not None:
        try:
            markdown_text = docling_doc.export_to_markdown()
        except Exception:
            return []

    if not markdown_text:
        return []

    return ArxivReferenceExtractor().extract(markdown_text, max_refs=max_refs)
