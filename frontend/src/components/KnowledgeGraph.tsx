import { useEffect, useRef, useMemo, useCallback, useState } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from 'lucide-react';

export interface GraphNode {
  id: string;
  label: string;
  name?: string;
  source: 'main' | 'reference' | 'shared' | 'core' | 'seed-only' | 'refs-only';
  importance: number;
  type: string;
  documents?: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  confidence: number;
  documents?: string[];
}

export type NodeFilter = 'all' | 'main' | 'reference' | 'shared' | 'core' | 'seed-only' | 'refs-only';

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
  height?: number;
  fill?: boolean;
  filter?: NodeFilter;
}

const DOC_COLORS = [
  '#a78bfa', // violet
  '#5b8cff', // cobalt
  '#f5b759', // amber
  '#fb7185', // red
  '#34d399', // emerald
  '#fb923c', // orange
  '#2dd4bf', // teal
  '#f472b6', // pink
];

const DOC_COLOR_GRADIENT = `conic-gradient(${DOC_COLORS.join(', ')}, ${DOC_COLORS[0]})`;

const SHARED_COLOR = '#f8fafc';
const SHARED_EDGE_COLOR = '#35d6c1';
const EDGE_COLOR = '#3f4c5f';
const NODE_OUTLINE = '#0b1120';
const LABEL_COLOR = '#c9d4e3';
const ORPHAN_OPACITY = 0.28;

function computeOrphanSet(nodes: GraphNode[], edges: GraphEdge[]): Set<string> {
  const connected = new Set<string>();
  edges.forEach((e) => {
    connected.add(e.source);
    connected.add(e.target);
  });
  return new Set(nodes.filter((n) => !connected.has(n.id)).map((n) => n.id));
}

