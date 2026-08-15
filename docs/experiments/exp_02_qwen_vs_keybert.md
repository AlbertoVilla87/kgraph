# Exp 02 — Qwen vs. KeyBERT: which one seeds the graph better?

*Notebook: `backend/experiments/exp_02_qwen_versus_keybert.ipynb`*

An informal comparison of two competing ways to bootstrap a knowledge graph from a single document. Both routes feed the extracted labels to GLiNER as **entity labels**; only the seed route differs.

| Route | Step 1 — topic discovery | Step 2 — graph extraction |
| --- | --- | --- |
| **A** | KeyBERT — fast, local keyword extraction | GLiNER uses the keywords as entity labels |
| **B** | Qwen3 (via LiteLLM, local Ollama) — LLM concept extraction | GLiNER uses the concepts as entity labels |

## Setup

Test subject: `data/case_1/mortgage.txt` — a first-person narrative of a mortgage servicing dispute (≈1.1 KB, rich in domain entities: lenders, servicers, amounts, legal notices).

## What was measured

**Route A (KeyBERT)** — keywords with `use_maxsum=True` (diverse set, not just most frequent):

```
disputed late fee · foreclosure notice · obtained mortgage loan · summit loan servicing · missed payments equifax
```

**Route B (Qwen3)** — structured concepts via a strict Pydantic schema:

```
Loan Agreement and Terms · Credit Reporting · Credit Score · Loan Servicing · Late Fees ·
Foreclosure Notice · Credit Reporting Service · ... · Credit Score Adjustment Request
```

Then each set became the GLiNER entity labels over the same document:

| Metric | Route A (KeyBERT) | Route B (Qwen) |
| --- | --- | --- |
| Unique entities | **12** | **21** |
| Relations | **13** | **15** |

## Discussion & takeaways

1. **GLiNER works in both routes.** The graph machinery (entities + relations) runs identically; only the *seed labels* differ. That's the whole experiment.
2. **KeyBERT stays grounded in the document.** Its keywords are surface-level and precise ("summit loan servicing", "disputed late fee"). The graph it feeds is compact and faithful to the text — but narrow.
3. **Qwen reaches a higher abstraction layer.** Its concepts ("Loan Servicing Dispute", "Credit Score Adjustment") are broader, which makes GLiNER tag more and richer spans → a denser graph (21 vs 12 entities).
4. **This is far from a fair fight — nothing is conclusive yet.**
   - Qwen's number of topics was **not constrained** — it was free to emit as many concepts as it wanted, which naturally inflates the entity count.
   - KeyBERT had **no algorithm yet** to decide the *optimal* number of topics — `use_maxsum` returned 5, but that's a heuristic, not a principled choice.
5. **Tentative direction:** Qwen's ability to produce **more abstract terms** looks genuinely promising — abstraction is exactly what you'd want to *lift* a graph beyond raw surface forms. But the two sides need to be compared on equal footing before any conclusion.

## What it changed in the pipeline

The experiment drove two follow-ups:

- **Adaptive KeyBERT** — the "optimal topic count" problem got a principled answer: the elbow of the similarity scores. → [Discovery](../architecture/discovery.md)
- **Deterministic discovery** — a 0.6b model cannot be trusted to ground evidence or relations, so discovery moved to spaCy dependency parsing (LLM-free). The discovery pipeline answers the follow-up question: can a deterministic dependency parse grow the graph from KeyBERT seeds instead? The initial answer, with the mortgage case, is yes — at the cost of surface-level labels ("obtained from") versus the abstract ones an LLM would invent. → [Discovery](../architecture/discovery.md)

## What to try next

- Cap Qwen's concept count (e.g. `max_concepts` in the schema) to make Route B comparable with Route A.
- Run both routes on a *corpus* (not one doc) and compare graph metrics: coverage, density, and precision of relations.
- Evaluate downstream, not upstream: which graph makes retrieval (`kgraph.retriever`) answer real questions better?
