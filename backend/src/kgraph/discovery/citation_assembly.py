"""Citation-guided assembly: discovery → GLiNER → classification.

Orchestrates the full citation-guided pipeline:
1. CitationDiscovery builds the taxonomy from citing contexts.
2. GLiNER extracts entities/relations with per-document labels.
3. Nodes are classified as core / seed-only / refs-only.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Set, Tuple

from dataclasses import dataclass, field

from kgraph.discovery.bibliography import (
    BibliographyEntry,
    build_entry_index,
    parse_bibliography_entries,
)
from kgraph.discovery.citation_graph import (
    CitationDiscovery,
    CitationDiscoveryResult,
    ensure_ollama,
    unload_ollama,
)
from kgraph.extractors.gliner import GLiNERGraph
from kgraph.graph.config import build_pipeline_config, load_pipeline_config
from kgraph.graph.models import RawDocument
from kgraph.segmentation.extractor import SegmentedGraphExtractor

log = logging.getLogger(__name__)


@dataclass
class CitationGraphResult:
    """Result of the citation-guided assembly pipeline."""
    graph: GLiNERGraph
    node_classifications: Dict[str, str]
    discovery: CitationDiscoveryResult


class CitationAssembly:
    """Orchestrate citation-guided discovery → GLiNER → classification.

    Usage::

        assembly = CitationAssembly("./configs/params.yaml")
        result = assembly.run(seed_doc, ref_docs, bibliography)
        # result.graph — the final GLiNERGraph
        # result.node_classifications — nid → "core"|"seed-only"|"refs-only"
    """

    SEED_DOC_ID = "__seed__"

    def __init__(self, config_path: str):
        self.config_path = config_path

    def run(
        self,
        seed_doc: RawDocument,
        ref_docs: List[RawDocument],
        bibliography: List[BibliographyEntry] | None = None,
        *,
        segmented: bool | None = None,
        on_progress: Callable[[GLiNERGraph, Dict[str, str]], None] | None = None,
    ) -> CitationGraphResult:
        """Run the full citation-guided pipeline.

        Args:
            seed_doc: The seed paper body (without references section).
            ref_docs: Resolved reference documents.
            bibliography: Parsed bibliography entries. If None, parsed from seed_doc.
            segmented: Override segmentation config. None = use config default.
            on_progress: Optional callback invoked periodically with a snapshot of
                the partial ``GLiNERGraph`` and its live node classifications
                (computed from the mentions accumulated so far). Used for
                progressive rendering while extraction runs.

        Returns:
            CitationGraphResult with the classified graph.
        """
        # Parse bibliography if not provided
        if bibliography is None:
            from kgraph.discovery.bibliography import parse_bibliography_entries
            # Try to find the references section in the seed doc
            import re
            m = re.search(r"^#{1,3}\s*References\s*$", seed_doc.content, flags=re.M)
            if m:
                ref_section = seed_doc.content[m.end():]
                nxt = re.search(r"^#{1,3}\s+", ref_section, flags=re.M)
                if nxt:
                    ref_section = ref_section[:nxt.start()]
                bibliography = parse_bibliography_entries(ref_section)
            else:
                bibliography = []
            log.info("Parsed %d bibliography entries from seed", len(bibliography))

        # 1. Citation discovery
        log.info("Running citation discovery...")
        discovery = CitationDiscovery(load_pipeline_config(self.config_path))
        result = discovery.build(seed_doc, ref_docs, bibliography)
        log.info(
            "Discovery done: %d entity labels, %d relation labels, %d per-doc mappings",
            len(result.entity_labels),
            len(result.relation_labels),
            len(result.per_doc_labels),
        )

        # 2. Build GLiNER config with global taxonomy
        base_config = load_pipeline_config(self.config_path)
        final_config = build_pipeline_config(
            self.config_path,
            entities=result.entity_labels,
            relations=result.relation_labels,
        )

        # Determine segmentation
        use_segmentation = (
            base_config.segmentation.enabled if segmented is None else segmented
        )

        # 3. Per-document extraction with per-doc labels
        log.info("Running GLiNER extraction (segmented=%s)...", use_segmentation)
        log.info("GLiNER model path: %s", final_config.ner.name)
        all_docs = self._all_docs(seed_doc, ref_docs)

        def _report(graph: GLiNERGraph) -> None:
            if on_progress is None:
                return
            on_progress(graph, self._classify_nodes(graph, result))

        if use_segmentation:
            kg = SegmentedGraphExtractor(final_config).build(
                self._build_docs_with_labels(seed_doc, ref_docs, result),
                on_progress=_report,
            )
        else:
            from tqdm import tqdm
            kg = GLiNERGraph(final_config)
            for doc in tqdm(all_docs, desc="GLiNER extract", unit="doc", leave=False):
                e_lab, r_lab = result.per_doc_labels.get(
                    doc.id, (result.entity_labels, result.relation_labels)
                )
                ents, rels = kg.extract_from_document(
                    doc,
                    entity_labels=e_lab or result.entity_labels,
                    relation_labels=r_lab or result.relation_labels,
                )
                for e in ents:
                    kg.add_entity(e)
                for r in rels:
                    kg.add_relation(r)
                _report(kg)

        # 4. Classify nodes
        classifications = self._classify_nodes(kg, result)

        # 5. Add metadata (year, type) to nodes
        self._enrich_nodes(kg, result, classifications)

        log.info(
            "Graph built: %d entities, %d relations (%d core, %d seed-only, %d refs-only)",
            kg.graph.number_of_nodes(),
            kg.graph.number_of_edges(),
            sum(1 for v in classifications.values() if v == "core"),
            sum(1 for v in classifications.values() if v == "seed-only"),
            sum(1 for v in classifications.values() if v == "refs-only"),
        )

        return CitationGraphResult(
            graph=kg,
            node_classifications=classifications,
            discovery=result,
        )

    def _all_docs(
        self, seed_doc: RawDocument, ref_docs: List[RawDocument]
    ) -> List[RawDocument]:
        """Return seed + refs as a flat list."""
        return [seed_doc] + list(ref_docs)

    def _build_docs_with_labels(
        self,
        seed_doc: RawDocument,
        ref_docs: List[RawDocument],
        result: CitationDiscoveryResult,
    ) -> List[RawDocument]:
        """Build doc list with per-doc labels stored in metadata.

        The SegmentedGraphExtractor doesn't accept per-doc labels directly,
        so we store them in metadata for now and use the global taxonomy.
        For full per-doc label support, a custom extractor loop is needed.
        """
        docs = []
        for doc in self._all_docs(seed_doc, ref_docs):
            e_lab, r_lab = result.per_doc_labels.get(
                doc.id, (result.entity_labels, result.relation_labels)
            )
            doc_copy = RawDocument(
                id=doc.id,
                content=doc.content[:result.entity_labels.__len__() and 24000 or 24000],
                source=doc.source,
                metadata={**doc.metadata, "_entity_labels": e_lab, "_relation_labels": r_lab},
                docling_doc=doc.docling_doc,
            )
            docs.append(doc_copy)
        return docs

    @staticmethod
    def _classify_nodes(
        kg: GLiNERGraph,
        result: CitationDiscoveryResult,
    ) -> Dict[str, str]:
        """Classify graph nodes as core / seed-only / refs-only.

        - core: appears in seed AND at least 1 reference
        - seed-only: appears only in the seed (novelty surface)
        - refs-only: appears only in references (background concepts)
        """
        classifications: Dict[str, str] = {}
        for nid, data in kg.graph.nodes(data=True):
            docs_of = {m["doc_id"] for m in data.get("mentions", [])}
            n_refs = len(docs_of - {CitationAssembly.SEED_DOC_ID})
            if CitationAssembly.SEED_DOC_ID in docs_of and n_refs:
                classifications[nid] = "core"
            elif CitationAssembly.SEED_DOC_ID in docs_of:
                classifications[nid] = "seed-only"
            else:
                classifications[nid] = "refs-only"
        return classifications

    @staticmethod
    def _enrich_nodes(
        kg: GLiNERGraph,
        result: CitationDiscoveryResult,
        classifications: Dict[str, str],
    ) -> None:
        """Add year, type, and classification metadata to graph nodes."""
        # Build doc_id → year lookup from bibliography
        doc_year: Dict[str, int] = {}
        for entry in result.bibliography:
            if entry.year:
                for aid in entry.arxiv_ids:
                    import re
                    base = re.sub(r"v\d+$", "", aid)
                    doc_year[base] = entry.year

        for nid, data in kg.graph.nodes(data=True):
            data["classification"] = classifications.get(nid, "unknown")

            # Year from the source document
            mentions = data.get("mentions", [])
            if mentions:
                doc_id = mentions[0].get("doc_id", "")
                if doc_id in doc_year:
                    data["year"] = doc_year[doc_id]

            # Type from concept_type_map (best effort: match node text)
            text_lower = data["text"].lower().strip()
            if text_lower in result.concept_type_map:
                data["entity_type"] = result.concept_type_map[text_lower]
