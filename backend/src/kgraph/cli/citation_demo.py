"""CLI demo for citation-guided discovery.

Usage:
    uv run citation-demo --seed 2404.16130
    uv run citation-demo --seed 2404.16130 --output output/citation_kg.json
    uv run citation-demo --seed 2404.16130 --max-refs 10
"""

import argparse
import logging
import re
from pathlib import Path

from kgraph.discovery.bibliography import parse_bibliography_entries
from kgraph.discovery.citation_assembly import CitationAssembly
from kgraph.discovery.citation_graph import ensure_ollama, shutdown_ollama
from kgraph.graph import config
from kgraph.graph.models import RawDocument
from kgraph.ingestion.arxiv import ArxivSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SEED_DOC_ID = "__seed__"


def _split_at_references(text: str) -> tuple[str, str]:
    """Split document body from references section."""
    m = re.search(r"^#{1,3}\s*References\s*$", text, flags=re.M)
    if not m:
        return text, ""
    body = text[:m.start()]
    section = text[m.end():]
    nxt = re.search(r"^#{1,3}\s+", section, flags=re.M)
    return body, (section[:nxt.start()] if nxt else section)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a knowledge graph using citation-guided discovery."
    )
    parser.add_argument(
        "--seed",
        required=True,
        help="arXiv ID of the seed paper (e.g. 2404.16130).",
    )
    parser.add_argument(
        "--output",
        default="output/citation_kg.json",
        help="Where to export the graph JSON (default: output/citation_kg.json).",
    )
    parser.add_argument(
        "--max-refs",
        type=int,
        default=None,
        help="Max references to resolve (default: from config).",
    )
    parser.add_argument(
        "--no-segmentation",
        action="store_true",
        help="Disable segmented extraction (faster but less thorough).",
    )
    args = parser.parse_args()

    config_path = "./configs/params.yaml"
    cfg = config.load_pipeline_config(config_path)

    if args.max_refs:
        cfg.citation.max_refs = args.max_refs

    # 1. Fetch seed paper
    log.info("Fetching seed paper %s...", args.seed)
    source = ArxivSource(query=args.seed, max_results=1)
    docs = source.fetch()
    if not docs:
        log.error("Could not fetch seed paper %s", args.seed)
        return

    seed_doc = docs[0]
    seed_body, seed_ref_section = _split_at_references(seed_doc.content)

    # Extract title
    tm = re.search(r"^##\s+(.+)$", seed_doc.content, flags=re.M)
    seed_title = re.split(r"\s{2,}", tm.group(1).strip())[0] if tm else args.seed

    seed_raw = RawDocument(
        id=SEED_DOC_ID,
        content=seed_body,
        source="citation_demo",
        metadata={"title": seed_title},
    )

    # 2. Parse bibliography
    log.info("Parsing bibliography...")
    bibliography = parse_bibliography_entries(seed_ref_section)
    log.info("Found %d bibliography entries", len(bibliography))

    # 3. Resolve references
    ref_ids = []
    for entry in bibliography:
        for aid in entry.arxiv_ids:
            base = re.sub(r"v\d+$", "", aid)
            if base not in ref_ids:
                ref_ids.append(base)
    ref_ids = ref_ids[: cfg.citation.max_refs]
    log.info("Selected %d references to resolve", len(ref_ids))

    ref_docs: list[RawDocument] = []
    for rid in ref_ids:
        try:
            ref_source = ArxivSource(query=rid, max_results=1)
            ref_fetched = ref_source.fetch()
            if ref_fetched:
                ref_body, _ = _split_at_references(ref_fetched[0].content)
                entry = next(
                    (e for e in bibliography if any(
                        re.sub(r"v\d+$", "", a) == rid for a in e.arxiv_ids
                    )),
                    None,
                )
                ref_docs.append(RawDocument(
                    id=rid,
                    content=ref_body,
                    source="citation_demo",
                    metadata={
                        "title": entry.title if entry else rid,
                        "year": entry.year if entry else None,
                    },
                ))
                log.info("  Resolved %s (%d chars)", rid, len(ref_body))
        except Exception as e:
            log.warning("  Failed to resolve %s: %s", rid, e)

    if not ref_docs:
        log.error("No references resolved. Check your network and arXiv availability.")
        return

    # 4. Start Ollama
    log.info("Ensuring Ollama is running...")
    try:
        ensure_ollama(base=cfg.citation.ollama_api_base)
    except RuntimeError as e:
        log.error("Ollama not available: %s", e)
        log.error("Start Ollama with: ollama serve")
        return

    # 5. Run citation assembly
    log.info("Running citation-guided discovery...")
    assembly = CitationAssembly(config_path)
    result = assembly.run(
        seed_raw,
        ref_docs,
        bibliography= bibliography,
        segmented=not args.no_segmentation,
    )

    # 6. Export
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.graph.export_to_json(str(out_path))
    log.info("Graph exported to %s", out_path)

    # 7. Print summary
    kg = result.graph
    classifications = result.node_classifications

    print(f"\n{'='*60}")
    print(f"Seed: {seed_title}")
    print(f"{'='*60}")
    print(f"\nGraph: {kg.graph.number_of_nodes()} entities, {kg.graph.number_of_edges()} relations")
    print(f"\nClassification:")
    for klass in ("core", "seed-only", "refs-only"):
        count = sum(1 for v in classifications.values() if v == klass)
        print(f"  {klass:12s}: {count}")

    print(f"\nTop entities by classification:")
    for klass in ("core", "seed-only", "refs-only"):
        nodes = [
            (data["text"], data.get("score", 0))
            for nid, data in kg.graph.nodes(data=True)
            if classifications.get(nid) == klass
        ]
        nodes.sort(key=lambda x: x[1], reverse=True)
        if nodes:
            print(f"\n  [{klass}]")
            for text, score in nodes[:5]:
                year = ""
                node_data = next(
                    (d for _, d in kg.graph.nodes(data=True) if d["text"] == text),
                    {},
                )
                if "year" in node_data:
                    year = f" ({node_data['year']})"
                print(f"    - {text}{year} [{score:.2f}]")

    print(f"\nTop relations:")
    for u, v, data in list(kg.graph.edges(data=True))[:10]:
        u_text = kg.graph.nodes[u]["text"]
        v_text = kg.graph.nodes[v]["text"]
        print(f"  {u_text} --[{data['relation_type']} ({data['score']:.2f})]--> {v_text}")

    # 8. Cleanup
    shutdown_ollama()


if __name__ == "__main__":
    main()
