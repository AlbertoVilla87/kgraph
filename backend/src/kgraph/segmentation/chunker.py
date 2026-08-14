"""Section-aware segmentation for the extraction pipeline.

GLiNER truncates any input longer than its context window (``max_len``, 1024
tokens for the relex-large model), so long documents lose everything past the
window. This module splits a document into token-bounded segments that stay
within the model's budget while preserving the document structure:

- When a docling ``DoclingDocument`` is available (PDFs and markdown parsed
  through docling) the ``HierarchicalChunker`` from ``docling_core`` provides
  layout/section-aware chunks with their heading paths.
- Otherwise a plain markdown fallback splits on ``#`` heading lines.
- Oversized sections are split at paragraph / sentence / token boundaries,
  consecutive chunks are greedily merged up to the token budget, and a small
  overlap is carried across segment boundaries so entities and relations
  spanning a cut are still captured by GLiNER.

All token counting uses the same tokenizer the GLiNER model ships with, so the
budget matches the model's own counting exactly.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional

from transformers import AutoTokenizer

from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker

from kgraph.graph.config import SegmentationConfig
from kgraph.graph.models import RawDocument
from kgraph.segmentation.models import Segment

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

_DEFAULT_MAX_LEN = 1024


def _model_max_len(model_dir: str) -> int:
    """Return the GLiNER model's context window (``gliner_config.json``).

    Falls back to ``1024`` when the file is missing or has no ``max_len``.
    """
    gliner_cfg = Path(model_dir) / "gliner_config.json"
    if gliner_cfg.exists():
        try:
            data = json.loads(gliner_cfg.read_text(encoding="utf-8"))
            if "max_len" in data:
                return int(data["max_len"])
        except (ValueError, OSError):
            pass
    return _DEFAULT_MAX_LEN


class TokenBudget:
    """Token counting against the GLiNER model's tokenizer and window."""

    def __init__(self, model_dir: str, max_tokens: Optional[int] = None, reserve: int = 8):
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model_max = _model_max_len(model_dir)
        budget = min(max_tokens, model_max) if max_tokens else model_max
        self.max_tokens = max(1, budget - reserve)

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def tail(self, text: str, n_tokens: int) -> str:
        """Return the last ``n_tokens`` of ``text`` as a string."""
        if not text or n_tokens <= 0:
            return ""
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= n_tokens:
            return text
        return self.tokenizer.decode(tokens[-n_tokens:], skip_special_tokens=True)

    def split_hard(self, text: str) -> Iterator[str]:
        """Split ``text`` into pieces of at most ``max_tokens`` tokens."""
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        for i in range(0, len(tokens), self.max_tokens):
            piece = self.tokenizer.decode(tokens[i:i + self.max_tokens], skip_special_tokens=True)
            if piece.strip():
                yield piece


@dataclass
class _Block:
    """A structural unit of a document: body text plus its heading path."""

    text: str
    headings: List[str] = field(default_factory=list)


def _docling_blocks(doc) -> List[_Block]:
    """Chunk a docling document into section-aware blocks.

    Chunks without a heading path (captions, figures, leading content)
    inherit the previous chunk's headings so the section context carries
    through without producing spurious boundaries.
    """
    chunker = HierarchicalChunker(always_emit_headings=True)
    blocks: List[_Block] = []
    last_headings: List[str] = []
    for chunk in chunker.chunk(doc):
        text = (chunk.text or "").strip()
        if not text:
            continue
        headings = [h for h in (chunk.meta.headings or []) if h]
        if headings:
            last_headings = headings
        blocks.append(_Block(text=text, headings=list(last_headings)))
    return blocks


def _markdown_blocks(text: str) -> List[_Block]:
    """Split markdown into blocks grouped by ``#`` heading lines."""
    blocks: List[_Block] = []
    headings: List[str] = []
    lines: List[str] = []

    def flush() -> None:
        if not lines:
            return
        body = "\n".join(lines).strip()
        if body:
            blocks.append(_Block(text=body, headings=list(headings)))
        lines.clear()

    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            flush()
            headings.append(match.group(2).strip())
            continue
        if not line.strip():
            flush()
            continue
        lines.append(line)
    flush()
    return blocks


def _group_sections(blocks: List[_Block]) -> List[tuple[str, List[str]]]:
    """Merge consecutive blocks sharing the same heading path into one section."""
    sections: List[tuple[str, List[str]]] = []
    for block in blocks:
        if not block.text:
            continue
        if sections and sections[-1][1] == block.headings:
            text, headings = sections[-1]
            sections[-1] = (text + "\n\n" + block.text, headings)
        else:
            sections.append((block.text, block.headings))
    return sections


def docling_sections(doc) -> List[tuple[str, List[str]]]:
    """Return ``(section_text, heading_path)`` pairs from a docling document."""
    return _group_sections(_docling_blocks(doc))


def markdown_sections(text: str) -> List[tuple[str, List[str]]]:
    """Return ``(section_text, heading_path)`` pairs from markdown (heading-based fallback)."""
    return _group_sections(_markdown_blocks(text))


