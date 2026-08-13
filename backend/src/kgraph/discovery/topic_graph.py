import json
from collections import deque
from typing import List

import networkx as nx

from kgraph.discovery.dependency_relations import DependencyRelationExtractor
from kgraph.extractors.key_bert import AdaptiveKeyBERT
from kgraph.graph.config import PipelineConfig
from kgraph.graph.models import RawDocument


class TopicGraph:
    """Topic-guided graph expansion, deterministic and LLM-free.

    KeyBERT seeds are the roots of the graph. Relations produced by the
    dependency extractor are only kept when at least one endpoint touches a
    known topic; the other endpoint becomes a new node that is expanded in
    turn, up to ``max_depth``. The graph therefore grows from the seeds without
    drowning in every subject-verb-object triple of the document.
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
        doc = documents[0].content
        self.seeds = [kw for kw, _ in self.keybert.extract(doc)]
        self.relations = self.extractor.extract(doc)

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
