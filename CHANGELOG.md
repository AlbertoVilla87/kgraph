# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- :package: Docker deployment toolchain: backend/frontend Dockerfiles (ML models baked, spaCy excluded), `docker-compose.yml`, nginx server config
- :package: CI/CD via GitHub Actions — `build.yml` (tag → ECR push) and `deploy.yml` (manual → SSM compose up)
- :package: One-time EC2 bootstrap script (`scripts/ec2-provision.sh`)
- :package: Operational deployment runbook (`docs/architecture/deployment.md`)
- :sparkles: Citation-guided discovery: seed paper's citations define the GLiNER taxonomy (exp_04)
- :sparkles: Entity classification: core / seed-only / refs-only originality proxy
- :sparkles: Per-document GLiNER labels via citation context analysis
- :sparkles: Bibliography parser with arXiv/DOI extraction and author–year matching
- :sparkles: Configurable stopwords utility (spaCy-first, graceful fallback)
- :sparkles: `citation-demo` CLI entry point

### Changed

### Fixed

## [1.1.0] - 2026-08-18

### Added

- :sparkles: Seed-paper reference expansion: download a paper, extract its references, analyze them together
- :sparkles: Quick mode (abstracts-only) for ~30s analysis vs ~5min deep mode
- :sparkles: SegmentLabelFilter — cosine similarity filtering reduces GLiNER labels from ~40 to 5-10 per segment (~5x inference speedup)
- :sparkles: Functional graph filter buttons (All / Main Paper / References / Shared)
- :sparkles: Depth mode toggle in frontend (Quick ~30s / Deep ~5min)

### Changed

- :zap: KeyBERT truncation to 250 words (model max_seq_length is 256 tokens)
- :zap: arXiv rate limit reduced from 3s to 0.5s
- :zap: Orphan nodes (no edges) filtered before sending to frontend
- :zap: EntityMerger integration in quick mode merge for near-duplicate detection
- :art: Graph visualization redesign — shared nodes get thicker border + glow, orphan nodes dimmed
- :art: Edge styling — shared edges thicker+colored, unique edges thinner, opacity scales with confidence
- :lipstick: Granular progress detail for seed paper downloads
- :construction_worker: Structured logging across core modules (INFO/WARNING/DEBUG)
- :construction_worker: Root logger configured, uvicorn.access silenced to WARNING
- :construction_worker: Post-analysis memory cleanup (gc.collect, torch.mps.empty_cache)

### Fixed

- :mute: Silence uvicorn access logs (200 OK polling noise)
- :bug: _advance_steps("done") now correctly sets status = "completed"

## [1.0.0] - 2026-08-17

### Highlights

- Full-stack knowledge graph explorer (React + FastAPI + Cytoscape.js)
- Multi-document corpus graph with entity normalization and section-aware segmentation
- LLM-free topic-guided discovery using spaCy dependency relations
- Adaptive KeyBERT with elbow-based keyword count

### Added

- :sparkles: React + TypeScript frontend skeleton (ArXiv Graph Explorer) — #17
- :sparkles: FastAPI backend for frontend integration — #18
- :sparkles: Cytoscape.js knowledge graph visualization — #19
- :sparkles: Connect frontend to real backend with progress tracking — #20
- :sparkles: Multi-doc corpus graph — #14
- :sparkles: Section-aware segmentation to beat 1024-token GLiNER window — #13
- :sparkles: arXiv source retriever with full-text parsing — #12
- :sparkles: Entity normalization, GLiNER label handling and graph viz — #10
- :sparkles: Assembly pipeline: discovery-driven GLiNER taxonomy — #9
- :sparkles: LLM-free topic-guided graph discovery with spaCy dependency relations — #8
- :sparkles: Adaptive KeyBERT with elbow-based keyword count — #6
- :sparkles: Implemented keyBERT — #3
- :sparkles: Explore Qwen vs KeyBERT using GLiner — #4
- :memo: Start documentation — #1

### Changed

- :recycle: Restructure docs, decouple mkdocs env, rebrand to Astrolabe — #15
- :recycle: Reframe project as state-of-the-art explorer — #11
- :recycle: Reorganize project structure — #2
- :wrench: Update PR skill: commit-first, ## headings, gitmoji — #21

### Fixed

- :bug: Fix node labels: fallback to name when label is missing
- :bug: Fix graph data mapping: use correct field names from corpus graph
- :bug: Fix config path: parents[3] = backend/
- :bug: Fix arxiv import: use ArxivSource directly instead of fetch_arxiv
- :bug: Fix circular import: extract shared state to api/state.py
- :bug: Simplify runner: use CorpusGraphBuilder directly

### Docs

- :memo: Corpus pipeline timing report with charts and docs — #16
- :memo: Embed Jupyter notebooks directly in mkdocs (single source of truth)
- :memo: Add preamble markdown cells to experiment and report notebooks
- :memo: Update corpus docs with accurate parallelization model and Mermaid diagram
- :memo: Add root README with banner — #5
- :memo: Add CodeGraph dev tooling and opencode integration docs — #7
- :memo: Add frontend screenshot to docs and README

### Tooling

- :wrench: gitignore .cache/ (mkdocs-jupyter build cache)
