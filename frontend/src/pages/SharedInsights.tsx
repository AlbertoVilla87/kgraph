import { Layers } from 'lucide-react';

const sharedTopics = [
  { name: 'Transformer Architecture', documents: 5, type: 'Core' },
  { name: 'Attention Mechanism', documents: 4, type: 'Core' },
  { name: 'Self-Attention', documents: 3, type: 'Mechanism' },
  { name: 'Sequence Modeling', documents: 4, type: 'Task' },
  { name: 'Neural Machine Translation', documents: 3, type: 'Application' },
];

const sharedRelationships = [
  { source: 'Attention Mechanism', relation: 'improves', target: 'Translation', documents: 4 },
  { source: 'Self-Attention', relation: 'enables', target: 'Transformer', documents: 3 },
  { source: 'Positional Encoding', relation: 'required by', target: 'Self-Attention', documents: 3 },
];

export default function SharedInsights() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Shared Insights</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Explore concepts and relationships shared between documents.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Shared Topics */}
        <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          <div className="flex items-center gap-2 mb-4">
            <Layers size={18} className="text-[var(--color-teal)]" />
            <h3 className="font-semibold">Shared Topics</h3>
          </div>
          <div className="space-y-3">
            {sharedTopics.map((topic) => (
              <div
                key={topic.name}
                className="flex items-center justify-between p-3 rounded-lg bg-[var(--color-surface-2)] hover:bg-[var(--color-surface-3)] cursor-pointer transition-colors"
              >
                <div>
                  <div className="text-sm font-medium">{topic.name}</div>
                  <div className="text-xs text-[var(--color-text-secondary)]">{topic.type}</div>
                </div>
                <div className="text-xs text-[var(--color-teal)] font-medium">
                  {topic.documents} docs
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Shared Relationships */}
        <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          <div className="flex items-center gap-2 mb-4">
            <Layers size={18} className="text-[var(--color-teal)]" />
            <h3 className="font-semibold">Shared Relationships</h3>
          </div>
          <div className="space-y-3">
            {sharedRelationships.map((rel) => (
              <div
                key={`${rel.source}-${rel.relation}-${rel.target}`}
                className="p-3 rounded-lg bg-[var(--color-surface-2)] hover:bg-[var(--color-surface-3)] cursor-pointer transition-colors"
              >
                <div className="text-sm">
                  <span className="font-medium">{rel.source}</span>
                  <span className="text-[var(--color-text-secondary)] mx-2">→ {rel.relation} →</span>
                  <span className="font-medium">{rel.target}</span>
                </div>
                <div className="text-xs text-[var(--color-teal)] mt-1">
                  {rel.documents} documents
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
