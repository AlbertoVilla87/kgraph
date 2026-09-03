import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import {
  GitBranch,
  ArrowRight,
  ArrowUpRight,
  Compass,
  Plus,
  X,
} from 'lucide-react';
import KnowledgeGraph, { GraphNode, GraphEdge } from '../components/KnowledgeGraph';
import AnalysisProgress from '../components/AnalysisProgress';
import ChunkViewer from '../components/ChunkViewer';

const API_BASE = '/api';

const STORAGE_KEY = 'astrolabe_last_analysis';
const EXTRA_KEY = 'astrolabe_extra_nodes';

interface Step {
  key: string;
  label: string;
  status: 'pending' | 'running' | 'done';
}

interface AnalysisStatus {
  id: string;
  status: string;
  topic: string;
  progress: number;
  current_step: string;
  detail: string;
  steps: Step[];
  error: string | null;
  partial_graph?: { topics: GraphNode[]; relationships: GraphEdge[] } | null;
}

interface PaperInfo {
  id: string;
  title: string;
  year?: number | null;
  url?: string | null;
}

interface AnalysisResult {
  id: string;
  topic: string;
  papers: PaperInfo[];
  topics: GraphNode[];
  relationships: GraphEdge[];
  stats: Record<string, unknown>;
}

interface UserTopic {
  id: string;
  name: string;
  status: 'found' | 'partial' | 'not_found';
}

interface EntityRelation {
  relation: string;
  head: string;
  tail: string;
  head_id?: string | null;
  tail_id?: string | null;
  head_is_query?: boolean;
  tail_is_query?: boolean;
  score: number;
  doc_id?: string;
}

interface EntitySearchResult {
  status: 'found' | 'partial' | 'not_found';
  existing_node?: {
    id: string;
    name?: string;
    label?: string;
    type?: string;
    importance?: number;
    documents?: string[];
  } | null;
  mentions?: { doc_id?: string; segment?: number; start?: number; end?: number; text?: string }[];
  relations?: EntityRelation[];
  documents?: string[];
  query?: string;
}

const mockUserTopics: UserTopic[] = [
  { id: '1', name: 'Few-shot Learning', status: 'found' },
  { id: '2', name: 'Graph Neural Networks', status: 'partial' },
  { id: '3', name: 'Quantum Computing', status: 'not_found' },
];

