"""Background task that runs the corpus pipeline and updates analysis status."""

import gc
import logging
import time
import traceback
from pathlib import Path

from kgraph.api.state import analyses

log = logging.getLogger(__name__)


def _advance_steps(a: dict, current_key: str, status: str = "running"):
    """Mark steps as done/running based on their order."""
    # The final "done" step always means the analysis completed
    if current_key == "done":
        a["status"] = "completed"
        for s in a["steps"]:
            s["status"] = "done"
        return

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
    mode = a.get("mode", "quick")
    discovery = a.get("discovery", "topic")
    config_path = str(Path(__file__).resolve().parents[3] / "configs" / "params.yaml")

    log.info("Starting analysis %s (seed=%s, topic=%s, mode=%s, discovery=%s)",
             analysis_id, seed_url or "-", topic or "-", mode, discovery)

    def update(step_key: str, progress: float, detail: str = ""):
        a["current_step"] = step_key
        a["progress"] = progress
        a["detail"] = detail
        _advance_steps(a, step_key)

    try:
        if seed_url:
            if discovery == "citation":
                _run_citation_pipeline(a, seed_url, max_references, update, config_path, mode)
            else:
                _run_seed_pipeline(a, seed_url, max_references, update, config_path, mode)
        else:
            if discovery == "citation":
                a["status"] = "error"
                a["error"] = "Citation discovery requires a seed paper (seed_url), not a topic query"
                return
            _run_topic_pipeline(a, topic, max_papers, update, config_path, mode)

        log.info("Analysis %s completed successfully", analysis_id)

    except Exception as e:
        a["status"] = "error"
        a["error"] = str(e)
        a["traceback"] = traceback.format_exc()
        log.error("Analysis %s failed: %s", analysis_id, e, exc_info=True)
    finally:
        gc.collect()


def _run_topic_pipeline(a: dict, topic: str, max_papers: int, update, config_path: str, mode: str = "quick"):
    """Topic-based pipeline: search a data source by query."""
    from kgraph.ingestion.arxiv import ArxivSource

    update("fetch", 0.10, f"Searching arXiv for '{topic}'...")
    time.sleep(0.3)
    source = ArxivSource(query=topic, max_results=max_papers)
    raw_docs = source.fetch()  # abstracts only — fast
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

    _run_corpus_pipeline(a, raw_docs, update, config_path, mode)


def _run_seed_pipeline(
    a: dict, seed_url: str, max_references: int, update, config_path: str, mode: str = "quick"
):
    """Seed paper pipeline: download seed, extract references, download them."""
    from kgraph.ingestion.seed_paper import SeedPaperSource, _parse_arxiv_id
    from kgraph.ingestion.arxiv import ArxivSource
    from kgraph.ingestion.references import ArxivReferenceExtractor

    update("fetch_seed", 0.05, f"Fetching seed paper: {seed_url}")
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

    # Quick mode: fetch abstracts only (no PDF download)
    if mode == "quick":
        raw_docs = _fetch_abstracts_only(source, seed_id, max_references, update)
    else:
        # Deep mode: download PDFs and parse with Docling
        def on_seed_progress(current: int, total: int, detail: str):
            if total > 0:
                progress = 0.10 + (current / total) * 0.20
            else:
                progress = 0.10
            update("fetch_refs", progress, detail)
        raw_docs = source.fetch(on_progress=on_seed_progress)

    if not raw_docs:
        a["status"] = "error"
        a["error"] = f"Could not fetch seed paper: {seed_url}"
        return

    update("fetch_refs", 0.30, f"Fetched {len(raw_docs)} papers total")
    time.sleep(0.2)

    a["papers_fetched"] = len(raw_docs)
    a["papers"] = [
        {"id": doc.id, "title": doc.metadata.get("title", doc.id)}
        for doc in raw_docs
    ]

    _run_corpus_pipeline(a, raw_docs, update, config_path, mode)


