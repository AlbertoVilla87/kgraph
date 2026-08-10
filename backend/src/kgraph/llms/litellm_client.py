from typing import Any

from litellm import completion
from pydantic import BaseModel

from kgraph.llms.base import LLM


class LiteLLMClient(LLM):
    def __init__(self, api_base: str = "http://localhost:11434"):
        self.api_base = api_base

    def chat(
        self,
        prompt: str,
        model: str = "ollama/qwen3:0.6b",
        schema: type[BaseModel] | dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> str:
        response = completion(
            model=model,
            api_base=self.api_base,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                },
            },
        )
        return response.choices[0].message.content

    def chat_structured(self, prompt: str, schema: type[BaseModel], model: str = "ollama/qwen3:0.6b", temperature: float = 0.0,) -> BaseModel:
        content = self.chat(prompt=prompt, model=model, schema=schema, temperature=temperature)
        return schema.model_validate_json(content)
