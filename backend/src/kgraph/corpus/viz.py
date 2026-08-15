"""Interactive HTML visualization of a cross-document corpus graph.

Reuses the vis-network setup from ``kgraph.cli.graph_viz`` but colors nodes and
edges by origin instead of by entity type:

- **common** (present in >= 2 documents) renders in green;
- **unique** to a single document renders in that document's palette color.

A legend, a summary panel (totals, common/unique counts, per-document novelty)
and a per-document filter are overlaid on the graph.
"""

import json
from pathlib import Path

VIS_NETWORK_CDN = "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corpus Knowledge Graph</title>
<script src="{cdn}"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: system-ui, sans-serif; }}
  #graph {{ width: 100%; height: 100vh; }}
  .panel {{
    position: fixed; top: 12px; z-index: 10; font-size: 12px;
    background: rgba(255, 255, 255, 0.96); border: 1px solid #ddd;
    border-radius: 8px; padding: 10px 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  }}
  #summary {{ left: 12px; max-width: 300px; }}
  #legend {{ right: 12px; max-height: 90vh; overflow: auto; }}
  .panel h3 {{ margin: 0 0 8px; font-size: 13px; }}
  .row {{ display: flex; align-items: center; gap: 6px; margin: 3px 0; }}
  .swatch {{ width: 12px; height: 12px; border-radius: 3px; flex: 0 0 auto; }}
  .count {{ color: #666; margin-left: auto; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 4px; }}
  th, td {{ text-align: left; padding: 2px 6px; border-bottom: 1px solid #eee; }}
  th {{ font-weight: 600; }}
  select {{ margin-top: 6px; width: 100%; padding: 3px; }}
</style>
</head>
<body>
<div id="graph"></div>
<div id="summary" class="panel"></div>
<div id="legend" class="panel"></div>
<script>
const GRAPH = {graph_json};
const S = GRAPH.summary;
const palette = [
  "#e74c3c", "#f39c12", "#2980b9", "#8e44ad", "#16a085",
  "#d35400", "#c0392b", "#1abc9c", "#9b59b6", "#3498db",
];
const COMMON_COLOR = "#27ae60";
const docIds = S.documents;
const docColor = {};
docIds.forEach((d, i) => {{ docColor[d] = palette[i % palette.length]; }});

const docCount = {{}};
GRAPH.nodes.forEach(n => {{ const d = n.docs[0]; if (!n.unique && d) return; docCount[d] = (docCount[d] || 0) + 1; }});

const legendEl = document.getElementById("legend");
legendEl.innerHTML =
  "<h3>Legend</h3>" +
  "<div class='row'><span class='swatch' style='background:" + COMMON_COLOR + "'></span>" +
  "<span>common (in ≥2 docs)</span><span class='count'>" + S.common_nodes + "</span></div>" +
  docIds.map(d =>
    "<div class='row'><span class='swatch' style='background:" + docColor[d] + "'></span>" +
    "<span>unique · " + d + "</span><span class='count'>" + (S.per_document[d].unique_nodes) + "</span></div>"
  ).join("") +
  "<h3 style='margin-top:10px'>Filter</h3>" +
  "<select id='filter'><option value='__all__'>All documents</option>" +
  docIds.map(d => "<option value='" + d + "'>" + d + "</option>").join("") +
  "</select>";

const sumEl = document.getElementById("summary");
sumEl.innerHTML =
  "<h3>Summary</h3>" +
  "<div class='row'><span>Nodes</span><span class='count'>" + S.total_nodes + " (common " + S.common_nodes + " · unique " + S.unique_nodes + ")</span></div>" +
  "<div class='row'><span>Edges</span><span class='count'>" + S.total_edges + " (common " + S.common_edges + " · unique " + S.unique_edges + ")</span></div>" +
  "<table><tr><th>Document</th><th>nodes</th><th>unique</th><th>novelty</th></tr>" +
  docIds.map(d => {{
    const p = S.per_document[d];
    return "<tr><td>" + d + "</td><td>" + p.nodes_in_doc + "</td><td>" + p.unique_nodes + "</td><td>" + (p.novelty * 100).toFixed(0) + "%</td></tr>";
  }}).join("") +
  "</table>";

function nodeStatus(n) {{ return n.unique ? "unique" : "common"; }}
function nodeColor(n) {{ return n.unique ? docColor[n.docs[0]] : COMMON_COLOR; }}

const maxScore = Math.max(...GRAPH.edges.map(e => e.score || 0), 0.01);

const edgeNodeIds = new Set();
GRAPH.edges.forEach(e => {{ edgeNodeIds.add(e.source); edgeNodeIds.add(e.target); }});

const nodes = GRAPH.nodes.filter(n => edgeNodeIds.has(n.id)).map(n => ({{
  id: n.id,
  label: n.text,
  title:
    "<b>" + n.text + "</b><br>type: " + n.entity_type + "<br>" +
    "status: " + (n.unique ? "unique to " + n.docs[0] : "common in " + n.docs.length + " docs") + "<br>" +
    "docs: " + n.docs.join(", ") + "<br>" +
    "mentions: " + (n.mentions || []).length + "<br>" +
    "score: " + (n.score || 0).toFixed(3),
  color: {{ background: nodeColor(n), border: "#333" }},
  font: {{ color: "#111", size: 14 }},
  shadow: true,
}}));

const edges = GRAPH.edges.map(e => {{
  const score = e.score || 0;
  const color = e.unique ? docColor[e.docs[0]] : COMMON_COLOR;
  return {{
    from: e.source,
    to: e.target,
    label: e.relation_type,
    arrows: "to",
    width: 1 + 3 * (score / maxScore),
    color: {{ color: color, opacity: 0.35 + 0.65 * (score / maxScore) }},
    font: {{ size: 11, color: "#444", strokeWidth: 3, strokeColor: "#fff" }},
    title:
      "<b>" + e.relation_type + "</b><br>" +
      "status: " + (e.unique ? "unique to " + e.docs[0] : "common in " + e.docs.length + " docs") + "<br>" +
      "docs: " + e.docs.join(", ") + "<br>" +
      "score: " + score.toFixed(3) + "<br>count: " + (e.count || 1),
  }};
}});

const nodesDataSet = new vis.DataSet(nodes);
const edgesDataSet = new vis.DataSet(edges);

const network = new vis.Network(
  document.getElementById("graph"),
  {{ nodes: nodesDataSet, edges: edgesDataSet }},
  {{
    nodes: {{ shape: "dot", size: 18, borderWidth: 2 }},
    edges: {{ smooth: {{ type: "dynamic" }} }},
    physics: {{
      solver: "forceAtlas2Based",
      forceAtlas2Based: {{
        gravitationalConstant: -40, centralGravity: 0.008,
        springLength: 120, springConstant: 0.05, damping: 0.4,
      }},
      stabilization: {{ iterations: 300 }},
    }},
    interaction: {{ hover: true, tooltipDelay: 120, navigationButtons: true, keyboard: true }},
  }}
);

document.getElementById("filter").addEventListener("change", (ev) => {{
  const doc = ev.target.value;
  if (doc === "__all__") {{
    nodesDataSet.forEach((n) => nodesDataSet.update([{{ id: n.id, hidden: false }}]));
    edgesDataSet.forEach((e) => edgesDataSet.update([{{ id: e.id, hidden: false }}]));
    return;
  }}
  nodesDataSet.forEach((n) => {{
    const keep = !n.unique || (n.docs || []).includes(doc);
    nodesDataSet.update([{{ id: n.id, hidden: !keep }}]);
  }});
  edgesDataSet.forEach((e) => {{
    const src = nodesDataSet.get(e.from);
    const tgt = nodesDataSet.get(e.to);
    const keep = src && tgt && !src.hidden && !tgt.hidden;
    edgesDataSet.update([{{ id: e.id, hidden: !keep }}]);
  }});
}});
</script>
</body>
</html>
"""


def render_corpus_html(data: dict, output: str) -> None:
    """Write ``data`` (as produced by ``export_corpus_json``) to an HTML file."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = (
        HTML_TEMPLATE.replace("{{", "{")
        .replace("}}", "}")
        .replace("{cdn}", VIS_NETWORK_CDN)
        .replace("{graph_json}", json.dumps(data))
    )
    path.write_text(html)
