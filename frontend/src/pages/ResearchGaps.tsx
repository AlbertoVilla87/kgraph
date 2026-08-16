import { Search, AlertTriangle, TrendingUp } from 'lucide-react';

const missingTopics = [
  { name: 'Long-term memory integration', relatedTopics: ['Attention', 'Memory'], documents: ['Ref 3', 'Ref 7'] },
  { name: 'Interpretability of attention', relatedTopics: ['Attention', 'Explainability'], documents: ['Ref 2'] },
];

const missingRelationships = [
  { source: 'Transformer', relation: 'applied in', target: 'Computer Vision', documents: [] },
  { source: 'Attention', relation: 'improves', target: 'Long-term Dependencies', documents: ['Ref 5'] },
];

const underexploredCombinations = [
  { topics: ['Transformer', 'Graph Neural Networks', 'Few-shot Learning'], evidence: 0 },
  { topics: ['Attention', 'Neuromorphic Computing', 'Energy Efficiency'], evidence: 1 },
];

export default function ResearchGaps() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Research Gaps</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Missing or weakly connected areas between topics.
        </p>
      </div>

      {/* Missing Topics */}
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle size={18} className="text-[var(--color-warning)]" />
          <h3 className="font-semibold">Missing Topics</h3>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] mb-4">
          Important concepts found in related literature but not connected to the analyzed paper.
        </p>
        <div className="space-y-2">
          {missingTopics.map((topic) => (
            <div
              key={topic.name}
              className="p-3 rounded-lg bg-gray-50 hover:bg-gray-100 cursor-pointer"
            >
              <div className="text-sm font-medium">{topic.name}</div>
              <div className="flex items-center gap-4 mt-2">
                <div className="flex gap-1">
                  {topic.relatedTopics.map((t) => (
                    <span key={t} className="px-2 py-0.5 rounded-full text-[10px] bg-gray-200 text-gray-600">
                      {t}
                    </span>
                  ))}
                </div>
                <span className="text-xs text-[var(--color-text-secondary)]">
                  Found in: {topic.documents.join(', ')}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Missing Relationships */}
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <Search size={18} className="text-[var(--color-blue)]" />
          <h3 className="font-semibold">Missing Relationships</h3>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] mb-4">
          Two topics exist in the corpus, but their relationship is not present in the analyzed paper.
        </p>
        <div className="space-y-2">
          {missingRelationships.map((rel) => (
            <div
              key={`${rel.source}-${rel.relation}-${rel.target}`}
              className="p-3 rounded-lg bg-gray-50 hover:bg-gray-100 cursor-pointer"
            >
              <div className="text-sm">
                <span className="font-medium">{rel.source}</span>
                <span className="text-[var(--color-text-secondary)] mx-2">→ {rel.relation} →</span>
                <span className="font-medium">{rel.target}</span>
              </div>
              <div className="text-xs text-[var(--color-text-secondary)] mt-1">
                {rel.documents.length === 0
                  ? 'No evidence in corpus'
                  : `Found in: ${rel.documents.join(', ')}`}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Underexplored Combinations */}
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={18} className="text-[var(--color-teal)]" />
          <h3 className="font-semibold">Underexplored Combinations</h3>
        </div>
        <p className="text-xs text-[var(--color-text-secondary)] mb-4">
          Concept combinations appearing in different documents but rarely connected.
        </p>
        <div className="space-y-3">
          {underexploredCombinations.map((combo) => (
            <div
              key={combo.topics.join('-')}
              className="p-4 rounded-lg bg-gray-50 border border-dashed border-gray-300"
            >
              <div className="flex items-center gap-2">
                {combo.topics.map((topic, i) => (
                  <span key={topic} className="flex items-center gap-2">
                    <span className="px-3 py-1 rounded-full text-sm bg-[var(--color-teal)] bg-opacity-10 text-[var(--color-teal)] font-medium">
                      {topic}
                    </span>
                    {i < combo.topics.length - 1 && (
                      <span className="text-gray-400">+</span>
                    )}
                  </span>
                ))}
              </div>
              <div className="text-xs text-[var(--color-text-secondary)] mt-2">
                {combo.evidence === 0
                  ? 'No direct connections found'
                  : `${combo.evidence} weak connection(s) found`}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
