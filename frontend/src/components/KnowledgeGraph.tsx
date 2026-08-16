import { useEffect, useRef } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';

export interface GraphNode {
  id: string;
  label: string;
  source: 'main' | 'reference' | 'shared';
  importance: number;
  type: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  confidence: number;
}

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
  height?: number;
}

const sourceColors: Record<string, string> = {
  main: '#8b5cf6',
  reference: '#3b82f6',
  shared: '#14b8a6',
};

export default function KnowledgeGraph({
  nodes,
  edges,
  onNodeClick,
  onEdgeClick,
  height = 500,
}: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements = [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          source: n.source,
          importance: n.importance,
          type: n.type,
        },
      })),
      ...edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          relation: e.relation,
          confidence: e.confidence,
        },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': (ele: cytoscape.NodeSingular) =>
              sourceColors[ele.data('source')] || '#94a3b8',
            color: '#1e293b',
            'font-size': '11px',
            'font-weight': '500' as cytoscape.Css.FontWeight,
            width: (ele: cytoscape.NodeSingular) =>
              20 + ele.data('importance') * 4,
            height: (ele: cytoscape.NodeSingular) =>
              20 + ele.data('importance') * 4,
            'text-valign': 'bottom',
            'text-margin-y': 6,
            'text-outline-color': '#fff',
            'text-outline-width': 2,
            'border-width': 2,
            'border-color': (ele: cytoscape.NodeSingular) =>
              sourceColors[ele.data('source')] || '#94a3b8',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#cbd5e1',
            'target-arrow-color': '#cbd5e1',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(relation)',
            'font-size': '9px',
            color: '#94a3b8',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
            'text-outline-color': '#fff',
            'text-outline-width': 1.5,
          } as cytoscape.Css.Edge,
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#f59e0b',
            'background-color': '#f59e0b',
          } as cytoscape.Css.Node,
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
  }, [nodes, edges, onNodeClick, onEdgeClick]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: `${height}px` }}
      className="bg-gray-50 rounded-lg"
    />
  );
}
