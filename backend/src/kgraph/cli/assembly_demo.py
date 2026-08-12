import logging

from kgraph.discovery.assembly import DiscoveryAssembly
from kgraph.graph import config
from kgraph.ingestion.factory import build_data_source

logging.basicConfig(level=logging.INFO)


def main() -> None:
    config_path = "./configs/params.yaml"
    my_config = config.load_pipeline_config(config_path)
    source = build_data_source(my_config.data_source)

    documents = source.fetch()
    kgraph = DiscoveryAssembly(config_path).run(documents)

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
