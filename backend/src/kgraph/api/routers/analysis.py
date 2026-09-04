from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from kgraph.api.state import analyses
from kgraph.api.runner import run_analysis

router = APIRouter()


class AnalyzeRequest(BaseModel):
    topic: str | None = None
    max_papers: int = 2
    seed_url: str | None = None
    max_references: int = 15


class AnalysisStatus(BaseModel):
    id: str
    status: str
    topic: str
    progress: float = 0.0
    current_step: str = ""
    detail: str = ""
    steps: list[dict] = []
    error: str | None = None
    partial_graph: dict | None = None


class TopicOut(BaseModel):
    id: str
    name: str
    type: str
    importance: float
    source: str
    documents: list[str]
    community: int | None = None


class RelationshipOut(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    confidence: float
    documents: list[str]
    inter_community: bool = False


class PaperOut(BaseModel):
    id: str
    title: str
    year: int | None = None
    url: str | None = None


class AnalysisResult(BaseModel):
    id: str
    topic: str
    papers: list[PaperOut]
    topics: list[TopicOut]
    relationships: list[RelationshipOut]
    stats: dict
    communities: dict | None = None


@router.post("/analyze", response_model=AnalysisStatus)
def start_analysis(req: AnalyzeRequest):
    if not req.topic and not req.seed_url:
        raise HTTPException(
            status_code=400,
            detail="Either 'topic' or 'seed_url' must be provided",
        )

    is_seed = req.seed_url is not None
    label = req.seed_url if is_seed else req.topic
    analysis_id = f"analysis_{(label or 'unknown').replace('/', '_').replace(':', '_').replace(' ', '_').lower()}"

    steps = []
    if is_seed:
        steps = [
            {"key": "fetch_seed", "label": "Downloading seed paper", "status": "pending"},
            {"key": "bibliography", "label": "Parsing bibliography", "status": "pending"},
            {"key": "fetch_refs", "label": "Downloading referenced papers", "status": "pending"},
        ]
    steps += [
        {"key": "ollama", "label": "Extracting concepts with Qwen", "status": "pending"},
        {"key": "parse", "label": "Parsing documents", "status": "pending"},
        {"key": "segment", "label": "Segmenting documents", "status": "pending"},
        {"key": "extract", "label": "Extracting entities and relationships", "status": "pending"},
        {"key": "merge", "label": "Merging cross-document graph", "status": "pending"},
        {"key": "done", "label": "Analysis complete", "status": "pending"},
    ]

    analyses[analysis_id] = {
        "id": analysis_id,
        "status": "pending",
        "topic": req.topic or "",
        "seed_url": req.seed_url,
        "max_papers": req.max_papers,
        "max_references": req.max_references,
        "progress": 0.0,
        "current_step": "",
        "detail": "",
        "steps": steps,
        "error": None,
    }

    import threading
    thread = threading.Thread(target=run_analysis, args=(analysis_id,), daemon=True)
    thread.start()

    return AnalysisStatus(**analyses[analysis_id])


@router.get("/{analysis_id}", response_model=AnalysisStatus)
def get_status(analysis_id: str):
    if analysis_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisStatus(**analyses[analysis_id])


@router.get("/{analysis_id}/result", response_model=AnalysisResult)
def get_result(analysis_id: str):
    if analysis_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")
    a = analyses[analysis_id]
    if a["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed yet")
    return AnalysisResult(**a.get("result", {}))
