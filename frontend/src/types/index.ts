export interface Paper {
  id: string;
  arxivId: string;
  title: string;
  authors: string[];
  abstract: string;
  publishedAt: string;
  url: string;
}

export interface Topic {
  id: string;
  name: string;
  type: 'topic' | 'method' | 'concept' | 'application' | 'dataset' | 'model' | 'technique';
  importance: number;
  source: 'main' | 'reference' | 'shared';
  documents: string[];
}

export interface Relationship {
  id: string;
  source: string;
  target: string;
  relation: string;
  confidence: number;
  documents: string[];
  isUnique?: boolean;
}

export interface Analysis {
  id: string;
  paper: Paper;
  topics: Topic[];
  relationships: Relationship[];
  references: Paper[];
  stats: {
    totalTopics: number;
    totalRelationships: number;
    referencesAnalyzed: number;
    uniqueInsights: number;
    sharedPercentage: number;
    uniquePercentage: number;
  };
  createdAt: string;
}

export interface UserTopic {
  id: string;
  name: string;
  status: 'found' | 'partial' | 'not_found';
  relatedTopics: string[];
  documents: string[];
}

export interface ChunkHighlight {
  start: number;
  end: number;
  kind: 'node' | 'edge';
  label: string;
}

export interface Chunk {
  doc_id: string;
  index: number;
  text: string;
  headings: string[];
  highlights: ChunkHighlight[];
}

export interface ChunksResponse {
  node_id: string;
  chunks: Chunk[];
}
