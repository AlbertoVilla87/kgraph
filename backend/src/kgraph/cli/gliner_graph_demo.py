from kgraph.graph import config
from kgraph.ingestion.factory import build_data_source
from kgraph.extractors.gliner import GLiNERGraph
from kgraph.retriever.gliner import GLiNERRetriever

def main():
    my_config = config.load_pipeline_config("./configs/params.yaml")
    source = build_data_source(my_config.data_source)
    documents = source.fetch()
    kgraph = GLiNERGraph(my_config)
    kgraph.build(documents)
    
    retriever = GLiNERRetriever(
        config=my_config,
        knowledge_graph=kgraph,
        expansion_depth=2,
    )

    result = retriever.retrieve("lender")

    print("Query entities:")
    for e in result.query_entities:
        print(f"  [{e['type']}] {e['text']} -> graph matches: {e['graph_matches']}")

    print("\nExpanded entities:")
    for e in result.expanded_entities:
        marker = "(direct match)" if e.get("is_query_match") else "(expanded)"
        print(f"  {e['text']} ({e['type']}) {marker}")

    print("\nRelations:")
    for rel in result.relevant_relations:
        print(f"  {rel['source']} --[{rel['relation']}]--> {rel['target']}")

    print("\nSource documents:", result.context_documents)

if __name__ == "__main__":
    main()
