"""Parallel GLiNER extraction over segments, concatenated into one graph.

GLiNER truncates documents longer than its context window, so the whole
document cannot be fed at once. ``SegmentedGraphExtractor``:

1. segments every document with the section-aware ``Segmenter``,
2. runs GLiNER over every segment concurrently (one shared model, one
   Python thread per worker),
3. concatenates the results into a ``GLiNERGraph`` reusing its existing
   merge logic (canonical dedup for entities, best-score + count for
   relations), so cross-segment mentions accumulate as if the document had
   been processed whole.

Concurrency model: torch releases the GIL during inference, so threads give
real parallelism on CPU. To avoid intra-op oversubscription each worker is
pinned to a single torch thread when more than one worker is used.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import torch

from kgraph.extractors.gliner import GLiNERGraph, extract_entities_relations
from kgraph.graph.config import PipelineConfig
from kgraph.graph.models import Entity, RawDocument, Relation
from kgraph.segmentation.chunker import Segmenter
from kgraph.segmentation.models import Segment

log = logging.getLogger(__name__)


def _default_workers() -> int:
    return max(1, (os.cpu_count() or 1) // 2)


class SegmentedGraphExtractor:
    """Build a ``GLiNERGraph`` by extracting entities/relations per segment."""

    def __init__(self, config: PipelineConfig):
        from kgraph.extractors.model_cache import get_gliner_model
        self.config = config
        self.model = get_gliner_model(config.ner.name)
        self.entity_labels = config.entities
        self.relation_labels = config.relations
        self.entity_threshold = config.thresholds.entity
        self.relation_threshold = config.thresholds.relation
        self.segmenter = Segmenter(config.ner.name, config.segmentation)
        self.workers = config.segmentation.workers or _default_workers()

    def build(self, documents: List[RawDocument]) -> GLiNERGraph:
        """Segment the documents, extract per segment and concatenate the graph."""
        from tqdm import tqdm

        graph = GLiNERGraph(self.config, model=self.model)
        segments = [
            segment
            for doc in documents
            for segment in self.segmenter.segment(doc)
        ]
        if not segments:
            return graph

        log.info("Processing %d segments across %d documents", len(segments), len(documents))

        if len(segments) <= 1 or self.workers <= 1:
            for segment in tqdm(segments, desc="GLiNER segments", unit="seg", leave=False):
                self._merge(graph, self._extract(segment))
            return graph

        self._limit_torch_threads()
        pbar = tqdm(total=len(segments), desc="GLiNER segments", unit="seg", leave=False)
        with ThreadPoolExecutor(max_workers=min(self.workers, len(segments))) as executor:
            futures = [executor.submit(self._extract, segment) for segment in segments]
            for future in as_completed(futures):
                self._merge(graph, future.result())
                pbar.update(1)
        pbar.close()
        return graph

    def _extract(
        self, segment: Segment
    ) -> Tuple[List[Entity], List[Relation]]:
        return extract_entities_relations(
            self.model,
            segment.text,
            self.entity_labels,
            self.relation_labels,
            self.entity_threshold,
            self.relation_threshold,
            doc_id=segment.doc_id,
            segment_index=segment.index,
        )

    @staticmethod
    def _merge(graph: GLiNERGraph, result: Tuple[List[Entity], List[Relation]]) -> None:
        entities, relations = result
        for entity in entities:
            graph.add_entity(entity)
        for relation in relations:
            graph.add_relation(relation)

    def _limit_torch_threads(self) -> None:
        torch.set_num_threads(1)
