# Assembly — stage 4 (discovered taxonomy → GLiNER)

`DiscoveryAssembly` (in `kgraph/discovery/assembly.py`) closes the loop. After the topic graph is built, the discovered nodes and edges become the label set GLiNER extracts with:

```python
entity_labels   = [data["text"] for _, data in discovery_graph.nodes(data=True)]
relation_labels = [data["relation"] for _, _, data in discovery_graph.edges(data=True)]
```

**Labels are underscore-joined.** GLiNER tokenizes labels on whitespace, so a multi-word taxonomy like `dumping papers` is ambiguous ("dumping" and "papers" read as two separate labels). `DiscoveryAssembly._label` replaces every space with `_` before handing the taxonomy to GLiNER:

```python
"dumping papers"  →  "dumping_papers"      # one label
"describe"        →  "describe"            # single word, unchanged
```

`build_pipeline_config` overrides the static `entities`/`relations` in `params.yaml` with these two lists, and `GLiNERGraph` builds the final graph from the same documents. The pipeline is therefore **self-tuning**: the taxonomy is not hand-written but derived from what the document actually talks about.

## Merging in `GLiNERGraph`

**Relations.** Duplicate relations (the same head/relation/tail decoded from several overlapping entity spans) are merged in `GLiNERGraph.add_relation`: the edge keeps the **maximum score** and a `count` attribute records how often it was observed, so the retriever can rank by both confidence and supporting evidence.

**Entities.** `GLiNERGraph.add_entity` deduplicates nodes through `kgraph/extractors/normalization.py` instead of a plain lowercased key:

- **`canonical(text)`** — lowercases, collapses whitespace, and strips a leading article, so `"A CoT-trained model"` and `"CoT-trained model"` canonicalize to the same key.
- **`EntityMerger`** (enabled via `entity_merging.enabled` in `params.yaml`) adds a second, containment-based pass: `token_subset(short, long)` is true when every token of one text appears in the other (e.g. `model` ⊆ `reasoning model`, `artifacts` ⊆ `formatting artifacts`). The shorter text merges into the longer, keeping the more specific label.

Merging keeps the node with the best score, accumulates mentions, and updates the entity-type index accordingly. `find_entity` uses the same `canonical` key so relations still resolve against merged nodes.

## Configuration

The config exposes an `entity_merging` block used by this stage:

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Toggle the near-duplicate entity merge in `GLiNERGraph.add_entity` |
| `threshold` | `0.85` | Reserved for the embedding-similarity merge pass (not yet wired up) |
| `model` | `models/all-MiniLM-L6-v2` | Reserved for the embedding-similarity merge pass (not yet wired up) |

The static `entities` / `relations` lists in `params.yaml` are overridden by the discovered taxonomy; they remain as fallback/standalone labels (e.g. for `gliner-demo`).

## Demo output (medium case)

`uv run assembly-demo` extracts 4 entities and 8 raw relations from `data/case_2/medium.txt`, merged into a final graph of **4 entities and 2 unique relations**:

```text
Karpathy --[describe (0.91, x4)]--> papers
Safi Shamsi --[release (0.99, x4)]--> Graphify
```

> **Known caveat — GLiNER truncates long documents.** GLiNER's context window is 1024 tokens; `medium.txt` is 2388 tokens, so the whole-document path only analyzes the first half and emits a `UserWarning` (`Sentence of length 2388 has been truncated to 1024`). This is now solved by the segmented extractor — see [Segmentation](segmentation.md).

## Continue reading

- [Segmentation](segmentation.md) — running the same assembly over token-bounded segments
- [Data model & configuration](data-model.md) — `Entity` / `Relation` schemas and the full `params.yaml` reference
- [Citation-guided discovery](discovery.md#citation-guided-discovery-alternative) — an alternative assembly path that uses the seed's citations to define the taxonomy

---

# Citation-guided assembly

`CitationAssembly` (in `kgraph/discovery/citation_assembly.py`) orchestrates the alternative pipeline validated in Experiment 04:

```python
assembly = CitationAssembly("./configs/params.yaml")
result = assembly.run(seed_doc, ref_docs, bibliography)

result.graph                    # GLiNERGraph with the final KG
result.node_classifications     # nid → "core" | "seed-only" | "refs-only"
result.discovery                # CitationDiscoveryResult for inspection
```

### Pipeline

1. **CitationDiscovery.build()** — parses bibliography, finds citing contexts, runs Qwen, aggregates taxonomy
2. **Per-document GLiNER extraction** — each reference uses its own Qwen-derived labels; the seed uses the union of all
3. **Node classification** — entities are tagged by where they survived (core / seed-only / refs-only)
4. **Metadata enrichment** — year and entity_type from Qwen are added to each node

### Classification

| Class | Meaning | Example |
| --- | --- | --- |
| **core** | In seed + ≥1 references | "query focused summarization" (seed + 4 refs) |
| **seed-only** | Only in the seed | "GraphRAG" (the paper's own contribution) |
| **refs-only** | Only in references | "T5" (background model) |

This classification is a cheap originality proxy: if the seed-only class is empty, the paper may be more derivative than it sounds.
