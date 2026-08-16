import { useState } from 'react';
import {
  GitBranch,
  Sparkles,
  ArrowRight,
  Users,
  BookOpen,
  Plus,
  X,
} from 'lucide-react';

const mockStats = {
  totalTopics: 18,
  totalRelationships: 42,
  referencesAnalyzed: 23,
  uniqueInsights: 15,
  sharedPercentage: 62,
  uniquePercentage: 25,
  referenceOnlyPercentage: 13,
};

const mockRelationships = [
  { id: '1', type: 'improves', count: 8 },
  { id: '2', type: 'enables', count: 7 },
  { id: '3', type: 'uses', count: 6 },
  { id: '4', type: 'applied in', count: 5 },
  { id: '5', type: 'replaces', count: 4 },
  { id: '6', type: 'extends', count: 3 },
];

const mockUserTopics = [
  { id: '1', name: 'Few-shot Learning', status: 'found' as const },
  { id: '2', name: 'Graph Neural Networks', status: 'partial' as const },
  { id: '3', name: 'Quantum Computing', status: 'not_found' as const },
];

export default function Overview() {
  const [arxivInput, setArxivInput] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [userTopics, setUserTopics] = useState(mockUserTopics);
  const [newTopic, setNewTopic] = useState('');

  const handleAnalyze = () => {
    if (!arxivInput) return;
    setIsAnalyzing(true);
    setTimeout(() => setIsAnalyzing(false), 3000);
  };

  const handleAddTopic = () => {
    if (!newTopic.trim()) return;
    setUserTopics([
      ...userTopics,
      {
        id: String(Date.now()),
        name: newTopic.trim(),
        status: 'not_found' as const,
      },
    ]);
    setNewTopic('');
  };

  const handleRemoveTopic = (id: string) => {
    setUserTopics(userTopics.filter((t) => t.id !== id));
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Paper Input */}
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
        <h2 className="text-lg font-semibold mb-1">Analyze an arXiv Paper</h2>
        <p className="text-sm text-[var(--color-text-secondary)] mb-4">
          Enter an arXiv URL or ID to discover its topics, relationships, and research context.
        </p>
        <div className="flex gap-3">
          <input
            type="text"
            value={arxivInput}
            onChange={(e) => setArxivInput(e.target.value)}
            placeholder="https://arxiv.org/abs/2401.12345"
            className="flex-1 px-4 py-2.5 rounded-lg border border-[var(--color-border)] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
          />
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !arxivInput}
            className="px-6 py-2.5 bg-[var(--color-primary)] text-white rounded-lg text-sm font-medium hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            {isAnalyzing ? (
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
          {['2401.12345', '2306.00912', '2210.07113'].map((id) => (
            <button
              key={id}
              onClick={() => setArxivInput(id)}
              className="text-xs text-[var(--color-primary)] hover:underline"
            >
              {id}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          icon={<BookOpen size={18} />}
          label="Main Topics"
          value={mockStats.totalTopics}
          color="var(--color-purple)"
        />
        <StatCard
          icon={<GitBranch size={18} />}
          label="Relationships"
          value={mockStats.totalRelationships}
          color="var(--color-blue)"
        />
        <StatCard
          icon={<Users size={18} />}
          label="References Analyzed"
          value={mockStats.referencesAnalyzed}
          color="var(--color-teal)"
        />
        <StatCard
          icon={<Sparkles size={18} />}
          label="Unique Insights"
          value={mockStats.uniqueInsights}
          color="var(--color-orange)"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Knowledge Graph (2 columns) */}
        <div className="col-span-2 bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Knowledge Graph Overview</h2>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Key topics and relationships from the paper and its references.
              </p>
            </div>
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
          </div>
          <div className="h-96 bg-gray-50 rounded-lg border border-[var(--color-border)] flex items-center justify-center">
            <div className="text-center">
              <GitBranch size={48} className="mx-auto text-gray-300 mb-3" />
              <p className="text-sm text-[var(--color-text-secondary)]">
                Knowledge graph will appear here
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Analyze a paper to visualize topics and relationships
              </p>
            </div>
          </div>
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* User Topics */}
          <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
            <h3 className="font-semibold mb-1">Explore Your Own Topics</h3>
            <p className="text-xs text-[var(--color-text-secondary)] mb-4">
              Add topics you are interested in and see how they connect to the literature.
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
                <div
                  key={topic.id}
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50"
                >
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
                    <button
                      onClick={() => handleRemoveTopic(topic.id)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Shared vs Unique */}
          <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
            <h3 className="font-semibold mb-1">Shared vs Unique Insights</h3>
            <p className="text-xs text-[var(--color-text-secondary)] mb-4">
              Compare this paper with its referenced literature.
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-12 text-right text-sm font-medium">{mockStats.sharedPercentage}%</div>
                <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-teal)]"
                    style={{ width: `${mockStats.sharedPercentage}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--color-text-secondary)] w-20">Shared</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-12 text-right text-sm font-medium">{mockStats.uniquePercentage}%</div>
                <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-purple)]"
                    style={{ width: `${mockStats.uniquePercentage}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--color-text-secondary)] w-20">Unique</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-12 text-right text-sm font-medium">{mockStats.referenceOnlyPercentage}%</div>
                <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-blue)]"
                    style={{ width: `${mockStats.referenceOnlyPercentage}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--color-text-secondary)] w-20">References</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top Relationships */}
        <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          <h3 className="font-semibold mb-1">Top Relationships</h3>
          <p className="text-xs text-[var(--color-text-secondary)] mb-4">
            Most important relationships discovered.
          </p>
          <div className="space-y-3">
            {mockRelationships.map((rel) => (
              <div key={rel.id} className="flex items-center gap-3">
                <span className="text-sm w-24 text-right">{rel.type}</span>
                <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-primary)]"
                    style={{ width: `${(rel.count / 8) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium w-8">{rel.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Document Comparison */}
        <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          <h3 className="font-semibold mb-1">Document Comparison</h3>
          <p className="text-xs text-[var(--color-text-secondary)] mb-4">
            Compare topics and relationships across papers.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)]">
                  <th className="text-left py-2 pr-4 font-medium text-[var(--color-text-secondary)]">Metric</th>
                  <th className="text-center py-2 px-2 font-medium text-[var(--color-purple)]">Main</th>
                  <th className="text-center py-2 px-2 font-medium text-[var(--color-blue)]">Ref 1</th>
                  <th className="text-center py-2 px-2 font-medium text-[var(--color-blue)]">Ref 2</th>
                  <th className="text-center py-2 px-2 font-medium text-[var(--color-blue)]">Ref 3</th>
                </tr>
              </thead>
              <tbody className="text-[var(--color-text-secondary)]">
                <tr className="border-b border-gray-100">
                  <td className="py-2 pr-4">Topics</td>
                  <td className="text-center py-2 px-2">18</td>
                  <td className="text-center py-2 px-2">12</td>
                  <td className="text-center py-2 px-2">15</td>
                  <td className="text-center py-2 px-2">10</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="py-2 pr-4">Relationships</td>
                  <td className="text-center py-2 px-2">42</td>
                  <td className="text-center py-2 px-2">28</td>
                  <td className="text-center py-2 px-2">35</td>
                  <td className="text-center py-2 px-2">22</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4">Shared</td>
                  <td className="text-center py-2 px-2">8</td>
                  <td className="text-center py-2 px-2">6</td>
                  <td className="text-center py-2 px-2">9</td>
                  <td className="text-center py-2 px-2">5</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-5">
      <div className="flex items-center gap-2 mb-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${color}15`, color }}
        >
          {icon}
        </div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-[var(--color-text-secondary)]">{label}</div>
    </div>
  );
}
