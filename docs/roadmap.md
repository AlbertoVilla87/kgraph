# Roadmap

The assembled pipeline is the extraction core of a larger goal: a **state-of-the-art explorer** for any research topic. This page tracks what is implemented and what is still designed-but-not-built.

## Implemented

| Feature | Where |
| --- | --- |
| Local + arXiv ingestion | [Ingestion](architecture/ingestion.md) — `LocalFileSource`, `ArxivSource` (abstracts, PDF download, docling full text) |
| Adaptive KeyBERT seeding | [Discovery](architecture/discovery.md) |
| LLM-free topic-guided discovery (spaCy) | [Discovery](architecture/discovery.md) |
| Discovery-driven GLiNER assembly | [Assembly](architecture/assembly.md) |
| Section-aware segmentation | [Segmentation](architecture/segmentation.md) |
| Multi-document corpus graph + originality view | [Corpus](architecture/corpus.md) |

## Pending

### Sources (arXiv implemented, IEEE planned)

A topic query harvests documents from IEEE and similar sources in addition to arXiv. The harvested corpus defines the "state of the art" window for that topic. IEEE plugs in as another `DataSource` implementation without touching the extraction pipeline.

### Accumulated topic graph

Today each `assembly-demo` run builds a fresh graph from one corpus. The target is an **accumulated graph per topic** that persists and grows as documents are added — nodes and edges carry frequency and confidence, so the map of the field only gets more precise over time. This is the architecture solution still pending.

### Originality signal

A new paper or idea, run through the same pipeline, is compared against the accumulated topic graph (WL-kernel, structural invariants, embeddings). Novel nodes, novel edges, and novel **combinations** of known nodes stand out structurally even when the wording overlaps with prior work.

### Gap discovery

Concepts and relations that are rare or absent in the accumulated graph are candidate **unexplored directions** — the tool becomes inspiration rather than just a search index.

### GLiNER idea check

Because GLiNER is zero-shot, **any idea the user thinks of becomes a label**. The tool can then ask the corpus directly: does this idea appear in any document, and how is it connected? That is a live originality check against the state of the art — the answer is grounded in the accumulated graph, not in an LLM's guess.

## Open design questions

- **Granularity**: too fine-grained and everything looks "new"; too coarse and nothing ever registers as novel. Will likely need iteration once there's real data flowing through.
- **Scope of the accumulated graph**: per topic, per author, or both? An originality score per author (% of their output that maps to already-seen nodes/edges) is an interesting downstream product on top of the same graph.
