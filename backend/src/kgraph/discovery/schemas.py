from pydantic import BaseModel


class DiscoveredRelation(BaseModel):
    source: str
    relation: str
    target: str
    evidence: str


class DiscoveryResult(BaseModel):
    relations: list[DiscoveredRelation]
