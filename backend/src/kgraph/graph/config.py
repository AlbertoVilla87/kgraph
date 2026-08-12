from pathlib import Path
import yaml
from pydantic import BaseModel
from typing import Tuple

class DataSourceConfig(BaseModel):
    type: str
    folder: str
    file_type: str

class NERConfig(BaseModel):
    name: str

class AdaptiveExtractorConfig(BaseModel):
    min_k: int = 2
    max_k: int = 20
    words_per_kw: int = 40
    score_floor: float = 0.2
    max_candidates: int = 25

class ExtractorConfig(BaseModel):
    name: str
    stop_words: str
    diversity: float
    n_grams: Tuple[int, int]
    adaptive: AdaptiveExtractorConfig = AdaptiveExtractorConfig()

class LLMConfig(BaseModel):
    name: str

class DiscoveryConfig(BaseModel):
    spacy_model: str = "en_core_web_sm"
    pronouns: list[str] = []
    determiners: list[str] = []
    max_depth: int = 2
    max_relations: int = 100

class ThresholdConfig(BaseModel):
    entity: float
    relation: float

class PipelineConfig(BaseModel):
    data_source: DataSourceConfig
    entities: list[str] = []
    relations: list[str] = []
    thresholds: ThresholdConfig
    ner: NERConfig
    keyword_extractor: ExtractorConfig
    llm: LLMConfig
    discovery: DiscoveryConfig = DiscoveryConfig()

def load_pipeline_config(path: str) -> PipelineConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return PipelineConfig(**raw)

def build_pipeline_config(
    path: str,
    *,
    entities: list[str] | None = None,
    relations: list[str] | None = None,
) -> PipelineConfig:
    cfg = load_pipeline_config(path)
    if entities is not None:
        cfg.entities = entities
    if relations is not None:
        cfg.relations = relations
    return cfg