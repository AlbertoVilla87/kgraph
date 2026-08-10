from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLM(ABC):
    @abstractmethod
    def chat(
        self,
        prompt: str,
        model: str,
        schema: type[BaseModel] | dict[str, Any] | None = None,
        temperature: float = 0.0
    ) -> str:
        ...