def _fetch_abstracts_only(source, seed_id: str, max_references: int, update) -> list:
    """Quick mode: download seed PDF for refs, then fetch referenced abstracts only."""
    from kgraph.ingestion.arxiv import ArxivSource
    from kgraph.ingestion.references import ArxivReferenceExtractor
    from kgraph.ingestion.parsers.parsers import parse_pdf_full
    import urllib.request
    from pathlib import Path

    # Step 1: Download seed PDF and parse it (needed for reference extraction)
    update("fetch_seed", 0.05, f"Downloading seed PDF: {seed_id}")
    source.source.max_results = 1
    source.source.query = seed_id
    seed_results = list(source.source.client.results(
        __import__('arxiv').Search(query=seed_id, max_results=1)
    ))
    if not seed_results:
        return []

    seed_result = seed_results[0]
    pdf_url = seed_result.pdf_url
    if not pdf_url:
        return []

    # Download seed PDF
    download_dir = Path("data/papers")
    download_dir.mkdir(parents=True, exist_ok=True)
    safe_id = seed_id.replace("/", "_")
    pdf_path = download_dir / f"{safe_id}.pdf"

    if not pdf_path.exists():
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "kgraph/0.1"})
        with urllib.request.urlopen(req) as resp, open(pdf_path, "wb") as f:
            f.write(resp.read())

    # Parse seed PDF to get full text for reference extraction
    update("references", 0.10, "Parsing seed PDF for references...")
    try:
        docling_doc, seed_text = parse_pdf_full(pdf_path)
    except Exception as e:
        log.warning("Failed to parse seed PDF: %s", e)
        # Fallback: use abstract
        seed_text = seed_result.summary or ""

    # Build seed doc with full text (for reference extraction)
    from kgraph.graph.models import RawDocument
    seed_doc = RawDocument(
        id=f"arxiv:{seed_result.get_short_id()}",
        content=seed_text,
        source="arxiv_seed",
        metadata=ArxivSource.metadata(seed_result),
        docling_doc=docling_doc if 'docling_doc' in dir() else None,
    )

    # Step 2: Extract references from the parsed PDF
    extractor = ArxivReferenceExtractor()
    extracted = extractor.extract(seed_text, max_refs=max_references)
    ref_ids = [ref.source_id for ref in extracted]
    update("references", 0.15, f"Found {len(ref_ids)} references")

    if not ref_ids:
        return [seed_doc]

    # Step 3: Fetch referenced abstracts only (no PDF download)
    ref_docs = []
    total = len(ref_ids)
    for i, rid in enumerate(ref_ids, 1):
        update("fetch_refs", 0.15 + (i / total) * 0.15, f"Fetching abstract {i}/{total}: {rid}")
        try:
            source.source.query = rid
            source.source.max_results = 1
            results = source.source.fetch()
            if results:
                ref_docs.append(results[0])
        except Exception as e:
            log.warning("Failed to fetch abstract %s: %s", rid, e)
            continue

    return [seed_doc] + ref_docs


def _run_citation_pipeline(a: dict, seed_url: str, max_references: int, update, config_path: str, mode: str = "quick"):
    """Citation-guided pipeline; always shuts down Ollama when finished.

    Ollama is a local server kept only for the duration of an analysis: killing
    it frees CPU/VRAM (and quietens the fans). The server is only terminated
    when kgraph started it itself (see citation_graph.shutdown_ollama).
    """
    try:
        _run_citation_pipeline_impl(a, seed_url, max_references, update, config_path, mode)
    finally:
        from kgraph.discovery.citation_graph import shutdown_ollama
        shutdown_ollama()
        # Release GLiNER/torch resources so the process does not keep cores
        # busy or memory held after extraction (parity with corpus pipeline).
        import gc
        import torch
        gc.collect()
        torch.set_num_threads(1)
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        elif torch.cuda.is_available():
            torch.cuda.empty_cache()


