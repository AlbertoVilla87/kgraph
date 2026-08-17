import { useState } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Search,
  Filter,
  Fullscreen,
} from 'lucide-react';
import KnowledgeGraph, { GraphNode, GraphEdge } from '../components/KnowledgeGraph';

const mockNodes: GraphNode[] = [
  { id: '1', label: 'Transformer Architecture', source: 'shared', importance: 10, type: 'concept' },
  { id: '2', label: 'Attention Mechanism', source: 'main', importance: 9, type: 'concept' },
  { id: '3', label: 'Self-Attention', source: 'main', importance: 8, type: 'method' },
  { id: '4', label: 'Positional Encoding', source: 'main', importance: 7, type: 'technique' },
  { id: '5', label: 'Sequence Modeling', source: 'shared', importance: 6, type: 'task' },
  { id: '6', label: 'Neural Machine Translation', source: 'reference', importance: 5, type: 'application' },
  { id: '7', label: 'RNNs', source: 'reference', importance: 4, type: 'model' },
  { id: '8', label: 'CNNs', source: 'reference', importance: 3, type: 'model' },
  { id: '9', label: 'Multi-Head Attention', source: 'main', importance: 7, type: 'method' },
  { id: '10', label: 'Feed-Forward Network', source: 'shared', importance: 5, type: 'concept' },
  { id: '11', label: 'Layer Normalization', source: 'main', importance: 4, type: 'technique' },
  { id: '12', label: 'Training Efficiency', source: 'reference', importance: 6, type: 'concept' },
  { id: '13', label: 'Generalization', source: 'shared', importance: 5, type: 'concept' },
  { id: '14', label: 'Transfer Learning', source: 'reference', importance: 4, type: 'method' },
];

const mockEdges: GraphEdge[] = [
  { id: 'e1', source: '2', target: '1', relation: 'enables', confidence: 0.95 },
  { id: 'e2', source: '3', target: '2', relation: 'implements', confidence: 0.9 },
  { id: 'e3', source: '9', target: '2', relation: 'extends', confidence: 0.88 },
  { id: 'e4', source: '4', target: '1', relation: 'required by', confidence: 0.85 },
  { id: 'e5', source: '1', target: '5', relation: 'improves', confidence: 0.82 },
  { id: 'e6', source: '1', target: '6', relation: 'applied in', confidence: 0.78 },
  { id: 'e7', source: '7', target: '1', relation: 'replaced by', confidence: 0.75 },
  { id: 'e8', source: '8', target: '1', relation: 'alternative to', confidence: 0.7 },
  { id: 'e9', source: '10', target: '1', relation: 'part of', confidence: 0.88 },
  { id: 'e10', source: '11', target: '1', relation: 'used in', confidence: 0.85 },
  { id: 'e11', source: '1', target: '12', relation: 'improves', confidence: 0.8 },
  { id: 'e12', source: '1', target: '13', relation: 'enables', confidence: 0.78 },
  { id: 'e13', source: '14', target: '1', relation: 'builds on', confidence: 0.72 },
  { id: 'e14', source: '5', target: '6', relation: 'used in', confidence: 0.85 },
];

export default function GraphExplorer() {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  return (
    <div className="h-full flex flex-col">
      {/* Graph Controls */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold">Graph Explorer</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Interactive knowledge graph visualization
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] hover:bg-gray-50">
            <ZoomIn size={16} />
          </button>
          <button className="p-2 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] hover:bg-gray-50">
            <ZoomOut size={16} />
          </button>
          <button className="p-2 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] hover:bg-gray-50">
            <Maximize2 size={16} />
          </button>
          <button className="p-2 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] hover:bg-gray-50">
            <RotateCcw size={16} />
          </button>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search graph..."
              className="pl-9 pr-3 py-2 rounded-lg border border-[var(--color-border)] text-sm w-48 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            />
          </div>
          <button className="p-2 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] hover:bg-gray-50">
            <Filter size={16} />
          </button>
          <button className="p-2 rounded-lg bg-[var(--color-card)] border border-[var(--color-border)] hover:bg-gray-50">
            <Fullscreen size={16} />
          </button>
        </div>
      </div>

      {/* Filter chips */}
      <div className="flex gap-2 mb-4">
        <span className="text-xs text-[var(--color-text-secondary)] self-center">Source:</span>
        {['All', 'Main Paper', 'References', 'Shared'].map((filter) => (
          <button
            key={filter}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filter === 'All'
                ? 'bg-[var(--color-primary)] text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {filter}
          </button>
        ))}
        <span className="text-xs text-[var(--color-text-secondary)] self-center ml-4">Type:</span>
        {['Topic', 'Method', 'Concept'].map((filter) => (
          <button
            key={filter}
            className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200"
          >
            {filter}
          </button>
        ))}
      </div>

      <div className="flex-1 flex gap-4">
        {/* Graph Canvas */}
        <div className="flex-1 bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] overflow-hidden">
          <KnowledgeGraph
            nodes={mockNodes}
            edges={mockEdges}
            onNodeClick={setSelectedNode}
            height={600}
          />
        </div>

        {/* Node Detail Panel */}
        <div className="w-80 bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-5">
          {selectedNode ? (
            <>
              <h3 className="font-semibold mb-4">{selectedNode.label}</h3>
              <div className="space-y-4">
                <div>
                  <span className="text-xs text-[var(--color-text-secondary)]">Type</span>
                  <div className="text-sm font-medium capitalize">{selectedNode.type}</div>
                </div>
                <div>
                  <span className="text-xs text-[var(--color-text-secondary)]">Source</span>
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{
                        backgroundColor:
                          selectedNode.source === 'main'
                            ? '#8b5cf6'
                            : selectedNode.source === 'reference'
                            ? '#3b82f6'
                            : '#14b8a6',
                      }}
                    />
                    <span className="text-sm font-medium capitalize">{selectedNode.source}</span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-[var(--color-text-secondary)]">Importance</span>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[var(--color-primary)]"
                        style={{ width: `${selectedNode.importance * 10}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium">{selectedNode.importance}/10</span>
                  </div>
                </div>
                <div>
                  <span className="text-xs text-[var(--color-text-secondary)]">Connected to</span>
                  <div className="mt-2 space-y-1">
                    {mockEdges
                      .filter(
                        (e) =>
                          e.source === selectedNode.id || e.target === selectedNode.id
                      )
                      .map((e) => {
                        const otherId =
                          e.source === selectedNode.id ? e.target : e.source;
                        const other = mockNodes.find((n) => n.id === otherId);
                        return (
                          <div
                            key={e.id}
                            className="text-xs p-2 rounded bg-gray-50"
                          >
                            <span className="text-[var(--color-text-secondary)]">
                              {e.relation}
                            </span>
                            <span className="mx-1">→</span>
                            <span className="font-medium">{other?.label}</span>
                          </div>
                        );
                      })}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-[var(--color-text-secondary)]">
              Click a node to inspect
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
