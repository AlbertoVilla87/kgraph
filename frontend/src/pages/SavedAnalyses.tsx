import { Eye, GitBranch, Trash2 } from 'lucide-react';

const savedAnalyses = [
  {
    id: '1',
    title: 'Attention Is All You Need',
    arxivId: '1706.03762',
    date: '2024-01-15',
    topics: 18,
    references: 23,
    uniqueInsights: 15,
  },
  {
    id: '2',
    title: 'BERT: Pre-training of Deep Bidirectional Transformers',
    arxivId: '1810.04805',
    date: '2024-01-14',
    topics: 22,
    references: 31,
    uniqueInsights: 18,
  },
  {
    id: '3',
    title: 'GPT-4 Technical Report',
    arxivId: '2303.08774',
    date: '2024-01-12',
    topics: 35,
    references: 45,
    uniqueInsights: 28,
  },
];

export default function SavedAnalyses() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Saved Analyses</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Previously analyzed papers.
        </p>
      </div>

      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)]">
              <th className="text-left py-3 px-6 text-sm font-medium text-[var(--color-text-secondary)]">
                Paper
              </th>
              <th className="text-left py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                arXiv ID
              </th>
              <th className="text-left py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Date
              </th>
              <th className="text-center py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Topics
              </th>
              <th className="text-center py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                References
              </th>
              <th className="text-center py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Unique
              </th>
              <th className="text-center py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {savedAnalyses.map((analysis) => (
              <tr
                key={analysis.id}
                className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-2)] transition-colors"
              >
                <td className="py-4 px-6">
                  <div className="text-sm font-medium">{analysis.title}</div>
                </td>
                <td className="py-4 px-4">
                  <span className="text-sm text-[var(--color-primary)]">{analysis.arxivId}</span>
                </td>
                <td className="py-4 px-4">
                  <span className="text-sm text-[var(--color-text-secondary)]">{analysis.date}</span>
                </td>
                <td className="py-4 px-4 text-center">
                  <span className="text-sm font-medium">{analysis.topics}</span>
                </td>
                <td className="py-4 px-4 text-center">
                  <span className="text-sm font-medium">{analysis.references}</span>
                </td>
                <td className="py-4 px-4 text-center">
                  <span className="text-sm font-medium text-[var(--color-purple)]">
                    {analysis.uniqueInsights}
                  </span>
                </td>
                <td className="py-4 px-4">
                  <div className="flex items-center justify-center gap-2">
                    <button className="p-1.5 rounded-lg hover:bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] hover:text-[var(--color-primary)]">
                      <Eye size={14} />
                    </button>
                    <button className="p-1.5 rounded-lg hover:bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] hover:text-[var(--color-blue)]">
                      <GitBranch size={14} />
                    </button>
                    <button className="p-1.5 rounded-lg hover:bg-[var(--color-surface-3)] text-[var(--color-text-secondary)] hover:text-[var(--color-error)]">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
