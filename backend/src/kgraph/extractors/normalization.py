import re
from typing import Dict, Optional

import numpy as np


LEADING_ARTICLES = ("the ", "a ", "an ")


def canonical(text: str) -> str:
    """Normalize an entity text: lowercase, collapse whitespace, strip leading articles.

    Hyphen- and underscore-separated tokens are treated as space-separated, so
    ``"Chain-of-Thought Hub"`` and ``"chain-of-thought-hub"`` share a canonical
    form.
    """
    norm = re.sub(r"[\s\-_]+", " ", text.strip().lower())

    for article in LEADING_ARTICLES:
        if norm.startswith(article):
            norm = norm[len(article):]
            break

    return norm


def token_subset(short: str, long: str) -> bool:
    """Return True if every token of ``short`` appears in ``long``.

    Handles near-duplicate patterns such as:
    ``model`` in ``reasoning model``
    ``artifacts`` in ``formatting artifacts``
    """
    tokens = long.split()
    return all(tok in tokens for tok in short.split())


def _is_acronym_of(short: str, long: str) -> bool:
    """Return True if ``short`` is the acronym of ``long`` (or vice versa).

    Examples that should match:
    - ``llm`` ↔ ``large language model``
    - ``cnn`` ↔ ``convolutional neural network``
    - ``nlp`` ↔ ``natural language processing``

    Plurals/suffixes are stripped before comparing, so ``llms`` matches
    ``large language models``.
    """
    def _strip_suffixes(text: str) -> str:
        """Remove common trailing suffixes like 's', 'es', 'ies'."""
        t = text.strip()
        if t.endswith("ies"):
            return t[:-3]
        if t.endswith("es"):
            return t[:-2]
        if t.endswith("s"):
            return t[:-1]
        return t

    # Strip suffixes from both sides
    short_ = _strip_suffixes(short)
    long_ = _strip_suffixes(long)

    # Try: short is the acronym of long
    words = long_.split()
    if len(words) >= 2:
        acronym = "".join(w[0] for w in words)
        if short_ == acronym.lower():
            return True

    # Try: long is the acronym of short
    words_s = short_.split()
    if len(words_s) >= 2:
        acronym_s = "".join(w[0] for w in words_s)
        if long_ == acronym_s.lower():
            return True

    return False


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class EntityMerger:
    """Merge near-duplicate entity mentions.

    Two passes are applied lazily per entity:
    - Exact canonical match: same canonical form collapses.
    - Token containment: a shorter text fully contained in a longer one
      merges into it.
    - Embedding similarity: when a sentence-transformer model is available,
      entities whose embeddings exceed ``threshold`` are merged.
    """

    def __init__(self, threshold: float = 0.85, model_path: str | None = None):
        self._entities: Dict[str, str] = {}
        self._embeddings: Dict[str, np.ndarray] = {}
        self._threshold = threshold
        self._model_path = model_path
        self._model = None  # lazy-loaded

    def _get_model(self):
        """Lazy-load the sentence-transformer model."""
        if self._model is None and self._model_path:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_path)
            except Exception:
                pass
        return self._model

    def _embed(self, text: str) -> np.ndarray | None:
        """Compute embedding for text, returning None if model unavailable."""
        model = self._get_model()
        if model is None:
            return None
        return model.encode(text, normalize_embeddings=True)

    def match(self, canonical_text: str) -> Optional[str]:
        """Return an existing canonical key matching ``canonical_text``.

        Returns ``None`` when no lexical match is found and registers the
        new canonical text for future matches.
        """
        if canonical_text in self._entities:
            return canonical_text

        # Pass 1 & 2: lexical matching (exact canonical + token containment)
        for existing in self._entities:
            if token_subset(canonical_text, existing):
                return existing

            if token_subset(existing, canonical_text):
                return existing

        # Pass 3: acronym detection (e.g. "llm" ↔ "large language model")
        for existing in self._entities:
            if _is_acronym_of(canonical_text, existing):
                return existing

        # Pass 4: embedding similarity
        model = self._get_model()
        if model is not None:
            emb = self._embed(canonical_text)
            if emb is not None:
                for existing, existing_emb in self._embeddings.items():
                    sim = _cosine_similarity(emb, existing_emb)
                    if sim >= self._threshold:
                        return existing
                self._embeddings[canonical_text] = emb

        self._entities[canonical_text] = canonical_text
        return None