def _run_citation_pipeline_impl(a: dict, seed_url: str, max_references: int, update, config_path: str, mode: str = "quick"):
    """Citation-guided pipeline: seed citations define the GLiNER taxonomy.

    quick: seed gets full text (for bibliography), refs get abstracts only
    deep: seed + refs get full text, segmentation enabled
    """
    import re
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path

    import httpx
    from tqdm import tqdm

    from kgraph.graph.models import RawDocument
    from kgraph.ingestion.arxiv import ArxivSource
    from kgraph.discovery.bibliography import parse_bibliography_entries
    from kgraph.discovery.citation_assembly import CitationAssembly
    from kgraph.discovery.citation_graph import ensure_ollama, unload_ollama

    SEED_DOC_ID = "__seed__"

    # Fast HTTP client for downloads
    _http = httpx.Client(
        headers={"User-Agent": "kgraph/0.1"},
        timeout=httpx.Timeout(30.0, read=60.0),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    )

    def _fetch_arxiv_html(arxiv_id: str) -> tuple[str, str]:
        """Fetch paper from ar5iv HTML. Returns (body_text, references_text).

        Uses the semantic HTML structure instead of regex on plain text.
        """
        from bs4 import BeautifulSoup

        url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
        for attempt in range(3):
            try:
                resp = _http.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Extract body text (everything before the bibliography section)
                bib_section = soup.find("section", id="bib")
                body_text = ""
                if bib_section:
                    # Get all sections before bibliography
                    for el in bib_section.previous_siblings:
                        if hasattr(el, "get_text"):
                            body_text = el.get_text(separator="\n", strip=True) + "\n" + body_text
                else:
                    # Fallback: use article or body
                    article = soup.find("article") or soup.find("body") or soup
                    body_text = article.get_text(separator="\n", strip=True)

                # Extract references as structured text from <li> items
                refs_text = ""
                if bib_section:
                    bib_list = bib_section.find("ul", class_="ltx_biblist")
                    if bib_list:
                        ref_items = []
                        for li in bib_list.find_all("li", class_="ltx_bibitem"):
                            ref_items.append(li.get_text(separator=" ", strip=True))
                        refs_text = "\n".join(ref_items)

                max_chars = 24_000
                return body_text[:max_chars], refs_text
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                log.warning("HTTP %d fetching ar5iv %s", e.response.status_code, arxiv_id)
                return "", ""
            except httpx.RequestError as e:
                log.warning("Request error fetching ar5iv %s: %s", arxiv_id, e)
                if attempt < 2:
                    import time
                    time.sleep(1)
                    continue
                return "", ""
        return "", ""

    # 1. Fetch seed paper (full text via ar5iv HTML — needed for bibliography)
    update("fetch_seed", 0.05, f"Fetching seed paper: {seed_url}")
    log.info("Fetching seed paper: %s", seed_url)

    # Extract arxiv ID from URL
    seed_id = seed_url.rstrip("/").split("/")[-1]
    seed_id = re.sub(r"v\d+$", "", seed_id)  # strip version

    # Search arXiv for the seed (fast: single lookup)
    source = ArxivSource(query=seed_id, max_results=1)
    seed_results_raw = source.fetch()
    if not seed_results_raw:
        a["status"] = "error"
        a["error"] = f"Could not find seed paper: {seed_url}"
        return

    # Fetch full text from ar5iv HTML (much faster than PDF+docling)
    update("fetch_seed", 0.08, "Fetching full text from ar5iv...")
    seed_body, seed_ref_section = _fetch_arxiv_html(seed_id)
    if not seed_body:
        # Fallback: try abstract only
        seed_body = seed_results_raw[0].content if seed_results_raw else ""

    seed_title = seed_results_raw[0].metadata.get("title", seed_id)

    seed_doc = RawDocument(
        id=SEED_DOC_ID,
        content=seed_body,
        source="arxiv_seed",
        metadata={"title": seed_title},
    )

    a["papers"] = [{"id": SEED_DOC_ID, "title": seed_title}]
    update("fetch_seed", 0.15, f"Seed paper: {seed_title}")

    # 2. Parse bibliography
    update("bibliography", 0.20, "Parsing bibliography...")
    # ar5iv refs come as one-per-line from <li> items; prefix with "- " for parser
    if seed_ref_section:
        seed_ref_section = "\n".join(
            f"- {line.strip()}" for line in seed_ref_section.splitlines() if line.strip()
        )
    bibliography = parse_bibliography_entries(seed_ref_section)
    log.info("Parsed %d bibliography entries", len(bibliography))

    # Select references by arXiv ID
    ref_ids = []
    for entry in bibliography:
        for aid in entry.arxiv_ids:
            base = re.sub(r"v\d+$", "", aid)
            if base not in ref_ids:
                ref_ids.append(base)
    ref_ids = ref_ids[:max_references]
    update("bibliography", 0.25, f"Found {len(bibliography)} entries, resolving {len(ref_ids)}")

    # 3. Resolve references (quick: abstracts only; deep: full text via ar5iv)

    def _resolve_one_ref(rid: str):
        """Resolve a single reference. Returns RawDocument or None."""
        try:
            ref_source = ArxivSource(query=rid, max_results=1)
            if mode == "deep":
                # Full text from ar5iv HTML (much faster than PDF+docling)
                ref_body, _ = _fetch_arxiv_html(rid)
                if not ref_body:
                    ref_fetched = ref_source.fetch()
                    ref_body = ref_fetched[0].content if ref_fetched else ""
            else:
                # Quick: abstracts only
                ref_fetched = ref_source.fetch()
                ref_body = ref_fetched[0].content if ref_fetched else ""

            entry = next(
                (e for e in bibliography if any(
                    re.sub(r"v\d+$", "", a) == rid for a in e.arxiv_ids
                )),
                None,
            )
            return RawDocument(
                id=rid,
                content=ref_body,
                source="citation_ref",
                metadata={
                    "title": entry.title if entry else rid,
                    "year": entry.year if entry else None,
                },
            )
        except Exception as e:
            log.warning("Failed to resolve %s: %s", rid, e)
            return None

    # Parallel fetching for both modes
    ref_docs = []
    total = len(ref_ids)

    completed = 0
    pbar = tqdm(ref_ids, desc="Fetching refs", unit="ref", leave=False)
    with ThreadPoolExecutor(max_workers=min(8, total)) as pool:
        futures = {pool.submit(_resolve_one_ref, rid): rid for rid in ref_ids}
        for future in as_completed(futures):
            completed += 1
            rid = futures[future]
            pbar.set_postfix_str(rid)
            pbar.update(1)
            update("fetch_refs", 0.25 + (completed / total) * 0.25, f"Resolved {completed}/{total}: {rid}")
            doc = future.result()
            if doc:
                ref_docs.append(doc)
    pbar.close()

    if not ref_docs:
        a["status"] = "error"
        a["error"] = "No references could be resolved"
        return

    a["papers_fetched"] = 1 + len(ref_docs)
    a["papers"] = [{"id": SEED_DOC_ID, "title": seed_title}] + [
        {"id": d.id, "title": d.metadata.get("title", d.id)} for d in ref_docs
    ]
    update("fetch_refs", 0.50, f"Resolved {len(ref_docs)} references")

    # 4. Start Ollama and run citation assembly
    update("ollama", 0.55, "Ensuring Ollama is running...")
    time.sleep(0.1)
    try:
        ensure_ollama()
    except RuntimeError as e:
        a["status"] = "error"
        a["error"] = f"Ollama not available: {e}. Start with: ollama serve"
        return

    segmented = mode == "deep"
    update("extract", 0.60, "Running citation-guided discovery + GLiNER extraction...")
    assembly = CitationAssembly(config_path)
    try:
        result = assembly.run(
            seed_doc,
            ref_docs,
            bibliography=bibliography,
            segmented=segmented,
        )
    except Exception as e:
        log.error("CitationAssembly failed: %s", e, exc_info=True)
        a["status"] = "error"
        a["error"] = f"Citation assembly failed: {e}"
        return

    # 5. Convert CitationGraphResult → API format
    update("merge", 0.90, "Building response...")
    time.sleep(0.1)

    kg = result.graph
    classifications = result.node_classifications

    # Persist per-node chunk data for the lazy chunks endpoint.
    from kgraph.api.chunks import build_node_mentions, build_segments
    from kgraph.api.state import analysis_chunks
    segmented = mode == "deep"
    analysis_chunks[a["id"]] = {
        "segments": build_segments(
            [seed_doc] + list(ref_docs), config_path, segmented=segmented
        ),
        "node_mentions": build_node_mentions(kg.graph),
    }

    connected_nodes = set()
    for u, v in kg.graph.edges():
        connected_nodes.add(u)
        connected_nodes.add(v)

    nodes = []
    for nid, data in kg.graph.nodes(data=True):
        if nid not in connected_nodes:
            continue
        node_docs = list({m["doc_id"] for m in data.get("mentions", [])})
        classification = classifications.get(nid, "unknown")
        nodes.append({
            "id": nid,
            "name": data.get("text", nid),
            "type": data.get("entity_type", "concept"),
            "importance": round(data.get("score", 0.5) * 10, 1),
            "source": classification,
            "documents": node_docs,
        })

    edges = []
    for u, v, key, data in kg.graph.edges(keys=True, data=True):
        edge_docs = list(data.get("docs", set()))
        edges.append({
            "id": f"{u}_{v}_{key}",
            "source": u,
            "target": v,
            "relation": data.get("relation_type", "related to"),
            "confidence": round(data.get("score", 0.5), 2),
            "documents": edge_docs,
        })

    # Summary stats
    stats = {
        "total_nodes": kg.graph.number_of_nodes(),
        "total_edges": kg.graph.number_of_edges(),
        "core": sum(1 for v in classifications.values() if v == "core"),
        "seed_only": sum(1 for v in classifications.values() if v == "seed-only"),
        "refs_only": sum(1 for v in classifications.values() if v == "refs-only"),
        "entity_labels": len(result.discovery.entity_labels),
        "relation_labels": len(result.discovery.relation_labels),
    }

    update("done", 1.0, "Analysis complete")
    a["result"] = {
        "id": a["id"],
        "topic": a.get("topic") or a.get("seed_url") or "",
        "papers": a["papers"],
        "topics": nodes,
        "relationships": edges,
        "stats": stats,
    }

    # Cleanup: unload Ollama model
    try:
        from kgraph.graph.config import load_pipeline_config
        cfg = load_pipeline_config(config_path)
        unload_ollama(cfg.citation.ollama_model)
    except Exception:
        pass


