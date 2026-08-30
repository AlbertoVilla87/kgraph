import { useState, useCallback } from 'react';
import {
  GitBranch,
  ArrowRight,
  BookOpen,
  Compass,
  Plus,
  X,
} from 'lucide-react';
import KnowledgeGraph, { GraphNode, GraphEdge, NodeFilter } from '../components/KnowledgeGraph';
import AnalysisProgress from '../components/AnalysisProgress';

const API_BASE = '/api';

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
}

interface AnalysisResult {
  id: string;
  topic: string;
  papers: { id: string; title: string }[];
  topics: GraphNode[];
  relationships: GraphEdge[];
  stats: Record<string, unknown>;
}

interface UserTopic {
  id: string;
  name: string;
  status: 'found' | 'partial' | 'not_found';
}

const mockUserTopics: UserTopic[] = [
  { id: '1', name: 'Few-shot Learning', status: 'found' },
  { id: '2', name: 'Graph Neural Networks', status: 'partial' },
  { id: '3', name: 'Quantum Computing', status: 'not_found' },
];

export default function Overview() {
  const [depthMode, setDepthMode] = useState<'quick' | 'deep'>('quick');
  const [discoveryMode, setDiscoveryMode] = useState<'topic' | 'citation'>('citation');
  const [seedUrl, setSeedUrl] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [userTopics, setUserTopics] = useState<UserTopic[]>(mockUserTopics);
  const [newTopic, setNewTopic] = useState('');
  const [graphFilter, setGraphFilter] = useState<NodeFilter>('all');

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
    setAnalyzing(true);

    try {
      const body = { seed_url: seedUrl.trim(), max_references: 15, mode: depthMode, discovery: discoveryMode };

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
    if (!newTopic.trim()) return;
    setUserTopics([
      ...userTopics,
      { id: String(Date.now()), name: newTopic.trim(), status: 'not_found' },
    ]);
    setNewTopic('');
  };

  const handleRemoveTopic = (id: string) => {
    setUserTopics(userTopics.filter((t) => t.id !== id));
  };

  const graphNodes: GraphNode[] = analysisResult?.topics ?? [];
  const graphEdges: GraphEdge[] = analysisResult?.relationships ?? [];
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

          <div className="seg">
            <button data-active={depthMode === 'quick'} onClick={() => setDepthMode('quick')} disabled={analyzing}>
              Quick ~30s
            </button>
            <button data-active={depthMode === 'deep'} onClick={() => setDepthMode('deep')} disabled={analyzing}>
              Deep ~5min
            </button>
          </div>

          <div className="seg">
            <button data-active={discoveryMode === 'topic'} onClick={() => setDiscoveryMode('topic')} disabled={analyzing}>
              Discovery · AutoDiscover
            </button>
            <button data-active={discoveryMode === 'citation'} onClick={() => setDiscoveryMode('citation')} disabled={analyzing}>
              Discovery · Citation
            </button>
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
          {depthMode === 'quick' ? '~30s · abstracts only' : '~5min · full text + PDF'}
          <span className="mx-2 text-[var(--color-line)]">|</span>
          {discoveryMode === 'topic' ? 'AutoDiscovers topic taxonomy from the abstract' : 'Reads citing contexts from reference papers'}
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

        {/* filter chips */}
        {analysisResult && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 glass-chip rounded-xl px-2 py-1.5 z-10 flex gap-1">
            {(['all', 'main', 'reference', 'shared'] as NodeFilter[]).map((f) => {
              const labels: Record<NodeFilter, string> = {
                all: 'All',
                main: 'Seed',
                reference: 'Refs',
                shared: 'Shared',
                core: 'Core',
                'seed-only': 'Seed only',
                'refs-only': 'Refs only',
              };
              return (
                <button
                  key={f}
                  onClick={() => setGraphFilter(f)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                    graphFilter === f
                      ? 'text-[#04201c] bg-[var(--color-primary)]'
                      : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-3)]'
                  }`}
                >
                  {labels[f]}
                </button>
              );
            })}
          </div>
        )}

        {/* graph or empty state */}
        {graphNodes.length > 0 ? (
          <div className="absolute inset-0">
            <KnowledgeGraph nodes={graphNodes} edges={graphEdges} fill filter={graphFilter} />
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

        {/* Floating: explore your own topics */}
        <TopicDock topics={userTopics} onAdd={handleAddTopic} onRemove={handleRemoveTopic} value={newTopic} onChange={setNewTopic} />
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

          {/* References list */}
          <div className="flex items-center justify-between mb-1.5">
            <h4 className="data-label">references analyzed</h4>
            <span className="text-[10px] font-mono text-[var(--color-text-faint)]">
              {analysisResult.papers.length} papers
            </span>
          </div>
          <ul className="max-h-32 overflow-y-auto space-y-1 pr-1">
            {analysisResult.papers.map((paper, i) => (
              <li
                key={paper.id}
                className="group flex items-center gap-3 px-3 py-1.5 rounded-xl hover:bg-[var(--color-surface-3)] transition-colors"
              >
                <span className="text-[10px] font-mono text-[var(--color-text-faint)] w-5 text-right tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="w-6 h-6 rounded-lg bg-[var(--color-surface-3)] flex items-center justify-center shrink-0">
                  <BookOpen size={12} className="text-[var(--color-text-secondary)]" />
                </span>
                <span className="text-[13px] truncate">{paper.title}</span>
                <span className="ml-auto text-[11px] font-mono text-[var(--color-text-faint)] shrink-0 hidden md:block">
                  {paper.id}
                </span>
              </li>
            ))}
          </ul>
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

function TopicDock({
  topics,
  onAdd,
  onRemove,
  value,
  onChange,
}: {
  topics: UserTopic[];
  onAdd: () => void;
  onRemove: (id: string) => void;
  value: string;
  onChange: (v: string) => void;
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
              onKeyDown={(e) => e.key === 'Enter' && onAdd()}
              placeholder="e.g. few-shot learning"
              className="field h-9 flex-1 px-3 text-[13px]"
            />
            <button onClick={onAdd} className="btn-primary h-9 px-3 flex items-center justify-center" title="Add topic">
              <Plus size={15} strokeWidth={2.4} />
            </button>
          </div>

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