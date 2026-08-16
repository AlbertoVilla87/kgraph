# Reports

Long-form write-ups that capture decisions, benchmarks, or demo runs. This section is intentionally thin for now — the main pending entry is the **accumulated-graph architecture solution** (see [Roadmap](../roadmap.md)).

## Architecture decision records (ADRs)

When a significant design decision is made (or revisited), record it here following a lightweight ADR format:

```markdown
# ADR-00N: <title>

**Status:** proposed | accepted | superseded by ADR-0XX
**Date:** YYYY-MM-DD

## Context
What problem led to this decision, and what options were considered.

## Decision
What we decided to do.

## Consequences
What becomes easier, harder, or what we now accept as a trade-off.
```

## Candidate reports

| Report | Status |
| --- | --- |
| Accumulated graph architecture (persistence, growth, frequency/confidence aggregation, WL-kernel comparison) | **pending** — the main open piece; see [Roadmap](../roadmap.md) |
| Corpus pipeline timing (5 arXiv PDFs) | [notebook](corpus_timing.ipynb) |
| Originality / gap-signal benchmark | blocked on the accumulated graph |

## Existing decisions worth documenting

- Discovery is deterministic and LLM-free because a 0.6b model hallucinated evidence — see [Exp 02](../experiments/exp_02_qwen_versus_keybert.ipynb) and [Discovery](../architecture/discovery.md).
- Segmentation keeps a structured `DoclingDocument` through the pipeline to enable section-aware chunking — see [Segmentation](../architecture/segmentation.md).
- Cross-document novelty is currently lexical (canonical/containment merging) — see [Corpus](../architecture/corpus.md).
