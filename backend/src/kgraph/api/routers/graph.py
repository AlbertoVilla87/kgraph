from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/{analysis_id}")
def get_graph(analysis_id: str):
    return {
        "nodes": [],
        "edges": [],
        "message": "Graph visualization endpoint — connect to real pipeline data",
    }


@router.get("/{analysis_id}/subgraph")
def get_subgraph(analysis_id: str, topic: str = "", source: str = ""):
    return {
        "nodes": [],
        "edges": [],
        "filter": {"topic": topic, "source": source},
    }
