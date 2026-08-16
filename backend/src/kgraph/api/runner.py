"""Background task that runs the corpus pipeline and updates analysis status."""

import time
import traceback
from pathlib import Path
from threading import Thread

from kgraph.api.routers.analysis import _analyses


def run_analysis(analysis_id: str):
    """Run the full pipeline in a background thread."""
    a = _analyses.get(analysis_id)
    if not a:
        return

    topic = a["topic"]
    max_papers = a.get("max_papers", 2)
    config_path = str(Path(__file__).resolve().parents[4] / "configs" / "params.yaml")

    def update(step_key: str, progress: float, status: str = "running"):
        a["status"] = status
        a["progress"] = progress
        a["current_step"] = step_key
        for s in a["steps"]:
            if s["key"] == step_key:
                s["status"] = "running"
            elif a["steps"].index(s) < a["steps"].index(
                next(x for x in a["steps"] if x["key"] == step_key)
            ):
                s["status"] = "done"

    try:
        from kgraph.cli.arxiv_demo import fetch_arxiv
        from kgraph.ingestion.parsers.parsers import parse_document
        from kgraph.discovery.topic_graph import TopicGraph
        from kgraph.discovery.assembly import DiscoveryAssembly
        from kgraph.segmentation.chunker import Segmenter
        from kgraph.segmentation.extractor import SegmentedGraphExtractor
        from kgraph.corpus.merge import CorpusGraphBuilder
        from kgraph.graph.config import load_config

        # Step 1: Fetch papers
        update("fetch", 0.05)
        time.sleep(0.3)
        config = load_config(config_path)
        raw_docs = fetch_arxiv(topic, max_results=max_papers, config=config)
        if not raw_docs:
            a["status"] = "error"
            a["error"] = f"No papers found for topic: {topic}"
            return
        a["papers_fetched"] = len(raw_docs)
        update("fetch", 0.15, "running")
        time.sleep(0.2)

        # Step 2: Parse documents
        update("parse", 0.20)
        time.sleep(0.3)
        docs = []
        for doc in raw_docs:
            parsed = parse_document(doc, config)
            docs.append(parsed)
        update("parse", 0.30)
        time.sleep(0.2)

        # Step 3: Build taxonomy per document
        update("taxonomy", 0.35)
        time.sleep(0.3)
        taxonomies = {}
        for doc in docs:
            tg = TopicGraph(config)
            tg.build(doc)
            assembly = DiscoveryAssembly(tg.graph)
            entity_labels, relation_labels = assembly.build()
            taxonomies[doc.id] = (entity_labels, relation_labels)
        update("taxonomy", 0.50)
        time.sleep(0.2)

        # Step 4: Segment
        update("segment", 0.55)
        time.sleep(0.3)
        segmenter = Segmenter(config)
        all_segments = []
        for doc in docs:
            segs = segmenter.segment(doc)
            all_segments.extend([(doc, s) for s in segs])
        update("segment", 0.60)
        time.sleep(0.2)

        # Step 5: Extract
        update("extract", 0.65)
        time.sleep(0.3)
        extractor = SegmentedGraphExtractor(config)
        per_doc = {}
        for doc in docs:
            segs = [s for d, s in all_segments if d.id == doc.id]
            tax = taxonomies[doc.id]
            entities, relations = extractor.extract(segs, tax)
            per_doc[doc.id] = (entities, relations)
        update("extract", 0.80)
        time.sleep(0.2)

        # Step 6: Merge
        update("merge", 0.85)
        time.sleep(0.3)
        per_document = [
            (doc_id, entities, relations)
            for doc_id, (entities, relations) in per_doc.items()
        ]
        from kgraph.corpus.merge import _merge_per_document, summarize_corpus
        graph = _merge_per_document(per_document)
        summary = summarize_corpus(graph, [doc.id for doc in docs])
        update("merge", 0.95)
        time.sleep(0.2)

        # Build result
        nodes = []
        for nid, data in graph.nodes(data=True):
            nodes.append({
                "id": nid,
                "name": data.get("text", nid),
                "type": data.get("type", "concept"),
                "importance": round(data.get("score", 0.5) * 10, 1),
                "source": "shared" if data.get("count", 1) > 1 else "main",
                "documents": data.get("documents", []),
            })

        edges = []
        for u, v, data in graph.edges(data=True):
            edges.append({
                "id": f"{u}_{v}",
                "source": u,
                "target": v,
                "relation": data.get("relation", "related to"),
                "confidence": round(data.get("score", 0.5), 2),
                "documents": data.get("documents", []),
            })

        update("done", 1.0, "completed")
        a["result"] = {
            "id": analysis_id,
            "topic": topic,
            "papers": [{"id": doc.id, "title": doc.title} for doc in docs],
            "topics": nodes,
            "relationships": edges,
            "stats": summary,
        }

    except Exception as e:
        a["status"] = "error"
        a["error"] = str(e)
        a["traceback"] = traceback.format_exc()
