import argparse
import logging
import time

from kgraph.corpus import CorpusGraphBuilder, export_corpus_json, render_corpus_html
from kgraph.graph import config
from kgraph.ingestion.arxiv import ArxivSource
from kgraph.ingestion.factory import build_data_source
from kgraph.ingestion.local_files import LocalFileSource

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build one knowledge graph from many documents, tracking which "
            "nodes/edges are shared vs unique per document (originality view)."
        )
    )
    parser.add_argument(
        "--output-json",
        default="output/corpus_graph.json",
        help="Where to export the corpus graph JSON.",
    )
    parser.add_argument(
        "--output-html",
        default="output/corpus_graph.html",
        help="Where to write the interactive HTML visualization.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Parallel extraction workers (0 = half the CPUs).",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Limit to the first N documents of the data source.",
    )
    parser.add_argument(
        "--fetch",
        type=int,
        nargs="?",
        const=5,
        metavar="N",
        help=(
            "Download N arXiv PDFs (default 5) into the configured data "
            "folder first, then process all documents in that folder."
        ),
    )
    parser.add_argument(
        "--arxiv-query",
        default='all:"chain of thought" AND all:"large language models"',
        help="arXiv API query used by --fetch.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Discard PDFs with more than N pages (warned in the log, skipped "
            "before parsing so they cost no docling time)."
        ),
    )
    args = parser.parse_args()

    config_path = "./configs/params.yaml"
    my_config = config.load_pipeline_config(config_path)

    if args.fetch is not None:
        folder = my_config.data_source.folder or "data/arxiv_pdfs"
        source = ArxivSource(query=args.arxiv_query, max_results=args.fetch)
        saved = source.download_pdfs(folder)
        print(
            f"Downloaded {len(saved)} PDF(s) to {folder} "
            f"(existing files are skipped, so re-runs are idempotent)."
        )

    if args.max_pages is not None and my_config.data_source.type == "local_files":
        source = LocalFileSource(
            my_config.data_source.folder,
            my_config.data_source.file_type,
            max_pages=args.max_pages,
        )
    else:
        source = build_data_source(my_config.data_source)

    t0 = time.perf_counter()
    documents = source.fetch()
    fetch_secs = time.perf_counter() - t0
    if args.max_docs:
        documents = documents[: args.max_docs]
    if not documents:
        raise SystemExit("No documents found in the data source")

    print(f"Building corpus graph from {len(documents)} documents "
          f"(fetch/parse took {fetch_secs:.1f}s)...")
    builder = CorpusGraphBuilder(config_path, workers=args.workers)
    graph, summary = builder.build(documents)

    data = export_corpus_json(graph, summary, args.output_json)
    render_corpus_html(data, args.output_html)

    print(f"\nCorpus graph JSON exported to {args.output_json}")
    print(f"HTML visualization exported to {args.output_html}")

    print("\nSummary:")
    print(f"  nodes: {summary['total_nodes']} "
          f"(common {summary['common_nodes']} | unique {summary['unique_nodes']})")
    print(f"  edges: {summary['total_edges']} "
          f"(common {summary['common_edges']} | unique {summary['unique_edges']})")
    for doc_id, per in summary["per_document"].items():
        print(
            f"  {doc_id}: {per['nodes_in_doc']} nodes, "
            f"{per['unique_nodes']} unique ({per['novelty'] * 100:.0f}% novelty), "
            f"{per['unique_edges']} unique edges"
        )


if __name__ == "__main__":
    main()
