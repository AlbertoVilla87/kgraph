"""Debug script for abstract-mode topic discovery.

Based on: "From Local to Global: A Graph RAG Approach to Query-Focused Summarization"
(arXiv:2404.16130)

Runs the discovery pipeline on arXiv abstracts with all parameters
configurable via CLI for easy iteration and debugging in VSCode.

Usage:
    python -m kgraph.cli.debug_abstract
    python -m kgraph.cli.debug_abstract --max-seeds 10 --max-depth 3
    python -m kgraph.cli.debug_abstract --seed-paper 2301.12345
"""

import argparse
import logging
import sys
from pathlib import Path

from kgraph.discovery.topic_graph import TopicGraph
from kgraph.graph import config
from kgraph.graph.config import PipelineConfig
from kgraph.ingestion.arxiv import ArxivSource
from kgraph.ingestion.seed_paper import SeedPaperSource
from kgraph.ingestion.references import ArxivReferenceExtractor

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("debug_abstract")

DEFAULT_SEED_PAPER = "2404.16130"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Debug abstract-mode topic discovery with parameterized options.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Reference:
    Edge, D. et al. (2024). "From Local to Global: A Graph RAG Approach to
    Query-Focused Summarization." arXiv:2404.16130.

Examples:
    python -m kgraph.cli.debug_abstract
    python -m kgraph.cli.debug_abstract --max-seeds 5 --max-depth 3
    python -m kgraph.cli.debug_abstract --output output/debug_graph.json
        """,
    )

    parser.add_argument(
        "--seed-paper",
        default=DEFAULT_SEED_PAPER,
        help=f"arXiv ID of the seed paper (default: {DEFAULT_SEED_PAPER})",
    )
    parser.add_argument(
        "--no-references",
        action="store_true",
        help="Skip reference paper fetching (seed only).",
    )
    parser.add_argument(
        "--max-references",
        type=int,
        default=1,
        help="Number of reference papers to fetch (default: 1).",
    )

    parser.add_argument(
        "--max-seeds",
        type=int,
        default=None,
        help="Max seed topics from KeyBERT (default: from config).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Max graph depth from seed topics (default: from config).",
    )
    parser.add_argument(
        "--max-relations",
        type=int,
        default=None,
        help="Max relations in the graph (default: from config).",
    )

    parser.add_argument(
        "--diversity",
        type=float,
        default=None,
        help="KeyBERT diversity parameter (default: from config).",
    )
    parser.add_argument(
        "--min-k",
        type=int,
        default=None,
        help="Min keywords for adaptive KeyBERT (default: from config).",
    )
    parser.add_argument(
        "--max-k",
        type=int,
        default=None,
        help="Max keywords for adaptive KeyBERT (default: from config).",
    )
    parser.add_argument(
        "--score-floor",
        type=float,
        default=None,
        help="Min score for KeyBERT keywords (default: from config).",
    )

    parser.add_argument(
        "--merge-threshold",
        type=float,
        default=None,
        help="Entity merging similarity threshold (default: from config).",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Disable entity merging.",
    )

    parser.add_argument(
        "--no-segmentation",
        action="store_true",
        help="Disable segmentation (use whole document).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max tokens per segment (default: from config).",
    )
    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=None,
        help="Overlap tokens between segments (default: from config).",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Export graph to JSON file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    return parser


def apply_overrides(cfg: PipelineConfig, args: argparse.Namespace) -> PipelineConfig:
    if args.max_seeds is not None:
        cfg.discovery.max_seeds = args.max_seeds
    if args.max_depth is not None:
        cfg.discovery.max_depth = args.max_depth
    if args.max_relations is not None:
        cfg.discovery.max_relations = args.max_relations

    if args.diversity is not None:
        cfg.keyword_extractor.diversity = args.diversity
    if args.min_k is not None:
        cfg.keyword_extractor.adaptive.min_k = args.min_k
    if args.max_k is not None:
        cfg.keyword_extractor.adaptive.max_k = args.max_k
    if args.score_floor is not None:
        cfg.keyword_extractor.adaptive.score_floor = args.score_floor

    if args.merge_threshold is not None:
        cfg.entity_merging.threshold = args.merge_threshold
    if args.no_merge:
        cfg.entity_merging.enabled = False

    if args.no_segmentation:
        cfg.segmentation.enabled = False
    if args.max_tokens is not None:
        cfg.segmentation.max_tokens = args.max_tokens
    if args.overlap_tokens is not None:
        cfg.segmentation.overlap_tokens = args.overlap_tokens

    return cfg


def print_config(cfg: PipelineConfig) -> None:
    print("\n" + "=" * 60)
    print("ACTIVE CONFIGURATION")
    print("=" * 60)

    print("\n[Discovery]")
    print(f"  max_seeds:     {cfg.discovery.max_seeds}")
    print(f"  max_depth:     {cfg.discovery.max_depth}")
    print(f"  max_relations: {cfg.discovery.max_relations}")
    print(f"  skip_headings: {cfg.discovery.skip_headings}")

    print("\n[KeyBERT]")
    print(f"  model:              {cfg.keyword_extractor.name}")
    print(f"  diversity:          {cfg.keyword_extractor.diversity}")
    print(f"  n_grams:            {cfg.keyword_extractor.n_grams}")
    print(f"  adaptive.min_k:     {cfg.keyword_extractor.adaptive.min_k}")
    print(f"  adaptive.max_k:     {cfg.keyword_extractor.adaptive.max_k}")
    print(f"  adaptive.score_floor: {cfg.keyword_extractor.adaptive.score_floor}")
    print(f"  adaptive.words_per_kw: {cfg.keyword_extractor.adaptive.words_per_kw}")

    print("\n[Entity Merging]")
    print(f"  enabled:   {cfg.entity_merging.enabled}")
    print(f"  threshold: {cfg.entity_merging.threshold}")
    print(f"  model:     {cfg.entity_merging.model}")

    print("\n[Segmentation]")
    print(f"  enabled:        {cfg.segmentation.enabled}")
    print(f"  max_tokens:     {cfg.segmentation.max_tokens}")
    print(f"  overlap_tokens: {cfg.segmentation.overlap_tokens}")

    print("\n[Thresholds]")
    print(f"  entity:   {cfg.thresholds.entity}")
    print(f"  relation: {cfg.thresholds.relation}")

    print("=" * 60 + "\n")


def print_graph_stats(graph, label: str = "") -> None:
    depths = {}
    for n in graph.nodes:
        d = graph.nodes[n]["depth"]
        depths[d] = depths.get(d, 0) + 1

    print(f"\n{'─' * 40}")
    print(f"GRAPH STATS{f' ({label})' if label else ''}")
    print(f"{'─' * 40}")
    print(f"  Nodes:     {graph.number_of_nodes()}")
    print(f"  Relations: {graph.number_of_edges()}")
    print(f"  By depth:  {dict(sorted(depths.items()))}")
    print(f"{'─' * 40}")


def print_seeds(seeds: list) -> None:
    print(f"\n{'─' * 40}")
    print(f"SEED TOPICS (KeyBERT, depth 0)")
    print(f"{'─' * 40}")
    for i, seed in enumerate(seeds, 1):
        print(f"  {i:2d}. {seed}")
    print(f"{'─' * 40}")


def print_edges(graph) -> None:
    print(f"\n{'─' * 40}")
    print("DISCOVERED RELATIONS")
    print(f"{'─' * 40}")
    for u, v, data in graph.edges(data=True):
        du = graph.nodes[u]["depth"]
        dv = graph.nodes[v]["depth"]
        print(
            f"  (d{du}) {graph.nodes[u]['text']} "
            f"--[{data['relation']}]--> "
            f"(d{dv}) {graph.nodes[v]['text']}"
        )
    print(f"{'─' * 40}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config_path = "./configs/params.yaml"
    logger.info("Loading config from %s", config_path)
    cfg = config.load_pipeline_config(config_path)
    cfg = apply_overrides(cfg, args)

    if args.verbose:
        print_config(cfg)

    logger.info("Fetching seed paper: %s", args.seed_paper)

    if args.no_references:
        source = ArxivSource(query=args.seed_paper, max_results=1)
        documents = source.fetch()
        logger.info("Fetched %d abstract(s) (no references)", len(documents))
    else:
        seed_source = ArxivSource(query="dummy", max_results=1)
        extractor = ArxivReferenceExtractor()
        seed_paper_source = SeedPaperSource(
            source=seed_source,
            extractor=extractor,
            seed_id=args.seed_paper,
            max_references=args.max_references,
        )
        documents = seed_paper_source.fetch()
        logger.info(
            "Fetched seed + %d reference(s) = %d total",
            len(documents) - 1,
            len(documents),
        )

    if not documents:
        logger.error("No documents fetched. Check your seed paper ID and network.")
        sys.exit(1)

    for i, doc in enumerate(documents):
        title = doc.metadata.get("title", "Unknown")
        arxiv_id = doc.metadata.get("arxiv_id", doc.id)
        content_len = len(doc.content.split())
        print(f"\n  [{i + 1}] {title}")
        print(f"      arXiv: {arxiv_id}")
        print(f"      Words: {content_len}")

    logger.info("Building topic graph...")
    graph_builder = TopicGraph(cfg)
    graph = graph_builder.build(documents)

    print_seeds(graph_builder.seeds)
    print_edges(graph)
    print_graph_stats(graph, "topic discovery")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        graph_builder.export_to_json(str(output_path))
        logger.info("Graph exported to %s", output_path)

    print("\nDone. Add breakpoints and inspect variables in VSCode debugger.\n")


if __name__ == "__main__":
    main()
