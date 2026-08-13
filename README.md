<p align="center">
  <img src="assets/icon.png" alt="kgraph">
</p>

## The problem

Content on a given topic (RAG, prompt engineering, agents, etc.) piles up fast, and most of it says the same thing in different words. Judging "originality" by reading text or asking an LLM to compare two posts doesn't scale and doesn't accumulate: an LLM has no persistent memory of everything published on a topic, and lexical similarity misses cases where the *wording* is new but the *idea* isn't — or the reverse, where the wording is generic but the combination of ideas genuinely is new.

## The idea

Represent each piece of content (paper, post, article) as a small knowledge graph of concepts and how they relate, then compare it against an accumulated graph for that topic built from everything processed so far.

```
new post/paper → concept extraction → relation extraction → mini knowledge graph
                                                                      │
                                                                      ▼
                                              compare against accumulated topic graph
                                                                      │
                                                                      ▼
                                                          originality signal
```

### What "not new" looks like

| Case | Node (concept) | Edge (relation) | Interpretation |
|---|---|---|---|
| Pure repetition | exists | exists | Recycled content, reworded |
| Novel combination | exists | new | Known ideas connected in a new way — often the most genuinely original case |
| New concept | new | — | Either real innovation, or invented jargon dressed up as novelty |

The "café recalentado" case — a LinkedIn post using different vocabulary to say something that's been said 50 times — shows up as **high structural similarity** (graph/WL-kernel level) even when **lexical similarity is low** (plain text embeddings). That's the gap this approach is meant to close: plain-text comparison alone misses it.

## Pipeline

**Concept (entity) extraction**
- Adaptive KeyBERT → candidate topic seeds per document (adaptive count via score elbow)
- Topic-guided expansion (spaCy dependency parsing, LLM-free) → grows the seeds into a graph of topics and relations
- GLiNER → zero-shot entity + relation extraction using exactly those discovered topics/relations as labels (underscore-joined), with confidence scores
- Entity normalization & merging (`normalization.py`) collapses near-duplicates (`canonical`, token containment) before the final graph

**Relation extraction**
- spaCy dependency parsing (verb lemma + preposition, e.g. `obtained from`) → candidate relation phrases
- Kept only when an endpoint touches a known topic; new endpoints become topics to expand, up to `max_depth`
- GLiNER extracts the final relations between the extracted entities using the discovered relation labels, with confidence scores

**Graph comparison** (planned)
- Weisfeiler-Lehman (WL) kernel, structural invariants, and/or semantic embedding similarity to score how much a new mini-graph diverges structurally from the accumulated topic graph
- New nodes / new edges relative to the accumulated graph become the raw originality signal

## Constraints / design choices

- No paid per-token LLM APIs in the pipeline; local/open models only (GLiNER — Apache 2.0; spaCy — MIT)
- Labels (both entity and relation types) are discovered from the data via deterministic dependency parsing, not hand-defined
- Discovery is deterministic and LLM-free (a small local model hallucinated evidence, so it was dropped from discovery)
- One accumulated graph per topic, growing over time as new content is processed — the comparison only gets more meaningful as the corpus grows

## Status

Implemented: Adaptive KeyBERT seeding, LLM-free topic-guided discovery (spaCy), and the discovery-driven GLiNER assembly that builds the final knowledge graph. Current default corpus: `backend/data/case_2/medium.txt`.

Still open:
- **GLiNER context truncation**: documents longer than ~1024 tokens are truncated; chunking the document before extraction is the planned fix.
- **Source feed**: where does new content come from — arXiv, RSS, manual upload, scraping Medium/LinkedIn? Not solved yet.
- **Granularity**: too fine-grained and everything looks "new"; too coarse and nothing ever registers as novel. Will likely need iteration once there's real data flowing through.
- **Scope of the accumulated graph**: per topic, per author, or both? An originality score per author (% of their output that maps to already-seen nodes/edges) is an interesting downstream product on top of the same graph.
- **Graph comparison (originality signal)**: the WL-kernel / embedding comparison against an accumulated topic graph is designed but not yet implemented.

The extraction pipeline reuses techniques prototyped in a separate insurance-claims knowledge graph project, applied here to a different domain.
