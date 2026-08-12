import logging

from kgraph.discovery.topic_graph import TopicGraph
from kgraph.graph import config
from kgraph.ingestion.factory import build_data_source

logging.basicConfig(level=logging.INFO)


def main() -> None:
    my_config = config.load_pipeline_config("./configs/params.yaml")
    source = build_data_source(my_config.data_source)
    documents = source.fetch()

    graph_builder = TopicGraph(my_config)
    graph = graph_builder.build(documents)

    print("\nSeed topics (KeyBERT, depth 0):\n")
    for seed in graph_builder.seeds:
        print(f"  {seed}")

    print("\nDiscovered graph (depth = hops from seeds):\n")
    for u, v, data in graph.edges(data=True):
        du, dv = graph.nodes[u]["depth"], graph.nodes[v]["depth"]
        print(
            f"  (d{du}) {graph.nodes[u]['text']} "
            f"--[{data['relation']}]--> "
            f"(d{dv}) {graph.nodes[v]['text']}"
        )

    print("\nStats:\n")
    depths = {}
    for n in graph.nodes:
        depths[graph.nodes[n]["depth"]] = depths.get(graph.nodes[n]["depth"], 0) + 1
    print(f"  nodes:     {graph.number_of_nodes()}  {dict(sorted(depths.items()))}")
    print(f"  relations: {graph.number_of_edges()}")


if __name__ == "__main__":
    main()
