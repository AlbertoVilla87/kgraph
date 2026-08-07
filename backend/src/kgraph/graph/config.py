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

class ExtractorConfig(BaseModel):
    name: str
    stop_words: str
    diversity: float
    n_grams: Tuple[int, int]

class ThresholdConfig(BaseModel):
    entity: float
    relation: float

class PipelineConfig(BaseModel):
    data_source: DataSourceConfig
    entities: list[str]
    relations: list[str]
    thresholds: ThresholdConfig
    ner: NERConfig
    keyword_extractor: ExtractorConfig

def load_pipeline_config(path: str) -> PipelineConfig:
    with open(Path(path)) as f:
        raw = yaml.safe_load(f)
    return PipelineConfig(**raw)