export default function Overview() {
  // Restore the last completed analysis from localStorage so refreshing the
  // page (or re-mounting the app) doesn't wipe the graph.
  const loadStoredResult = (): AnalysisResult | null => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as AnalysisResult;
      if (!parsed || !parsed.topics || !parsed.relationships) return null;
      return parsed;
    } catch {
      return null;
    }
  };

  const loadExtras = (): { nodes: GraphNode[]; edges: GraphEdge[] } => {
    try {
      const raw = localStorage.getItem(EXTRA_KEY);
      if (!raw) return { nodes: [], edges: [] };
      const parsed = JSON.parse(raw) as { nodes: GraphNode[]; edges: GraphEdge[] };
      return { nodes: parsed.nodes || [], edges: parsed.edges || [] };
    } catch {
      return { nodes: [], edges: [] };
    }
  };

  const [seedUrl, setSeedUrl] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(() => loadStoredResult());
  const [error, setError] = useState<string | null>(null);
  const [userTopics, setUserTopics] = useState<UserTopic[]>(mockUserTopics);
  const [newTopic, setNewTopic] = useState('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [extraNodes, setExtraNodes] = useState<GraphNode[]>(() => loadExtras().nodes);
  const [extraEdges, setExtraEdges] = useState<GraphEdge[]>(() => loadExtras().edges);
  const [highlightNodeId, setHighlightNodeId] = useState<string | null>(null);
  const [highlightIsNew, setHighlightIsNew] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);

  // Refs to the latest graph node/edge lists so async search handlers can
  // read current values without stale closures.
  const graphNodesRef = useRef<GraphNode[]>([]);
  const extraEdgesRef = useRef<GraphEdge[]>([]);

  const pollStatus = useCallback(async (analysisId: string) => {
    try {
      const res = await fetch(`${API_BASE}/analysis/${analysisId}`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const status: AnalysisStatus = await res.json();
      setAnalysisStatus(status);

      if (status.status === 'completed') {
        const resultRes = await fetch(`${API_BASE}/analysis/${analysisId}/result`);
        if (resultRes.ok) {
          const result: AnalysisResult = await resultRes.json();
          setAnalysisResult(result);
        }
        setAnalyzing(false);
      } else if (status.status === 'error') {
        setError(status.error || 'Analysis failed');
        setAnalyzing(false);
      } else {
        setTimeout(() => pollStatus(analysisId), 1000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
      setAnalyzing(false);
    }
  }, []);

  const handleAnalyze = async () => {
    if (!seedUrl.trim()) return;
    setError(null);
    setAnalysisResult(null);
    setAnalysisStatus(null);
      setSelectedNode(null);
      setHighlightNodeId(null);
      setHighlightIsNew(false);
    setSearchMessage(null);
    setExtraNodes([]);
    setExtraEdges([]);
    setAnalyzing(true);

    try {
      const body = { seed_url: seedUrl.trim(), max_references: 15 };

      const res = await fetch(`${API_BASE}/analysis/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to start analysis' }));
        throw new Error(err.detail || 'Failed to start analysis');
      }
      const status: AnalysisStatus = await res.json();
      setAnalysisStatus(status);
      pollStatus(status.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
      setAnalyzing(false);
    }
  };

  const handleAddTopic = () => {
    const topic = newTopic.trim();
    if (!topic) return;
    setNewTopic('');

    if (!analysisResult || !analysisResult.id) {
      setSearchMessage('Run an analysis first to search for this entity.');
      setUserTopics((prev) => [
        ...prev,
        { id: String(Date.now()), name: topic, status: 'not_found' },
      ]);
      return;
    }

    setSearching(true);
    setSearchMessage(null);
    setUserTopics((prev) => [...prev, { id: String(Date.now()), name: topic, status: 'not_found' }]);

    fetch(`${API_BASE}/graph/${analysisResult.id}/entity-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: topic }),
    })
      .then((r) => {
        if (!r.ok) throw new Error('Search failed');
        return r.json();
      })
      .then((res: EntitySearchResult) => {
        applySearchResult(topic, res);
      })
      .catch((e) => {
        setSearchMessage(e instanceof Error ? e.message : 'Search failed');
      })
      .finally(() => setSearching(false));
  };

  const applySearchResult = (topic: string, res: EntitySearchResult) => {
    if (res.status === 'not_found') {
      setSearchMessage(`"${topic}" not found in the analyzed papers.`);
      setUserTopics((prev) => prev.map((t) => (t.name === topic ? { ...t, status: 'not_found' } : t)));
      return;
    }

    // Found: existing node — pulse it and report its connections.
    if (res.existing_node?.id) {
      setHighlightNodeId(res.existing_node.id);
      setHighlightIsNew(false);
      const relCount = res.relations?.length ?? 0;
      setSearchMessage(
        `Already in graph — "${res.existing_node.name || res.existing_node.label || res.existing_node.id}" links to ${relCount} relation(s).`,
      );
      setUserTopics((prev) => prev.map((t) => (t.name === topic ? { ...t, status: 'found' } : t)));
      return;
    }

    // Partial: entity present in text but not a known node. Add it, wired to
    // whichever existing nodes GLiNER connected it to.
    setUserTopics((prev) => prev.map((t) => (t.name === topic ? { ...t, status: 'partial' } : t)));
    const docList = res.documents || [];
    const newNodeId = `user:${topic.toLowerCase().replace(/\s+/g, '-')}`;
    const newNode: GraphNode = {
      id: newNodeId,
      label: topic,
      name: topic,
      source: 'refs-only',
      importance: 8,
      type: 'concept',
      documents: docList,
    };

    const existingIds = new Set(graphNodesRef.current.map((n) => n.id));
    setExtraNodes((prev) => {
      if (prev.some((n) => n.id === newNodeId)) return prev;
      return [...prev, newNode];
    });

    const newEdges: GraphEdge[] = [];
    for (const rel of res.relations || []) {
      let otherId: string | null = null;
      if (rel.head_is_query) otherId = rel.tail_id ?? null;
      else if (rel.tail_is_query) otherId = rel.head_id ?? null;
      else continue;
      if (!otherId || !existingIds.has(otherId) || otherId === newNodeId) continue;
      const edgeId = `${newNodeId}_${otherId}_${rel.relation}`;
      if (extraEdgesRef.current.some((e) => e.id === edgeId)) continue;
      newEdges.push({
        id: edgeId,
        source: newNodeId,
        target: otherId,
        relation: rel.relation,
        confidence: rel.score,
        documents: rel.doc_id ? [rel.doc_id] : docList,
      });
    }

    if (newEdges.length) setExtraEdges((prev) => [...prev, ...newEdges]);
    setHighlightNodeId(newNodeId);
    setHighlightIsNew(true);
    setSearchMessage(
      newEdges.length
        ? `Found by you — added "${topic}" and linked to ${newEdges.length} existing node(s).`
        : `Found by you — "${topic}" appears in the papers but could not be linked to existing nodes.`,
    );
  };

  const handleRemoveTopic = (id: string) => {
    setUserTopics(userTopics.filter((t) => t.id !== id));
  };

  // Persist the completed analysis so a page reload / re-mount of the app
  // doesn't lose the graph (the backend keeps state in memory only).
  useEffect(() => {
    if (analysisResult) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(analysisResult));
      } catch {
        // ignore quota / private-mode failures
      }
    }
  }, [analysisResult]);

  // Persist user-added nodes/edges so they survive a page reload.
  useEffect(() => {
    try {
      localStorage.setItem(EXTRA_KEY, JSON.stringify({ nodes: extraNodes, edges: extraEdges }));
    } catch {
      // ignore quota / private-mode failures
    }
  }, [extraNodes, extraEdges]);

  const graphNodes: GraphNode[] = useMemo(
    () => [
      ...(analysisResult?.topics ?? analysisStatus?.partial_graph?.topics ?? []),
      ...extraNodes,
    ],
    [analysisResult, analysisStatus, extraNodes],
  );
  const graphEdges: GraphEdge[] = useMemo(
    () => [
      ...(analysisResult?.relationships ?? analysisStatus?.partial_graph?.relationships ?? []),
      ...extraEdges,
    ],
    [analysisResult, analysisStatus, extraEdges],
  );

  // Keep refs in sync for async search handlers (computed after extras merge).
  graphNodesRef.current = graphNodes;
  extraEdgesRef.current = extraEdges;
  const sharedTopics = graphNodes.filter((n) => (n.documents?.length ?? 0) > 1).length;

  return (
    <div className="h-full flex flex-col gap-3">
      {/* ===================== Analysis console ===================== */}
      <section className="glass rounded-2xl p-3.5 shrink-0 animate-rise">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mb-3">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-[var(--color-primary)] pulse-dot" />
            <h2 className="font-display text-[17px] font-semibold tracking-tight">New citation sweep</h2>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)]">
            Seed a paper and chart its references as a live knowledge graph.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[240px]">
            <GitBranch size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-text-faint)]" />
            <input
              type="text"
              value={seedUrl}
              onChange={(e) => setSeedUrl(e.target.value)}
              placeholder="https://arxiv.org/abs/2301.12345"
              className="field h-11 w-full pl-10 pr-4 text-sm"
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
              disabled={analyzing}
            />
          </div>

          <button
            onClick={handleAnalyze}
            disabled={analyzing || !seedUrl.trim()}
            className="btn-primary h-11 px-5 text-sm flex items-center gap-2"
          >
            {analyzing ? (
              <>
                <div className="w-4 h-4 border-2 border-[#04201c] border-t-transparent rounded-full animate-spin" />
                Sweeping…
              </>
            ) : (
              <>
                Expand
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </div>
        <p className="text-[11px] text-[var(--color-text-faint)] mt-2 font-mono">
          ~5min · full text + PDF
          <span className="mx-2 text-[var(--color-line)]">|</span>
          Reads citing contexts from reference papers
          <span className="mx-2 text-[var(--color-line)]">|</span>
          paste an arXiv URL to begin
        </p>
      </section>

      {/* ===================== Graph hero ===================== */}
      <section className="relative flex-1 min-h-0 glass rounded-2xl overflow-hidden animate-rise">
        {/* meta chip */}
        <div className="absolute top-3 left-3 glass-chip rounded-xl px-3 py-1.5 z-10 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)]" />
          <span className="text-[11px] font-mono text-[var(--color-text-secondary)] truncate max-w-[280px]">
            {analyzing
              ? 'sweep in progress…'
              : analysisResult
                ? `field: ${analysisResult.topic}`
                : 'field empty — awaiting a seed paper'}
          </span>
        </div>

        {/* graph or empty state */}
        {graphNodes.length > 0 ? (
          <div className="absolute inset-0">
            <KnowledgeGraph
              nodes={graphNodes}
              edges={graphEdges}
              fill
              onNodeClick={setSelectedNode}
              incremental={analyzing && !analysisResult && !!analysisStatus?.partial_graph}
              highlightNodeId={highlightNodeId}
              highlightIsNewNode={highlightIsNew}
            />
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center max-w-sm px-6 animate-pop">
              <div className="relative w-14 h-14 mx-auto mb-5">
                <div className="absolute inset-0 rounded-2xl bg-[var(--color-primary-soft)] rotate-12" />
                <div className="absolute inset-0 rounded-2xl bg-[var(--color-surface-3)] -rotate-6 flex items-center justify-center">
                  <GitBranch size={22} className="text-[var(--color-primary)]" />
                </div>
              </div>
              <p className="font-display text-lg text-[var(--color-text)]">
                {(analysisStatus && analyzing) ? 'Mapping citations…' : 'The plot, when plotted'}
              </p>
              <p className="text-sm text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
                Paste an arXiv URL above and the citation graph will render here — no scrolling required.
              </p>
            </div>
          </div>
        )}

        {/* Node chunks overlay panel */}
        {selectedNode && analysisResult && (
          <ChunkViewer
            nodeId={selectedNode.id}
            nodeLabel={selectedNode.label || selectedNode.name || selectedNode.id}
            chunksUrl={`${API_BASE}/graph/${analysisResult.id}/nodes/${selectedNode.id}/chunks`}
            docTitles={Object.fromEntries(analysisResult.papers.map((p) => [p.id, p.title]))}
            onClose={() => setSelectedNode(null)}
          />
        )}

        {/* Floating: explore your own topics */}
        <TopicDock
          topics={userTopics}
          onAdd={handleAddTopic}
          onRemove={handleRemoveTopic}
          value={newTopic}
          onChange={setNewTopic}
          searching={searching}
          message={searchMessage}
        />
      </section>

      {/* ===================== Progress ===================== */}
      {analyzing && analysisStatus && (
        <section className="shrink-0 animate-rise">
          <AnalysisProgress status={analysisStatus} />
        </section>
      )}

      {/* ===================== Error ===================== */}
      {error && (
        <section className="shrink-0 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300 font-mono animate-rise">
          {error}
        </section>
      )}

      {/* ===================== Datasheet (below the graph) ===================== */}
      {analysisResult && (
        <section className="shrink-0 glass rounded-2xl p-3.5 animate-rise">
          {/* Compact statistics strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
            <CompactStat value={graphNodes.length} label="main topics" />
            <CompactStat value={graphEdges.length} label="relations mapped" />
            <CompactStat value={analysisResult.papers.length} label="references analyzed" />
            <CompactStat value={sharedTopics} label="shared topics" accent="var(--color-violet)" />
          </div>

          {/* References timeline */}
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="data-label">references analyzed</h4>
            <span className="text-[10px] font-mono text-[var(--color-text-faint)]">
              {analysisResult.papers.length} papers
            </span>
          </div>
          <ReferenceTimeline papers={analysisResult.papers} />
        </section>
      )}
    </div>
  );
}