export default function KnowledgeGraph({
  nodes,
  edges,
  onNodeClick,
  onEdgeClick,
  height = 500,
  fill = false,
  filter = 'all',
}: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [cyReady, setCyReady] = useState(false);

  const docColorMap = useMemo(() => {
    const allDocIds = new Set<string>();
    nodes.forEach((n) => n.documents?.forEach((d) => allDocIds.add(d)));
    const sorted = Array.from(allDocIds).sort();
    const map: Record<string, string | undefined> = {};
    sorted.forEach((docId, i) => {
      map[docId] = DOC_COLORS[i % DOC_COLORS.length];
    });
    return map;
  }, [nodes]);

  const orphanIds = useMemo(() => computeOrphanSet(nodes, edges), [nodes, edges]);

  const getNodeColor = useCallback(
    (node: GraphNode): string => {
      const docs = node.documents || [];
      if (docs.length > 1) return SHARED_COLOR;
      if (docs.length === 1 && docColorMap[docs[0]!]) return docColorMap[docs[0]!]!;
      return '#5a6b80';
    },
    [docColorMap],
  );

  const getEdgeColor = useCallback((edge: GraphEdge): string => {
    const docs = edge.documents || [];
    if (docs.length > 1) return SHARED_EDGE_COLOR;
    return EDGE_COLOR;
  }, []);

  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements = [
      ...nodes.map((n) => {
        const isOrphan = orphanIds.has(n.id);
        return {
          data: {
            id: n.id,
            label: n.label || n.name || n.id,
            source: n.source,
            importance: n.importance,
            type: n.type,
            docColor: getNodeColor(n),
            isOrphan: isOrphan,
            docCount: (n.documents || []).length,
          },
        };
      }),
      ...edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          relation: e.relation,
          confidence: e.confidence,
          docCount: (e.documents || []).length,
          edgeColor: getEdgeColor(e),
        },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        // --- Shared nodes: thick border + halo ---
        {
          selector: 'node[docCount > 1]',
          style: {
            'border-width': 3,
            'border-color': 'data(docColor)',
            'border-style': 'solid',
            'background-color': 'data(docColor)',
            'background-opacity': 0.92,
            'overlay-padding': '8px',
            'overlay-opacity': 0.18,
            'overlay-color': 'data(docColor)',
          },
        },
        // --- Unique single-doc nodes ---
        {
          selector: 'node[docCount = 1]',
          style: {
            'border-width': 2,
            'border-color': 'data(docColor)',
            'background-color': 'data(docColor)',
            'background-opacity': 0.88,
          },
        },
        // --- Orphan nodes: dimmed ---
        {
          selector: 'node[?isOrphan]',
          style: {
            opacity: ORPHAN_OPACITY,
            'border-width': 1,
            'border-style': 'dashed',
          },
        },
        // --- Base node style ---
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            color: LABEL_COLOR,
            'font-size': '11px',
            'font-weight': '500' as cytoscape.Css.FontWeight,
            width: (ele: cytoscape.NodeSingular) => {
              const base = 18 + ele.data('importance') * 3.5;
              return ele.data('docCount') > 1 ? base * 1.15 : base;
            },
            height: (ele: cytoscape.NodeSingular) => {
              const base = 18 + ele.data('importance') * 3.5;
              return ele.data('docCount') > 1 ? base * 1.15 : base;
            },
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'text-outline-color': NODE_OUTLINE,
            'text-outline-width': 3,
          },
        },
        // --- Shared edges: thicker + phosphor ---
        {
          selector: 'edge[docCount > 1]',
          style: {
            width: (ele: cytoscape.EdgeSingular) => 2 + ele.data('confidence') * 2,
            'line-color': SHARED_EDGE_COLOR,
            'target-arrow-color': SHARED_EDGE_COLOR,
            'line-opacity': (ele: cytoscape.EdgeSingular) => 0.55 + ele.data('confidence') * 0.45,
          },
        },
        // --- Unique edges: thinner ---
        {
          selector: 'edge[docCount = 1]',
          style: {
            width: (ele: cytoscape.EdgeSingular) => 1 + ele.data('confidence') * 1.5,
            'line-color': EDGE_COLOR,
            'target-arrow-color': EDGE_COLOR,
            'line-opacity': (ele: cytoscape.EdgeSingular) => 0.35 + ele.data('confidence') * 0.4,
          },
        },
        // --- Base edge style ---
        {
          selector: 'edge',
          style: {
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(relation)',
            'font-size': '9px',
            color: '#62748c',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
            'text-outline-color': NODE_OUTLINE,
            'text-outline-width': 2,
          },
        },
        // --- Selected node ---
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#f5b759',
            'background-color': 'data(docColor)',
            opacity: 1,
          },
        },
      ],
      layout: {
        name: 'cose',
        idealEdgeLength: 120,
        nodeOverlap: 30,
        refresh: 20,
        randomize: false,
        componentSpacing: 60,
        nodeRepulsion: 8000,
        edgeElasticity: 100,
        nestingFactor: 1.2,
        gravity: 0.25,
        numIter: 1500,
        animate: true,
        animationDuration: 600,
      },
      minZoom: 0.3,
      maxZoom: 3,
      wheelSensitivity: 0.2,
    });

    if (onNodeClick) {
      cy.on('tap', 'node', (evt: EventObject) => {
        const node = nodes.find((n) => n.id === evt.target.id());
        if (node) onNodeClick(node);
      });
    }

    if (onEdgeClick) {
      cy.on('tap', 'edge', (evt: EventObject) => {
        const edge = edges.find((e) => e.id === evt.target.id());
        if (edge) onEdgeClick(edge);
      });
    }

    cyRef.current = cy;
    setCyReady(true);

    return () => {
      setCyReady(false);
      cy.destroy();
    };
  }, [nodes, edges, onNodeClick, onEdgeClick, docColorMap, orphanIds, getNodeColor, getEdgeColor]);

  // Apply filter
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;

    if (filter === 'all') {
      cy.elements().removeClass('filtered-out');
      return;
    }

    cy.nodes().forEach((node) => {
      const source = node.data('source');
      const matches = filter === source;
      nodetoggleClass(node, 'filtered-out', !matches);
    });

    // Also dim edges connected to filtered-out nodes
    cy.edges().forEach((edge) => {
      const src = edge.source().hasClass('filtered-out');
      const tgt = edge.target().hasClass('filtered-out');
      nodetoggleClass(edge, 'filtered-out', src || tgt);
    });
  }, [filter]);

  return (
    <div className="relative h-full w-full canvas-rings">
      <div
        ref={containerRef}
        style={fill ? { width: '100%', height: '100%' } : { width: '100%', height: `${height}px` }}
      />

      {/* Floating zoom controls */}
      <div className="absolute top-3 right-3 glass-chip rounded-xl p-1 flex flex-col gap-0.5">
        <button
          onClick={() => cyRef.current?.zoom(cyRef.current.zoom() + 0.35)}
          disabled={!cyReady}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)] disabled:opacity-40 transition-colors"
          title="Zoom in"
        >
          <ZoomIn size={15} />
        </button>
        <button
          onClick={() => cyRef.current?.zoom(cyRef.current.zoom() - 0.35)}
          disabled={!cyReady}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)] disabled:opacity-40 transition-colors"
          title="Zoom out"
        >
          <ZoomOut size={15} />
        </button>
        <div className="w-6 h-px bg-[var(--color-line)] mx-auto" />
        <button
          onClick={() => cyRef.current?.fit(undefined, 40)}
          disabled={!cyReady}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)] disabled:opacity-40 transition-colors"
          title="Fit to view"
        >
          <Maximize2 size={15} />
        </button>
        <button
          onClick={() => {
            const cy = cyRef.current;
            if (!cy) return;
            cy.reset();
            cy.fit(undefined, 40);
          }}
          disabled={!cyReady}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)] disabled:opacity-40 transition-colors"
          title="Reset view"
        >
          <RotateCcw size={15} />
        </button>
      </div>

      {/* Inline legend */}
      <div className="absolute bottom-3 left-3 glass-chip rounded-xl px-3 py-2.5 text-[10px] space-y-1.5">
        <div className="data-label mb-1">field legend</div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: SHARED_COLOR, border: '2px solid ' + SHARED_COLOR }} />
          <span className="text-[var(--color-text-secondary)]">Shared (2+ papers)</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-full"
            style={{ background: DOC_COLOR_GRADIENT, border: '2px solid ' + NODE_OUTLINE }}
          />
          <span className="text-[var(--color-text-secondary)]">Unique to paper — a color per paper</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full border border-dashed" style={{ background: '#5a6b80', opacity: ORPHAN_OPACITY }} />
          <span className="text-[var(--color-text-secondary)]">Orphan — no edges</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-5 h-0.5 rounded" style={{ background: SHARED_EDGE_COLOR }} />
          <span className="text-[var(--color-text-secondary)]">Shared edge</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-5 h-0.5 rounded" style={{ background: EDGE_COLOR }} />
          <span className="text-[var(--color-text-secondary)]">Unique edge</span>
        </div>
      </div>
    </div>
  );
}

function nodetoggleClass(
  ele: cytoscape.NodeSingular | cytoscape.EdgeSingular,
  cls: string,
  add: boolean,
) {
  if (add) ele.addClass(cls);
  else ele.removeClass(cls);
}