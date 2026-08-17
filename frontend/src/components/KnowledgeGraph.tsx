import { useEffect, useRef, useMemo, useCallback } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';

export interface GraphNode {
  id: string;
  label: string;
  name?: string;
  source: 'main' | 'reference' | 'shared';
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

export type NodeFilter = 'all' | 'main' | 'reference' | 'shared';

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
  height?: number;
  filter?: NodeFilter;
  onFilterChange?: (filter: NodeFilter) => void;
}

const DOC_COLORS = [
  '#8b5cf6', // purple
  '#3b82f6', // blue
  '#f59e0b', // amber
  '#ef4444', // red
  '#10b981', // emerald
  '#f97316', // orange
  '#6366f1', // indigo
  '#ec4899', // pink
];

const SHARED_COLOR = '#0d9488';
const ORPHAN_OPACITY = 0.35;

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
  filter = 'all',
}: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

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
      return '#94a3b8';
    },
    [docColorMap],
  );

  const getEdgeColor = useCallback((edge: GraphEdge): string => {
    const docs = edge.documents || [];
    if (docs.length > 1) return SHARED_COLOR;
    return '#94a3b8';
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
        // --- Shared nodes: thick border + glow ---
        {
          selector: 'node[docCount > 1]',
          style: {
            'border-width': 3,
            'border-color': 'data(docColor)',
            'border-style': 'solid',
            'background-color': 'data(docColor)',
            'background-opacity': 0.9,
            'overlay-padding': '6px',
            'overlay-opacity': 0.15,
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
            'background-opacity': 0.85,
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
            color: '#1e293b',
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
            'text-outline-color': '#fff',
            'text-outline-width': 2,
          },
        },
        // --- Shared edges: thicker + colored ---
        {
          selector: 'edge[docCount > 1]',
          style: {
            width: (ele: cytoscape.EdgeSingular) => 2 + ele.data('confidence') * 2,
            'line-color': SHARED_COLOR,
            'target-arrow-color': SHARED_COLOR,
            'line-opacity': (ele: cytoscape.EdgeSingular) => 0.5 + ele.data('confidence') * 0.5,
          },
        },
        // --- Unique edges: thinner ---
        {
          selector: 'edge[docCount = 1]',
          style: {
            width: (ele: cytoscape.EdgeSingular) => 1 + ele.data('confidence') * 1.5,
            'line-color': '#cbd5e1',
            'target-arrow-color': '#cbd5e1',
            'line-opacity': (ele: cytoscape.EdgeSingular) => 0.35 + ele.data('confidence') * 0.45,
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
            color: '#94a3b8',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
            'text-outline-color': '#fff',
            'text-outline-width': 1.5,
          },
        },
        // --- Selected node ---
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#f59e0b',
            'background-color': '#f59e0b',
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

    return () => {
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
    <div className="relative">
      <div
        ref={containerRef}
        style={{ width: '100%', height: `${height}px` }}
        className="bg-gray-50 rounded-lg"
      />
      {/* Inline legend */}
      <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 px-3 py-2 text-[10px] space-y-1.5 shadow-sm">
        <div className="font-medium text-gray-600 mb-1">Legend</div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: SHARED_COLOR, border: '2px solid ' + SHARED_COLOR }} />
          <span>Shared (2+ papers)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: DOC_COLORS[0], border: '2px solid ' + DOC_COLORS[0] }} />
          <span>Unique to paper</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full border border-dashed border-gray-400" style={{ background: '#94a3b8', opacity: ORPHAN_OPACITY }} />
          <span>Orphan (no edges)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-5 h-0.5 rounded" style={{ background: SHARED_COLOR }} />
          <span>Shared edge</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-5 h-0.5 rounded" style={{ background: '#cbd5e1' }} />
          <span>Unique edge</span>
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
