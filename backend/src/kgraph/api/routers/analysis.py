from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from kgraph.api.state import analyses
from kgraph.api.runner import run_analysis

router = APIRouter()


class AnalyzeRequest(BaseModel):
    topic: str
    max_papers: int = 2


class AnalysisStatus(BaseModel):
    id: str
    status: str
    topic: str
    progress: float = 0.0
    current_step: str = ""
    steps: list[dict] = []
    error: str | None = None


class TopicOut(BaseModel):
    id: str
    name: str
    type: str
    importance: float
    source: str
    documents: list[str]


class RelationshipOut(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    confidence: float
    documents: list[str]


class AnalysisResult(BaseModel):
    id: str
    topic: str
    papers: list[dict]
    topics: list[TopicOut]
    relationships: list[RelationshipOut]
    stats: dict


@router.post("/analyze", response_model=AnalysisStatus)
def start_analysis(req: AnalyzeRequest):
    analysis_id = f"analysis_{req.topic.replace(' ', '_').lower()}"
    steps = [
        {"key": "fetch", "label": "Fetching papers from arXiv", "status": "pending"},
        {"key": "parse", "label": "Parsing documents", "status": "pending"},
        {"key": "taxonomy", "label": "Building topic taxonomy", "status": "pending"},
        {"key": "segment", "label": "Segmenting documents", "status": "pending"},
        {"key": "extract", "label": "Extracting entities and relationships", "status": "pending"},
        {"key": "merge", "label": "Merging cross-document graph", "status": "pending"},
        {"key": "done", "label": "Analysis complete", "status": "pending"},
    ]
    analyses[analysis_id] = {
        "id": analysis_id,
        "status": "pending",
        "topic": req.topic,
        "max_papers": req.max_papers,
        "progress": 0.0,
        "current_step": "",
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
