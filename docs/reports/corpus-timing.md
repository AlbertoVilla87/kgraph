# Corpus Pipeline Timing Report

This report documents the wall-clock time of each phase in the multi-document corpus pipeline, run on the default arXiv corpus (5 PDFs from `data/arxiv_pdfs/`).

**Date:** 2025-07-13
**Environment:** macOS 15.5, Apple M1 Pro, 16 GB RAM
**Code version:** `e7f9ed0` (branch `ft/multi_doc_comparison`)
**Pipeline config:** `configs/params.yaml` (default)

## Pipeline phases

| Phase | Time (s) | Share |
|-------|----------|-------|
| **Extraction** (GLiNER, 5 workers) | 151.2 | 71.8% |
| **Taxonomy** (KeyBERT + spaCy BFS) | 38.7 | 18.4% |
| **Fetch & parse** (docling) | 20.6 | 9.8% |
| **Segmentation** | 0.18 | 0.1% |
| Merge + Summarize + Export | 0.03 | <0.1% |
| **Pipeline total** | **210.7** | 100% |

Model load time (GLiNER relex-large + all-MiniLM): **7.1s**

## Per-document breakdown

| Document | Chars | Segments | Taxonomy (s) | Extraction (s) | Entities | Relations |
|----------|-------|----------|--------------|----------------|----------|-----------|
| 2308.13916v5 | 29,455 | 10 | 6.1 | 33.5 | 645 | 36 |
| 2404.17000v1 | 29,467 | 11 | 8.1 | 10.8 | 577 | 115 |
| 2408.02377v1 | 23,775 | 8 | 5.1 | 8.9 | 264 | 184 |
| 2408.13521v1 | 27,591 | 7 | 6.5 | 19.8 | 473 | 71 |
| 2604.04450v1 | 75,444 | 23 | 12.8 | 78.3 | 692 | 6 |

## Corpus graph summary

- **Total nodes:** 1,349 (common: 50, unique: 1,299)
- **Total edges:** 176 (common: 22, unique: 154)
- **Per-document novelty:** 87–90% (most nodes are document-unique)

## Key observations

1. **Extraction dominates** at ~72% of pipeline time. GLiNER inference on 59 segments with 5 parallel workers is the bottleneck. Larger documents (e.g., 2604.04450v1 with 23 segments) take proportionally longer.

2. **Taxonomy is the second cost** at ~18%. KeyBERT keyword extraction and spaCy dependency parsing run sequentially per document, so scaling to many documents will increase this linearly.

3. **Fetch/parse (docling)** is ~10% of the pipeline. Docling's layout detection (RT-DETR) and table structure recognition (TableFormer) dominate this phase.

4. **Segmentation and merge are negligible** — the chunking algorithm and graph merge are both O(n) in segment/document count.

5. **Novelty is high** (87–90%) across all documents, meaning most extracted knowledge is unique to each paper. This is expected for diverse arXiv papers on related but distinct topics.

## How to reproduce

```bash
cd backend
uv run jupyter notebook reports/corpus_timing.ipynb
```

Or from the CLI (partial timing):

```bash
uv run corpus-demo --verbose
```

!!! note
    The notebook provides more granular timing (per-document taxonomy, segmentation, and extraction) compared to the CLI's aggregated output.
