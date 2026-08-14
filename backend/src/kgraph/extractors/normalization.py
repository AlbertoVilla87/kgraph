import re
from typing import Dict, Optional


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


class EntityMerger:
    """Merge near-duplicate entity mentions.

    Two passes are applied lazily per entity:
    - Exact canonical match: same canonical form collapses.
    - Token containment: a shorter text fully contained in a longer one
      merges into it.
    """

    def __init__(self):
        self._entities: Dict[str, str] = {}

    def match(self, canonical_text: str) -> Optional[str]:
        """Return an existing canonical key matching ``canonical_text``.

        Returns ``None`` when no lexical match is found and registers the
        new canonical text for future matches.
        """
        if canonical_text in self._entities:
            return canonical_text

        for existing in self._entities:
            if token_subset(canonical_text, existing):
                return existing

            if token_subset(existing, canonical_text):
                return existing

        self._entities[canonical_text] = canonical_text
        return None