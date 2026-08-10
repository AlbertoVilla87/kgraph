from kgraph.graph import config
from kgraph.ingestion.factory import build_data_source
from kgraph.llms.schemas import concepts
from kgraph.llms import LiteLLMClient


def main() -> None:
    my_config = config.load_pipeline_config("./configs/params.yaml")
    source = build_data_source(my_config.data_source)
    doc = source.fetch()[0].content

    client = LiteLLMClient()
    response = client.chat_structured(
        prompt=f"Infer the list of general concepts associated this document: {doc}",
        model=my_config.llm.name,
        schema=concepts.Concepts
    )

    print("\nResponse:\n")
    print(response)


if __name__ == "__main__":
    main()
