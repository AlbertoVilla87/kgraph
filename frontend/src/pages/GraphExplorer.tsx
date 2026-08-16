import {
  GitBranch,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Search,
  Filter,
  Fullscreen,
} from 'lucide-react';

export default function GraphExplorer() {
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

      {/* Graph Canvas */}
      <div className="flex-1 bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] flex items-center justify-center min-h-[500px]">
        <div className="text-center">
          <GitBranch size={64} className="mx-auto text-gray-300 mb-4" />
          <p className="text-[var(--color-text-secondary)]">Knowledge graph visualization</p>
          <p className="text-sm text-gray-400 mt-1">
            D3.js or Cytoscape.js graph will render here
          </p>
        </div>
      </div>
    </div>
  );
}
