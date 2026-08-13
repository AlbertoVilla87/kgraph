from typing import Dict, List

import networkx as nx

from kgraph.discovery.topic_graph import TopicGraph
from kgraph.extractors.gliner import GLiNERGraph
from kgraph.graph.config import build_pipeline_config, load_pipeline_config
from kgraph.graph.models import RawDocument


class DiscoveryAssembly:
    """Assemble discovery outputs into the GLiNER taxonomy and build the final KG.

    The TopicGraph discovers topics (nodes) and relations (edges) from the
    document using KeyBERT seeds and spaCy dependency parsing. The discovered
    node texts and edge relation labels replace the static entities/relations
    taxonomy, so GLiNER extracts exactly the graph the document talks about.
    """

    def __init__(self, config_path: str):
        self.config_path = config_path

    def run(self, documents: List[RawDocument]) -> GLiNERGraph:
        base_config = load_pipeline_config(self.config_path)
        topic_graph = TopicGraph(base_config)
        discovery_graph = topic_graph.build(documents)

        entity_labels = self._node_labels(discovery_graph)
        relation_labels = self._edge_labels(discovery_graph)

        final_config = build_pipeline_config(
            self.config_path,
            entities=entity_labels,
            relations=relation_labels,
        )
        final_graph = GLiNERGraph(final_config)
        final_graph.build(documents)
        return final_graph

    @staticmethod
    def _label(text: str) -> str:
        """GLiNER tokenizes labels on whitespace, so multi-word labels must use ``_``."""
        return text.replace(" ", "_")

    @staticmethod
    def _node_labels(graph: nx.MultiDiGraph) -> List[str]:
        return [DiscoveryAssembly._label(data["text"]) for _, data in graph.nodes(data=True)]

    @staticmethod
    def _edge_labels(graph: nx.MultiDiGraph) -> List[str]:
        labels: Dict[str, None] = {}
        for _, _, data in graph.edges(data=True):
            labels.setdefault(DiscoveryAssembly._label(data["relation"]), None)
        return list(labels)
