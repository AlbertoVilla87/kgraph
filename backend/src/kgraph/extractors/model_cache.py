"""Singleton cache for GLiNER model to avoid reloading on every analysis."""

import threading
from gliner import GLiNER

_lock = threading.Lock()
_model: GLiNER | None = None
_model_path: str | None = None


def get_gliner_model(path: str) -> GLiNER:
    """Return a cached GLiNER model, loading from *path* on first call."""
    global _model, _model_path
    if _model is not None and _model_path == path:
        return _model
    with _lock:
        if _model is not None and _model_path == path:
            return _model
        _model = GLiNER.from_pretrained(path)
        _model_path = path
        return _model
