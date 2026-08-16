import { useState, useCallback } from 'react';
import {
  GitBranch,
  Sparkles,
  ArrowRight,
  Users,
  BookOpen,
  Plus,
  X,
} from 'lucide-react';
import KnowledgeGraph, { GraphNode, GraphEdge } from '../components/KnowledgeGraph';
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

const mockUserTopics = [
  { id: '1', name: 'Few-shot Learning', status: 'found' as const },
  { id: '2', name: 'Graph Neural Networks', status: 'partial' as const },
  { id: '3', name: 'Quantum Computing', status: 'not_found' as const },
];

export default function Overview() {
  const [topicInput, setTopicInput] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [userTopics, setUserTopics] = useState(mockUserTopics);
  const [newTopic, setNewTopic] = useState('');

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
    if (!topicInput.trim()) return;
    setError(null);
    setAnalysisResult(null);
    setAnalyzing(true);

    try {
      const res = await fetch(`${API_BASE}/analysis/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topicInput.trim(), max_papers: 2 }),
      });
      if (!res.ok) throw new Error('Failed to start analysis');
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
      { id: String(Date.now()), name: newTopic.trim(), status: 'not_found' as const },
    ]);
    setNewTopic('');
  };

  const handleRemoveTopic = (id: string) => {
    setUserTopics(userTopics.filter((t) => t.id !== id));
  };

  const graphNodes: GraphNode[] = analysisResult?.topics ?? [];
  const graphEdges: GraphEdge[] = analysisResult?.relationships ?? [];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Topic Input */}
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
        <h2 className="text-lg font-semibold mb-1">Analyze a Research Topic</h2>
        <p className="text-sm text-[var(--color-text-secondary)] mb-4">
          Enter a topic to discover its concepts, relationships, and research context.
        </p>
        <div className="flex gap-3">
          <input
            type="text"
            value={topicInput}
            onChange={(e) => setTopicInput(e.target.value)}
            placeholder="e.g. transformer attention mechanism"
            className="flex-1 px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
            disabled={analyzing}
          />
          <button
            onClick={handleAnalyze}
            disabled={analyzing || !topicInput.trim()}
            className="px-6 py-2.5 bg-[var(--color-primary)] text-white rounded-lg text-sm font-medium hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            {analyzing ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                Analyze
                <ArrowRight size={14} />
              </>
            )}
          </button>
        </div>
        <div className="flex gap-2 mt-3">
          <span className="text-xs text-[var(--color-text-secondary)]">Try:</span>
          {['transformer attention mechanism', 'graph neural networks', 'few-shot learning'].map((t) => (
            <button
              key={t}
              onClick={() => setTopicInput(t)}
              className="text-xs text-[var(--color-primary)] hover:underline"
              disabled={analyzing}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Progress Bar */}
      {analyzing && analysisStatus && (
        <AnalysisProgress status={analysisStatus} />
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Stats Grid */}
      {analysisResult && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            icon={<BookOpen size={18} />}
            label="Main Topics"
            value={graphNodes.length}
            color="var(--color-purple)"
          />
          <StatCard
            icon={<GitBranch size={18} />}
            label="Relationships"
            value={graphEdges.length}
            color="var(--color-blue)"
          />
          <StatCard
            icon={<Users size={18} />}
            label="Papers Analyzed"
            value={analysisResult.papers.length}
            color="var(--color-teal)"
          />
          <StatCard
            icon={<Sparkles size={18} />}
            label="Unique Insights"
            value={graphNodes.filter((n) => n.source === 'main').length}
            color="var(--color-orange)"
          />
        </div>
      )}

      {/* Papers Found */}
      {analysisResult && analysisResult.papers.length > 0 && (
        <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          <h3 className="font-semibold mb-3">Papers Analyzed</h3>
          <div className="space-y-2">
            {analysisResult.papers.map((paper) => (
              <div key={paper.id} className="flex items-center gap-3 p-2 rounded-lg bg-gray-50">
                <div className="w-8 h-8 rounded bg-[var(--color-blue)] bg-opacity-10 flex items-center justify-center">
                  <BookOpen size={14} className="text-[var(--color-blue)]" />
                </div>
                <div>
                  <div className="text-sm font-medium">{paper.title}</div>
                  <div className="text-xs text-[var(--color-text-secondary)]">{paper.id}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Knowledge Graph (2 columns) */}
        <div className="col-span-2 bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Knowledge Graph</h2>
              <p className="text-sm text-[var(--color-text-secondary)]">
                {analysisResult
                  ? `Topics and relationships from "${analysisResult.topic}"`
                  : 'Analyze a topic to see the knowledge graph'}
              </p>
            </div>
            {analysisResult && (
              <div className="flex gap-2">
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
              </div>
            )}
          </div>
          {graphNodes.length > 0 ? (
            <KnowledgeGraph nodes={graphNodes} edges={graphEdges} height={420} />
          ) : (
            <div className="h-96 bg-gray-50 rounded-lg border border-[var(--color-border)] flex items-center justify-center">
              <div className="text-center">
                <GitBranch size={48} className="mx-auto text-gray-300 mb-3" />
                <p className="text-sm text-[var(--color-text-secondary)]">
                  Knowledge graph will appear here
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Enter a topic above to start analysis
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* User Topics */}
          <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
            <h3 className="font-semibold mb-1">Explore Your Own Topics</h3>
            <p className="text-xs text-[var(--color-text-secondary)] mb-4">
              Add topics you are interested in and see how they connect.
            </p>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={newTopic}
                onChange={(e) => setNewTopic(e.target.value)}
                placeholder="Enter a topic..."
                className="flex-1 px-3 py-2 rounded-lg border border-[var(--color-border)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                onKeyDown={(e) => e.key === 'Enter' && handleAddTopic()}
              />
              <button
                onClick={handleAddTopic}
                className="px-3 py-2 bg-[var(--color-primary)] text-white rounded-lg text-sm hover:bg-[var(--color-primary-hover)]"
              >
                <Plus size={14} />
              </button>
            </div>
            <div className="space-y-2">
              {userTopics.map((topic) => (
                <div key={topic.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50">
                  <span className="text-sm">{topic.name}</span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        topic.status === 'found'
                          ? 'bg-green-100 text-green-700'
                          : topic.status === 'partial'
                          ? 'bg-orange-100 text-orange-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {topic.status}
                    </span>
                    <button onClick={() => handleRemoveTopic(topic.id)} className="text-gray-400 hover:text-gray-600">
                      <X size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Shared vs Unique */}
          {analysisResult && (
            <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
              <h3 className="font-semibold mb-1">Shared vs Unique Insights</h3>
              <p className="text-xs text-[var(--color-text-secondary)] mb-4">
                Compare this topic with its referenced literature.
              </p>
              <div className="space-y-3">
                {[
                  { label: 'Shared', pct: 62, color: 'var(--color-teal)' },
                  { label: 'Unique', pct: 25, color: 'var(--color-purple)' },
                  { label: 'References', pct: 13, color: 'var(--color-blue)' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-3">
                    <div className="w-12 text-right text-sm font-medium">{item.pct}%</div>
                    <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${item.pct}%`, backgroundColor: item.color }} />
                    </div>
                    <span className="text-xs text-[var(--color-text-secondary)] w-20">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  return (
    <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}15`, color }}>
          {icon}
        </div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-[var(--color-text-secondary)]">{label}</div>
    </div>
  );
}
