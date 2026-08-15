# Data model & configuration

## Core data structures (`graph/models.py`)

All dataclasses, with `Entity` and `Relation` being the two output graph elements:

```python
@dataclass
class Entity:
    id: str
    text: str
    entity_type: str
    score: float
    source_doc: str
    mentions: list[dict] = field(default_factory=list)
```

- `id` is `md5(f"{entity_type}:{text.lower().strip()}")[:12]` (`Entity.generate_id`) — deterministic, so the same entity across runs/documents gets the same id.
- `mentions` accumulates one entry per observation (each records its `segment` index for provenance in the segmented pipeline).

```python
@dataclass
class Relation:
    head_text: str
    relation_type: str
    tail_text: str
    score: float
    source_doc: str
```

A `Relation` is stored on the graph edge; the edge also keeps a `count` of how many times the same `(head, relation, tail)` was observed, and the **maximum** score across observations.

```python
@dataclass
class RawDocument:
    id: str
    content: str
    source: str
    metadata: dict = field(default_factory=dict)
    docling_doc: Any = None
```

`docling_doc` holds the structured `DoclingDocument` when the source is parsed fresh (needed by the section-aware `Segmenter`); re-read cached `.md` files don't have one.

Discovery-side schemas (`discovery/schemas.py`, Pydantic):

```python
class DiscoveredRelation(BaseModel):
    source: str
    relation: str
    target: str
    evidence: str          # the sentence the relation was parsed from

class DiscoveryResult(BaseModel):
    relations: list[DiscoveredRelation]
```

## Configuration (`graph/config.py`)

`params.yaml` is loaded into a `PipelineConfig` (`load_pipeline_config`); `build_pipeline_config(entities=..., relations=...)` additionally overrides the static label lists with the discovered taxonomy.

| Block | Key | Default | Meaning |
| --- | --- | --- | --- |
| `data_source` | `type` | `local_files` | `local_files` \| `arxiv` |
| | `folder` | `data/arxiv_pdfs` | folder read by `LocalFileSource` |
| | `file_type` | `pdf` | `txt` \| `md` \| `json` \| `pdf` |
| | `query`, `max_results` | — | used by the arXiv source |
| `entities` / `relations` | | (mortgage schema) | static fallback labels; overridden by discovery |
| `thresholds` | `entity` / `relation` | `0.5` / `0.5` | minimum GLiNER score to keep a result |
| `ner` | `name` | `models/gliner-relex-large-v0.5` | local GLiNER model path |
| `keyword_extractor` | `name` | `models/all-MiniLM-L6-v2` | local embedding model path |
| | `diversity` | `0.7` | KeyBERT maxsum diversity |
| | `stop_words` | `english` | KeyBERT stop words |
| | `n_grams` | `[1, 2]` | keyphrase n-gram range |
| | `adaptive.*` | see [Discovery](discovery.md) | adaptive seed-count tuning |
| `discovery.*` | | see [Discovery](discovery.md) | spaCy model, BFS depth, skip headings, ... |
| `entity_merging.*` | | see [Assembly](assembly.md) | near-duplicate entity merge |
| `segmentation.*` | | see [Segmentation](segmentation.md) | token budget, overlap, workers |
| `llm` | `name` | `ollama/qwen3:0.6b` | used only by `qwen-demo` |

## Module → configuration mapping

| Concern | Module | Config block |
| --- | --- | --- |
| Sources | `ingestion/` | `data_source` |
| Seeds | `extractors/key_bert.py` | `keyword_extractor` |
| Relations + BFS | `discovery/dependency_relations.py`, `discovery/topic_graph.py` | `discovery` |
| Taxonomy + merge | `discovery/assembly.py`, `extractors/gliner.py`, `extractors/normalization.py` | `entity_merging`, `thresholds` |
| Segmentation | `segmentation/` | `segmentation` |
| (Optional) LLM route | `llms/` | `llm` |
