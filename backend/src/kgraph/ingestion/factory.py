"""Factory for building data sources from configuration.

New source types are added by:
  1. Implementing DataSource (and optionally ReferenceExtractor)
  2. Registering them here in ``build_data_source``
"""

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

    if config.type == "seed_paper":
        return _build_seed_paper(config)

    raise ValueError(f"Unknown data source type: {config.type}")


def _build_seed_paper(config: DataSourceConfig) -> DataSource:
    """Wire a SeedPaperSource with the correct source + extractor."""
    from kgraph.ingestion.seed_paper import SeedPaperSource, _parse_arxiv_id
    from kgraph.ingestion.references import ArxivReferenceExtractor

    if not config.seed_url:
        raise ValueError("seed_paper source requires a 'seed_url' in data_source config")

    # Detect source type from the seed URL
    seed_id = _parse_arxiv_id(config.seed_url)
    inner_source = ArxivSource(query=seed_id, max_results=1)
    extractor = ArxivReferenceExtractor()

    return SeedPaperSource(
        source=inner_source,
        extractor=extractor,
        seed_id=seed_id,
        max_references=config.max_references,
    )
