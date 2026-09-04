"""Community detection via Louvain, agnostic of how the graph was built.

This module is deliberately detached from any specific pipeline. It takes any
``networkx`` graph (the citation graph from ``CitationAssembly``, the corpus
graph from ``CorpusGraphBuilder``, a ``GLiNERGraph``, …), converts it to the
undirected single-edge form Louvain expects, runs
``networkx.algorithms.community.louvain_communities``, and annotates each node
in the *original* graph with its community plus per-community metadata.

Weight aggregation
------------------
GLiNER produces a ``MultiDiGraph`` whose parallel edges carry a ``score`` (best
detection confidence) and a ``count`` (how often the relation was observed). To
build a single weighted undirected edge per pair of nodes we sum the product
``score * count`` across every directed parallel edge between them. Using only
``score`` would ignore frequency; using only ``count`` would ignore confidence.
The product balances both: a relation seen many times with high confidence
carries the most weight into the community structure.

Heuristic: edges are bidirectional, so a relation ``A -> B`` and its reverse
``B -> A`` both contribute toward the same undirected pair.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import networkx as nx

log = logging.getLogger(__name__)


def _undirected_weighted(G: nx.Graph) -> Tuple[nx.Graph, Dict]:
    """Build a weighted undirected ``nx.Graph`` from any graph ``G``.

    Parallel directed edges between the same pair of nodes are aggregated into
    a single undirected edge whose ``weight`` is the sum of ``score * count``
    across all of them (respecting direction symmetry). Isolated nodes are
    preserved so they can still be placed in their own community.

    Returns ``(simple, weight_map)`` where ``simple`` is the undirected graph
    and ``weight_map`` maps ``frozenset({u, v})`` → total weight.
    """
    out = nx.Graph()
    out.add_nodes_from(G.nodes())

    pair_weight: Dict[frozenset, float] = defaultdict(float)
    for u, v, data in G.edges(data=True):
        if u == v:
            continue
        score = float(data.get("score", 0.0) or 0.0)
        count = float(data.get("count", 1) or 1)
        pair_weight[frozenset((u, v))] += score * count

    for pair, weight in pair_weight.items():
        a, b = tuple(pair)
        out.add_edge(a, b, weight=weight)

    return out, pair_weight


def detect_communities(
    G: nx.Graph,
    *,
    weight: str = "weight",
    resolution: float = 1.0,
    threshold: float = 1e-07,
    seed: int | None = None,
    min_community_size: int = 1,
) -> Dict[str, int]:
    """Annotate nodes of ``G`` with community membership and return the map.

    Args:
        G: Any NetworkX graph (``DiGraph``/``MultiDiGraph``/``Graph`` allowed).
            Nodes are annotated in place with ``community`` (int) and
            ``community_size`` (int). Edges are annotated in place with
            ``inter_community`` (bool) when both endpoints are present.
        weight: edge attribute used as the Louvain weight on the converted graph.
        resolution: Louvain resolution parameter (higher → more, smaller
            communities).
        threshold: Louvain modularity gain threshold.
        seed: Random seed for deterministic Louvain runs.
        min_community_size: Communities smaller than this (after the first,
            which is allowed to stay small) are relabelled to ``-1``
            (``noise``), so callers can collapse tiny spurious communities.

    Returns:
        A mapping ``node_id -> community`` (int). ``-1`` marks a node that was
        dropped to a noise community by ``min_community_size``.
    """
    simple, _ = _undirected_weighted(G)

    communities = nx.algorithms.community.louvain_communities(
        simple,
        weight=weight,
        resolution=resolution,
        threshold=threshold,
        max_level=None,
        seed=seed,
    )

    # Sort communities by descending size so the index 0 is the largest one.
    communities = sorted(communities, key=len, reverse=True)

    node_to_community: Dict[str, int] = {}
    community_sizes: List[int] = []

    for idx, members in enumerate(communities):
        size = len(members)
        community_sizes.append(size)
        label = idx if size >= min_community_size or idx == 0 else -1
        for node in members:
            node_to_community[node] = label

    _annotate(G, node_to_community, community_sizes)

    return node_to_community


def _annotate(
    G: nx.Graph,
    node_to_community: Dict[str, int],
    community_sizes: List[int],
) -> None:
    """Write community metadata onto nodes and edges of ``G`` in place."""
    for node, community in node_to_community.items():
        if node not in G:
            continue
        data = G.nodes[node]
        data["community"] = community
        data["community_size"] = community_sizes[community] if community >= 0 else 0

    if community_sizes:
        total = sum(community_sizes)
        data = G.graph
        data["num_communities"] = len([s for s in community_sizes if s > 0])
        data["community_sizes"] = community_sizes
        data["community_coverage"] = (
            round((community_sizes[0] / total), 3) if total else 0
        )

    for u, v in G.edges():
        cu = node_to_community.get(u, -1)
        cv = node_to_community.get(v, -1)
        # Parallel edges share the same pair, so the flag is identical for all
        # of them; iterate over the (possibly multiple) edge data dicts.
        for data in G.get_edge_data(u, v).values() if G.is_multigraph() else [G.get_edge_data(u, v)]:
            data["inter_community"] = cu != cv and cu >= 0 and cv >= 0


def summarize_communities(G: nx.Graph, node_to_community: Dict[str, int]) -> dict:
    """Return a compact summary of the detected communities for reporting."""
    by_community: Dict[int, List[str]] = {}
    for node, community in node_to_community.items():
        by_community.setdefault(community, []).append(node)

    sizes = []
    for community, members in sorted(by_community.items(), key=lambda kv: -len(kv[1])):
        if community < 0:
            continue
        top = sorted(
            (
                (G.nodes[m].get("text", m), G.nodes[m].get("score", 0.0))
                for m in members
            ),
            key=lambda t: t[1],
            reverse=True,
        )[:3]
        sizes.append(
            {
                "community": community,
                "size": len(members),
                "top_entities": [t for t, _ in top],
            }
        )

    return {"communities": sizes, "total": len(node_to_community)}
