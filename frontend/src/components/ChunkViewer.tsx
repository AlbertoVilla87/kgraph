import { useEffect, useMemo, useRef, useState } from 'react';
import { X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import 'katex/dist/katex.min.css';
import type { Chunk, ChunkHighlight } from '../types';

const NODE_CLASS = 'kg-node';
const EDGE_CLASS = 'kg-edge';

interface ChunkViewerProps {
  nodeId: string;
  nodeLabel: string;
  chunksUrl: string;
  docTitles?: Record<string, string>;
  onClose: () => void;
}

interface HighlightInterval {
  start: number;
  end: number;
  kind: 'node' | 'edge';
}

function shortDoc(docId: string, docTitles?: Record<string, string>): string {
  const title = docTitles?.[docId];
  if (title) return title.length > 22 ? `${title.slice(0, 22)}…` : title;
  const clean = docId.replace(/^arxiv:/, '');
  return clean.length > 16 ? `${clean.slice(0, 16)}…` : clean;
}

// Inject balanced <mark> tags into the markdown string at the highlight offsets.
// Node highlights take priority over edge highlights when they overlap.
function withHighlights(text: string, intervals: HighlightInterval[]): string {
  if (!intervals.length) return text;
  const markByIndex = new Map<number, 'node' | 'edge'>();
  for (const iv of intervals) {
    const start = Math.max(0, iv.start);
    const end = Math.min(text.length, iv.end);
    for (let i = start; i < end; i++) {
      const cur = markByIndex.get(i);
      if (cur === 'node') continue;
      if (iv.kind === 'node') markByIndex.set(i, 'node');
      else if (!cur) markByIndex.set(i, 'edge');
    }
  }
  let out = '';
  let active: 'node' | 'edge' | null = null;
  for (let i = 0; i < text.length; i++) {
    const k: 'node' | 'edge' | null = markByIndex.get(i) ?? null;
    if (k !== active) {
      if (active === 'node') out += '</mark>';
      else if (active === 'edge') out += '</mark>';
      if (k === 'node') out += `<mark class="${NODE_CLASS}">`;
      else if (k === 'edge') out += `<mark class="${EDGE_CLASS}">`;
      active = k;
    }
    out += text[i];
  }
  if (active === 'node') out += '</mark>';
  else if (active === 'edge') out += '</mark>';
  return out;
}

export default function ChunkViewer({ nodeId, nodeLabel, chunksUrl, docTitles, onClose }: ChunkViewerProps) {
  const [chunks, setChunks] = useState<Chunk[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setChunks(null);
    setActive(0);

    fetch(chunksUrl)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load chunks');
        return r.json();
      })
      .then((data: { chunks: Chunk[] }) => {
        if (cancelled) return;
        setChunks(data.chunks);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load chunks');
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [chunksUrl]);

  const chunk = chunks?.[active] ?? null;
  const intervals = useMemo<HighlightInterval[]>(() => {
    if (!chunk) return [];
    return (chunk.highlights || []).map((h: ChunkHighlight) => ({
      start: h.start,
      end: h.end,
      kind: h.kind,
    }));
  }, [chunk]);

  const markdown = useMemo(() => {
    if (!chunk) return '';
    return withHighlights(chunk.text, intervals);
  }, [chunk, intervals]);

  if (loading) {
    return (
      <PanelShell onClose={onClose} title={nodeLabel}>
        <div className="space-y-2">
          <div className="h-3 rounded bg-[var(--color-surface-3)] animate-pulse w-3/4" />
          <div className="h-3 rounded bg-[var(--color-surface-3)] animate-pulse w-full" />
          <div className="h-3 rounded bg-[var(--color-surface-3)] animate-pulse w-5/6" />
        </div>
      </PanelShell>
    );
  }

  if (error) {
    return (
      <PanelShell onClose={onClose} title={nodeLabel}>
        <p className="text-sm text-[var(--color-error)]">{error}</p>
      </PanelShell>
    );
  }

  if (!chunk) {
    return (
      <PanelShell onClose={onClose} title={nodeLabel}>
        <p className="text-sm text-[var(--color-text-secondary)]">
          No chunks found for this node.
        </p>
      </PanelShell>
    );
  }

  const legend = {
    node: 'selected node',
    edge: 'connected node',
  };

  return (
    <div className="absolute left-3 top-12 z-20 w-[720px] glass rounded-2xl p-4 shadow-[0_24px_60px_-20px_rgba(0,0,0,0.9)] flex flex-col gap-3 animate-rise">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-display text-sm font-semibold leading-snug truncate">{nodeLabel}</h3>
          <p className="text-[11px] font-mono text-[var(--color-text-faint)] mt-0.5">{nodeId}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-[var(--color-text-faint)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)] shrink-0"
          title="Close"
        >
          <X size={15} />
        </button>
      </div>

      {/* Chunk tabs — one per place the node appears */}
      {chunks && chunks.length > 1 && (
        <div>
          <div className="flex gap-1.5 flex-wrap">
            {chunks.map((c, i) => (
              <button
                key={`${c.doc_id}-${c.index}`}
                onClick={() => setActive(i)}
                title={`${docTitles?.[c.doc_id] || c.doc_id} · paragraph ${c.index + 1}`}
                className={`px-2 py-0.5 rounded-md text-[11px] font-mono max-w-[120px] truncate transition-colors ${
                  i === active
                    ? 'text-[#04201c] bg-[var(--color-primary)]'
                    : 'glass-chip text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'
                }`}
              >
                {c.index + 1}: {shortDoc(c.doc_id, docTitles)}
              </button>
            ))}
          </div>
          <p className="text-[10px] font-mono text-[var(--color-text-faint)] mt-1">
            {chunks.length} place{chunks.length > 1 ? 's' : ''} · {new Set(chunks.map((c) => c.doc_id)).size} document{new Set(chunks.map((c) => c.doc_id)).size > 1 ? 's' : ''}
          </p>
        </div>
      )}

      {/* Active chunk provenance */}
      <div className="text-[11px] font-mono text-[var(--color-text-faint)] leading-snug">
        <span className="text-[var(--color-text-secondary)]">doc:</span> {docTitles?.[chunk.doc_id] || chunk.doc_id}
        <span className="mx-1 text-[var(--color-line)]">·</span>
        <span className="text-[var(--color-text-secondary)]">paragraph</span> {chunk.index + 1}
      </div>

      {/* Headings */}
      {chunk.headings.length > 0 && (
        <div className="text-[11px] font-mono text-[var(--color-text-faint)]">
          {chunk.headings.join(' / ')}
        </div>
      )}

      {/* Highlights legend */}
      <div className="flex items-center gap-3 text-[10px] text-[var(--color-text-secondary)]">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm border kg-node" />
          {legend.node}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm border kg-edge" />
          {legend.edge}
        </span>
      </div>

      {/* Chunk content — markdown with tables & math — scrollable */}
      <div
        ref={scrollRef}
        className="kg-markdown max-h-[260px] overflow-y-auto pr-1 text-[13px] leading-relaxed text-[var(--color-text-secondary)]"
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeRaw, rehypeKatex]}
        >
          {markdown}
        </ReactMarkdown>
      </div>
    </div>
  );
}

function PanelShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="absolute left-3 top-12 z-20 w-[360px] glass rounded-2xl p-4 shadow-[0_24px_60px_-20px_rgba(0,0,0,0.9)] animate-rise">
      <div className="flex items-start justify-between gap-2 mb-3">
        <h3 className="font-display text-sm font-semibold leading-snug truncate">{title}</h3>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-[var(--color-text-faint)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)] shrink-0"
        >
          <X size={15} />
        </button>
      </div>
      {children}
    </div>
  );
}
