import json
from collections import deque
from typing import Dict, List, Tuple

import networkx as nx

from kgraph.discovery.dependency_relations import DependencyRelationExtractor
from kgraph.extractors.key_bert import AdaptiveKeyBERT
from kgraph.graph.config import PipelineConfig
from kgraph.graph.models import RawDocument
from kgraph.segmentation.chunker import docling_sections, markdown_sections


class TopicGraph:
    """Topic-guided graph expansion, deterministic and LLM-free.

    KeyBERT seeds are the roots of the graph. Relations produced by the
    dependency extractor are only kept when at least one endpoint touches a
    known topic; the other endpoint becomes a new node that is expanded in
    turn, up to ``max_depth``. The graph therefore grows from the seeds without
    drowning in every subject-verb-object triple of the document.

    Discovery runs per document section (docling headings, markdown fallback)
    and the seeds/relations are unioned, so each section contributes its own
    domain terms instead of a single whole-document keyword pool dominated by
    abstract-level discourse. Boilerplate sections (references, ...) are
    skipped via ``discovery.skip_headings``.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.keybert = AdaptiveKeyBERT(config.keyword_extractor)
        self.extractor = DependencyRelationExtractor(
            model=config.discovery.spacy_model,
            determiners=config.discovery.determiners,
        )
        self.graph = nx.MultiDiGraph()
        self.seeds: List[str] = []
        self.relations: List = []

    def build(self, documents: List[RawDocument]) -> nx.MultiDiGraph:
        doc = documents[0]
        sections = _document_sections(doc)
        sections = [
            (text, headings)
            for text, headings in sections
            if not self._is_skipped(headings)
        ]
        if not sections:
            sections = [(doc.content, [])]

        seeds: Dict[str, float] = {}
        relations: List = []
        for text, _headings in sections:
            if not text.split():
                continue
            for keyword, score in self.keybert.extract(text):
                key = keyword.strip().lower()
                if key and score > seeds.get(key, float("-inf")):
                    seeds[key] = score
            relations.extend(self.extractor.extract(text))

        self.relations = _dedup_relations(relations)
        ranked = sorted(seeds.items(), key=lambda kv: kv[1], reverse=True)
        self.seeds = [
            keyword
            for keyword, _ in ranked[: self.config.discovery.max_seeds]
        ]

        for seed in self.seeds:
            self._add_node(seed, depth=0)

        queue: deque[str] = deque(self._key(s) for s in self.seeds)
        visited: set[str] = set()
        added_edges: set[tuple[str, str, str]] = set()

        while queue:
            if self.graph.number_of_edges() >= self.config.discovery.max_relations:
                break
            topic_key = queue.popleft()
            if topic_key in visited:
                continue
            visited.add(topic_key)

            depth = self.graph.nodes[topic_key]["depth"]
            if depth >= self.config.discovery.max_depth:
                continue

            for rel in self.relations:
                source_key = self._key(rel.source)
                target_key = self._key(rel.target)
                if source_key == target_key:
                    continue
                edge_key = (source_key, target_key, rel.relation)
                if edge_key in added_edges:
                    continue

                if not (
                    self._touches(source_key, topic_key)
                    or self._touches(target_key, topic_key)
                ):
                    continue

                children = []
                for node_key, text in (
                    (source_key, rel.source),
                    (target_key, rel.target),
                ):
                    if node_key == topic_key or node_key in self.graph:
                        continue
                    self._add_node(text, depth + 1)
                    children.append(node_key)

                added_edges.add(edge_key)
                self.graph.add_edge(
                    source_key,
                    target_key,
                    relation=rel.relation,
                    evidence=rel.evidence,
                )
                queue.extend(children)

        return self.graph

    def _add_node(self, text: str, depth: int) -> None:
        node_key = self._key(text)
        if node_key not in self.graph:
            self.graph.add_node(node_key, text=text, depth=depth)

    @staticmethod
    def _touches(node_key: str, topic_key: str) -> bool:
        return bool(set(node_key.split()) & set(topic_key.split()))

    @staticmethod
    def _key(text: str) -> str:
        return text.strip().lower()

    def _is_skipped(self, headings: List[str]) -> bool:
        skip = [s.lower() for s in self.config.discovery.skip_headings]
        return any(s in h.lower() for h in headings for s in skip)

    def export_to_json(self, filepath: str) -> None:
        data = {
            "seeds": self.seeds,
            "nodes": [{"id": n, **d} for n, d in self.graph.nodes(data=True)],
            "edges": [
                {"source": u, "target": v, **d}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)


def _document_sections(doc: RawDocument) -> List[Tuple[str, List[str]]]:
    """Return ``(text, heading_path)`` sections, docling first, markdown fallback."""
    if doc.docling_doc is not None:
        try:
            sections = docling_sections(doc.docling_doc)
            if sections:
                return sections
        except Exception:
            pass
    return markdown_sections(doc.content)


def _dedup_relations(relations: List) -> List:
    seen: set = set()
    deduped = []
    for rel in relations:
        key = (rel.source.lower(), rel.relation, rel.target.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rel)
    return deduped
