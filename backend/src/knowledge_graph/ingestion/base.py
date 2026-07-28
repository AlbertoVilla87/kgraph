from abc import ABC, abstractmethod
from backend.src.knowledge_graph.models import RawDocument

class DataSource(ABC):
    @abstractmethod
    def fetch(self) -> list[RawDocument]:
        ...