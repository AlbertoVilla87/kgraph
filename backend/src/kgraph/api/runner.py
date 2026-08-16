"""Background task that runs the corpus pipeline and updates analysis status."""

import time
import traceback
from pathlib import Path

from kgraph.api.state import analyses


def run_analysis(analysis_id: str):
    """Run the full pipeline in a background thread."""
    a = analyses.get(analysis_id)
    if not a:
        return

    topic = a["topic"]
    max_papers = a.get("max_papers", 2)
    config_path = str(Path(__file__).resolve().parents[3] / "configs" / "params.yaml")

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
        from kgraph.ingestion.arxiv import ArxivSource
        from kgraph.corpus import CorpusGraphBuilder

        # Step 1: Fetch papers from arXiv
        update("fetch", 0.10)
        time.sleep(0.3)
        source = ArxivSource(query=topic, max_results=max_papers)
        raw_docs = source.fetch()
        if not raw_docs:
            a["status"] = "error"
            a["error"] = f"No papers found for topic: {topic}"
            return
        a["papers_fetched"] = len(raw_docs)
        a["papers"] = [
            {"id": doc.id, "title": doc.metadata.get("title", doc.id)}
            for doc in raw_docs
        ]
        update("fetch", 0.20, "running")
        time.sleep(0.2)

        # Steps 2-6: Run the full corpus pipeline
        # The builder handles parsing, taxonomy, segmentation, extraction, merge
        update("parse", 0.25)
        time.sleep(0.2)
        update("taxonomy", 0.30)
        time.sleep(0.2)
        update("segment", 0.35)

        builder = CorpusGraphBuilder(config_path, workers=0)
        update("extract", 0.40)

        graph, summary = builder.build(raw_docs)

        update("merge", 0.90)
        time.sleep(0.2)

        # Build result
        doc_ids = [doc.id for doc in raw_docs]
        nodes = []
        for nid, data in graph.nodes(data=True):
            node_docs = list(data.get("docs", set()))
            nodes.append({
                "id": nid,
                "name": data.get("text", nid),
                "type": data.get("entity_type", "concept"),
                "importance": round(data.get("score", 0.5) * 10, 1),
                "source": "shared" if len(node_docs) > 1 else "main",
                "documents": node_docs,
            })

        edges = []
        for u, v, key, data in graph.edges(keys=True, data=True):
            edge_docs = list(data.get("docs", set()))
            edges.append({
                "id": f"{u}_{v}_{key}",
                "source": u,
                "target": v,
                "relation": data.get("relation_type", "related to"),
                "confidence": round(data.get("score", 0.5), 2),
                "documents": edge_docs,
            })

        update("done", 1.0, "completed")
        a["result"] = {
            "id": analysis_id,
            "topic": topic,
            "papers": a["papers"],
            "topics": nodes,
            "relationships": edges,
            "stats": summary,
        }

    except Exception as e:
        a["status"] = "error"
        a["error"] = str(e)
        a["traceback"] = traceback.format_exc()