function CompactStat({
  value,
  label,
  accent = 'var(--color-primary)',
}: {
  value: number;
  label: string;
  accent?: string;
}) {
  return (
    <div className="card px-3.5 py-2 flex items-center gap-3 hover-lift">
      <span
        className="w-1.5 h-9 rounded-full shrink-0"
        style={{ background: `linear-gradient(180deg, ${accent}, transparent)` }}
      />
      <div className="min-w-0">
        <div className="font-mono text-lg leading-none font-medium tabular-nums" style={{ color: accent }}>
          {value}
        </div>
        <div className="text-[10.5px] text-[var(--color-text-faint)] mt-1 truncate">{label}</div>
      </div>
    </div>
  );
}

function ReferenceTimeline({ papers }: { papers: PaperInfo[] }) {
  const byYear = useMemo(() => {
    const map = new Map<number, PaperInfo[]>();
    const undated: PaperInfo[] = [];
    for (const paper of papers) {
      if (paper.year != null) {
        const list = map.get(paper.year) ?? [];
        list.push(paper);
        map.set(paper.year, list);
      } else {
        undated.push(paper);
      }
    }
    return { years: [...map.keys()].sort((a, b) => a - b), map, undated };
  }, [papers]);

  return (
    <div>
      {/* Axis: one dot per year. Spacing is proportional to elapsed years,
          so temporal distance is visible. Hover reveals that year's docs. */}
      <div className="relative">
        <div className="absolute top-[5px] left-0 right-0 h-px bg-[var(--color-line)]" />
        <div className="flex items-end">
          {byYear.years.map((year, i) => {
            const gap = i + 1 < byYear.years.length ? byYear.years[i + 1]! - year : 1;
            return (
              <YearNode
                key={year}
                year={year}
                papers={byYear.map.get(year) ?? []}
                style={{ flexGrow: Math.max(1, gap), flexBasis: 0 }}
              />
            );
          })}

          {byYear.undated.length > 0 && (
            <YearNode
              key="undated"
              year={null}
              papers={byYear.undated}
              style={{ flexGrow: 1, flexBasis: 0 }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function YearNode({
  year,
  papers,
  style,
}: {
  year: number | null;
  papers: PaperInfo[];
  style?: React.CSSProperties;
}) {
  const [hover, setHover] = useState(false);
  const count = papers.length;
  const label = year ?? 'no date';
  return (
    <div className="relative flex justify-center" style={style}>
      {/* Year node. The popover and the node share this wrapper so moving the
          mouse from the dot into the floating list keeps it open. */}
      <div
        className="relative flex flex-col items-center cursor-help"
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        {/* Floating popover with that year's papers */}
        {hover && (
          <div className="absolute bottom-[26px] left-1/2 -translate-x-1/2 w-64 glass-chip rounded-xl p-2 z-50 animate-pop">
            <div
              className={`text-[10px] font-mono mb-1.5 px-0.5 ${
                year == null ? 'text-[var(--color-text-faint)]' : 'text-[var(--color-text-secondary)]'
              }`}
            >
              {label} · {count} {count === 1 ? 'paper' : 'papers'}
            </div>
            <div className="flex flex-col gap-1 max-h-48 overflow-y-auto pr-1">
              {papers.map((paper) => (
                <ReferenceChip key={paper.id} paper={paper} />
              ))}
            </div>
          </div>
        )}

        {/* Year node */}
        <div
          className={`w-3 h-3 rounded-full border-2 relative z-10 transition-colors ${
            year == null
              ? 'border-dashed border-[var(--color-line)] bg-[var(--color-surface-3)]'
              : 'border-[var(--color-primary)] bg-[var(--color-primary-glow)]'
          }`}
        />
        <span
          className={`mt-1.5 text-[11px] font-mono ${
            year == null ? 'text-[var(--color-text-faint)]' : 'text-[var(--color-text-secondary)]'
          }`}
        >
          {label}
        </span>
        {count > 0 && (
          <span className="mt-0.5 text-[9px] font-mono text-[var(--color-text-faint)] tabular-nums">
            {count}
          </span>
        )}
      </div>
    </div>
  );
}

function ReferenceChip({ paper }: { paper: PaperInfo }) {
  const content = (
    <>
      <span className="min-w-0 flex-1 truncate text-[12px]">{paper.title}</span>
      <ArrowUpRight size={12} className="ml-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-[var(--color-primary)]" />
    </>
  );

  const cls =
    'group flex items-center gap-2 w-full h-8 px-2.5 rounded-lg glass-chip hover:border-[var(--color-primary-glow)] hover:text-[var(--color-text)] transition-colors text-left';

  if (paper.url) {
    return (
      <a href={paper.url} target="_blank" rel="noopener noreferrer" title={paper.title} className={cls}>
        {content}
      </a>
    );
  }
  return (
    <span title={paper.title} className={cls + ' cursor-default'}>
      {content}
    </span>
  );
}

function TopicDock({
  topics,
  onAdd,
  onRemove,
  value,
  onChange,
  searching,
  message,
}: {
  topics: UserTopic[];
  onAdd: () => void;
  onRemove: (id: string) => void;
  value: string;
  onChange: (v: string) => void;
  searching?: boolean;
  message?: string | null;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="absolute bottom-3 right-3 z-10 flex flex-col items-end">
      {open && (
        <div className="glass-chip rounded-2xl p-3.5 w-[280px] mb-2 animate-pop shadow-[0_24px_60px_-20px_rgba(0,0,0,0.8)]">
          <div className="flex items-baseline justify-between mb-0.5">
            <h4 className="font-display text-sm font-semibold">Explore your own topics</h4>
            <button onClick={() => setOpen(false)} className="p-1 rounded-md text-[var(--color-text-faint)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)]">
              <X size={14} />
            </button>
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] mb-3">
            Pin topics that matter to you — see if they surface in the field.
          </p>

          <div className="flex gap-1.5 mb-3">
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !searching && onAdd()}
              placeholder="e.g. few-shot learning"
              disabled={searching}
              className="field h-9 flex-1 px-3 text-[13px]"
            />
            <button onClick={onAdd} disabled={searching} className="btn-primary h-9 px-3 flex items-center justify-center" title="Add topic">
              {searching ? (
                <div className="w-3.5 h-3.5 border-2 border-[#04201c] border-t-transparent rounded-full animate-spin" />
              ) : (
                <Plus size={15} strokeWidth={2.4} />
              )}
            </button>
          </div>

          {message && (
            <p className="text-[11px] leading-snug mb-3 px-0.5 text-[var(--color-text-secondary)]">
              {message}
            </p>
          )}

          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {topics.map((topic) => (
              <div key={topic.id} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[var(--color-surface-3)]/60">
                <span
                  className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    topic.status === 'found'
                      ? 'bg-[var(--color-success)]'
                      : topic.status === 'partial'
                        ? 'bg-[var(--color-warning)]'
                        : 'bg-[var(--color-error)]'
                  }`}
                />
                <span className="text-[13px] truncate flex-1">{topic.name}</span>
                <span className="text-[10px] font-mono uppercase tracking-wide text-[var(--color-text-faint)]">
                  {topic.status.replace('_', ' ')}
                </span>
                <button onClick={() => onRemove(topic.id)} className="p-0.5 text-[var(--color-text-faint)] hover:text-[var(--color-text)] rounded">
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        className="glass-chip rounded-full h-11 px-4 flex items-center gap-2.5 hover:border-[var(--color-primary-glow)] transition-all"
      >
        <Compass size={16} className={open ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-secondary)]'} />
        <span className="text-xs font-medium">Your topics</span>
        <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-[var(--color-primary-soft)] text-[var(--color-primary)] tabular-nums">
          {topics.length}
        </span>
      </button>
    </div>
  );
}