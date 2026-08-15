"""Cross-document corpus graphs: per-document discovery, parallel extraction, merge.

Each document is processed with its own taxonomy (per-section discovery), so
the comparison is fair: a node/edge is unique to a document only because that
document genuinely talks about it, not because a shared taxonomy forced it.
All documents' segments are extracted concurrently with one shared GLiNER
model, then the per-document results are merged into a single graph where
every node and edge records the set of documents that produced it (``docs``).
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple

import networkx as nx
from tqdm import tqdm

from kgraph.discovery.topic_graph import TopicGraph
from kgraph.extractors.gliner import extract_entities_relations
from kgraph.extractors.normalization import canonical
from kgraph.graph.config import load_pipeline_config
from kgraph.graph.models import RawDocument
from kgraph.segmentation.chunker import Segmenter

from gliner import GLiNER


def _default_workers() -> int:
    return max(1, (os.cpu_count() or 1) // 2)


def _label(text: str) -> str:
    """GLiNER tokenizes labels on whitespace, so multi-word labels use ``_``."""
    return text.replace(" ", "_")


class CorpusGraphBuilder:
    """Build one graph from many documents, tracking per-document provenance.

    ``build`` returns ``(merged_graph, summary)`` where ``merged_graph`` is a
    ``networkx.MultiDiGraph`` whose nodes and edges carry a ``docs`` set
    attribute, and ``summary`` holds the common/unique counts per document.
    """

    def __init__(self, config_path: str, workers: int = 0):
        self.config_path = config_path
        self.base_config = load_pipeline_config(config_path)
        self.workers = workers or _default_workers()
        self.model = GLiNER.from_pretrained(self.base_config.ner.name)
        self.topic_graph = TopicGraph(self.base_config)
        self.segmenter = Segmenter(
            self.base_config.ner.name, self.base_config.segmentation
        )

    def build(
        self, documents: List[RawDocument]
    ) -> Tuple[nx.MultiDiGraph, dict]:
        if not documents:
            raise ValueError("CorpusGraphBuilder needs at least one document")

        taxonomies: Dict[str, Tuple[List[str], List[str]]] = {}
        t0 = time.perf_counter()
        for doc in tqdm(documents, desc="taxonomy", unit="doc"):
            taxonomies[doc.id] = self._taxonomy(doc)
        taxonomy_secs = time.perf_counter() - t0

        t0 = time.perf_counter()
        tasks = [
            (doc, segment)
            for doc in documents
            for segment in self.segmenter.segment(doc)
        ]
        segment_secs = time.perf_counter() - t0
        n_segments = len(tasks)

        per_doc: Dict[str, Tuple[List, List]] = {}
        t0 = time.perf_counter()
        if n_segments <= 1 or self.workers <= 1:
            with tqdm(total=n_segments, desc="extraction", unit="seg") as pbar:
                for doc, segment in tasks:
                    self._accumulate(
                        per_doc, doc.id, self._extract(segment, taxonomies[doc.id])
                    )
                    pbar.set_postfix(doc=segment.doc_id, seg=segment.index)
                    pbar.update(1)
        else:
            import torch

            torch.set_num_threads(1)
            with ThreadPoolExecutor(
                max_workers=min(self.workers, n_segments)
            ) as executor:
                futures = [
                    executor.submit(
                        self._extract, segment, taxonomies[doc.id]
                    )
                    for doc, segment in tasks
                ]
                with tqdm(total=n_segments, desc="extraction", unit="seg") as pbar:
                    for (doc, segment), future in zip(tasks, futures):
                        self._accumulate(per_doc, doc.id, future.result())
                        pbar.set_postfix(doc=segment.doc_id, seg=segment.index)
                        pbar.update(1)
        extraction_secs = time.perf_counter() - t0

        print(
            f"[corpus] {len(documents)} docs | {n_segments} segments | "
            f"taxonomy {taxonomy_secs:.1f}s | segmentation {segment_secs:.1f}s | "
            f"extraction {extraction_secs:.1f}s | "
            f"segments/doc {n_segments / len(documents):.1f}"
        )

        per_document = [
            (doc_id, entities, relations)
            for doc_id, (entities, relations) in per_doc.items()
        ]
        graph = _merge_per_document(per_document)
        summary = summarize_corpus(graph, [doc.id for doc in documents])
        return graph, summary

    def _taxonomy(self, doc: RawDocument) -> Tuple[List[str], List[str]]:
        discovery = self.topic_graph.build([doc])
        entity_labels: List[str] = []
        seen_entities: set[str] = set()
        for _, data in discovery.nodes(data=True):
            key = canonical(data["text"])
            if key in seen_entities:
                continue
            seen_entities.add(key)
            entity_labels.append(_label(data["text"]))

        relation_labels: List[str] = []
        seen_relations: set[str] = set()
        for _, _, data in discovery.edges(data=True):
            key = canonical(data["relation"])
            if key in seen_relations:
                continue
            seen_relations.add(key)
            relation_labels.append(_label(data["relation"]))
        return entity_labels, relation_labels

    def _extract(self, segment, taxonomy):
        entity_labels, relation_labels = taxonomy
        return extract_entities_relations(
            self.model,
            segment.text,
            entity_labels,
            relation_labels,
            self.base_config.thresholds.entity,
            self.base_config.thresholds.relation,
            doc_id=segment.doc_id,
            segment_index=segment.index,
        )

    @staticmethod
    def _accumulate(per_doc, doc_id, result) -> None:
        entities, relations = result
        per_doc.setdefault(doc_id, ([], []))[0].extend(entities)
        per_doc.setdefault(doc_id, ([], []))[1].extend(relations)


def _merge_per_document(per_doc: List[Tuple[str, List, List]]) -> nx.MultiDiGraph:
    """Merge per-document ``(entities, relations)`` into one provenance graph."""
    graph = nx.MultiDiGraph()
    text_to_id: Dict[str, str] = {}
    edge_lookup: Dict[Tuple[str, str, str], int] = {}

    for doc_id, entities, relations in per_doc:
        for entity in entities:
            key = canonical(entity.text)
            node_id = text_to_id.get(key)
            if node_id is None:
                node_id = entity.id
                text_to_id[key] = node_id
                graph.add_node(
                    node_id,
                    text=entity.text,
                    entity_type=entity.entity_type,
                    score=entity.score,
                    mentions=[],
                    docs=set(),
                )
            node = graph.nodes[node_id]
            node["mentions"].extend(entity.mentions)
            node["docs"].add(doc_id)
            if entity.score > node["score"]:
                node["score"] = entity.score

        for relation in relations:
            head_id = text_to_id.get(canonical(relation.head_text))
            tail_id = text_to_id.get(canonical(relation.tail_text))
            if head_id is None or tail_id is None:
                continue
            key = (head_id, tail_id, relation.relation_type)
            edge_key = edge_lookup.get(key)
            if edge_key is None:
                edge_key = graph.add_edge(
                    head_id,
                    tail_id,
                    relation_type=relation.relation_type,
                    score=relation.score,
                    count=0,
                    docs=set(),
                )
                edge_lookup[key] = edge_key
            edge = graph.edges[head_id, tail_id, edge_key]
            edge["count"] += 1
            edge["docs"].add(doc_id)
            if relation.score > edge["score"]:
                edge["score"] = relation.score

    return graph


def summarize_corpus(graph: nx.MultiDiGraph, doc_ids: List[str]) -> dict:
    """Count common vs unique nodes/edges across the documents."""
    node_docs = [set(d["docs"]) for _, d in graph.nodes(data=True)]
    edge_docs = [set(d["docs"]) for _, _, d in graph.edges(data=True)]

    common_nodes = sum(1 for docs in node_docs if len(docs) >= 2)
    common_edges = sum(1 for docs in edge_docs if len(docs) >= 2)

    per_document = {}
    for doc_id in doc_ids:
        in_doc = sum(1 for docs in node_docs if doc_id in docs)
        unique_nodes = sum(1 for docs in node_docs if docs == {doc_id})
        unique_edges = sum(1 for docs in edge_docs if docs == {doc_id})
        per_document[doc_id] = {
            "nodes_in_doc": in_doc,
            "unique_nodes": unique_nodes,
            "unique_edges": unique_edges,
            "novelty": round(unique_nodes / in_doc, 3) if in_doc else 0.0,
        }

    return {
        "documents": doc_ids,
        "total_nodes": len(node_docs),
        "total_edges": len(edge_docs),
        "common_nodes": common_nodes,
        "unique_nodes": len(node_docs) - common_nodes,
        "common_edges": common_edges,
        "unique_edges": len(edge_docs) - common_edges,
        "per_document": per_document,
    }


def export_corpus_json(
    graph: nx.MultiDiGraph, summary: dict, filepath: str
) -> dict:
    """Export the corpus graph with ``docs`` provenance as JSON, and return it."""
    data = {
        "summary": summary,
        "nodes": [
            {
                "id": node_id,
                "text": data.get("text", node_id),
                "entity_type": data.get("entity_type", "unknown"),
                "score": data.get("score", 0.0),
                "mentions": data.get("mentions", []),
                "docs": sorted(data["docs"]),
                "unique": len(data["docs"]) < 2,
            }
            for node_id, data in graph.nodes(data=True)
        ],
        "edges": [
            {
                "source": source,
                "target": target,
                "relation_type": data.get("relation_type", ""),
                "score": data.get("score", 0.0),
                "count": data.get("count", 1),
                "docs": sorted(data["docs"]),
                "unique": len(data["docs"]) < 2,
            }
            for source, target, data in graph.edges(data=True)
        ],
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return data
