# Discovery — stages 1–3 (LLM-free)

Discovery grows the *topic graph* from the document: the seeds and relations that later become GLiNER's label taxonomy. It is deliberately **LLM-free and deterministic** — a small local model hallucinated evidence and generic relations during early exploration, so it was dropped from discovery.

**The key idea: KeyBERT provides the seeds, and from those seeds the pipeline discovers both the relations and the new topics — iteratively and without an LLM.**

The design is a synthesis of two extremes that were both unsatisfactory on their own:

- **KeyBERT alone falls short** — it returns a handful of phrases and no relationships between them.
- **Extracting every subject-verb-object triple** (the naive spaCy approach) is too much — every sentence of the document produces edges, drowning the signal in noise.

The compromise is a **topic-guided expansion**: only the relations whose endpoints touch a *known* topic are kept, and each new endpoint becomes a topic that can be expanded in turn, up to a configured depth.

## Stage 1 — Adaptive KeyBERT (seeds)

`AdaptiveKeyBERT` (in `kgraph/extractors/key_bert.py`) replaces a fixed `top_n` with an **adaptive count** driven by two signals: document length and the shape of the similarity scores.

### The adaptive count algorithm

1. **Generous pool.** Ask KeyBERT for a wide pool of candidates (`use_maxsum=True` for diversity), scaled to document length:

   ```python
   est = round(n_words / words_per_kw)              # length signal
   pool = max(max_k, min(max_candidates, est))
   ```

2. **Noise floor.** Drop anything below `score_floor`.

3. **Elbow cutoff.** Look for the *knee* of the sorted similarity scores inside the `[min_k, max_k]` window, using the `kneed` library:

   ```python
   window = scores[min_k - 1 : min(max_k, len(scores))]
   knee = KneeLocator(x, window, curve="convex", direction="decreasing").knee
   cutoff = max(min_k, min(max_k, knee))
   ```

   The idea: KeyBERT's scores normally drop sharply at the point where "this describes the text" becomes "this is filler".

### Configuration

Under `keyword_extractor.adaptive` in `backend/configs/params.yaml`:

| Key | Default | Meaning |
| --- | --- | --- |
| `min_k` | 2 | Minimum keywords to keep |
| `max_k` | 20 | Upper bound of the elbow search window |
| `words_per_kw` | 40 | Length scaling: ~1 keyword per N words |
| `score_floor` | 0.2 | Relevance threshold below which candidates are dropped |
| `max_candidates` | 25 | Cap on the generous pool requested from KeyBERT |

## Stage 2 — Relation extraction (spaCy dependencies, no LLM)

`DependencyRelationExtractor` (in `kgraph/discovery/dependency_relations.py`) extracts relations from the dependency tree. For each sentence it takes the predicate verbs — the root verb plus verb complements/conjuncts (`xcomp`, `ccomp`, `conj`) — and derives the arguments from each verb:

```python
for sent in nlp(doc).sents:
    root = sent.root
    for verb in _verbs(root):        # root + xcomp / ccomp / conj
        subj = _subject(verb, root)  # nsubj / nsubjpass
        obj  = _object(verb)         # dobj, or pobj of a preposition
        label = f"{verb.lemma_} {prep}"   # "obtained from", "reported to"
```

Key rules:

- **Relation labels are auto-discovered.** The label is the verb lemma plus its preposition ("obtained from", "reported to", "charging"). There is no ontology — it emerges from the parse.
- **Pronoun subjects are dropped as nodes.** When the subject is a pronoun ("I obtained..."), the relation is re-anchored between the direct object and the prepositional object: *"I obtained a mortgage loan from Meridian Home Lending"* → `mortgage loan --obtained from--> Meridian Home Lending`.
- **Prepositions attached to nouns are also followed** (*"reported the missed payments **to Equifax**"*, where `to` hangs off `payments`).
- The **evidence** is always the sentence the relation was parsed from — it cannot be hallucinated because nothing generates it.

### A worked example

Sentences in, relations out:

```text
"I obtained a mortgage loan from Meridian Home Lending in June 2021."
  → mortgage loan --obtain from--> Meridian Home Lending
  → mortgage loan --obtain in--> June

"The servicing of my loan was transferred to Summit Loan Servicing."
  → servicing --transfer to--> Summit Loan Servicing

"Summit Loan Servicing reported the missed payments to Equifax."
  → Summit Loan Servicing --report--> missed payments
  → Summit Loan Servicing --report to--> Equifax        # 'to' hangs off the noun

"Summit Loan Servicing began charging me a late fee of $75."
  → Summit Loan Servicing --charge--> late fee          # 'charging' is xcomp of 'began'
```

