from dataclasses import dataclass
from typing import List

from fastapi import APIRouter, HTTPException

from kgraph.api.state import analyses, analysis_chunks

router = APIRouter()


def _edge_pairs(analysis_id: str) -> dict[str, List[tuple[str, str]]]:
    """Return ``node_id -> [(neighbor_id, relation)]`` for the analysis graph."""
    result = analyses.get(analysis_id, {}).get("result")
    rels = (result or {}).get("relationships", []) or []
    pairs: dict[str, List[tuple[str, str]]] = {}
    for rel in rels:
        pairs.setdefault(rel["source"], []).append((rel["target"], rel["relation"]))
        pairs.setdefault(rel["target"], []).append((rel["source"], rel["relation"]))
    return pairs


@dataclass
class _Chunk:
    doc_id: str
    index: int
    text: str
    headings: List[str]
    highlights: List[dict] = None

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "index": self.index,
            "text": self.text,
            "headings": self.headings,
            "highlights": self.highlights or [],
        }


@router.get("/{analysis_id}/nodes/{node_id}/chunks")
def get_node_chunks(analysis_id: str, node_id: str):
    """Return the chunks where ``node_id`` appears, with highlight spans.

    Each chunk carries ``highlights``:
    - ``kind == "node"`` for occurrences of the selected node itself.
    - ``kind == "edge"`` for the *other endpoint* of each edge connected to the
      selected node, but only when that endpoint also appears in the same chunk
      (i.e. the relationship is actually present in this text).
    """
    if analysis_id not in analysis_chunks:
        raise HTTPException(status_code=404, detail="Analysis not found")
    store = analysis_chunks[analysis_id]
    node_mentions = store.get("node_mentions", {})
    segments = store.get("segments", {})

    mentions = [
        m for m in node_mentions.get(node_id, []) if m.get("kind") == "node"
    ]
    if not mentions:
        return {"node_id": node_id, "chunks": []}

    # Map (doc_id, segment) -> node mention offsets for this node.
    node_by_chunk: dict[tuple[str, int], List[dict]] = {}
    for m in mentions:
        node_by_chunk.setdefault((m["doc_id"], m["segment"]), []).append(m)

    # For edges we need every neighbor's mentions in the same chunk.
    neighbor_mentions: dict[str, List[dict]] = {
        nid: ns
        for nid, ns in node_mentions.items()
        if nid != node_id and ns
    }
    neighbor_by_chunk: dict[tuple[str, int], List[dict]] = {}
    for nid, ms in neighbor_mentions.items():
        for m in ms:
            neighbor_by_chunk.setdefault((m["doc_id"], m["segment"]), []).append(
                {**m, "_node_id": nid}
            )

    edge_pairs = _edge_pairs(analysis_id)
    node_edges = {
        nid
        for nid, _ in edge_pairs.get(node_id, [])
    }
    edge_rel_by_neighbor: dict[str, str] = {
        nid: rel for nid, rel in edge_pairs.get(node_id, [])
    }

    chunks: List[_Chunk] = []

    for (doc_id, seg_idx), node_spans in node_by_chunk.items():
        chunk_text = None
        for c in segments.get(doc_id, []):
            if c["index"] == seg_idx:
                chunk_text = c
                break
        if chunk_text is None:
            continue

        highlights: List[dict] = []
        for sp in node_spans:
            highlights.append(
                {
                    "start": sp["start"],
                    "end": sp["end"],
                    "kind": "node",
                    "label": node_id,
                }
            )

        # Only edges whose other endpoint actually appears in this chunk.
        for other in neighbor_by_chunk.get((doc_id, seg_idx), []):
            if other["_node_id"] in node_edges:
                highlights.append(
                    {
                        "start": other["start"],
                        "end": other["end"],
                        "kind": "edge",
                        "label": edge_rel_by_neighbor.get(other["_node_id"], ""),
                    }
                )

        chunks.append(
            _Chunk(
                doc_id=doc_id,
                index=seg_idx,
                text=chunk_text["text"],
                headings=chunk_text.get("headings", []),
                highlights=highlights,
            )
        )

    # Deterministic ordering by document then segment index.
    chunks.sort(key=lambda c: (c.doc_id, c.index))
    return {"node_id": node_id, "chunks": [c.to_dict() for c in chunks]}
