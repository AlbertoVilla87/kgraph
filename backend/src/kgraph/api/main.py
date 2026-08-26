import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kgraph.api.routers import analysis, graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet noisy libraries; keep our loggers at INFO
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
# Only show uvicorn access logs on errors (4xx/5xx), not every 200 OK poll
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

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
