"""Search an arbitrary user-typed entity inside an analysis's documents.

The user can ask "does this entity exist in the fetched papers?" and, if so,
whether it can be linked to an existing graph node — or added as a new node
with its relations. This module implements that lookup:

1. **Lexical pre-filter**: only chunks whose normalized text contains a token
   of the searched entity are considered. This keeps the (relatively slow)
   GLiNER inference to a tiny subset of the corpus.
2. **GLiNER as a probe**: run GLiNER on the candidate chunks passing the
   searched text itself as the label (e.g. ``labels=["few-shot learning"]``).
   This detects the entity — and its surface variants — directly in the text,
   independent of the pipeline's fixed label set.
3. **Existing-node matching**: the searched entity is normalized and compared
   against the analysis's existing nodes (canonical form + token containment),
   reusing the same ``EntityMerger`` the pipeline uses.
4. **New-node relations**: when the entity appears in the text but does not
   match an existing node, run GLiNER with ``relations`` over the segments
   where it appears so it can be added as a new node connected to others.
"""

import logging
import re
from typing import List, Optional, Tuple

from kgraph.api.state import analysis_chunks, analyses
from kgraph.extractors.model_cache import get_gliner_model
from kgraph.extractors.normalization import EntityMerger, canonical

log = logging.getLogger(__name__)

_MAX_CANDIDATES = 24
_ENTITY_THRESHOLD = 0.4
_RELATION_THRESHOLD = 0.4


def _config_path() -> str:
    from pathlib import Path
    return str(Path(__file__).resolve().parents[3] / "configs" / "params.yaml")


def _load_config():
    from kgraph.graph.config import load_pipeline_config
    return load_pipeline_config(_config_path())


def _tokens(text: str) -> List[str]:
    return [t for t in re.split(r"\W+", text.lower()) if t]


def _span_mentions(query: str, text: str) -> Tuple[List[dict], int]:
    """Case-insensitive substring spans of ``query`` in ``text``."""
    spans: List[dict] = []
    if not query or not text:
        return spans, 0
    low = text.lower()
    q = query.lower()
    start = 0
    while True:
        idx = low.find(q, start)
        if idx == -1:
            break
        spans.append({"start": idx, "end": idx + len(q)})
        start = idx + len(q)
    return spans, len(spans)


def _existing_node_id(entity_text: str, topics: List[dict]) -> Optional[dict]:
    """Return the analysis node best matching ``entity_text``, if any."""
    query_canonical = canonical(entity_text)
    if not query_canonical:
        return None
    best: Optional[dict] = None
    for node in topics or []:
        name = node.get("name") or node.get("label") or ""
        if not name:
            continue
        node_canonical = canonical(name)
        if query_canonical == node_canonical:
            return node
        # Token containment either way (substring-equivalence).
        if _token_subset(query_canonical, node_canonical) or _token_subset(
            node_canonical, query_canonical
        ):
            best = node
    return best


def _token_subset(short: str, long: str) -> bool:
    """True if every token of ``short`` matches a token of ``long``.

    Tokens match on exact equality or a short-prefix relation, so singular /
    plural and light inflections ("network" vs "networks") still match.
    """
    st = short.split()
    lt = long.split()
    if not st:
        return False
    for tok in st:
        if not any(_token_equiv(tok, other) for other in lt):
            return False
    return True


def _token_equiv(a: str, b: str) -> bool:
    if a == b:
        return True
    return (len(a) >= 4 and b.startswith(a)) or (len(b) >= 4 and a.startswith(b))


def _gliner_probe(
    entity_text: str,
    candidates: List[Tuple[str, int, str]],
) -> Tuple[List[dict], List[str]]:
    """Run GLiNER with ``entity_text`` as the label over candidate chunks.

    Returns ``(mentions, docs)`` where each mention is
    ``{"doc_id", "segment", "start", "end", "text", "score"}``.
    """
    cfg = _load_config()
    model = get_gliner_model(cfg.ner.name)
    docs: set[str] = set()
    mentions: List[dict] = []

    for doc_id, segment, text in candidates:
        if not text.strip():
            continue
        raw = model.inference(
            texts=[text],
            labels=[entity_text],
            threshold=_ENTITY_THRESHOLD,
            flat_ner=False,
        )
        # GLiNER returns a list-of-list (one entry per input text); the first
        # document's entities are at ``raw[0][0]``.
        spans = []
        if raw and raw[0]:
            spans = raw[0][0] if raw[0][0] else []
        for item in spans:
            if not isinstance(item, dict):
                continue
            start = item.get("start")
            end = item.get("end")
            span_text = item.get("text") or ""
            if (start is None or end is None) and span_text:
                loc = _span_mentions(span_text, text)
                if loc[1]:
                    start, end = loc[0][0]["start"], loc[0][0]["end"]
            if start is None or end is None:
                continue
            mentions.append(
                {
                    "doc_id": doc_id,
                    "segment": segment,
                    "start": int(start),
                    "end": int(end),
                    "text": span_text,
                    "score": round(float(item.get("score", 0.0)), 3),
                }
            )
            if doc_id:
                docs.add(doc_id)
    return mentions, sorted(docs)


def _resolve_existing(text: str, topics: List[dict]) -> Optional[str]:
    """Return a matching existing node ``id`` for ``text``, else None."""
    q = canonical(text)
    if not q:
        return None
    for node in topics or []:
        name = node.get("name") or node.get("label") or ""
        if not name:
            continue
        n = canonical(name)
        if q == n or _token_subset(q, n) or _token_subset(n, q):
            return node.get("id")
    return None


