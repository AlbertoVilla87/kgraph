import { useState } from 'react';
import { Sparkles, TrendingUp } from 'lucide-react';

const uniqueTopics = [
  { name: 'New positional encoding approach', documents: 1, confidence: 0.85 },
  { name: 'Scaled dot-product attention efficiency', documents: 1, confidence: 0.78 },
  { name: 'Parallelization advantages', documents: 1, confidence: 0.72 },
  { name: 'Combination of self-attention and feed-forward layers', documents: 1, confidence: 0.68 },
];

const uniqueRelationships = [
  { source: 'Self-Attention', relation: 'improves', target: 'Long Context Reasoning', documents: 1 },
  { source: 'Transformer', relation: 'enables', target: 'Parallelization', documents: 1 },
];

const researchGaps = [
  { name: 'Long-term memory integration', relatedTopics: ['Attention', 'Memory'], documents: 0 },
  { name: 'Interpretability of attention', relatedTopics: ['Attention', 'Explainability'], documents: 1 },
  { name: 'Low-resource language generalization', relatedTopics: ['NMT', 'Transfer Learning'], documents: 1 },
  { name: 'Energy efficiency', relatedTopics: ['Training', 'Hardware'], documents: 0 },
];

export default function Originality() {
  const [activeTab, setActiveTab] = useState<'topics' | 'relationships'>('topics');

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Originality & Inspiration</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Focus on what is new, what is shared, and what may be missing.
        </p>
      </div>

      {/* Unique Contributions */}
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={18} className="text-[var(--color-purple)]" />
          <h3 className="font-semibold">Potential Unique Contributions</h3>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] mb-4">
          Concepts and relationships that appear unique within the analyzed reference corpus.
        </p>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('topics')}
className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'topics'
                  ? 'text-[#04201c] bg-[var(--color-primary)]'
                  : 'bg-[var(--color-surface-2)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-3)] hover:text-[var(--color-text)]'
              }`}
          >
            Topics
          </button>
          <button
            onClick={() => setActiveTab('relationships')}
className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'relationships'
                  ? 'text-[#04201c] bg-[var(--color-primary)]'
                  : 'bg-[var(--color-surface-2)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-3)] hover:text-[var(--color-text)]'
              }`}
          >
            Relationships
          </button>
        </div>

        {activeTab === 'topics' ? (
          <div className="space-y-2">
            {uniqueTopics.map((topic) => (
              <div
                key={topic.name}
                className="flex items-center justify-between p-3 rounded-lg bg-[var(--color-surface-2)] hover:bg-[var(--color-surface-3)] cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-[var(--color-purple)]" />
                  <span className="text-sm font-medium">{topic.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-[var(--color-text-secondary)]">
                    {topic.documents} docs
                  </span>
                  <span
                    className={`text-xs font-medium ${
                      topic.confidence >= 0.8
                        ? 'text-[var(--color-success)]'
                        : topic.confidence >= 0.6
                        ? 'text-[var(--color-warning)]'
                        : 'text-[var(--color-error)]'
                    }`}
                  >
                    {Math.round(topic.confidence * 100)}% conf.
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {uniqueRelationships.map((rel) => (
              <div
                key={`${rel.source}-${rel.relation}-${rel.target}`}
className="p-3 rounded-lg bg-[var(--color-surface-2)] hover:bg-[var(--color-surface-3)] cursor-pointer"
              >
                <div className="text-sm">
                  <span className="font-medium">{rel.source}</span>
                  <span className="text-[var(--color-text-secondary)] mx-2">→ {rel.relation} →</span>
                  <span className="font-medium">{rel.target}</span>
                </div>
                <div className="text-xs text-[var(--color-purple)] mt-1">
                  {rel.documents} document (unique)
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Research Gaps */}
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={18} className="text-[var(--color-orange)]" />
          <h3 className="font-semibold">Potential Research Gaps</h3>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] mb-4">
          Missing or weakly connected areas between topics.
        </p>
        <div className="space-y-2">
          {researchGaps.map((gap) => (
            <div
              key={gap.name}
              className="p-3 rounded-lg bg-[var(--color-surface-2)] hover:bg-[var(--color-surface-3)] cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{gap.name}</span>
                <span
                  className={`text-xs font-medium ${
                    gap.documents === 0 ? 'text-[var(--color-error)]' : 'text-[var(--color-warning)]'
                  }`}
                >
                  {gap.documents === 0 ? 'No evidence' : 'Weak evidence'}
                </span>
              </div>
              <div className="flex gap-2 mt-2">
                {gap.relatedTopics.map((topic) => (
                  <span
                    key={topic}
                    className="px-2 py-0.5 rounded-full text-[10px] bg-[var(--color-surface-3)] text-[var(--color-text-secondary)]"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
