from kgraph.graph import config
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from kgraph.ingestion.factory import build_data_source


def main() -> None:
    my_config = config.load_pipeline_config("./configs/params.yaml")
    embedding_model = SentenceTransformer(my_config.keyword_extractor.name)
    kw_model = KeyBERT(model=embedding_model)
    source = build_data_source(my_config.data_source)
    doc = source.fetch()[0].content

    keywords = kw_model.extract_keywords(doc, 
                                         keyphrase_ngram_range=my_config.keyword_extractor.n_grams,
                                         stop_words=my_config.keyword_extractor.stop_words,
                                         use_mmr=True,
                                         diversity=my_config.keyword_extractor.diversity)

    print("\nKeywords:\n")

    for keyword, score in keywords:
        print(f"{keyword:<40} {score:.4f}")


if __name__ == "__main__":
    main()