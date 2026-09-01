"""Shared state for the analysis API."""

analyses: dict[str, dict] = {}

# Per-analysis chunk data: analysis_id -> {"segments": {doc_id: [chunk]},
# "node_mentions": {node_id: [mention]}}. Populated by the runner once the
# graph is assembled and consumed lazily by the chunks endpoint.
analysis_chunks: dict[str, dict] = {}
