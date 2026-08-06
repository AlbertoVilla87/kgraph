from abc import ABC, abstractmethod
import networkx as nx


class KnowledgeGraph(ABC):

    @abstractmethod
    def build(self, text: str) -> nx.Graph:
        pass