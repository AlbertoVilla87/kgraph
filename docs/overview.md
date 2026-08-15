# Overview

## The problem

Knowing the *state of the art* of any topic is hard. Research piles up fast (arXiv, IEEE, RSS feeds...) and most papers say the same thing in different words. Reading it all — or asking an LLM to summarize it — doesn't scale and doesn't accumulate: an LLM has no persistent memory of everything published on a topic, and lexical similarity misses cases where the *wording* is new but the *idea* isn't — or the reverse, where the wording is generic but the combination of ideas genuinely is new. On top of that, researchers need to spot what has **not** been done yet: the gaps worth exploring.

## The idea

<table>
<tr>
<td width="70%">

Build an **accumulated knowledge graph per topic** from the actual research sources (arXiv, IEEE), and use it to answer three questions:

1. **What is the state of the art?** — the structure of the topic graph (the concepts and how they relate, their confidence and frequency) is a map of the field as it stands today.
2. **What is original?** — a new paper, post, or idea is compared against the accumulated topic graph: novel nodes, novel edges, and novel combinations stand out structurally even when the wording is similar to prior work.
3. **What is missing?** — the graph exposes **gaps**: concepts and relations that are rare or absent, which become inspiration for unexplored directions.

</td>
<td width="30%" align="center">

<img src="assets/icon.png" alt="kgraph" width="300">

</td>
</tr>
</table>

```
topic search (arXiv/IEEE) → concept extraction → relation extraction → accumulated topic graph
                                                                        │
                            ┌───────────────────────────────────────────┤
                            │                                           │
                  new paper/idea                             user idea as a GLiNER label
                            │                                           │
                            ▼                                           ▼
                 compare against                             does that label appear
                 accumulated topic graph                     in any document? (GLiNER)
                            │                                           │
                            ▼                                           ▼
                 originality signal                     originality / state-of-the-art pattern
```

The user-facing loop is powerful and cheap: because GLiNER is zero-shot, **any topic that occurs to the user becomes a label** and we can ask directly "does this idea appear in any document of the corpus, and how is it connected?" — a live originality check against the state of the art, plus the graph shows which related ideas exist around it.

## What "not new" looks like

| Case | Node (concept) | Edge (relation) | Interpretation |
|---|---|---|---|
| Pure repetition | exists | exists | Recycled content, reworded |
| Novel combination | exists | new | Known ideas connected in a new way — often the most genuinely original case |
| New concept | new | — | Either real innovation, or invented jargon dressed up as novelty |

The "café recalentado" case — a post using different vocabulary to say something that's been said 50 times — shows up as **high structural similarity** (graph/WL-kernel level) even when **lexical similarity is low** (plain text embeddings). That's the gap this approach is meant to close: plain-text comparison alone misses it.

## Multi-document view of a corpus

`uv run corpus-demo` in `backend/` builds a cross-document graph: every node/edge is labeled **common** (present in ≥2 documents, green) or **unique** to one document (originality view):

![Multi-document corpus graph](assets/multi_graph.jpg)

## Constraints / design choices

- No paid per-token LLM APIs in the pipeline; local/open models only (GLiNER — Apache 2.0; spaCy — MIT)
- Labels (both entity and relation types) are discovered from the data via deterministic dependency parsing, not hand-defined
- Discovery is deterministic and LLM-free (a small local model hallucinated evidence, so it was dropped from discovery)
- One accumulated graph per topic, growing over time as new content is processed — the comparison only gets more meaningful as the corpus grows

## Continue reading

- [Quickstart](quickstart.md) — install and run the pipeline on a document
- [Architecture](architecture/index.md) — how the pipeline works, stage by stage
- [Roadmap](roadmap.md) — what is implemented and what is still pending
