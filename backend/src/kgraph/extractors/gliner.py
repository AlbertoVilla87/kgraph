import logging
import networkx as nx
import json
from typing import List, Dict, Set, Optional
from kgraph.graph.models import Entity, Relation, RawDocument
from kgraph.graph.config import PipelineConfig
from kgraph.extractors.normalization import EntityMerger, canonical
from gliner import GLiNER

log = logging.getLogger(__name__)


def extract_entities_relations(
    model,
    text: str,
    entity_labels: List[str],
    relation_labels: List[str],
    entity_threshold: float,
    relation_threshold: float,
    doc_id: str,
    segment_index: Optional[int] = None,
) -> tuple[List[Entity], List[Relation]]:
    """Run GLiNER on a single text and build ``Entity``/``Relation`` objects.

    The shared helper is used both by the whole-document path and by the
    segmented extractor, so entity/relation construction stays in one place.
    """
    entities_raw, relations_raw = model.inference(
        texts=[text],
        labels=entity_labels,
        relations=relation_labels,
        threshold=entity_threshold,
        relation_threshold=relation_threshold,
        return_relations=True,
        flat_ner=False,
    )
    return (
        _entities_from_raw(entities_raw[0], doc_id, segment_index),
        _relations_from_raw(relations_raw[0], doc_id),
    )


def _entities_from_raw(
    raw: List[dict], doc_id: str, segment_index: Optional[int] = None
) -> List[Entity]:
    entities = []
    for item in raw:
        mention = {"doc_id": doc_id, "score": item["score"]}
        if segment_index is not None:
            mention["segment"] = segment_index
        entities.append(
            Entity(
                id=Entity.generate_id(item["text"], item["label"]),
                text=item["text"],
                entity_type=item["label"],
                score=item["score"],
                source_doc=doc_id,
                mentions=[mention],
            )
        )
    return entities


def _relations_from_raw(raw: List[dict], doc_id: str) -> List[Relation]:
    return [
        Relation(
            head_text=item["head"]["text"],
            relation_type=item["relation"],
            tail_text=item["tail"]["text"],
            score=item["score"],
            source_doc=doc_id,
        )
        for item in raw
    ]


class EntityRelationExtractor:
    def __init__(self, config: PipelineConfig, model=None):
        from kgraph.extractors.model_cache import get_gliner_model
        self.model = model if model is not None else get_gliner_model(config.ner.name)
        self.entity_labels = config.entities
        self.relation_labels = config.relations
        self.entity_threshold = config.thresholds.entity
        self.relation_threshold = config.thresholds.relation
        self.entity_index: Dict[str, Entity] = {}

    def extract_from_document(
        self,
        doc: RawDocument,
        entity_labels: Optional[List[str]] = None,
        relation_labels: Optional[List[str]] = None,
    ) -> tuple[list[dict], list[dict]]:
        """Extract entities and relations from a single document in one pass.

        ``entity_labels``/``relation_labels`` override the configured label
        sets for this call only, enabling per-document extraction lenses.
        """
        entities, relations = extract_entities_relations(
            self.model,
            doc.content,
            entity_labels if entity_labels is not None else self.entity_labels,
            relation_labels if relation_labels is not None else self.relation_labels,
            self.entity_threshold,
            self.relation_threshold,
            doc_id=doc.id,
        )
        # Process entities with deduplication
        new_entities = []
        for entity in entities:
            if entity.id in self.entity_index:
                self.entity_index[entity.id].mentions.extend(entity.mentions)
            else:
                self.entity_index[entity.id] = entity
                new_entities.append(entity)
        return new_entities, relations

    def extract_from_corpus(
        self, documents: List[RawDocument]
    ) -> tuple[Dict[str, List[Entity]], List[Relation]]:
        """Extract entities and relations from multiple documents."""
        doc_entities = []
        all_relations = []

        for doc in documents:
            entities, relations = self.extract_from_document(doc)
            doc_entities.extend(entities)
            all_relations.extend(relations)
            log.info(
                "Extracted %d entities and %d relations from %s",
                len(entities),
                len(relations),
                doc.id,
            )

        return doc_entities, all_relations

    def get_all_entities(self) -> List[Entity]:
        return list(self.entity_index.values())

