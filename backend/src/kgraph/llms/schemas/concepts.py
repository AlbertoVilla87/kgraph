from pydantic import BaseModel, Field


class Concept(BaseModel):
    name: str = Field(..., description="Concept name, maximum 3 words.")

class Concepts(BaseModel):
    concepts: list[Concept]