def _extract_relations(
    entity_text: str,
    mentions: List[dict],
    segments: dict,
    topics: List[dict],
) -> List[dict]:
    """Run GLiNER relation extraction over segments where the entity appears.

    Returns relation dicts wired to existing graph nodes where possible: each
    relation carries ``source_id``/``target_id`` (resolved against the
    analysis's topics) plus the raw endpoint texts, so the new node can be
    connected to neighbours that already exist in the graph.
    """
    cfg = _load_config()
    model = get_gliner_model(cfg.ner.name)
    relations: List[dict] = []
    seen_segments = {(m["doc_id"], m["segment"]) for m in mentions}
    query_canonical = canonical(entity_text)

    for doc_id, segment in seen_segments:
        text = None
        for c in segments.get(doc_id, []):
            if c.get("index") == segment:
                text = c.get("text") or ""
                break
        if not text:
            continue
        try:
            entities_raw, relations_raw = model.inference(
                texts=[text],
                labels=cfg.entities,
                relations=cfg.relations,
                threshold=_ENTITY_THRESHOLD,
                relation_threshold=_RELATION_THRESHOLD,
                return_relations=True,
                flat_ner=False,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("GLiNER relations failed on segment %s:%s: %s", doc_id, segment, e)
            continue

        # Map surface entity text -> existing node id for wiring. GLiNER nests
        # per-input-text, so entities for ``texts[0]`` live at ``[0]``.
        entity_nodes = {
            canonical(item.get("text", "")): _resolve_existing(item.get("text", ""), topics)
            for item in (entities_raw[0] if entities_raw and entities_raw[0] else [])
        }

        rels = relations_raw[0] if relations_raw and relations_raw[0] else []
        for rel in rels:
            head = rel.get("head", {}).get("text", "")
            tail = rel.get("tail", {}).get("text", "")
            head_id = entity_nodes.get(canonical(head))
            tail_id = entity_nodes.get(canonical(tail))
            head_is_query = canonical(head) == query_canonical
            tail_is_query = canonical(tail) == query_canonical
            relations.append(
                {
                    "relation": rel.get("relation", ""),
                    "head": head,
                    "tail": tail,
                    "head_id": head_id,
                    "tail_id": tail_id,
                    "head_is_query": head_is_query,
                    "tail_is_query": tail_is_query,
                    "score": round(float(rel.get("score", 0.0)), 3),
                    "doc_id": doc_id,
                    "segment": segment,
                }
            )
    return relations


def _node_relations(node_id: str, relationships: List[dict]) -> List[dict]:
    """Return the existing graph relations incident to ``node_id``."""
    out = []
    for rel in relationships or []:
        if rel.get("source") == node_id or rel.get("target") == node_id:
            out.append(rel)
    return out


def search_entity(analysis_id: str, entity_text: str) -> dict:
    """Search ``entity_text`` within the completed analysis's documents.

    The graph is auto-discovered from the state of the art, so the user's
    entity typically does NOT already exist in it. We therefore look the
    entity up in the fetched text and report how it relates to the current
    graph:

    - ``found``: the entity matches an existing graph node. Returns that node
      and its existing relations (so the UI can pulse it and show its links).
    - ``partial``: the entity appears in the text but is not yet a node —
      extracts its relations against existing nodes so it can be added and
      wired into the graph.
    - ``not_found``: the entity does not appear in the fetched papers.
    """
    if analysis_id not in analysis_chunks:
        raise LookupError("Analysis not found")
    if analysis_id not in analyses or analyses[analysis_id].get("status") != "completed":
        raise ValueError("Analysis not completed yet")

    store = analysis_chunks[analysis_id]
    segments = store.get("segments", {})
    result = analyses[analysis_id].get("result") or {}
    topics = result.get("topics", [])
    relationships = result.get("relationships", [])

    # 1. Existing-node match via canonical/token containment.
    matched = _existing_node_id(entity_text, topics)

    # 2. Lexical pre-filter over chunks.
    ent_tokens = _tokens(entity_text)
    candidates: List[Tuple[str, int, str]] = []
    for doc_id, chunks in segments.items():
        for c in chunks:
            text = c.get("text") or ""
            low = text.lower()
            if any(tok and tok in low for tok in ent_tokens):
                candidates.append((doc_id, c.get("index", 0), text))

    mentions: List[dict] = []
    docs: List[str] = []
    new_relations: List[dict] = []
    mode = "not_found"

    if candidates:
        mentions, docs = _gliner_probe(entity_text, candidates[:_MAX_CANDIDATES])
        if mentions:
            mode = "found" if matched is not None else "partial"
            # Whether or not it matches an existing node, surface how it relates
            # to the graph: for a found node we reuse its stored relations; for
            # a new entity we extract relations from the segments where it shows.
            if matched is not None:
                new_relations = _node_relations(matched.get("id"), relationships)
            else:
                try:
                    new_relations = _extract_relations(entity_text, mentions, segments, topics)
                except Exception as e:  # noqa: BLE001
                    log.warning("relation extraction failed: %s", e)
                    new_relations = []
        elif matched is not None:
            mode = "found"
            docs = sorted({d for d in (matched.get("documents") or [])})
            new_relations = _node_relations(matched.get("id"), relationships)

    if matched is not None and not mentions:
        mode = "found"
        if not new_relations:
            new_relations = _node_relations(matched.get("id"), relationships)

    return {
        "status": mode,  # "found" | "partial" | "not_found"
        "existing_node": matched,
        "mentions": mentions,
        "relations": new_relations,
        "documents": docs,
        "query": entity_text,
    }
