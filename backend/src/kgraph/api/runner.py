"""Background task that runs the corpus pipeline and updates analysis status."""

import time
import traceback
from pathlib import Path

from kgraph.api.state import analyses


def _advance_steps(a: dict, current_key: str, status: str = "running"):
    """Mark steps as done/running based on their order."""
    a["status"] = status
    for s in a["steps"]:
        if s["key"] == current_key:
            s["status"] = "running" if status != "completed" else "done"
            break
        s["status"] = "done"


def run_analysis(analysis_id: str):
    """Run the full pipeline in a background thread."""
    a = analyses.get(analysis_id)
    if not a:
        return

    seed_url = a.get("seed_url")
    topic = a.get("topic", "")
    max_papers = a.get("max_papers", 2)
    max_references = a.get("max_references", 15)
    config_path = str(Path(__file__).resolve().parents[3] / "configs" / "params.yaml")

    def update(step_key: str, progress: float, detail: str = ""):
        a["current_step"] = step_key
        a["progress"] = progress
        a["detail"] = detail
        _advance_steps(a, step_key)

    try:
        if seed_url:
            _run_seed_pipeline(a, seed_url, max_references, update, config_path)
        else:
            _run_topic_pipeline(a, topic, max_papers, update, config_path)

    except Exception as e:
        a["status"] = "error"
        a["error"] = str(e)
        a["traceback"] = traceback.format_exc()


def _run_topic_pipeline(a: dict, topic: str, max_papers: int, update, config_path: str):
    """Topic-based pipeline: search a data source by query."""
    from kgraph.ingestion.arxiv import ArxivSource

    update("fetch", 0.10, f"Searching arXiv for '{topic}'...")
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
    update("fetch", 0.20, f"Found {len(raw_docs)} papers")
    time.sleep(0.2)

    _run_corpus_pipeline(a, raw_docs, update, config_path)


def _run_seed_pipeline(
    a: dict, seed_url: str, max_references: int, update, config_path: str
):
    """Seed paper pipeline: download seed, extract references, download them."""
    from kgraph.ingestion.seed_paper import SeedPaperSource, _parse_arxiv_id
    from kgraph.ingestion.arxiv import ArxivSource
    from kgraph.ingestion.references import ArxivReferenceExtractor

    update("fetch_seed", 0.05, f"Downloading seed paper: {seed_url}")
    time.sleep(0.2)

    seed_id = _parse_arxiv_id(seed_url)
    inner_source = ArxivSource(query=seed_id, max_results=1)
    extractor = ArxivReferenceExtractor()

    source = SeedPaperSource(
        source=inner_source,
        extractor=extractor,
        seed_id=seed_id,
        max_references=max_references,
    )

    # Progress callback: updates detail text per paper downloaded
    def on_seed_progress(current: int, total: int, detail: str):
        # Map download progress into the 10%-30% range
        if total > 0:
            progress = 0.10 + (current / total) * 0.20
        else:
            progress = 0.10
        update("fetch_refs", progress, detail)

    raw_docs = source.fetch(on_progress=on_seed_progress)
    if not raw_docs:
        a["status"] = "error"
        a["error"] = f"Could not download seed paper: {seed_url}"
        return

    update("fetch_refs", 0.30, f"Downloaded {len(raw_docs)} papers total")
    time.sleep(0.2)

    a["papers_fetched"] = len(raw_docs)
    a["papers"] = [
        {"id": doc.id, "title": doc.metadata.get("title", doc.id)}
        for doc in raw_docs
    ]

    _run_corpus_pipeline(a, raw_docs, update, config_path)


def _run_corpus_pipeline(a: dict, raw_docs: list, update, config_path: str):
    """Shared corpus pipeline: taxonomy -> segment -> extract -> merge."""
    from kgraph.corpus import CorpusGraphBuilder

    n = len(raw_docs)
    update("parse", 0.35, f"Parsing {n} documents...")
    time.sleep(0.2)
    update("taxonomy", 0.40, "Building topic taxonomy per document...")
    time.sleep(0.2)
    update("segment", 0.45, "Segmenting documents for extraction...")

    builder = CorpusGraphBuilder(config_path, workers=0)
    update("extract", 0.50, f"Extracting entities from {n} documents...")

    graph, summary = builder.build(raw_docs)

    update("merge", 0.90, "Merging cross-document graph...")
    time.sleep(0.2)

    main_doc_id = raw_docs[0].id if raw_docs else None

    nodes = []
    for nid, data in graph.nodes(data=True):
        node_docs = list(data.get("docs", set()))
        if len(node_docs) > 1:
            source = "shared"
        elif main_doc_id and main_doc_id in data.get("docs", set()):
            source = "main"
        else:
            source = "reference"
        nodes.append({
            "id": nid,
            "name": data.get("text", nid),
            "type": data.get("entity_type", "concept"),
            "importance": round(data.get("score", 0.5) * 10, 1),
            "source": source,
            "documents": node_docs,
        })

    edges = []
    for u, v, key, data in graph.edges(keys=True, data=True):
        edge_docs = list(data.get("docs", set()))
        if len(edge_docs) > 1:
            source = "shared"
        elif main_doc_id and main_doc_id in data.get("docs", set()):
            source = "main"
        else:
            source = "reference"
        edges.append({
            "id": f"{u}_{v}_{key}",
            "source": u,
            "target": v,
            "relation": data.get("relation_type", "related to"),
            "confidence": round(data.get("score", 0.5), 2),
            "documents": edge_docs,
        })

    update("done", 1.0, "Analysis complete")
    a["result"] = {
        "id": a["id"],
        "topic": a.get("topic") or a.get("seed_url") or "",
        "papers": a["papers"],
        "topics": nodes,
        "relationships": edges,
        "stats": summary,
    }
