import { useState } from 'react';
import { Search } from 'lucide-react';
import KnowledgeGraph, { GraphNode, GraphEdge } from '../components/KnowledgeGraph';

const mockNodes: GraphNode[] = [
  { id: '1', label: 'Transformer Architecture', source: 'shared', importance: 10, type: 'concept', documents: ['a', 'b'] },
  { id: '2', label: 'Attention Mechanism', source: 'main', importance: 9, type: 'concept', documents: ['a'] },
  { id: '3', label: 'Self-Attention', source: 'main', importance: 8, type: 'method', documents: ['a', 'b'] },
  { id: '4', label: 'Positional Encoding', source: 'main', importance: 7, type: 'technique', documents: ['a'] },
  { id: '5', label: 'Sequence Modeling', source: 'shared', importance: 6, type: 'task', documents: ['a', 'b'] },
  { id: '6', label: 'Neural Machine Translation', source: 'reference', importance: 5, type: 'application', documents: ['b'] },
  { id: '7', label: 'RNNs', source: 'reference', importance: 4, type: 'model', documents: ['a'] },
  { id: '8', label: 'CNNs', source: 'reference', importance: 3, type: 'model', documents: ['b'] },
  { id: '9', label: 'Multi-Head Attention', source: 'main', importance: 7, type: 'method', documents: ['a'] },
  { id: '10', label: 'Feed-Forward Network', source: 'shared', importance: 5, type: 'concept', documents: ['a', 'b'] },
  { id: '11', label: 'Layer Normalization', source: 'main', importance: 4, type: 'technique', documents: ['a'] },
  { id: '12', label: 'Training Efficiency', source: 'reference', importance: 6, type: 'concept', documents: ['b'] },
  { id: '13', label: 'Generalization', source: 'shared', importance: 5, type: 'concept', documents: ['a', 'b'] },
  { id: '14', label: 'Transfer Learning', source: 'reference', importance: 4, type: 'method', documents: ['b'] },
];

const mockEdges: GraphEdge[] = [
  { id: 'e1', source: '2', target: '1', relation: 'enables', confidence: 0.95, documents: ['a', 'b'] },
  { id: 'e2', source: '3', target: '2', relation: 'implements', confidence: 0.9, documents: ['a'] },
  { id: 'e3', source: '9', target: '2', relation: 'extends', confidence: 0.88, documents: ['a', 'b'] },
  { id: 'e4', source: '4', target: '1', relation: 'required by', confidence: 0.85, documents: ['a'] },
  { id: 'e5', source: '1', target: '5', relation: 'improves', confidence: 0.82, documents: ['a', 'b'] },
  { id: 'e6', source: '1', target: '6', relation: 'applied in', confidence: 0.78, documents: ['b'] },
  { id: 'e7', source: '7', target: '1', relation: 'replaced by', confidence: 0.75, documents: ['a'] },
  { id: 'e8', source: '8', target: '1', relation: 'alternative to', confidence: 0.7, documents: ['b'] },
  { id: 'e9', source: '10', target: '1', relation: 'part of', confidence: 0.88, documents: ['a', 'b'] },
  { id: 'e10', source: '11', target: '1', relation: 'used in', confidence: 0.85, documents: ['a'] },
  { id: 'e11', source: '1', target: '12', relation: 'improves', confidence: 0.8, documents: ['b'] },
  { id: 'e12', source: '1', target: '13', relation: 'enables', confidence: 0.78, documents: ['a', 'b'] },
  { id: 'e13', source: '14', target: '1', relation: 'builds on', confidence: 0.72, documents: ['b'] },
  { id: 'e14', source: '5', target: '6', relation: 'used in', confidence: 0.85, documents: ['b'] },
];

export default function GraphExplorer() {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [query, setQuery] = useState('');

  const filterBy = (filter: string | null) => {
    // static mock explorer — reserved for live wiring
    void filter;
  };

  return (
    <div className="h-full flex flex-col gap-3">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div>
          <h2 className="font-display text-[17px] font-semibold tracking-tight">Graph explorer</h2>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            Inspect any node — its type, importance, and connections.
          </p>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search nodes…"
            className="field h-9 pl-9 pr-3 text-[13px] w-56"
          />
        </div>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap items-center gap-2 shrink-0">
        <span className="data-label mr-1">source</span>
        {['All', 'Main Paper', 'References', 'Shared'].map((f) => (
          <button
            key={f}
            onClick={() => filterBy(f === 'All' ? null : f)}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
              f === 'All'
                ? 'text-[#04201c] bg-[var(--color-primary)]'
                : 'glass-chip text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
            }`}
          >
            {f}
          </button>
        ))}
        <span className="data-label ml-4 mr-1">type</span>
        {['Topic', 'Method', 'Concept'].map((f) => (
          <button
            key={f}
            className="px-3 py-1 rounded-lg text-xs font-medium glass-chip text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
          >
            {f}
          </button>
        ))}
      </div>

      {/* Canvas + detail */}
      <div className="flex-1 min-h-0 flex gap-3">
        <div className="flex-1 min-w-0 glass rounded-2xl overflow-hidden relative">
          <KnowledgeGraph nodes={mockNodes} edges={mockEdges} onNodeClick={setSelectedNode} fill />
        </div>

        {/* Node detail panel */}
        <div className="w-80 shrink-0 glass rounded-2xl p-5 overflow-y-auto">
          {selectedNode ? (
            <div className="animate-rise">
              <div className="flex items-start justify-between gap-2 mb-4">
                <h3 className="font-display text-base font-semibold leading-snug">{selectedNode.label}</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wide bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] shrink-0">
                  {selectedNode.source}
                </span>
              </div>
              <div className="space-y-4">
                <div>
                  <span className="data-label">type</span>
                  <div className="text-sm font-medium capitalize mt-1">{selectedNode.type}</div>
                </div>
                <div>
                  <span className="data-label">source</span>
                  <div className="flex items-center gap-2 mt-1.5">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{
                        backgroundColor:
                          selectedNode.source === 'main'
                            ? '#5b8cff'
                            : selectedNode.source === 'reference'
                              ? '#a78bfa'
                              : '#35d6c1',
                      }}
                    />
                    <span className="text-sm font-medium capitalize">{selectedNode.source}</span>
                  </div>
                </div>
                <div>
                  <span className="data-label mb-1.5 block">importance</span>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-[var(--color-surface-3)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[var(--color-primary)] rounded-full"
                        style={{ width: `${selectedNode.importance * 10}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono tabular-nums">{selectedNode.importance}/10</span>
                  </div>
                </div>
                <div>
                  <span className="data-label mb-1.5 block">connected to</span>
                  <div className="space-y-1">
                    {mockEdges
                      .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                      .map((e) => {
                        const otherId = e.source === selectedNode.id ? e.target : e.source;
                        const other = mockNodes.find((n) => n.id === otherId);
                        return (
                          <div key={e.id} className="flex items-center gap-2 text-xs px-2.5 py-1.5 rounded-lg bg-[var(--color-surface-2)]">
                            <span className="text-[var(--color-text-faint)] w-16 truncate">{e.relation}</span>
                            <span className="text-[var(--color-primary)]">→</span>
                            <span className="font-medium truncate">{other?.label}</span>
                          </div>
                        );
                      })}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center gap-3 px-4 text-[var(--color-text-faint)]">
              <div className="w-12 h-12 rounded-2xl bg-[var(--color-surface-3)] flex items-center justify-center">
                <Search size={18} className="text-[var(--color-text-secondary)]" />
              </div>
              <p className="text-sm">Tap any node to inspect it.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}