def _quick_extract(builder, raw_docs: list):
    """Quick mode: run GLiNER on abstract text directly (no segmentation)."""
    import networkx as nx
    from kgraph.extractors.gliner import extract_entities_relations
    from kgraph.extractors.normalization import canonical, EntityMerger
    from kgraph.corpus.merge import summarize_corpus

    # Build taxonomy per doc
    taxonomies = {}
    for doc in raw_docs:
        taxonomies[doc.id] = builder._taxonomy(doc)

    # Extract entities/relations from each abstract directly (no segments)
    per_doc = {}
    for doc in raw_docs:
        entity_labels, relation_labels = taxonomies[doc.id]
        # Apply label filter
        builder.label_filter.fit(entity_labels, relation_labels)
        ent_labels, rel_labels = builder.label_filter.filter(
            doc.content or "", min_labels=5, max_labels=10
        )
        entities, relations = extract_entities_relations(
            builder.model,
            doc.content or "",
            ent_labels,
            rel_labels,
            builder.base_config.thresholds.entity,
            builder.base_config.thresholds.relation,
            doc_id=doc.id,
        )
        per_doc.setdefault(doc.id, ([], []))[0].extend(entities)
        per_doc[doc.id][1].extend(relations)

    per_document = [
        (doc_id, entities, relations)
        for doc_id, (entities, relations) in per_doc.items()
    ]

    # Use merge with EntityMerger for near-duplicate detection
    graph = nx.MultiDiGraph()
    text_to_id = {}
    edge_lookup = {}
    merger = EntityMerger()

    def _register_node(node_id: str, entity, doc_id: str) -> None:
        """Register a node and all its aliases in text_to_id."""
        key = canonical(entity.text)
        text_to_id[key] = node_id
        # Also register the EntityMerger's canonical so future matches resolve
        match = merger.match(key)
        if match is not None and match != key:
            text_to_id[match] = node_id
        node = graph.nodes[node_id]
        node["mentions"].extend(entity.mentions)
        node["docs"].add(doc_id)
        if entity.score > node["score"]:
            node["score"] = entity.score

    for doc_id, entities, relations in per_document:
        for entity in entities:
            key = canonical(entity.text)
            node_id = text_to_id.get(key)
            if node_id is None:
                match = merger.match(key)
                if match is not None:
                    node_id = text_to_id.get(match)
            if node_id is None:
                node_id = entity.id
                graph.add_node(
                    node_id,
                    text=entity.text,
                    entity_type=entity.entity_type,
                    score=entity.score,
                    mentions=[],
                    docs=set(),
                )
            _register_node(node_id, entity, doc_id)

        for relation in relations:
            head_key = canonical(relation.head_text)
            head_id = text_to_id.get(head_key)
            if head_id is None:
                match = merger.match(head_key)
                if match is not None:
                    head_id = text_to_id.get(match)
                    if head_id is not None:
                        text_to_id[head_key] = head_id
            tail_key = canonical(relation.tail_text)
            tail_id = text_to_id.get(tail_key)
            if tail_id is None:
                match = merger.match(tail_key)
                if match is not None:
                    tail_id = text_to_id.get(match)
                    if tail_id is not None:
                        text_to_id[tail_key] = tail_id
            if head_id is None or tail_id is None:
                continue
            key = (head_id, tail_id, relation.relation_type)
            edge_key = edge_lookup.get(key)
            if edge_key is None:
                edge_key = graph.add_edge(
                    head_id,
                    tail_id,
                    relation_type=relation.relation_type,
                    score=relation.score,
                    count=0,
                    docs=set(),
                )
                edge_lookup[key] = edge_key
            edge = graph.edges[head_id, tail_id, edge_key]
            edge["count"] += 1
            edge["docs"].add(doc_id)
            if relation.score > edge["score"]:
                edge["score"] = relation.score

    summary = summarize_corpus(graph, [doc.id for doc in raw_docs])
    return graph, summary


