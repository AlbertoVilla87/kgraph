from kgraph.extractors.key_bert import AdaptiveKeyBERT
from kgraph.graph import config
from kgraph.ingestion.factory import build_data_source


def main() -> None:
    my_config = config.load_pipeline_config("./configs/params.yaml")
    source = build_data_source(my_config.data_source)
    doc = source.fetch()[0].content

    kw_model = AdaptiveKeyBERT(my_config.keyword_extractor)
    keywords = kw_model.extract(doc)

    print("\nKeywords:\n")

    for keyword, score in keywords:
        print(f"{keyword:<40} {score:.4f}")


if __name__ == "__main__":
    main()