import argparse
import json
from pathlib import Path

VIS_NETWORK_CDN = "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knowledge Graph</title>
<script src="{cdn}"></script>
<style>
  html, body { margin: 0; height: 100%; font-family: system-ui, sans-serif; }
  #graph { width: 100%; height: 100vh; }
  #legend {
    position: fixed; top: 12px; right: 12px; z-index: 10;
    background: rgba(255, 255, 255, 0.95); border: 1px solid #ddd;
    border-radius: 8px; padding: 10px 12px; font-size: 12px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15); max-height: 90vh; overflow: auto;
  }
  #legend h3 { margin: 0 0 8px; font-size: 13px; }
  #legend .row { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
  #legend .swatch { width: 12px; height: 12px; border-radius: 3px; flex: 0 0 auto; }
  #legend .type { font-weight: 600; }
  #legend .count { color: #666; margin-left: auto; }
</style>
</head>
<body>
<div id="graph"></div>
<div id="legend"></div>
<script>
const GRAPH = {graph_json};

const palette = [
  "#e74c3c", "#f39c12", "#27ae60", "#2980b9", "#8e44ad",
  "#16a085", "#d35400", "#c0392b", "#2c3e50", "#7f8c8d",
  "#1abc9c", "#f1c40f", "#9b59b6", "#3498db", "#e67e22",
];

const types = [...new Set(GRAPH.nodes.map(n => n.entity_type || "unknown"))];
const colorOf = {};
types.forEach((t, i) => { colorOf[t] = palette[i % palette.length]; });

const legendEl = document.getElementById("legend");
const typeCount = {};
GRAPH.nodes.forEach(n => { typeCount[n.entity_type || "unknown"] = (typeCount[n.entity_type || "unknown"] || 0) + 1; });
legendEl.innerHTML =
  "<h3>Legend</h3>" +
  types.map(t =>
    `<div class="row"><span class="swatch" style="background:${colorOf[t]}"></span>` +
    `<span class="type">${t}</span><span class="count">${typeCount[t]}</span></div>`
  ).join("");

const maxScore = Math.max(...GRAPH.edges.map(e => e.score || 0), 0.01);

const nodes = GRAPH.nodes.map(n => ({
  id: n.id,
  label: n.text,
  title:
    `<b>${n.text}</b><br>type: ${n.entity_type || "unknown"}<br>` +
    `score: ${(n.score || 0).toFixed(3)}<br>mentions: ${(n.mentions || []).length}`,
  color: { background: colorOf[n.entity_type || "unknown"], border: "#333" },
  font: { color: "#111", size: 14 },
  shadow: true,
}));

const edges = GRAPH.edges.map(e => {
  const score = e.score || 0;
  return {
    from: e.source,
    to: e.target,
    label: `${e.relation_type}`,
    arrows: "to",
    width: 1 + 3 * (score / maxScore),
    color: { color: "#555", opacity: 0.5 + 0.5 * (score / maxScore) },
    font: { size: 11, color: "#444", strokeWidth: 3, strokeColor: "#fff" },
    title:
      `<b>${e.relation_type}</b><br>` +
      `score: ${score.toFixed(3)}<br>count: ${e.count || 1}`,
  };
});

new vis.Network(document.getElementById("graph"), {
  nodes: new vis.DataSet(nodes),
  edges: new vis.DataSet(edges),
}, {
  nodes: {
    shape: "dot",
    size: 18,
    borderWidth: 2,
  },
  edges: { smooth: { type: "dynamic" } },
  physics: {
    solver: "forceAtlas2Based",
    forceAtlas2Based: {
      gravitationalConstant: -40,
      centralGravity: 0.008,
      springLength: 120,
      springConstant: 0.05,
      damping: 0.4,
    },
    stabilization: { iterations: 300 },
  },
  interaction: { hover: true, tooltipDelay: 120, navigationButtons: true, keyboard: true },
});
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a graph JSON as a standalone HTML visualization."
    )
    parser.add_argument("input", help="Path to the graph JSON (from citation-demo --output).")
    parser.add_argument(
        "--output",
        default=None,
        help="Output HTML path (default: <input>.html next to the input).",
    )
    args = parser.parse_args()

    with open(args.input) as f:
        graph = json.load(f)

    output = Path(args.output or (args.input + ".html"))
    html = (
        HTML_TEMPLATE.replace("{cdn}", VIS_NETWORK_CDN)
        .replace("{graph_json}", json.dumps(graph))
    )
    output.write_text(html)
    print(f"Visualization written to {output}")


if __name__ == "__main__":
    main()
