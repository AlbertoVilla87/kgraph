from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kgraph.api.routers import analysis, graph

app = FastAPI(
    title="ArXiv Graph Explorer API",
    description="Knowledge graph extraction and analysis for arXiv papers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
