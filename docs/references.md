# References

## Project context

- The extraction pipeline reuses techniques prototyped in a separate insurance-claims knowledge graph project, applied here to a different domain.

## Libraries

| Library | Role | Link |
| --- | --- | --- |
| GLiNER | zero-shot NER + relation extraction | https://github.com/urchade/GLiNER |
| Qwen3 0.6b (via Ollama) | citation discovery — concepts, types, relations taxonomy, canonicalization | https://ollama.com/library/qwen3 |
| LiteLLM | unified LLM interface (Qwen route, structured output) | https://docs.litellm.ai/ |
| Ollama | local LLM runner (required for citation discovery) | https://ollama.com/ |
| docling | document → structured `DoclingDocument` (layout, tables, markdown) | https://ds4sd.github.io/docling/ |
| docling-core | `HierarchicalChunker` (section-aware chunks) | https://pypi.org/project/docling-core/ |
| networkx | the graph data structure (`networkx.MultiDiGraph`) | https://networkx.org/ |
| vis-network | interactive HTML graph rendering (`graph-viz`) | https://visjs.github.io/vis-network/ |
| HuggingFace Hub CLI | `hf download` for local model cache | https://huggingface.co/docs/huggingface_hub/ |

## Sources & data

| Resource | Link |
| --- | --- |
| arXiv API | https://arxiv.org/help/api |
| `urchade/gliner_multi-v2.1` (relex-large, relation extraction) | https://huggingface.co/urchade/gliner_multi-v2.1 |
| `ollama/qwen3:0.6b` (citation taxonomy) | https://ollama.com/library/qwen3 |
| `docling-project/docling-layout-heron`, `docling-project/docling-models` | https://huggingface.co/docling-project |

## Concepts

| Concept | Why it matters here | Reference |
| --- | --- | --- |
| Weisfeiler-Lehman (WL) kernel | structural similarity between graphs — planned for the originality signal | Shervashidze et al., *Weisfeiler-Lehman Graph Kernels* (2011) |
| Zero-shot NER / relation extraction | GLiNER generalizes to arbitrary labels, which powers the taxonomy-from-discovery loop | GLiNER paper: https://arxiv.org/abs/2311.08526 |
| Knowledge graph construction from documents | broader research area this project sits in | Google Scholar search: *knowledge graph construction from documents* |

## Development tooling

- **CodeGraph** — local code-intelligence index used by devs and AI agents: https://codegraph.ai
- **mkdocs-material** — this documentation site: https://squidfunk.github.io/mkdocs-material/
