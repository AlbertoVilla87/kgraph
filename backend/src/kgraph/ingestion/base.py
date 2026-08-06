from abc import ABC, abstractmethod
from kgraph.graph.models import RawDocument

class DataSource(ABC):
    @abstractmethod
    def fetch(self) -> list[RawDocument]:
        ...