from pathlib import Path
import yaml
from pydantic import BaseModel
from typing import Tuple

class DataSourceConfig(BaseModel):
    type: str
    folder: str = ""
    file_type: str = ""
    query: str | None = None
    max_results: int = 100
    seed_url: str | None = None
    max_references: int = 15

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
    determiners: list[str] = []
    max_depth: int = 2
    max_relations: int = 100
    skip_headings: list[str] = [
        "references",
        "bibliography",
        "acknowledgements",
        "acknowledgments",
    ]
    max_seeds: int = 25

class ThresholdConfig(BaseModel):
    entity: float
    relation: float

class EntityMergingConfig(BaseModel):
    enabled: bool = True

class SegmentationConfig(BaseModel):
    enabled: bool = True
    max_tokens: int = 1024
    overlap_tokens: int = 64
    workers: int = 0

class CitationDiscoveryConfig(BaseModel):
    """Configuration for citation-guided discovery (exp_04 approach)."""
    ollama_model: str = "ollama/qwen3:0.6b"
    ollama_api_base: str = "http://localhost:11434"
    keep_alive: str = "1m"
    max_refs: int = 15
    top_concepts: int = 15
    top_relations: int = 8
    max_chars: int = 24_000
    stopwords_source: str = "language"
    stopwords_lang: str = "en"
    stopwords: list[str] = []

class PipelineConfig(BaseModel):
    data_source: DataSourceConfig
    entities: list[str] = []
    relations: list[str] = []
    thresholds: ThresholdConfig
    ner: NERConfig
    keyword_extractor: ExtractorConfig = ExtractorConfig(
        name="",
        stop_words="english",
        diversity=0.7,
        n_grams=(1, 2),
    )
    llm: LLMConfig
    discovery: DiscoveryConfig = DiscoveryConfig()
    entity_merging: EntityMergingConfig = EntityMergingConfig()
    segmentation: SegmentationConfig = SegmentationConfig()
    citation: CitationDiscoveryConfig = CitationDiscoveryConfig()

def _resolve_model_paths(raw: dict, config_dir: Path) -> dict:
    """Resolve relative model paths relative to the config file's parent directory.

    Models live in ``backend/models/`` while the config lives in
    ``backend/configs/``, so we try the config dir first, then its parent.
    """

    def _resolve(v: str) -> str:
        if not isinstance(v, str):
            return v
        if v.startswith("http://") or v.startswith("https://"):
            return v
        # Try config dir first, then its parent (backend/)
        for base in (config_dir, config_dir.parent):
            candidate = (base / v).resolve()
            if candidate.exists():
                return str(candidate)
        return v

    if "ner" in raw and "name" in raw["ner"]:
        raw["ner"]["name"] = _resolve(raw["ner"]["name"])
    if "keyword_extractor" in raw and "name" in raw["keyword_extractor"]:
        raw["keyword_extractor"]["name"] = _resolve(raw["keyword_extractor"]["name"])
    if "discovery" in raw and "spacy_model" in raw["discovery"]:
        raw["discovery"]["spacy_model"] = _resolve(raw["discovery"]["spacy_model"])

    return raw


def load_pipeline_config(path: str) -> PipelineConfig:
    import logging
    log = logging.getLogger(__name__)
    config_dir = Path(path).parent
    with open(path) as f:
        raw = yaml.safe_load(f)
    raw = _resolve_model_paths(raw, config_dir)
    log.info("Loaded config from %s", path)
    log.info("  ner.name resolved to: %s", raw.get("ner", {}).get("name"))
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