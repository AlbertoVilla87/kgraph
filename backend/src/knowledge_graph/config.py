from pathlib import Path
import yaml
from pydantic import BaseModel

class DataSourceConfig(BaseModel):
    type: str
    folder: str
    file_type: str

class ModelConfig(BaseModel):
    name: str

class ThresholdConfig(BaseModel):
    entity: float
    relation: float

class PipelineConfig(BaseModel):
    data_source: DataSourceConfig
    entities: list[str]
    relations: list[str]
    thresholds: ThresholdConfig
    model: ModelConfig

def load_pipeline_config(path: str = "configs/pipeline.yaml") -> PipelineConfig:
    with open(Path(path)) as f:
        raw = yaml.safe_load(f)
    return PipelineConfig(**raw)