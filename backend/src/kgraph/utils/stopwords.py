"""Configurable stopword loader.

No hardcoded stopword sets — the source is always configurable.
Primary source is spaCy (already a project dependency); falls back to a
user-provided list or raises with installation instructions.
"""

from __future__ import annotations

import logging
from typing import List, Set

log = logging.getLogger(__name__)

# Module-level cache so the model is loaded at most once per process.
_cache: dict[str, Set[str]] = {}


def _spacy_stopwords() -> Set[str]:
    """Load stop words from the spaCy English pipeline."""
    try:
        import spacy
    except ImportError:
        raise ImportError(
            "spaCy is not installed. Add 'spacy' to your dependencies."
        )

    # Try common model names in order of preference
    for model_name in ("en_core_web_sm", "en_core_web_md", "en_core_web_lg"):
        try:
            nlp = spacy.load(model_name)
            return set(nlp.Defaults.stop_words)
        except Exception:
            continue

    raise RuntimeError(
        "No spaCy English model found. Install one:\n"
        "  uv run python -m spacy download en_core_web_sm"
    )


def get_stopwords(
    source: str = "spacy",
    extra: List[str] | None = None,
) -> Set[str]:
    """Return stop words from the configured source.

    Args:
        source: Where to load stop words from.
            - ``"spacy"``: load from spaCy's English pipeline (requires a
              downloaded model; see ``python -m spacy download en_core_web_sm``).
            - ``"config"``: use only the ``extra`` list provided by the caller.
        extra: Additional stop words to include regardless of source.

    Returns:
        Combined set of stop words.
    """
    cache_key = f"{source}:{','.join(sorted(extra or []))}"
    if cache_key in _cache:
        return _cache[cache_key]

    words: Set[str] = set()

    if source == "spacy":
        try:
            words = _spacy_stopwords()
            log.debug("Loaded %d stop words from spaCy", len(words))
        except (ImportError, RuntimeError) as e:
            log.warning(
                "Could not load spaCy stop words (%s). "
                "Falling back to 'config' source. "
                "Pass stop words via the 'extra' parameter or install a spaCy model.",
                e,
            )
            source = "config"

    if source == "config":
        if not extra:
            raise ValueError(
                "stopwords source is 'config' but no 'extra' list provided. "
                "Either pass a list of stop words or install a spaCy model "
                "and use source='spacy'."
            )

    if extra:
        words.update(w.lower() for w in extra)

    _cache[cache_key] = words
    return words
