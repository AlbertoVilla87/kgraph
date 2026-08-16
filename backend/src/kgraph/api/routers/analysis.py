from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_in_progress: dict[str, dict] = {}
_results: dict[str, dict] = {}


class AnalyzeRequest(BaseModel):
    arxiv_id: str


class AnalysisStatus(BaseModel):
    id: str
    status: str
    arxiv_id: str
    progress: str | None = None


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
    arxiv_id: str
    title: str
    authors: list[str]
    published_at: str
    topics: list[TopicOut]
    relationships: list[RelationshipOut]
    references: list[dict]
    stats: dict


@router.post("/analyze", response_model=AnalysisStatus)
def analyze_paper(req: AnalyzeRequest):
    analysis_id = f"analysis_{req.arxiv_id.replace('.', '_')}"
    _in_progress[analysis_id] = {
        "id": analysis_id,
        "status": "pending",
        "arxiv_id": req.arxiv_id,
        "progress": "Queued",
    }
    return AnalysisStatus(**_in_progress[analysis_id])


@router.get("/{analysis_id}", response_model=AnalysisStatus)
def get_status(analysis_id: str):
    if analysis_id in _in_progress:
        return AnalysisStatus(**_in_progress[analysis_id])
    if analysis_id in _results:
        return AnalysisStatus(
            id=analysis_id, status="completed", arxiv_id=_results[analysis_id]["arxiv_id"]
        )
    raise HTTPException(status_code=404, detail="Analysis not found")


@router.get("/{analysis_id}/result", response_model=AnalysisResult)
def get_result(analysis_id: str):
    if analysis_id not in _results:
        raise HTTPException(status_code=404, detail="Analysis not completed yet")
    return AnalysisResult(**_results[analysis_id])
