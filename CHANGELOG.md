# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

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