def _split_to_budget(text: str, budget: TokenBudget) -> Iterator[str]:
    """Split ``text`` into pieces of at most ``budget.max_tokens`` tokens.

    Cuts at paragraph boundaries first, then sentences, then tokens, so
    splitting never breaks a word.
    """
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    buf: List[str] = []
    buf_tokens = 0

    def yield_buf() -> Iterator[str]:
        nonlocal buf, buf_tokens
        if buf:
            yield "\n\n".join(buf)
        buf = []
        buf_tokens = 0

    for paragraph in paragraphs:
        tokens = budget.count(paragraph)
        if buf_tokens + tokens <= budget.max_tokens:
            buf.append(paragraph)
            buf_tokens += tokens
            continue
        yield from yield_buf()
        if tokens <= budget.max_tokens:
            buf.append(paragraph)
            buf_tokens = tokens
            continue
        for sentence in _split_sentences(paragraph, budget):
            tokens = budget.count(sentence)
            if buf_tokens + tokens > budget.max_tokens:
                yield from yield_buf()
            if tokens <= budget.max_tokens:
                buf.append(sentence)
                buf_tokens = tokens
            else:
                yield from yield_buf()
                yield from budget.split_hard(sentence)
    yield from yield_buf()


def _split_sentences(paragraph: str, budget: TokenBudget) -> Iterator[str]:
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(paragraph) if s.strip()]
    buf: List[str] = []
    buf_tokens = 0

    for sentence in sentences:
        tokens = budget.count(sentence)
        if buf_tokens + tokens <= budget.max_tokens:
            buf.append(sentence)
            buf_tokens += tokens
            continue
        if buf:
            yield " ".join(buf)
        buf = []
        buf_tokens = 0
        if tokens <= budget.max_tokens:
            buf.append(sentence)
            buf_tokens = tokens
        else:
            yield from budget.split_hard(sentence)
    if buf:
        yield " ".join(buf)


def _heading_prefix_tokens(headings: List[str], budget: TokenBudget) -> int:
    if not headings:
        return 0
    return budget.count("\n".join(headings) + "\n\n")


def _segments_from_blocks(
    blocks: List[_Block],
    doc_id: str,
    budget: TokenBudget,
    overlap_tokens: int,
) -> List[Segment]:
    """Merge blocks into token-bounded segments, with cross-boundary overlap.

    ``buf_tokens`` tracks the full token count of the pending segment:
    heading prefix of the last block + joined block bodies + the carried
    overlap tail. Prefix changes are handled as deltas as blocks are appended.
    """
    units: List[_Block] = []
    for block in blocks:
        if budget.count(block.text) <= budget.max_tokens:
            units.append(block)
        else:
            units.extend(
                _Block(piece, block.headings)
                for piece in _split_to_budget(block.text, budget)
            )

    segments: List[Segment] = []
    buf: List[_Block] = []
    buf_tokens = 0
    tail = ""
    tail_tokens = 0
    char_offset = 0
    index = 0

    def flush() -> None:
        nonlocal buf, buf_tokens, tail, tail_tokens, char_offset, index
        if not buf and not tail:
            return

        headings = buf[-1].headings if buf else []
        heading_prefix = "\n".join(headings) + "\n\n" if headings else ""

        def build() -> str:
            body_parts = [part for part in ([tail] if tail else []) + [u.text for u in buf] if part]
            return heading_prefix + "\n\n".join(body_parts)

        text = build()
        while buf and budget.count(text) > budget.max_tokens:
            buf.pop()
            buf_tokens = (
                _heading_prefix_tokens(buf[-1].headings, budget)
                + sum(budget.count(b.text) for b in buf)
                + tail_tokens
            ) if buf else tail_tokens
            headings = buf[-1].headings if buf else []
            heading_prefix = "\n".join(headings) + "\n\n" if headings else ""
            text = build()

        if not text.strip():
            return

        body_parts = [part for part in ([tail] if tail else []) + [u.text for u in buf] if part]
        body = "\n\n".join(body_parts)

        start = char_offset - len(tail)
        end = start + len(body)
        char_offset = end

        segments.append(
            Segment(
                doc_id=doc_id,
                index=index,
                text=text,
                headings=headings,
                start=start,
                end=end,
            )
        )
        index += 1

        tail = budget.tail(body, overlap_tokens)
        tail_tokens = budget.count(tail) if tail else 0
        buf = []
        buf_tokens = tail_tokens

    for unit in units:
        unit_tokens = budget.count(unit.text)
        new_prefix = _heading_prefix_tokens(unit.headings, budget)
        old_prefix = _heading_prefix_tokens(buf[-1].headings, budget) if buf else 0
        join_margin = len(buf) + (1 if tail else 0)
        if (
            buf
            and buf_tokens + unit_tokens + new_prefix - old_prefix + join_margin
            > budget.max_tokens
        ):
            flush()
        if (
            not buf
            and tail_tokens
            and tail_tokens + unit_tokens + new_prefix > budget.max_tokens
        ):
            tail = ""
            tail_tokens = 0
            buf_tokens = 0
        buf.append(unit)
        buf_tokens += unit_tokens + new_prefix - old_prefix
    flush()
    return segments


class Segmenter:
    """Segment a ``RawDocument`` into token-bounded, section-aware segments."""

    def __init__(self, model_dir: str, config: SegmentationConfig):
        self.config = config
        self.budget = TokenBudget(model_dir, config.max_tokens)

    def segment(self, doc: RawDocument) -> List[Segment]:
        blocks: List[_Block] = []
        if doc.docling_doc is not None:
            try:
                blocks = _docling_blocks(doc.docling_doc)
            except Exception:
                blocks = []
        if not blocks:
            blocks = _markdown_blocks(doc.content)
        if not blocks:
            return []
        return _segments_from_blocks(
            blocks,
            doc.id,
            self.budget,
            self.config.overlap_tokens,
        )


def segment_document(doc: RawDocument, config: SegmentationConfig, model_dir: str) -> List[Segment]:
    return Segmenter(model_dir, config).segment(doc)
