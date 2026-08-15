# Corpus & multi-document — stage 6

`corpus-demo` (`kgraph/corpus/merge.py`) scales the assembly pipeline to a **folder of documents** and turns them into a cross-document graph. Instead of one graph per document, it builds:

1. A **per-document taxonomy** — discovery (stages 1–3) runs independently on each document, so each paper contributes its own entity/relation labels.
2. **Parallel extraction** — every segment of every document is submitted to a thread pool (`--workers`, one shared GLiNER model), with tqdm progress bars for the three stages (docling parsing, taxonomy, extraction).
3. **A merged graph with an originality view** — `CorpusGraphBuilder.build` unions the per-document graphs and labels each node/edge as **common** (present in ≥2 documents) or **unique** to a single document, plus a per-document novelty ratio.

The interactive HTML (`--output-html`) renders common nodes/edges in green and document-unique ones in each document's palette color, with a summary/novelty panel and a per-document filter; nodes without edges are not drawn:

![Multi-document corpus graph](../assets/multi_graph.jpg)

```sh
uv run corpus-demo --workers 4 --max-pages 10   # local PDF folder, parallel, drop long papers
uv run corpus-demo --fetch 5 --arxiv-query '"LLM agents"'  # download arXiv PDFs first
```

## Known limitations

- Each `build()` call must start from a fresh `TopicGraph` per document — `TopicGraph.build` accumulates into `self.graph`, so reusing one instance across documents contaminates later taxonomies (`CorpusGraphBuilder` builds a fresh one per document).
- Cross-document **entity matching is lexical** (canonical/containment merging): the same concept phrased differently across papers still counts as two unique nodes, which inflates the novelty view.
