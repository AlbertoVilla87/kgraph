"""Robust bibliography parser for citation-guided discovery.

Parses the References section of a document into structured entries with
extracted identifiers (arXiv, DOI), author surnames, and publication years.
Uses pylatexenc for LaTeX artifact cleanup when present.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LaTeX cleanup (optional, via pylatexenc)
# ---------------------------------------------------------------------------

_latex2text = None

def _clean_latex(text: str) -> str:
    """Strip LaTeX formatting commands if pylatexenc is available."""
    global _latex2text
    if _latex2text is None:
        try:
            from pylatexenc.latex2text import LatexNodes2Text
            _latex2text = LatexNodes2Text()
        except ImportError:
            _latex2text = False
            log.debug("pylatexenc not installed, skipping LaTeX cleanup")
    if _latex2text is False:
        return text
    try:
        return _latex2text.latex_to_text(text)
    except Exception:
        return text


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BibliographyEntry:
    """A single parsed reference from the bibliography."""
    raw_text: str
    first_author: str | None = None
    year: int | None = None
    arxiv_ids: List[str] = field(default_factory=list)
    dois: List[str] = field(default_factory=list)
    title: str | None = None


# ---------------------------------------------------------------------------
# Identifier extraction
# ---------------------------------------------------------------------------

_ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b")
_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)")
_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s,;]+)")
_YEAR_RE = re.compile(r"\((\d{4})\)")
_YEAR_PLAIN_RE = re.compile(r"\b(19|20)\d{2}\b")


def extract_identifiers(text: str) -> Tuple[List[str], List[str]]:
    """Extract arXiv IDs and DOIs from a text string.

    Returns:
        (arxiv_ids, dois) — deduplicated, preserving order of first appearance.
    """
    arxiv_ids: list[str] = []
    dois: list[str] = []
    seen_arxiv: set[str] = set()
    seen_doi: set[str] = set()

    for match in _ARXIV_URL_RE.finditer(text):
        aid = match.group(1)
        if aid not in seen_arxiv:
            seen_arxiv.add(aid)
            arxiv_ids.append(aid)
    for match in _ARXIV_ID_RE.finditer(text):
        aid = match.group(1)
        if aid not in seen_arxiv:
            seen_arxiv.add(aid)
            arxiv_ids.append(aid)

    for match in _DOI_RE.finditer(text):
        doi = match.group(1)
        if doi not in seen_doi:
            seen_doi.add(doi)
            dois.append(doi)

    return arxiv_ids, dois


# ---------------------------------------------------------------------------
# Author-year extraction
# ---------------------------------------------------------------------------

# Patterns:
#   "Surname, F. and ..."  /  "Surname, A. B. and ..."
#   "Surname, F., and ..."  /  "Surname, F. and ..."
#   "Surname et al."
#   Just the first capitalised word run as surname fallback
_SURNAME_RE = re.compile(
    r"^([A-Z][\w'\-]+(?:\s+[A-Z][\w'\-]+){0,2})"
)


def extract_author_year(text: str) -> Tuple[str | None, int | None]:
    """Extract the first-author surname and publication year.

    Handles common bibliography formats:
      - "Baumel, M. T., ..."
      - "Baumel et al. (2018)"
      - "Baumel, A. B. (2018)"
      - Just "(2024)" somewhere in the entry
    """
    year = None
    ym = _YEAR_RE.search(text)
    if ym:
        year = int(ym.group(1))
    else:
        ym2 = _YEAR_PLAIN_RE.search(text)
        if ym2:
            year = int(ym2.group(0))

    surname = None
    sm = _SURNAME_RE.match(text.strip())
    if sm:
        raw_surname = sm.group(1)
        # Take just the last word of the surname if it looks like "Surname, F."
        parts = [p.strip() for p in raw_surname.split(",")]
        surname = parts[0]
        # Strip trailing initials like "Baumel, M" → "Baumel"
        surname = re.sub(r",?\s+[A-Z](?:\.|$)", "", surname).strip()
        surname = re.sub(r"\s+(?:and|et)\b.*", "", surname).strip()

    return surname, year


# ---------------------------------------------------------------------------
# Title extraction (heuristic)
# ---------------------------------------------------------------------------

def _extract_title(raw_text: str) -> str | None:
    """Best-effort title extraction from a bibliography entry.

    Heuristic: the title is usually the text between the author list and the
    publication venue/year.  We look for the first sentence-like fragment
    after the author names and before a period or year.
    """
    text = raw_text.strip()

    # Remove leading author list (up to first year or "and")
    # Try to find text after the author+year preamble
    m = re.search(r"\)\.\s*(.+?)(?:\.\s|$)", text)
    if m:
        return m.group(1).strip()[:120]

    # Fallback: text after "(YYYY)." or "(YYYY),"
    m = re.search(r"\((?:19|20)\d{2}\)[.,]\s*(.+?)(?:\.\s|$)", text)
    if m:
        return m.group(1).strip()[:120]

    # Last resort: first 80 chars
    return text[:80]


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def _split_bullets(ref_section: str) -> List[str]:
    """Split a markdown bullet-style reference section into entries.

    Docling renders references as ``- Author, Title... (Year). Venue...``
    with continuation lines that don't start with ``- ``.
    """
    entries: list[str] = []
    current: list[str] = []

    for line in ref_section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if current:
                entries.append(" ".join(current))
            current = [stripped[2:].strip()]
        elif stripped.startswith("["):
            # Numbered format: [1] Author...
            if current:
                entries.append(" ".join(current))
            cleaned = re.sub(r"^\[\d{1,3}\]\s*", "", stripped)
            current = [cleaned.strip()]
        else:
            # Continuation line
            if current:
                current.append(stripped)

    if current:
        entries.append(" ".join(current))

    return entries


def _split_numbered(ref_section: str) -> List[str]:
    """Split a numbered-style reference section (1. Author...).

    Handles formats:
      - 1. Author, Title... (Year). Venue...
      - 1) Author, Title...
    """
    entries: list[str] = []
    current: list[str] = []

    for line in ref_section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        is_new = bool(re.match(r"^\d{1,3}[\.\)]\s+", stripped))
        if is_new:
            if current:
                entries.append(" ".join(current))
            cleaned = re.sub(r"^\d{1,3}[\.\)]\s+", "", stripped)
            current = [cleaned.strip()]
        else:
            if current:
                current.append(stripped)

    if current:
        entries.append(" ".join(current))

    return entries


def _detect_format(ref_section: str) -> str:
    """Detect whether the reference section uses bullet or numbered format."""
    for line in ref_section.splitlines():
        s = line.strip()
        if s.startswith("- "):
            return "bullet"
        if re.match(r"^\d{1,3}[\.\)]\s+", s):
            return "numbered"
    return "bullet"


def parse_bibliography_entries(ref_section: str) -> List[BibliographyEntry]:
    """Parse a reference section into structured BibliographyEntry objects.

    Handles:
      - Markdown bullets (``- Author, Title (Year). Venue``) — docling format
      - Numbered references (``1. Author, Title (Year). Venue``)
      - Continuation lines across multiple lines

    Returns:
        List of BibliographyEntry with extracted metadata.
    """
    if not ref_section or not ref_section.strip():
        return []

    cleaned = _clean_latex(ref_section)
    fmt = _detect_format(cleaned)

    if fmt == "numbered":
        raw_entries = _split_numbered(cleaned)
    else:
        raw_entries = _split_bullets(cleaned)

    entries: list[BibliographyEntry] = []
    for raw in raw_entries:
        if not raw.strip():
            continue

        arxiv_ids, dois = extract_identifiers(raw)
        author, year = extract_author_year(raw)
        title = _extract_title(raw)

        entries.append(BibliographyEntry(
            raw_text=raw,
            first_author=author,
            year=year,
            arxiv_ids=arxiv_ids,
            dois=dois,
            title=title,
        ))

    return entries


def find_entry_by_arxiv(entries: List[BibliographyEntry], arxiv_id: str) -> BibliographyEntry | None:
    """Find a bibliography entry by its arXiv ID (ignoring version suffix)."""
    base = re.sub(r"v\d+$", "", arxiv_id)
    for entry in entries:
        for aid in entry.arxiv_ids:
            if re.sub(r"v\d+$", "", aid) == base:
                return entry
    return None


def build_entry_index(entries: List[BibliographyEntry]) -> dict[str, BibliographyEntry]:
    """Build a lookup index: arXiv ID → BibliographyEntry.

    Multiple entries may share an arXiv ID (unlikely but handled).
    Only the first occurrence is kept.
    """
    index: dict[str, BibliographyEntry] = {}
    for entry in entries:
        for aid in entry.arxiv_ids:
            base = re.sub(r"v\d+$", "", aid)
            if base not in index:
                index[base] = entry
    return index
