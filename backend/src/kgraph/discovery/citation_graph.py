"""Citation-guided discovery engine.

Instead of discovering topics from scratch (KeyBERT + spaCy), this module
uses the **seed paper's own citations** to define the GLiNER taxonomy:

1. Parse the seed's bibliography → arXiv IDs, author–year pairs.
2. Find citing contexts in the seed body (author–year matching).
3. Ask Qwen (via Ollama/LiteLLM) to extract {concepts, types, relations}
   from each citing context.
4. Aggregate across references → top-K become GLiNER zero-shot labels.
5. Build per-document label mappings (each ref gets its own lens).
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx
import requests
from pydantic import BaseModel, Field

from kgraph.discovery.bibliography import (
    BibliographyEntry,
    extract_author_year,
    parse_bibliography_entries,
)
from kgraph.graph.config import CitationDiscoveryConfig, PipelineConfig
from kgraph.graph.models import RawDocument
from kgraph.utils.stopwords import get_stopwords

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models for Qwen structured output
# ---------------------------------------------------------------------------

class ConceptItem(BaseModel):
    """A single concept with its canonical (deduplicated) form.

    ``concept`` is the term as it appears in the citing context (e.g. ``LLMs``);
    ``canonical`` is the preferred, expanded form that all surface variants
    should collapse into (e.g. ``Large Language Model``). Qwen resolves the
    acronym/paraphrase equivalence here so downstream labels and extracted
    entities share one canonical node per real concept.
    """
    concept: str = Field(
        description="The concept as it appears in the context, max 3 words"
    )
    canonical: str = Field(
        description=(
            "Canonical/expanded form that this concept collapses into across the "
            "whole corpus: expand acronyms (LLMs -> Large Language Model), pick one "
            "spelling, normalize plural/singular. Use the most common full form."
        )
    )
    type: str = Field(
        description="Semantic type (e.g. 'summarization', 'graph structure', 'language models')"
    )


class RefInsights(BaseModel):
    """Structured output from Qwen for a single reference."""
    concepts: List[ConceptItem] = Field(
        description="Key concepts this citing context highlights, each with its canonical form"
    )
    relations: List[str] = Field(
        description="Short relation phrases between concepts, e.g. 'outperforms', 'extends'"
    )


class CitationDiscoveryResult(BaseModel):
    """Full output of the citation discovery process."""
    entity_labels: List[str]
    relation_labels: List[str]
    per_doc_labels: Dict[str, Tuple[List[str], List[str]]]
    concept_type_map: Dict[str, str]
    bibliography: List[BibliographyEntry]
    insights: Dict[str, RefInsights]
    canonical_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Surface form → canonical form map across all references",
    )


# ---------------------------------------------------------------------------
# Ollama management
# ---------------------------------------------------------------------------

_OLLAMA_PROC = None


def ensure_ollama(base: str = "http://localhost:11434", wait_s: int = 30) -> None:
    """Start Ollama if not already running."""
    global _OLLAMA_PROC
    try:
        requests.get(f"{base}/api/tags", timeout=2).raise_for_status()
        log.info("Ollama already running")
        return
    except requests.ConnectionError:
        pass

    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        raise RuntimeError(
            "Ollama not installed. Get it from https://ollama.com"
        )

    _OLLAMA_PROC = subprocess.Popen(
        [ollama_bin, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + wait_s
    while time.time() < deadline:
        try:
            requests.get(f"{base}/api/tags", timeout=2).raise_for_status()
            log.info("Ollama started (pid %d)", _OLLAMA_PROC.pid)
            return
        except requests.ConnectionError:
            time.sleep(0.5)
    raise RuntimeError(f"Ollama did not respond within {wait_s}s")


def unload_ollama(model: str, base: str = "http://localhost:11434") -> None:
    """Unload a specific model from Ollama VRAM."""
    bare = model.split("/")[-1]
    try:
        requests.post(
            f"{base}/api/generate",
            json={"model": bare, "keep_alive": 0},
            timeout=60,
        )
        log.info("Unloaded %s from Ollama", bare)
    except Exception as e:
        log.warning("Could not unload %s: %s", bare, e)


def shutdown_ollama() -> None:
    """Shut down Ollama if we started it."""
    proc = globals().get("_OLLAMA_PROC")
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
            log.info("Ollama stopped (pid %d)", proc.pid)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            log.warning("Ollama force-killed (pid %d)", proc.pid)


# ---------------------------------------------------------------------------
# Sentence splitting (from notebook exp_04)
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> List[str]:
    """Split text into sentences, handling 'et al.' specially."""
    flat = re.sub(r"^#+\s+.*$", " ", text, flags=re.M)
    flat = flat.replace("et al.", "et al\u00a7")
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\u2018\u201c(\u201c])", flat)
    return [p.replace("et al\u00a7", "et al.").strip() for p in parts if len(p.split()) > 3]


# ---------------------------------------------------------------------------
# Citing context extraction
# ---------------------------------------------------------------------------

def find_citing_contexts(
    seed_body: str,
    entry_by_id: Dict[str, BibliographyEntry],
    ref_ids: List[str],
) -> Dict[str, List[str]]:
    """Find sentences in seed_body that cite each reference (author–year matching).

    Returns dict: arxiv_id → list of citing sentences.
    """
    seed_sents = _split_sentences(seed_body)
    cite_ctx: Dict[str, List[str]] = {}

    for rid in ref_ids:
        entry = entry_by_id.get(rid)
        if entry is None:
            cite_ctx[rid] = []
            continue

        surname = entry.first_author
        year = entry.year

        if surname and year:
            pattern = re.compile(
                rf"\b{re.escape(surname)}\b.*\b{year}\b",
                re.IGNORECASE,
            )
            cite_ctx[rid] = [s for s in seed_sents if pattern.search(s)]
        else:
            cite_ctx[rid] = []

    return cite_ctx


# ---------------------------------------------------------------------------
# Qwen extraction
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = (
    'You analyze how the paper "{seed}" cites the reference "{ref}" '
    '({surname}, {year}).\n\n'
    'Citing context from the seed paper:\n"""\n{context}\n"""\n\n'
    'Reference bibliography entry:\n"""\n{entry}\n"""\n\n'
    'List the key CONCEPTS (max 3 words each) this citing context highlights. '
    'For every concept, ALSO give its CANONICAL form: the preferred, expanded '
    'name it should collapse into across the whole corpus — expand acronyms '
    '(e.g. "LLMs" -> "Large Language Model"), pick a single consistent '
    'spelling/tense, and normalize plural/singular. Each concept gets a '
    'SEMANTIC TYPE (e.g. "summarization", "graph structure", "language '
    'models").\n'
    'Also list the RELATIONS (short verb phrases, max 3 words).\n'
    'Return JSON matching the RefInsights schema (concepts: {{concept, '
    'canonical, type}}[]).\n/no_think'
)


def qwen_insights(
    rid: str,
    seed_title: str,
    entry: BibliographyEntry,
    context: str,
    config: CitationDiscoveryConfig,
) -> RefInsights:
    """Call Qwen to extract concepts/types/relations from a citing context."""
    from litellm import completion

    surname = entry.first_author or "?"
    year = entry.year or "?"

    prompt = PROMPT_TEMPLATE.format(
        seed=seed_title,
        ref=entry.title or entry.raw_text[:60],
        surname=surname,
        year=year,
        context=context[:1500],
        entry=entry.raw_text[:400],
    )

    resp = completion(
        model=config.ollama_model,
        api_base=config.ollama_api_base,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=500,
        timeout=120,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "RefInsights",
                "schema": RefInsights.model_json_schema(),
            },
        },
        keep_alive=config.keep_alive,
    )
    return RefInsights.model_validate_json(resp.choices[0].message.content)


# ---------------------------------------------------------------------------
# Taxonomy aggregation
# ---------------------------------------------------------------------------

def _normalize_label(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def build_canonical_map(insights: Dict[str, RefInsights]) -> Dict[str, str]:
    """Build surface form → canonical form map from Qwen's per-doc concepts.

    Qwen already reports each concept's canonical form during discovery (no
    extra LLM call), so this aggregates them into a single lookup table that
    downstream entity extraction can apply to unify surface variants
    (``llms`` → ``large language model``). Canonical keys map to themselves so
    lookups are idempotent.
    """
    from kgraph.extractors.normalization import canonical

    surface_to_canonical: Dict[str, str] = {}
    for ins in insights.values():
        for item in ins.concepts:
            surface = canonical(item.concept)
            canon = canonical(item.canonical)
            if not surface or not canon:
                continue
            surface_to_canonical[surface] = canon
            surface_to_canonical[canon] = canon
    return surface_to_canonical


def aggregate_taxonomy(
    insights: Dict[str, RefInsights],
    top_concepts: int = 15,
    top_relations: int = 8,
    stopwords: set[str] | None = None,
) -> Tuple[List[str], List[str], Dict[str, str]]:
    """Aggregate Qwen outputs into global entity/relation labels.

    Concepts are grouped by their canonical form (assigned by Qwen during
    discovery), so surface variants like ``LLMs`` and ``Large Language Model``
    collapse into one entity label.

    Returns:
        (entity_labels, relation_labels, concept_type_map)
    """
    if stopwords is None:
        stopwords = set()

    concept_counter: Counter = Counter()
    relation_counter: Counter = Counter()
    type_votes: Dict[str, Counter] = {}

    for ins in insights.values():
        # Group by canonical form; fall back to the raw concept string when
        # canonical is empty.
        for item in ins.concepts:
            canonical_label = _normalize_label(item.canonical or item.concept)
            if not canonical_label or canonical_label in stopwords:
                continue
            concept_counter[canonical_label] += 1
            type_votes.setdefault(canonical_label, Counter()).update([item.type])

        norm_relations = {_normalize_label(r) for r in ins.relations} - stopwords - {""}
        relation_counter.update(norm_relations)

    entity_labels = [c for c, _ in concept_counter.most_common(top_concepts) if c]
    relation_labels = [r for r, _ in relation_counter.most_common(top_relations) if r]

    concept_type_map = {}
    for concept in entity_labels:
        if concept in type_votes:
            concept_type_map[concept] = type_votes[concept].most_common(1)[0][0]

    return entity_labels, relation_labels, concept_type_map


# ---------------------------------------------------------------------------
# Main discovery class
# ---------------------------------------------------------------------------

class CitationDiscovery:
    """Citation-guided discovery engine.

    Uses the seed paper's own citations to define what concepts and relations
    matter in the state of the art, producing a focused GLiNER taxonomy.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.citation_cfg = config.citation
        self.stopwords = get_stopwords(
            source=self.citation_cfg.stopwords_source,
            lang=self.citation_cfg.stopwords_lang,
            extra=self.citation_cfg.stopwords or None,
        )

    def build(
        self,
        seed_doc: RawDocument,
        ref_docs: List[RawDocument],
        bibliography: List[BibliographyEntry],
    ) -> CitationDiscoveryResult:
        """Run citation-guided discovery.

        Args:
            seed_doc: The seed paper (body without references section).
            ref_docs: The resolved reference documents.
            bibliography: Parsed bibliography entries from the seed.

        Returns:
            CitationDiscoveryResult with taxonomy, per-doc labels, and insights.
        """
        seed_title = seed_doc.metadata.get("title", seed_doc.id)
        max_refs = self.citation_cfg.max_refs

        # Build arxiv_id → entry lookup
        entry_by_id: Dict[str, BibliographyEntry] = {}
        for entry in bibliography:
            for aid in entry.arxiv_ids:
                base = re.sub(r"v\d+$", "", aid)
                entry_by_id.setdefault(base, entry)

        # Determine which refs to analyze
        ref_ids = []
        for doc in ref_docs:
            base = re.sub(r"v\d+$", "", doc.id)
            if base in entry_by_id:
                ref_ids.append(base)
        ref_ids = ref_ids[:max_refs]

        # Find citing contexts
        cite_ctx = find_citing_contexts(seed_doc.content, entry_by_id, ref_ids)

        # Qwen extraction per reference
        from tqdm import tqdm
        insights: Dict[str, RefInsights] = {}
        pbar = tqdm(ref_ids, desc="Qwen analysis", unit="ref", leave=False)
        for rid in pbar:
            pbar.set_postfix_str(rid)
            entry = entry_by_id[rid]
            context = "\n".join(cite_ctx.get(rid, [])[:4])
            if not context:
                context = f"The seed paper is: {seed_title}"

            try:
                insights[rid] = qwen_insights(
                    rid, seed_title, entry, context, self.citation_cfg
                )
                log.info("Qwen extracted insights for %s", rid)
            except Exception as e:
                log.warning("Qwen failed for %s: %s", rid, e)
        pbar.close()

        log.info("Qwen analysis: %d/%d references", len(insights), len(ref_ids))

        # Aggregate taxonomy
        entity_labels, relation_labels, concept_type_map = aggregate_taxonomy(
            insights,
            top_concepts=self.citation_cfg.top_concepts,
            top_relations=self.citation_cfg.top_relations,
            stopwords=self.stopwords,
        )

        # Build per-document labels
        per_doc_labels: Dict[str, Tuple[List[str], List[str]]] = {}
        seed_ents: set[str] = set()
        seed_rels: set[str] = set()

        canonical_map = build_canonical_map(insights)

        for rid, ins in insights.items():
            doc_ents = {
                _normalize_label(item.canonical or item.concept)
                for item in ins.concepts
            } - self.stopwords - {""}
            doc_rels = list({_normalize_label(r) for r in ins.relations} - self.stopwords - {""})
            per_doc_labels[rid] = (list(doc_ents) or entity_labels, doc_rels or relation_labels)
            seed_ents.update(doc_ents)
            seed_rels.update(doc_rels)

        # Seed gets the union of all per-doc labels
        seed_ent_list = [e for e in seed_ents if e] or entity_labels
        seed_rel_list = [r for r in seed_rels if r] or relation_labels
        per_doc_labels[seed_doc.id] = (seed_ent_list, seed_rel_list)

        return CitationDiscoveryResult(
            entity_labels=entity_labels,
            relation_labels=relation_labels,
            per_doc_labels=per_doc_labels,
            concept_type_map=concept_type_map,
            bibliography=bibliography,
            insights=insights,
            canonical_map=canonical_map,
        )
