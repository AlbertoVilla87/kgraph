# src/kg_graph/ingestion/factory.py
from backend.src.knowledge_graph.config import DataSourceConfig
from backend.src.knowledge_graph.ingestion.base import DataSource
from backend.src.knowledge_graph.ingestion.local_files import LocalFileSource

def build_data_source(config: DataSourceConfig) -> DataSource:
    if config.type == "local_files":
        return LocalFileSource(folder=config.folder, file_type=config.file_type)
    # elif config.type == "mongo":
    #     return MongoSource(...)
    raise ValueError(f"Unknown data source type: {config.type}")