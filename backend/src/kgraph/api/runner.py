"""Background task that runs the corpus pipeline and updates analysis status."""

import gc
import logging
import time
import traceback
from pathlib import Path

from kgraph.api.state import analyses

log = logging.getLogger(__name__)


def _paper_entry(doc_id: str, title: str, meta: dict | None = None) -> dict:
    """Build a {id, title, year, url} entry for a paper in the result payload.

    The year comes from arXiv's publication date (``published``) when
    available, otherwise from metadata ``year``. The url is the direct PDF
    link (``pdf_url``), falling back to the abstract page URL.
    """
    meta = meta or {}
    year = None
    published = meta.get("published")
    if published:
        try:
            year = int(str(published)[:4])
        except (TypeError, ValueError):
            year = None
    if year is None:
        year = meta.get("year")
    url = meta.get("pdf_url") or meta.get("url")
    return {"id": doc_id, "title": title, "year": year, "url": url}


def _wrap_math(soup) -> None:
    """Replace ar5iv math elements with ``$``-delimited LaTeX in-place.

    Display equations (``ltx_equationgroup`` / ``ltx_equation`` containers)
    become ``$$...$$`` blocks; inline math (``<math class="ltx_Math">`` or a
    ``<span class="ltx_Math">`` in prose) becomes ``$...$``. LaTeX is taken
    from ar5iv's ``alttext`` / ``x-tex`` annotation when present, so KaTeX can
    render it. Runs before markdown conversion.

    This is intentionally O(#math) — a single ``find_all`` plus ``find_parent``
    per element — because the naive per-element ``get_text`` walks the whole
    tree and is grotesquely slow on large ar5iv pages.
    """
    import re as _re

    def _tex(el) -> str:
        alt = el.get("alttext")
        if alt and alt.strip():
            return _re.sub(r"^\\displaystyle\s*", "", alt.strip())
        else:
            ann = el.find("annotation", encoding="application/x-tex")
            if ann is not None and (ann.text or "").strip():
                return _re.sub(r"^\\displaystyle\s*", "", ann.text.strip())
        return _re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()

    def _is_display(el) -> bool:
        cls = el.get("class") or []
        return any("ltx_equationgroup" in c or "ltx_equation" in c for c in cls)

    display_groups: dict[id, list[str]] = {}
    display_els: set = set()

    # Single pass over inline/display <math> elements.
    for el in soup.find_all("math", class_="ltx_Math"):
        tex = _tex(el)
        if not tex:
            continue
        disp = el.find_parent(_is_display)
        if disp is not None:
            # Promote to the topmost display container so we replace the whole
            # block (including any equation-number tag) in one go.
            while True:
                parent = disp.find_parent(_is_display)
                if parent is None:
                    break
                disp = parent
            display_groups.setdefault(id(disp), []).append(tex)
            display_els.add(disp)
        else:
            el.string = f" ${tex}$ "

    for d in display_els:
        d.string = "\n\n$$ " + "  ".join(display_groups[id(d)]) + " $$\n\n"

    # Fallback for legacy inline math wrapped directly in a <span class="ltx_Math">
    # that does not contain its own <math> element.
    for el in soup.find_all("span", class_="ltx_Math"):
        if el.find("math") is not None:
            continue
        tex = _tex(el)
        if tex:
            el.string = f" ${tex}$ "


def _to_markdown(html: str) -> str:
    """Convert an HTML fragment to markdown via markdownify."""
    from markdownify import markdownify
    return markdownify(html, heading_style="ATX")


def _graph_to_api(kg, classifications: dict, include_orphans: bool = False) -> tuple[list, list]:
    """Convert a GLiNERGraph + classifications into API node/edge payloads.

    Orphan nodes (no incident edges) are included only when ``include_orphans``
    is True — used for progressive partial snapshots where edges may not yet
    have been merged.
    """
    if include_orphans:
        connected_nodes = set(kg.graph.nodes())
    else:
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

    return nodes, edges


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
    discovery = a.get("discovery", "topic")
    config_path = str(Path(__file__).resolve().parents[3] / "configs" / "params.yaml")

    log.info("Starting analysis %s (seed=%s, topic=%s, discovery=%s)",
             analysis_id, seed_url or "-", topic or "-", discovery)

    def update(step_key: str, progress: float, detail: str = ""):
        a["current_step"] = step_key
        a["progress"] = progress
        a["detail"] = detail
        _advance_steps(a, step_key)

    try:
        if seed_url:
            if discovery == "citation":
                _run_citation_pipeline(a, seed_url, max_references, update, config_path)
            else:
                _run_seed_pipeline(a, seed_url, max_references, update, config_path)
        else:
            if discovery == "citation":
                a["status"] = "error"
                a["error"] = "Citation discovery requires a seed paper (seed_url), not a topic query"
                return
            _run_topic_pipeline(a, topic, max_papers, update, config_path)

        log.info("Analysis %s completed successfully", analysis_id)

    except Exception as e:
        a["status"] = "error"
        a["error"] = str(e)
        a["traceback"] = traceback.format_exc()
        log.error("Analysis %s failed: %s", analysis_id, e, exc_info=True)
    finally:
        gc.collect()


def _run_topic_pipeline(a: dict, topic: str, max_papers: int, update, config_path: str):
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
        _paper_entry(doc.id, doc.metadata.get("title", doc.id), doc.metadata)
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
        _paper_entry(doc.id, doc.metadata.get("title", doc.id), doc.metadata)
        for doc in raw_docs
    ]

    _run_corpus_pipeline(a, raw_docs, update, config_path)


