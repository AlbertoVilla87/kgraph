# KG Builder Lab

## Introduction

Experimenting with multiple approaches to knowledge graph construction from documents

---

## Approaches

-  Adaptive KeyBERT + Topic Discovery

---

## Installation

```bash
uv add mkdocs-material
uv run mkdocs serve
```

Open `http://127.0.0.1:8000` in your browser and you'll see the site running locally with live reload.

---

## Project structure

```
doc/
├── mkdocs.yml
└── docs/
    └── index.md
```

!!! tip "Adding more pages"
    Create new `.md` files inside `docs/` and register them in the `nav:` section of `mkdocs.yml`.