def _run_corpus_pipeline(a: dict, raw_docs: list, update, config_path: str, mode: str = "quick"):
    """Shared corpus pipeline. Quick mode skips PDF parsing and segmentation."""
    from kgraph.corpus import CorpusGraphBuilder

    n = len(raw_docs)

    if mode == "quick":
        update("taxonomy", 0.40, "Building topic taxonomy...")
        time.sleep(0.1)
    else:
        update("parse", 0.35, f"Parsing {n} documents...")
        time.sleep(0.2)
        update("taxonomy", 0.40, "Building topic taxonomy per document...")
        time.sleep(0.2)
        update("segment", 0.45, "Segmenting documents for extraction...")

    builder = CorpusGraphBuilder(config_path, workers=0)

    if mode == "quick":
        update("extract", 0.50, f"Extracting entities from {n} abstracts...")
        graph, summary = _quick_extract(builder, raw_docs)
    else:
        update("extract", 0.50, f"Extracting entities from {n} documents...")
        graph, summary = builder.build(raw_docs)

    # Free heavy models (GLiNER, SentenceTransformer, spaCy) immediately
    del builder
    gc.collect()

    # Persist per-node chunk data for the lazy chunks endpoint.
    from kgraph.api.chunks import build_node_mentions, build_segments
    from kgraph.api.state import analysis_chunks
    segmented = mode == "deep"
    analysis_chunks[a["id"]] = {
        "segments": build_segments(raw_docs, config_path, segmented=segmented),
        "node_mentions": build_node_mentions(graph),
    }

    # Release torch threads and clear MPS/CUDA cache
    import torch
    torch.set_num_threads(1)
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    elif torch.cuda.is_available():
        torch.cuda.empty_cache()

    update("merge", 0.90, "Merging cross-document graph...")
    time.sleep(0.2)

    main_doc_id = raw_docs[0].id if raw_docs else None

    # Filter orphan nodes (no edges) to reduce graph noise
    connected_nodes = set()
    for u, v in graph.edges():
        connected_nodes.add(u)
        connected_nodes.add(v)

    nodes = []
    for nid, data in graph.nodes(data=True):
        # Skip orphan nodes — entities with no relations are noise
        if nid not in connected_nodes:
            continue
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
