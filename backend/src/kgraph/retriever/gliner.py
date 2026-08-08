from gliner import GLiNER
from dataclasses import dataclass
from typing import List
from kgraph.graph.config import PipelineConfig
from kgraph.extractors.gliner import GLiNERGraph

@dataclass
class RetrievalResult:
    """Result from graph-based retrieval."""
    query_entities: List[dict]
    expanded_entities: List[dict]
    relevant_relations: List[dict]
    context_documents: List[str]


class GLiNERRetriever:
    """Retrieve relevant context using knowledge graph traversal."""

    def __init__(
        self,
        config: PipelineConfig,
        knowledge_graph: GLiNERGraph,
        expansion_depth: int = 2,
    ):
        self.model = GLiNER.from_pretrained(config.ner.name)
        self.knowledge_graph = knowledge_graph
        self.entity_types = config.entities
        self.relation_types = config.relations
        self.expansion_depth = expansion_depth

    def retrieve(
        self, query: str, top_k: int = 5, expansion_depth: int = None
    ) -> RetrievalResult:
        """
        Retrieve context for a query:
        1. Extract entities from query
        2. Match them in the graph
        3. Expand to neighbors
        4. Collect relations and source docs
        """
        depth = expansion_depth or self.expansion_depth

        # Extract entities from query (lower threshold to catch more)
        query_entities_raw, _ = self.model.inference(
            texts=[query],
            labels=self.entity_types,
            relations=self.relation_types,
            threshold=0.3,
            relation_threshold=0.3,
            return_relations=True,
            flat_ner=False,
        )

        query_entities = []
        matched_ids = set()

        for item in query_entities_raw[0]:
            matches = self.knowledge_graph.find_entity_type(item["text"])
            query_entities.append({
                "text": item["text"],
                "type": item["label"],
                "graph_matches": matches,
            })
            matched_ids.update(matches)

        # Expand neighborhood
        expanded_ids = set(matched_ids)
        for entity_id in matched_ids:
            neighbors = self.knowledge_graph.get_neighbors(entity_id, depth=depth)
            expanded_ids.update(neighbors)

        # Gather entity details
        expanded_entities = []
        for entity_id in expanded_ids:
            ctx = self.knowledge_graph.get_entity_context(entity_id)
            if ctx:
                ctx["is_query_match"] = entity_id in matched_ids
                expanded_entities.append(ctx)

        expanded_entities.sort(
            key=lambda e: (
                -int(e["is_query_match"]),
                -(len(e["outgoing_relations"]) + len(e["incoming_relations"])),
            )
        )

        # Collect relations from the subgraph
        subgraph = self.knowledge_graph.get_subgraph(expanded_ids)
        relevant_relations = []
        for source, target, data in subgraph.edges(data=True):
            s = subgraph.nodes[source]
            t = subgraph.nodes[target]
            relevant_relations.append({
                "source": s["text"],
                "relation": data["relation_type"],
                "target": t["text"],
            })

        # Find source documents
        context_docs = set()
        for entity_id in expanded_ids:
            node = self.knowledge_graph.graph.nodes.get(entity_id, {})
            for mention in node.get("mentions", []):
                context_docs.add(mention["doc_id"])

        return RetrievalResult(
            query_entities=query_entities,
            expanded_entities=expanded_entities[:top_k],
            relevant_relations=relevant_relations,
            context_documents=list(context_docs),
        )

    def format_context(self, result: RetrievalResult) -> str:
        """Format retrieval result as context for an LLM."""
        parts = []

        if result.expanded_entities:
            parts.append("## Relevant Entities\n")
            for entity in result.expanded_entities:
                marker = "-> " if entity.get("is_query_match") else "   "
                parts.append(f"{marker}**{entity['text']}** ({entity['type']})")

        if result.relevant_relations:
            parts.append("\n## Known Relationships\n")
            for rel in result.relevant_relations:
                parts.append(f"- {rel['source']} --[{rel['relation']}]--> {rel['target']}")

        return "\n".join(parts)