class GLiNERGraph(EntityRelationExtractor):
    """In-memory knowledge graph using NetworkX."""

    def __init__(self, my_config: PipelineConfig, model=None):
        super().__init__(my_config, model=model)
        self.graph = nx.MultiDiGraph()
        self.entity_text_index: Dict[str, List[str]] = {}
        self.entity_type_index: Dict[str, List[str]] = {}
        self.doc_index: Dict[str, Set[str]] = {}
        self.entities = list[Entity]
        self.relations = list[Relation]
        merging = my_config.entity_merging
        self.merger = (
            EntityMerger()
            if merging.enabled
            else None
        )
        
    def build(self, documents: List[RawDocument]):
        """Build graph"""
        self.extract_entities(documents)
        for entity in self.entities:
            self.add_entity(entity)
        for relation in self.relations:
            self.add_relation(relation)
        
    def extract_entities(self, documents: List[RawDocument]):
        """Extract entities from documents"""
        self.entities, self.relations = self.extract_from_corpus(documents)

    def add_entity(self, entity: Entity):
        """Add an entity as a node.

        Entities are deduplicated by normalized text: the same span decoded
        with different labels (e.g. "CoT RL" as ``CoT RL`` and ``CoT RL model``)
        is merged into a single node, keeping the best score and accumulating
        mentions. When ``entity_merging`` is enabled, near-duplicates are also
        collapsed via canonical form (leading articles, whitespace) and, when
        still unmatched, via embedding similarity.
        """
        normalized = canonical(entity.text)
        existing = self.entity_text_index.get(normalized)

        if existing is None and self.merger is not None:
            match = self.merger.match(normalized)
            if match is not None:
                existing = self.entity_text_index.get(match)

        if existing:
            node = self.graph.nodes[existing[0]]
            if entity.score > node.get("score", 0):
                node["score"] = entity.score
                node["entity_type"] = entity.entity_type
            node["mentions"].extend(entity.mentions)
            return

        self.graph.add_node(
            entity.id,
            text=entity.text,
            entity_type=entity.entity_type,
            score=entity.score,
            mentions=entity.mentions,
        )
        self.entity_text_index.setdefault(normalized, []).append(entity.id)
        self.entity_type_index.setdefault(entity.entity_type, []).append(entity.id)

        for mention in entity.mentions:
            self.doc_index.setdefault(mention["doc_id"], set()).add(entity.id)

    def add_relation(self, relation: Relation):
        """Add a relation as an edge between two entities.

        Duplicate relations (same head, relation type and tail) are merged:
        the score is kept at the best detection and a ``count`` attribute
        records how many times the relation was observed.
        """
        source_ids = self.find_entity(relation.head_text)
        target_ids = self.find_entity(relation.tail_text)

        if not source_ids or not target_ids:
            return

        source_id, target_id = source_ids[0], target_ids[0]
        key = self._find_edge(source_id, target_id, relation.relation_type)
        if key is None:
            self.graph.add_edge(
                source_id,
                target_id,
                relation_type=relation.relation_type,
                score=relation.score,
                count=1,
                source_doc=relation.source_doc,
                docs={relation.source_doc} if relation.source_doc else set(),
            )
            return

        existing = self.graph.edges[source_id, target_id, key]
        existing["score"] = max(existing["score"], relation.score)
        existing["count"] = existing.get("count", 1) + 1
        docs = existing.setdefault("docs", set())
        if relation.source_doc:
            docs.add(relation.source_doc)

    def _find_edge(self, source_id: str, target_id: str, relation_type: str):
        """Return the edge key between two nodes with the given relation type."""
        edge_data = self.graph.get_edge_data(source_id, target_id)
        if not edge_data:
            return None
        for key, data in edge_data.items():
            if data.get("relation_type") == relation_type:
                return key
        return None

    def find_entity(self, text: str) -> List[str]:
        """Find entity IDs by text (case-insensitive)."""
        return self.entity_text_index.get(canonical(text), [])

    def find_entity_type(self, entity_type: str) -> List[str]:
        """Find entity IDs by entity (case-insensitive)."""
        return self.entity_type_index.get(entity_type.lower(), [])

    def get_neighbors(
        self, entity_id: str, depth: int = 1, relation_types: List[str] = None
    ) -> Set[str]:
        """Get entity IDs reachable within N hops."""
        if entity_id not in self.graph:
            return set()

        neighbors = set()
        current_level = {entity_id}

        for _ in range(depth):
            next_level = set()
            for node in current_level:
                for _, target, data in self.graph.out_edges(node, data=True):
                    if relation_types is None or data["relation_type"] in relation_types:
                        next_level.add(target)
                for source, _, data in self.graph.in_edges(node, data=True):
                    if relation_types is None or data["relation_type"] in relation_types:
                        next_level.add(source)
            neighbors.update(next_level)
            current_level = next_level - neighbors

        neighbors.discard(entity_id)
        return neighbors

    def get_subgraph(self, entity_ids: Set[str]) -> nx.MultiDiGraph:
        """Extract a subgraph containing the specified entities."""
        return self.graph.subgraph(entity_ids).copy()

    def find_paths(
        self, source_id: str, target_id: str, max_length: int = 3
    ) -> List[List[str]]:
        """Find all simple paths between two entities."""
        if source_id not in self.graph or target_id not in self.graph:
            return []
        try:
            return list(
                nx.all_simple_paths(self.graph, source_id, target_id, cutoff=max_length)
            )
        except nx.NetworkXNoPath:
            return []

    def get_entity_context(self, entity_id: str) -> dict:
        """Get full context for an entity including its relations."""
        if entity_id not in self.graph:
            return None

        node = self.graph.nodes[entity_id]

        outgoing = []
        for _, target, data in self.graph.out_edges(entity_id, data=True):
            t = self.graph.nodes[target]
            outgoing.append({
                "relation": data["relation_type"],
                "target": t["text"],
                "target_type": t["entity_type"],
            })

        incoming = []
        for source, _, data in self.graph.in_edges(entity_id, data=True):
            s = self.graph.nodes[source]
            incoming.append({
                "relation": data["relation_type"],
                "source": s["text"],
                "source_type": s["entity_type"],
            })

        return {
            "id": entity_id,
            "text": node["text"],
            "type": node["entity_type"],
            "outgoing_relations": outgoing,
            "incoming_relations": incoming,
        }

    def get_stats(self) -> dict:
        return {
            "num_entities": self.graph.number_of_nodes(),
            "num_relations": self.graph.number_of_edges(),
            "avg_degree": (
                sum(dict(self.graph.degree()).values())
                / max(1, self.graph.number_of_nodes())
            ),
        }

    def export_to_json(self, filepath: str):
        data = {
            "nodes": [{"id": n, **d} for n, d in self.graph.nodes(data=True)],
            "edges": [
                {"source": u, "target": v, **d}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)