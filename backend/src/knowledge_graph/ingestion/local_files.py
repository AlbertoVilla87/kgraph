from pathlib import Path
from backend.src.knowledge_graph.ingestion.base import DataSource
from backend.src.knowledge_graph.models import RawDocument
from backend.src.knowledge_graph.ingestion.parsers.parsers import PARSERS

class LocalFileSource(DataSource):
    def __init__(self, folder: str, file_type: str):
        self.folder = Path(folder)
        self.file_type = file_type

        if file_type not in PARSERS:
            raise ValueError(f"Unsupported file_type: {file_type}. Available: {list(PARSERS.keys())}")

        self.parser = PARSERS[file_type]

    def fetch(self) -> list[RawDocument]:
        docs = []
        for path in self.folder.glob(f"*.{self.file_type}"):
            text, metadata = self.parser(path)
            docs.append(RawDocument(
                id=path.stem,
                content=text,
                source=f"local_{self.file_type}",
                metadata=metadata,
            ))
        return docs