Note what the rules do on the first example: the subject `I` is a pronoun, so the relation is re-anchored between the object `mortgage loan` and the prepositional object `Meridian Home Lending`, and the label becomes the verb lemma plus its preposition (`obtain from`).

## Stage 3 — Topic-guided expansion (BFS)

`TopicGraph` (in `kgraph/discovery/topic_graph.py`) grows the graph from the seeds:

```python
queue = deque(seeds)                    # depth 0
while queue:
    topic = queue.popleft()
    if depth(topic) >= max_depth:
        continue
    for rel in relations:
        if not (touches(rel.source, topic) or touches(rel.target, topic)):
            continue                    # relation not related to a known topic
        add_edge(rel)
        for endpoint in (rel.source, rel.target):
            if endpoint != topic and endpoint not in graph:
                add_node(endpoint, depth + 1)
                queue.append(endpoint)  # new topic to expand
```

- **`touches`** is a token overlap between the endpoint and the topic (e.g. the seed `payments equifax` pulls in `missed payments` because they share `payments`).
- Every endpoint that is not the topic itself and not yet in the graph becomes a **new node at `depth + 1`** and is queued for expansion — this is how new topics keep appearing from the seeds.
- Duplicate edges and the seed phrases themselves (which may not appear verbatim in the text) are handled: edges are deduplicated by `(source, target, relation)`.

### A worked example

Seeds are enqueued at depth 0 and expanded breadth-first. Each expansion pulls every relation touching the topic, and the *other* endpoint becomes a new node:

```text
depth 0  payments equifax  ·  late fee
         │
         ├─ report ─────────────►  missed payments   (shares "payments")
         ├─ report to ──────────►  Equifax           (shares "equifax")
         └─ charging ──────────►  late fee           (a seed itself)

depth 1  Summit Loan Servicing  ·  missed payments  ·  Equifax
         │
         ├─ transfer to ────────►  servicing
         ├─ respond to ────────►  my dispute
         ├─ obtain from ───────►  Meridian Home Lending   (via shared "loan")
         └─ receive from ──────►  foreclosure notice
```

The expansion stops because the nodes it reaches are at `max_depth = 2`; the graph is seeded, not exhaustive.

### Configuration

Under `discovery` in `backend/configs/params.yaml`:

| Key | Default | Meaning |
| --- | --- | --- |
| `spacy_model` | `models/en_core_web_sm` | Local spaCy model; swap for another language (e.g. `models/es_core_news_sm`) |
| `determiners` | `[]` | Extra leading determiners stripped from spans, added to the English defaults (`the`, `a`, `an`) |
| `max_depth` | 2 | Maximum hops from the seeds (how far the expansion may grow) |
| `max_relations` | 100 | Hard cap on the number of graph edges |
| `skip_headings` | `references, bibliography, acknowledgements, acknowledgments` | Section headings excluded from discovery (boilerplate) |
| `max_seeds` | 25 | Cap on the unioned per-section seed pool handed to the expansion |

> Discovery runs **per document section** (docling heading paths when available, markdown headings otherwise), and the seeds/relations are unioned into one consistent label set — so the taxonomy keeps the whole document's vocabulary instead of abstract-level boilerplate. Boilerplate sections are skipped via `discovery.skip_headings` and the seed pool is capped by `discovery.max_seeds`.

### Demo output (CoT RL case)

Seeds `commonsense reasoning` and `model reason` expand into a 16-node graph (2 seeds at depth 0, 12 nodes at depth 1, 2 at depth 2) with 9 unique relations, e.g.:

```text
model          --exploit--> formatting artifacts
CoT RL model   --discover in--> principle
CoT-trained model --learn--> decomposition
CoT RL         --extend--> this idea
```

### Demo output (medium case)

`data/case_2/medium.txt` is the current default corpus. Seeds `described dumping` and `graphify credible` expand into a 7-node graph (2 at depth 0, 4 at depth 1, 1 at depth 2) with 3 unique relations:

```text
(d1) Karpathy --[describe]--> (d1) dumping papers
(d1) Karpathy --[articulate]--> (d2) shift
(d1) developer --[release]--> (d1) Graphify
```

## Continue reading

The discovered taxonomy is handed to GLiNER in [Assembly](assembly.md).
