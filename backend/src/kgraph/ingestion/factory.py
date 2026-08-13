# src/kg_graph/ingestion/factory.py
from kgraph.graph.config import DataSourceConfig
from kgraph.ingestion.arxiv import ArxivSource
from kgraph.ingestion.base import DataSource
from kgraph.ingestion.local_files import LocalFileSource

def build_data_source(config: DataSourceConfig) -> DataSource:
    if config.type == "local_files":
        return LocalFileSource(folder=config.folder, file_type=config.file_type)
    if config.type == "arxiv":
        if not config.query:
            raise ValueError("arXiv source requires a 'query' in data_source config")
        return ArxivSource(query=config.query, max_results=config.max_results)
    # elif config.type == "mongo":
    #     return MongoSource(...)
    raise ValueError(f"Unknown data source type: {config.type}")