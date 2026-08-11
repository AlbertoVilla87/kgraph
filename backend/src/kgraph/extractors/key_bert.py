from typing import Tuple

import numpy as np
from kneed import KneeLocator
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

from kgraph.graph.config import ExtractorConfig


class AdaptiveKeyBERT:
    """KeyBERT wrapper that picks the number of keywords adaptively.

    Requests a generous pool of candidates (scaled to document length) and then
    cuts it off at the elbow of the cosine-similarity scores using KneeLocator,
    instead of relying on a fixed ``top_n``.
    """

    def __init__(self, config: ExtractorConfig):
        self.config = config
        self.adaptive = config.adaptive
        self.model = KeyBERT(model=SentenceTransformer(config.name))

    def _dynamic_bounds(self, n_words: int) -> Tuple[int, int]:
        est = round(n_words / self.adaptive.words_per_kw)
        max_k = max(self.adaptive.min_k, min(self.adaptive.max_k, est))
        min_k = min(self.adaptive.min_k, max_k)
        return min_k, max_k

    def _pool_size(self, n_words: int) -> int:
        est = round(n_words / self.adaptive.words_per_kw)
        _, max_k = self._dynamic_bounds(n_words)
        return max(max_k, min(self.adaptive.max_candidates, est))

    def extract(self, doc: str) -> list[tuple[str, float]]:
        n_words = len(doc.split())
        min_k, max_k = self._dynamic_bounds(n_words)

        candidates = self.model.extract_keywords(
            doc,
            keyphrase_ngram_range=self.config.n_grams,
            stop_words=self.config.stop_words,
            use_maxsum=True,
            top_n=self._pool_size(n_words),
        )
        if not candidates:
            return []

        candidates = [
            (kw, s) for kw, s in candidates if s >= self.adaptive.score_floor
        ]
        if len(candidates) <= min_k:
            return candidates

        scores = np.array([s for _, s in candidates])
        lo = min(min_k, len(scores))
        hi = min(max_k, len(scores))
        window = scores[lo - 1 : hi]
        if len(window) < 2:
            return candidates[:lo]

        knee = KneeLocator(
            np.arange(lo, hi + 1),
            window,
            curve="convex",
            direction="decreasing",
        ).knee
        if knee is None:
            diffs = -np.diff(window)
            cutoff = lo + int(np.argmax(diffs)) if len(diffs) else lo
        else:
            cutoff = int(knee)
        cutoff = max(lo, min(hi, cutoff))
        return candidates[:cutoff]
