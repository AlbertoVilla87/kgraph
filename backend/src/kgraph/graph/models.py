from dataclasses import dataclass, field
import hashlib
from typing import Any, Dict, List

@dataclass
class Entity:
    """An extracted entity."""
    id: str
    text: str
    entity_type: str
    score: float
    source_doc: str
    mentions: List[dict] = field(default_factory=list)

    @staticmethod
    def generate_id(text: str, entity_type: str) -> str:
        normalized = text.lower().strip()
        return hashlib.md5(f"{entity_type}:{normalized}".encode()).hexdigest()[:12]

@dataclass
class Relation:
    """A relation extracted between entities."""
    head_text: str
    relation_type: str
    tail_text: str
    score: float
    source_doc: str

@dataclass
class RawDocument:
    id: str
    content: str
    source: str
    metadata: Dict = field(default_factory=dict)
    docling_doc: Any = None