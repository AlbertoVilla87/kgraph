"""Build and persist per-node chunk data for lazy retrieval.

After a graph is assembled, the runner delegates here to build two artifacts
stored per ``analysis_id`` in ``kgraph.api.state``:

- ``segments``:  ``doc_id -> [chunk]`` where each chunk is the exact text that
  GLiNER scored (including its heading prefix), produced by the section-aware
  ``Segmenter``.
- ``node_mentions``:  ``node_id -> [mention]`` with the ``doc_id``, ``segment``
  index and character ``start``/``end`` offsets (relative to the chunk text)
  of each occurrence of that node, plus its ``kind``.

The offsets come straight from the ``mentions`` that ``GLiNERGraph`` /
``CorpusGraphBuilder`` store on each node, so they always align with the
chunk text that was fed to the model.
"""

from typing import Dict, List

from kgraph.graph.config import load_pipeline_config
from kgraph.graph.models import RawDocument
from kgraph.segmentation.chunker import Segmenter

NODE_KIND = "node"


def build_segments(
    documents: List[RawDocument],
    config_path: str,
) -> Dict[str, List[dict]]:
    """Return ``doc_id -> [chunk dict]`` for the given documents.

    Uses the section-aware ``Segmenter``; any document that fails to segment
    (or yields no chunks) falls back to a single whole-document chunk.
    """
    cfg = load_pipeline_config(config_path)
    segmenter = Segmenter(cfg.ner.name, cfg.segmentation)
    segments: Dict[str, List[dict]] = {}
    for doc in documents:
        chunks = []
        try:
            segs = segmenter.segment(doc)
        except Exception:
            segs = []
        for s in segs:
            chunks.append(
                {
                    "doc_id": s.doc_id,
                    "index": s.index,
                    "text": s.text,
                    "headings": list(s.headings),
                }
            )
        if not chunks:
            chunks = [
                {
                    "doc_id": doc.id,
                    "index": 0,
                    "text": doc.content or "",
                    "headings": [],
                }
            ]
        segments[doc.id] = chunks
    return segments


def build_node_mentions(graph) -> Dict[str, List[dict]]:
    """Collect every node's mentions (doc_id, segment, start, end) from the graph.

    ``graph`` is a networkx graph whose nodes carry ``mentions`` with
    ``doc_id``, ``start``/``end`` character offsets and (when segmented) a
    ``segment`` index. Mentions without a ``segment`` are treated as chunk 0.
    """
    node_mentions: Dict[str, List[dict]] = {}
    for nid, data in graph.nodes(data=True):
        mentions = []
        for m in data.get("mentions", []):
            if not m.get("doc_id"):
                continue
            mentions.append(
                {
                    "doc_id": m["doc_id"],
                    "segment": int(m.get("segment", 0)),
                    "start": int(m.get("start", 0)),
                    "end": int(m.get("end", 0)),
                    "kind": NODE_KIND,
                }
            )
        node_mentions[nid] = mentions
    return node_mentions
