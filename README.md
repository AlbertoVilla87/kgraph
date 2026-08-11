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
- KeyBERT → candidate key terms per document
- BERTopic (embeddings + UMAP + HDBSCAN + KeyBERTInspired/c-TF-IDF) → clusters candidate terms into emergent topic labels
- GLiNER → zero-shot entity extraction using those discovered labels, with confidence scores

**Relation extraction**
- spaCy dependency parsing (shortest syntactic path between entity pairs) → candidate relation phrases
- Same BERTopic clustering step → emergent relation labels
- GLiREL → zero-shot relation extraction between GLiNER's entities, using those discovered labels, with confidence scores

**Graph comparison**
- Weisfeiler-Lehman (WL) kernel, structural invariants, and/or semantic embedding similarity to score how much a new mini-graph diverges structurally from the accumulated topic graph
- New nodes / new edges relative to the accumulated graph become the raw originality signal

## Constraints / design choices

- No paid per-token LLM APIs in the pipeline; local/open models only (GLiNER, GLiREL — Apache 2.0; spaCy — MIT)
- Labels (both entity and relation types) are discovered from the data via clustering, not hand-defined
- One accumulated graph per topic, growing over time as new content is processed — the comparison only gets more meaningful as the corpus grows

## Open questions

- **Source feed**: where does new content come from — arXiv, RSS, manual upload, scraping Medium/LinkedIn? Not solved yet.
- **Granularity**: too fine-grained and everything looks "new"; too coarse and nothing ever registers as novel. Will likely need iteration once there's real data flowing through.
- **Scope of the accumulated graph**: per topic, per author, or both? An originality score per author (% of their output that maps to already-seen nodes/edges) is an interesting downstream product on top of the same graph.

## Status

Early-stage idea, not yet implemented. Design largely reuses techniques already prototyped in a separate insurance-claims knowledge graph project (same extraction pipeline, same graph-comparison techniques), applied here to a different domain.
