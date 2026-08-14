from dataclasses import dataclass, field
from typing import List


@dataclass
class Segment:
    """A token-bounded piece of a document ready for GLiNER inference.

    ``text`` is self-contained: it carries the section heading path as a
    prefix (when available) so the model sees the section context. ``start``
    and ``end`` are character offsets of the body (headings excluded) into the
    full source text, for provenance.
    """

    doc_id: str
    index: int
    text: str
    headings: List[str] = field(default_factory=list)
    start: int = 0
    end: int = 0
    metadata: dict = field(default_factory=dict)
