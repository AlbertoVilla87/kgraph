"""Configurable stopword loader, keyed by language.

Built-in stopword sets ship per language (``STOPWORDS_BY_LANG``) so no external
NLP model is required. Add a new language by extending the dict. Sources:

- ``"language"`` (default): built-in list for ``lang`` (falls back to English).
- ``"spacy"``: load from spaCy's English pipeline (requires a downloaded model;
  kept for backward compatibility).
- ``"config"``: use only the ``extra`` list provided by the caller.

The result is cached per (source, lang, extras) tuple.
"""

from __future__ import annotations

import logging
from typing import List, Set

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in stopword lists, indexed by language code.
# English is the spaCy English stop word list (MIT). Extend with new languages
# as needed, e.g.:
#     "es": {...}, "fr": {...}
# ---------------------------------------------------------------------------

STOPWORDS_BY_LANG: dict[str, Set[str]] = {
    "en": {
        "a", "about", "above", "across", "after", "afterwards", "again",
        "against", "all", "almost", "alone", "along", "already", "also",
        "although", "always", "am", "among", "amongst", "amoungst", "amount",
        "an", "and", "another", "any", "anyhow", "anyone", "anything",
        "anyway", "anywhere", "are", "around", "as", "at", "back", "be",
        "became", "because", "become", "becomes", "becoming", "been",
        "before", "beforehand", "behind", "being", "below", "beside",
        "besides", "between", "beyond", "bill", "both", "bottom", "but",
        "by", "call", "can", "cannot", "cant", "co", "con", "could", "couldnt",
        "cry", "de", "describe", "detail", "do", "done", "down", "due",
        "during", "each", "eg", "eight", "either", "eleven", "else",
        "elsewhere", "empty", "enough", "etc", "even", "ever", "every",
        "everyone", "everything", "everywhere", "except", "few", "fifteen",
        "fifty", "fill", "find", "fire", "first", "five", "for", "former",
        "formerly", "forty", "found", "four", "from", "front", "full",
        "further", "get", "give", "go", "had", "has", "hasnt", "have", "he",
        "hence", "her", "here", "hereafter", "hereby", "herein", "hereupon",
        "hers", "herself", "him", "himself", "his", "how", "however",
        "hundred", "i", "ie", "if", "in", "inc", "indeed", "interest",
        "into", "is", "it", "its", "itself", "keep", "last", "latter",
        "latterly", "least", "less", "ll", "ltd", "made", "many", "may",
        "me", "meanwhile", "might", "mill", "mine", "more", "moreover",
        "most", "mostly", "move", "much", "must", "my", "myself", "name",
        "namely", "neither", "never", "nevertheless", "next", "nine", "no",
        "nobody", "none", "noone", "nor", "not", "nothing", "now", "nowhere",
        "of", "off", "often", "on", "once", "one", "only", "onto", "or",
        "other", "others", "otherwise", "our", "ours", "ourselves", "out",
        "over", "own", "part", "per", "perhaps", "please", "put", "rather",
        "re", "same", "see", "seem", "seemed", "seeming", "seems", "serious",
        "several", "she", "should", "show", "side", "since", "sincere",
        "six", "sixty", "so", "some", "somehow", "someone", "something",
        "sometime", "sometimes", "somewhere", "still", "such", "system",
        "take", "ten", "than", "that", "the", "their", "them",
        "themselves", "then", "thence", "there", "thereafter", "thereby",
        "therefore", "therein", "thereupon", "these", "they", "thick",
        "thin", "third", "this", "those", "though", "three", "through",
        "throughout", "thru", "thus", "to", "together", "too", "top",
        "toward", "towards", "twelve", "twenty", "two", "un", "under",
        "until", "up", "upon", "us", "very", "via", "was", "we", "well",
        "were", "what", "whatever", "when", "whence", "whenever", "where",
        "whereafter", "whereas", "whereby", "wherein", "whereupon",
        "wherever", "whether", "which", "while", "whither", "who", "whoever",
        "whole", "whom", "whose", "why", "will", "with", "within", "without",
        "would", "yet", "you", "your", "yours", "yourself", "yourselves",
    },
    # Future languages, e.g.:
    # "es": {"a", "al", "algo", ...},
    # "fr": {"à", "là", "au", ...},
}

# Module-level cache so the lists are computed at most once per process.
_cache: dict[str, Set[str]] = {}


def _spacy_stopwords() -> Set[str]:
    """Load stop words from the spaCy English pipeline."""
    try:
        import spacy
    except ImportError:
        raise ImportError(
            "spaCy is not installed. Add 'spacy' to your dependencies."
        )

    # Try standard model names.
    model_names = ["en_core_web_sm", "en_core_web_md", "en_core_web_lg"]
    for model_name in model_names:
        try:
            nlp = spacy.load(model_name)
            return set(nlp.Defaults.stop_words)
        except Exception:
            continue

    raise RuntimeError(
        "No spaCy English model found. Install one:\n"
        "  uv run python -m spacy download en_core_web_sm"
    )


def _builtin_stopwords(lang: str) -> Set[str]:
    """Return the built-in stop words for ``lang`` (English fallback)."""
    return set(STOPWORDS_BY_LANG.get(lang, STOPWORDS_BY_LANG["en"]))


def get_stopwords(
    source: str = "language",
    lang: str = "en",
    extra: List[str] | None = None,
) -> Set[str]:
    """Return stop words from the configured source.

    Args:
        source: Where to load stop words from.
            - ``"language"``: built-in list for ``lang`` (default).
            - ``"spacy"``: load from spaCy's English pipeline (requires a
              downloaded model; see ``python -m spacy download en_core_web_sm``).
            - ``"config"``: use only the ``extra`` list provided by the caller.
        lang: Language code for the built-in lists (e.g. ``en``, ``es``).
        extra: Additional stop words to include regardless of source.

    Returns:
        Combined set of stop words.
    """
    cache_key = f"{source}:{lang}:{','.join(sorted(extra or []))}"
    if cache_key in _cache:
        return _cache[cache_key]

    words: Set[str] = set()

    if source == "language":
        words = _builtin_stopwords(lang)
    elif source == "spacy":
        try:
            words = _spacy_stopwords()
            log.debug("Loaded %d stop words from spaCy", len(words))
        except (ImportError, RuntimeError) as e:
            log.warning(
                "Could not load spaCy stop words (%s). "
                "Falling back to the built-in '%s' list.",
                e,
                lang,
            )
            words = _builtin_stopwords(lang)
    elif source == "config":
        if not extra:
            raise ValueError(
                "stopwords source is 'config' but no 'extra' list provided. "
                "Either pass a list of stop words or use source='language'."
            )
    else:
        raise ValueError(
            f"Unknown stopwords source: {source!r}. "
            "Expected one of: 'language', 'spacy', 'config'."
        )

    if extra:
        words.update(w.lower() for w in extra)

    _cache[cache_key] = words
    return words