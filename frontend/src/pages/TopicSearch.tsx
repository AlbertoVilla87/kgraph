import { useState } from 'react';
import { Search, Plus } from 'lucide-react';

const mockResults = [
  {
    name: 'Graph Neural Networks',
    status: 'found' as const,
    relatedTopics: ['Message Passing', 'Node Classification', 'Graph Convolution'],
    documents: ['Main Paper', 'Ref 3', 'Ref 7'],
    relationships: [
      { source: 'Graph Neural Networks', relation: 'enables', target: 'Node Classification' },
    ],
  },
  {
    name: 'Meta-Learning',
    status: 'found' as const,
    relatedTopics: ['Few-shot Learning', 'Transfer Learning', 'Generalization'],
    documents: ['Ref 2', 'Ref 5'],
    relationships: [
      { source: 'Meta-Learning', relation: 'enables', target: 'Few-shot Learning' },
    ],
  },
];

export default function TopicSearch() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);

  const filteredResults = mockResults.filter((r) =>
    r.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const selected = mockResults.find((r) => r.name === selectedTopic);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Topic Search</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Add topics you are interested in and see how they connect to the literature.
        </p>
      </div>

      {/* Search Input */}
      <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Enter a topic (e.g. 'few-shot learning')"
              className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-[var(--color-border)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            />
          </div>
          <button className="px-4 py-2.5 bg-[var(--color-primary)] text-white rounded-lg text-sm font-medium hover:bg-[var(--color-primary-hover)] flex items-center gap-2">
            <Plus size={14} />
            Add
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Results List */}
        <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          <h3 className="font-semibold mb-4">Discovered Topics</h3>
          <div className="space-y-2">
            {filteredResults.map((topic) => (
              <button
                key={topic.name}
                onClick={() => setSelectedTopic(topic.name)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  selectedTopic === topic.name
                    ? 'bg-[var(--color-primary)] bg-opacity-10 border border-[var(--color-primary)]'
                    : 'bg-gray-50 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{topic.name}</span>
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
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Topic Details */}
        <div className="col-span-2 bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
          {selected ? (
            <>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">{selected.name}</h3>
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    selected.status === 'found'
                      ? 'bg-green-100 text-green-700'
                      : selected.status === 'partial'
                      ? 'bg-orange-100 text-orange-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {selected.status}
                </span>
              </div>

              {/* Found in */}
              <div className="mb-6">
                <h4 className="text-sm font-medium mb-2">Found in</h4>
                <div className="flex gap-2">
                  {selected.documents.map((doc) => (
                    <span
                      key={doc}
                      className="px-3 py-1 rounded-full text-xs bg-blue-100 text-blue-700"
                    >
                      {doc}
                    </span>
                  ))}
                </div>
              </div>

              {/* Related Topics */}
              <div className="mb-6">
                <h4 className="text-sm font-medium mb-2">Related discovered topics</h4>
                <div className="flex gap-2">
                  {selected.relatedTopics.map((topic) => (
                    <span
                      key={topic}
                      className="px-3 py-1 rounded-full text-xs bg-gray-100 text-gray-700"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>

              {/* Relationships */}
              <div className="mb-6">
                <h4 className="text-sm font-medium mb-2">Relationships</h4>
                <div className="space-y-2">
                  {selected.relationships.map((rel) => (
                    <div
                      key={`${rel.source}-${rel.relation}-${rel.target}`}
                      className="p-3 rounded-lg bg-gray-50"
                    >
                      <span className="text-sm">
                        <span className="font-medium">{rel.source}</span>
                        <span className="text-[var(--color-text-secondary)] mx-2">
                          → {rel.relation} →
                        </span>
                        <span className="font-medium">{rel.target}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <button className="px-4 py-2 bg-[var(--color-primary)] text-white rounded-lg text-sm font-medium hover:bg-[var(--color-primary-hover)]">
                Show in Graph
              </button>
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-[var(--color-text-secondary)]">
              Select a topic to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