def _run_citation_pipeline(a: dict, seed_url: str, max_references: int, update, config_path: str):
    """Citation-guided pipeline; always shuts down Ollama when finished.

    Ollama is a local server kept only for the duration of an analysis: killing
    it frees CPU/VRAM (and quietens the fans). The server is only terminated
    when kgraph started it itself (see citation_graph.shutdown_ollama).
    """
    try:
        _run_citation_pipeline_impl(a, seed_url, max_references, update, config_path)
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


def _run_citation_pipeline_impl(a: dict, seed_url: str, max_references: int, update, config_path: str):
    """Citation-guided pipeline: seed citations define the GLiNER taxonomy.

    The seed and its references all get full text (via ar5iv HTML) and
    segmentation is enabled.
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
        """Fetch paper from ar5iv HTML. Returns (body_markdown, references_text).

        The body is converted to markdown so that ar5iv's structured tables and
        math survive (instead of being flattened to plain text), and real ``#``
        headings are produced — which the downstream ``Segmenter`` already
        expects to split on.
        """
        from bs4 import BeautifulSoup

        url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
        for attempt in range(3):
            try:
                resp = _http.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                _wrap_math(soup)

                # Extract body (everything before the bibliography section) as markdown.
                bib_section = soup.find("section", id="bib")
                if bib_section:
                    body_els = [
                        el for el in bib_section.previous_siblings if hasattr(el, "get_text")
                    ]
                    body_md = "\n\n".join(
                        _to_markdown(str(el)) for el in reversed(body_els)
                    )
                else:
                    # Fallback: use article or body
                    article = soup.find("article") or soup.find("body") or soup
                    body_md = _to_markdown(str(article))

                # Extract references as structured text from <li> items.
                # Kept as flat get_text() (NOT markdown) because the runner
                # prefixes each line with "- " and feeds it to
                # parse_bibliography_entries, which expects one entry per line.
                refs_text = ""
                if bib_section:
                    bib_list = bib_section.find("ul", class_="ltx_biblist")
                    if bib_list:
                        ref_items = []
                        for li in bib_list.find_all("li", class_="ltx_bibitem"):
                            ref_items.append(li.get_text(separator=" ", strip=True))
                        refs_text = "\n".join(ref_items)

                max_chars = 24_000
                return body_md[:max_chars], refs_text
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
        metadata={"title": seed_title, **seed_results_raw[0].metadata},
    )

    a["papers"] = [_paper_entry(SEED_DOC_ID, seed_title, seed_results_raw[0].metadata)]
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

    # 3. Resolve references (full text via ar5iv)

    def _resolve_one_ref(rid: str):
        """Resolve a single reference. Returns RawDocument or None."""
        try:
            ref_source = ArxivSource(query=rid, max_results=1)
            # Always fetch from arXiv to get metadata (published date, PDF url)
            ref_fetched = ref_source.fetch()
            ref_meta = ref_fetched[0].metadata if ref_fetched else {}
            # Full text from ar5iv HTML (much faster than PDF+docling)
            ref_body, _ = _fetch_arxiv_html(rid)
            if not ref_body:
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
                    **ref_meta,
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
    a["papers"] = [_paper_entry(SEED_DOC_ID, seed_title, seed_results_raw[0].metadata)] + [
        _paper_entry(d.id, d.metadata.get("title", d.id), d.metadata) for d in ref_docs
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

    update("extract", 0.60, "Running citation-guided discovery + GLiNER extraction...")
    assembly = CitationAssembly(config_path)

    def _on_gen_graph_progress(graph, classifications):
        partial_nodes, partial_edges = _graph_to_api(graph, classifications, include_orphans=True)
        a["partial_graph"] = {"topics": partial_nodes, "relationships": partial_edges}

    try:
        result = assembly.run(
            seed_doc,
            ref_docs,
            bibliography=bibliography,
            segmented=True,
            on_progress=_on_gen_graph_progress,
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
    analysis_chunks[a["id"]] = {
        "segments": build_segments(
            [seed_doc] + list(ref_docs), config_path
        ),
        "node_mentions": build_node_mentions(kg.graph),
    }

    nodes, edges = _graph_to_api(kg, classifications)

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


def _run_corpus_pipeline(a: dict, raw_docs: list, update, config_path: str):
    """Shared corpus pipeline: full-text parsing and segmentation."""
    from kgraph.corpus import CorpusGraphBuilder

    n = len(raw_docs)

    update("taxonomy", 0.40, "Building topic taxonomy...")
    time.sleep(0.1)
    update("parse", 0.35, f"Parsing {n} documents...")
    time.sleep(0.2)
    update("segment", 0.45, "Segmenting documents for extraction...")

    builder = CorpusGraphBuilder(config_path, workers=0)

    update("extract", 0.50, f"Extracting entities from {n} documents...")
    graph, summary = builder.build(raw_docs)

    # Free heavy models (GLiNER, SentenceTransformer, spaCy) immediately
    del builder
    gc.collect()

    # Persist per-node chunk data for the lazy chunks endpoint.
    from kgraph.api.chunks import build_node_mentions, build_segments
    from kgraph.api.state import analysis_chunks
    analysis_chunks[a["id"]] = {
        "segments": build_segments(raw_docs, config_path),
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
