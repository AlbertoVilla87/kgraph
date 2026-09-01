import { useEffect, useMemo, useRef, useState } from 'react';
import { X } from 'lucide-react';
import type { Chunk, ChunkHighlight } from '../types';

const NODE_COLOR = '#f5b759'; // amber — the selected node
const EDGE_COLOR = '#35d6c1'; // teal — connected edges

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
  label: string;
}

function clipIntervals(
  intervals: HighlightInterval[],
  limit: number,
): HighlightInterval[] {
  const out: HighlightInterval[] = [];
  for (const iv of intervals) {
    if (iv.start >= limit) continue;
    out.push({ ...iv, end: Math.min(iv.end, limit) });
  }
  return out;
}

function shortDoc(docId: string, docTitles?: Record<string, string>): string {
  const title = docTitles?.[docId];
  if (title) return title.length > 22 ? `${title.slice(0, 22)}…` : title;
  const clean = docId.replace(/^arxiv:/, '');
  return clean.length > 16 ? `${clean.slice(0, 16)}…` : clean;
}

export default function ChunkViewer({ nodeId, nodeLabel, chunksUrl, docTitles, onClose }: ChunkViewerProps) {
  const [chunks, setChunks] = useState<Chunk[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(0);
  const [revealed, setRevealed] = useState(0);
  const rafRef = useRef<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setChunks(null);
    setActive(0);
    setRevealed(0);
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
  const textLen = chunk?.text.length ?? 0;

  // Typewriter reveal for the active chunk.
  useEffect(() => {
    setRevealed(0);
    if (!chunk || textLen === 0) return;
    const start = performance.now();
    const duration = Math.min(textLen * 6, 2500); // ~6ms/char, capped
    const step = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      setRevealed(Math.floor(t * textLen));
      if (t < 1) rafRef.current = requestAnimationFrame(step);
      else rafRef.current = null;
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };
  }, [chunk, textLen]);

  // Keep the newly revealed text in view as the typewriter plays.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [revealed, active]);

  const intervals = useMemo<HighlightInterval[]>(() => {
    if (!chunk) return [];
    return (chunk.highlights || []).map((h: ChunkHighlight) => ({
      start: h.start,
      end: h.end,
      kind: h.kind,
      label: h.label,
    }));
  }, [chunk]);

  const shown = useMemo<{ before: string; parts: { text: string; kind: 'node' | 'edge' | 'plain' }[] }>(() => {
    if (!chunk) return { before: '', parts: [] };
    const visible = chunk.text.slice(0, revealed);
    const clipped = clipIntervals(intervals, revealed);
    // Walk visible text, grouping runs by whether they fall inside any interval.
    const parts: { text: string; kind: 'node' | 'edge' | 'plain' }[] = [];
    let buf = '';
    let bufKind: 'node' | 'edge' | 'plain' = 'plain';

    for (let i = 0; i < visible.length; i++) {
      let kind: 'node' | 'edge' | 'plain' = 'plain';
      for (const iv of clipped) {
        if (i >= iv.start && i < iv.end) {
          kind = iv.kind;
          break;
        }
      }
      if (kind !== bufKind) {
        if (buf) parts.push({ text: buf, kind: bufKind });
        buf = '';
        bufKind = kind;
      }
      buf += visible[i];
    }
    if (buf) parts.push({ text: buf, kind: bufKind });

    const before = chunk.text.slice(revealed);
    return { before, parts };
  }, [chunk, revealed, intervals]);

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
    <div className="absolute left-3 top-12 z-20 w-[360px] glass rounded-2xl p-4 shadow-[0_24px_60px_-20px_rgba(0,0,0,0.9)] flex flex-col gap-3 animate-rise">
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
          <span className="w-3 h-3 rounded-sm border" style={{ background: 'rgba(245,183,89,0.35)', borderColor: NODE_COLOR }} />
          {legend.node}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm border" style={{ background: 'rgba(53,214,193,0.3)', borderColor: EDGE_COLOR }} />
          {legend.edge}
        </span>
      </div>

      {/* Chunk text — scrollable */}
      <div
        ref={scrollRef}
        className="max-h-[260px] overflow-y-auto pr-1 text-[13px] leading-relaxed text-[var(--color-text-secondary)]"
      >
        {shown.parts.map((p, i) =>
          p.kind === 'node' ? (
            <mark key={i} className="rounded px-0.5" style={{ background: 'rgba(245,183,89,0.35)', color: '#fff', textDecoration: `underline 2px ${NODE_COLOR}` }}>
              {p.text}
            </mark>
          ) : p.kind === 'edge' ? (
            <mark key={i} className="rounded px-0.5" style={{ background: 'rgba(53,214,193,0.3)', color: '#fff', textDecoration: `underline 2px ${EDGE_COLOR}` }}>
              {p.text}
            </mark>
          ) : (
            <span key={i}>{p.text}</span>
          ),
        )}
        <span className="opacity-40">{shown.before}</span>
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
