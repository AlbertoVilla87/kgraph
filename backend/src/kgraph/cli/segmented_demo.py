import argparse
import logging
from pathlib import Path

from kgraph.discovery.assembly import DiscoveryAssembly
from kgraph.graph import config
from kgraph.ingestion.factory import build_data_source
from kgraph.segmentation import Segmenter

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the final KG via discovery → segmented GLiNER."
    )
    parser.add_argument(
        "--output",
        default="output/kg_segmented.json",
        help="Where to export the graph JSON (default: output/kg_segmented.json).",
    )
    parser.add_argument(
        "--no-segmentation",
        action="store_true",
        help="Fall back to whole-document GLiNER (truncated at 1024 tokens).",
    )
    parser.add_argument(
        "--show-segments",
        action="store_true",
        help="Print the segment boundaries produced for each document.",
    )
    args = parser.parse_args()

    config_path = "./configs/params.yaml"
    my_config = config.load_pipeline_config(config_path)
    source = build_data_source(my_config.data_source)

    documents = source.fetch()

    if args.show_segments:
        segmenter = Segmenter(my_config.ner.name, my_config.segmentation)
        for doc in documents:
            segments = segmenter.segment(doc)
            print(f"\n{doc.id}: {len(segments)} segments")
            for segment in segments:
                prefix = " > ".join(segment.headings) or "(no heading)"
                print(
                    f"  [{segment.index}] {prefix} | "
                    f"tokens={len(segment.text.split()):4d} | "
                    f"chars={segment.start}:{segment.end}"
                )

    kgraph = DiscoveryAssembly(config_path).run(
        documents, segmented=not args.no_segmentation
    )

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    kgraph.export_to_json(args.output)
    print(f"\nGraph JSON exported to {args.output}")

    print("\nFinal knowledge graph (GLiNER):\n")
    for u, v, data in kgraph.graph.edges(data=True):
        print(
            f"  {kgraph.graph.nodes[u]['text']} "
            f"--[{data['relation_type']} ({data['score']:.2f}, x{data.get('count', 1)})]--> "
            f"{kgraph.graph.nodes[v]['text']}"
        )

    print("\nStats:\n")
    print(f"  entities:  {kgraph.graph.number_of_nodes()}")
    print(f"  relations: {kgraph.graph.number_of_edges()}")


if __name__ == "__main__":
    main()
