---
name: architecture-diagram
description: Draw or update architecture / box diagrams as editable draw.io files (e.g. deploy.drawio) with real technology icons (simple-icons, base64-embedded and self-contained), export them to PNG with the draw.io CLI, and document them in the mkdocs site. Use when the user asks in any language to "draw a diagram", "diagrama", "dibuja un esquema", "arquitectura", "architecture diagram", mentions "draw.io"/"drawio", or references one of the *.drawio files in the repo. Works both for creating a diagram from scratch and for updating an existing one (either way: regenerate + re-export + sync docs). Do not use for UML data models or Mermaid-only flowcharts — those have other homes in the docs.
---

# Architecture diagrams (draw.io)

Box-and-icon architecture diagrams, stored as **editable draw.io files** with
technology logos embedded as base64 so they render offline, exported to a PNG
for the docs, and described on a docs page. The flip side of "draw a diagram"
is "update it": **never leave the `.drawio`, its PNG, and the docs page out of
sync**.

The canonical, working example in this repo is
`docs/assets/deploy.drawio` (source: `scripts/gen_deploy_drawio.mjs`, page:
`docs/architecture/deployment.md`). When updating, **prefer editing the
generator script over the XML** unless the user has hand-tweaked the diagram in
the draw.io app, in which case EDIT THE `.drawio` DIRECTLY so their manual
changes are preserved.

## Methodology (in order)

1. **Understand the system.** Use `codegraph_explore` / read / grep to identify
   the real components, data flows, and constraints of the code or infra being
   diagrammed. Cite actual files (e.g. `backend/src/kgraph/api/main.py`). Only
   include what exists or what the design phase explicitly proposes.
2. **Decide scope.** Solid = in scope now; dashed = optional / planned. Ask up
   front about ambiguous choices that change the boxes (e.g. optional Ollama,
   ALB, S3). State the product-style questions as a short question list.
3. **Design the layout first** (canvas ~1400x720): zones left→right
   `Client → AWS edge → EC2 host (Docker Compose) → external services`, title
   top-left, legend bottom-left. Sketch boxes and edges; then translate to code.
4. **Create or update the diagram** as a *layout-driven* generator script (see
   below) that emits BOTH the `.drawio` and the docs PNG from the same layout,
   so the docs image never depends on the draw.io CLI (its headless exporter
   **ignores embedded images entirely** — see Gotchas).
5. **Render** = run the generator (`node <script>.mjs`); it writes the PNG via
   its own SVG renderer + sharp.
6. **Sync the docs**: docs page, `mkdocs.yml` nav, `architecture/index.md`
   page index. Validate with `uv run mkdocs build`.
7. **Verify programmatically** (opencode cannot view images): run
   `node scripts/verify_icons.mjs` — it renders the SVG twice (normal vs. icon
   paths blanked) and diffs each icon region, so a missing logo fails loudly.
   Then tell the user to open the PNG/`.drawio` and confirm the layout.

## Creating (from scratch)

Use `scripts/gen_deploy_drawio.mjs` as the template — copy it, rename the
output path, and adjust `ICON_SLUGS` and the layout calls.

The script must be **layout-driven** (one element list → two emitters) and must:
- fetch each icon SVG from
  `https://cdn.jsdelivr.net/npm/simple-icons@14/icons/<slug>.svg`,
- for the **docs PNG**: embed the simple-icons **vector `<path d>`** (they live
  in a 24x24 viewBox → `<g transform="translate(x y) scale(w/24)"><path d=…/></g>`).
  Do NOT use SVG `<image>` raster elements there — sharp's renderer drops alpha
  and prints a solid black block;
- for the **`.drawio`** (human-editable, desktop app): rasterize the icon with
  `sharp` (`resize(64,64)`) and base64-embed as `data:image/png;base64,…`;
- emit every draw.io cell with `vertex="1"` / `edge="1"` **and `parent="1"`** (see
  Gotchas — missing `parent`/`vertex` is the #1 export failure);
- write a valid single-`<diagram>` mxfile.

The docs PNG (`deploy_architecture.png`) is produced by rendering the SVG at
2x with `node_modules/.bin/node` sharp — **do not call the draw.io CLI** for
exports (it silently drops embedded images; only the desktop app renders them).

Sanity-check after regenerating:

```bash
cd scripts && npm install && node gen_<name>.mjs && node verify_icons.mjs
```

## Updating

1. Locate the existing artifacts: `docs/assets/*.drawio`, the generator script
   under `scripts/`, and the docs page.
2. **If a generator script exists** and the user has NOT hand-edited the
   `.drawio`: change the script (components, geometry, labels, colors, edges),
   regenerate (writes both the `.drawio` and the PNG), verify icons, update the
   page text/nav where it changed.
3. **If the user edited the `.drawio` in the app** (or no script exists): edit
   the draw.io XML directly — find each cell by its `id` or geometry and
   adjust `style`/`value`/`geometry`, add/remove `<mxCell>` blocks. Preserve
   their tweaks; note that the generator is now stale.
4. Refresh the PNG and the docs page in the same pass.

## draw.io XML rules (gotchas learned the hard way)

- **Every vertex needs `vertex="1"` AND `parent="1"`** — including pure text
  cells. A cell missing either makes `draw.io --export` fail with the generic
  `Error: Export failed: <file>` (no detail). Validate shape, not just XML.
- **Edges**: `edge="1" parent="1"` plus `source`/`target` pointing at existing
  cell ids, and a child `<mxGeometry relative="1" as="geometry"/>`.
- **Attribute escaping**: `&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;`, `"`→`&quot;`.
  Newline inside a label use the entity `&#10;`.
- **Icon images in the `.drawio` MUST be `data:image/png;base64,...`** — the
  draw.io desktop app renders them; the **headless CLI exporter ignores every
  embedded image** (SVG *and* PNG data-URIs alike; a `shape=image` cell exports
  as an empty outline). So: use the desktop app for interactive drawing, and
  the generator's own SVG→sharp renderer for the docs PNG.
- **SVG renderer gotchas (sharp/librsvg)**: never emit attribute values like
  `fill="undefined"`/`stroke="undefined"` — they render as **solid black**;
  and `<image>` raster elements lose alpha (black box) — embed the icon's
  vector `d` instead.
- **Icon cell style** (draw.io):
  `shape=image;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;verticalAlign=top;aspect=fixed;imageAspect=1;html=1;image=data:image/png;base64,<b64>;`
- **Wrapper**: `<mxfile ...><diagram id="..." name="..."><mxGraphModel pageWidth="1400" pageHeight="720" ...><root><mxCell id="0"/><mxCell id="1" parent="0"/>...cells...</root></mxGraphModel></diagram></mxfile>`.
- **Validate** `xmllint --noout <file>.drawio` before exporting.
- Label text cells and image cells: icon at top-center of its box, box label
  pinned bottom via `verticalAlign=bottom;align=center;`; big container boxes
  use `verticalAlign=top;fontSize=13;fontStyle=1;spacingTop=12;`.

## Visual conventions

| Element | Style |
|---|---|
| Rounded box | `rounded=1;arcSize=8;whiteSpace=wrap;html=1;` + fill/stroke |
| Optional / planned | same + `dashed=1;` |
| AWS blue (edge services) | fill `#EAF3FD`, stroke `#1E88E5` |
| EC2 (host) | fill `#FDF8F6`, stroke `#E8652C` |
| nginx | fill `#F4F9F2`, stroke `#009639` |
| FastAPI / backend | fill `#EEF7F5`, stroke `#009485` |
| Neutral / external | fill `#FAFAFA`, stroke `#BBBBBB` (dashed) |
| Client | fill `#F5F5F5`, stroke `#707070` |
| Edges | `edgeStyle=orthogonalEdgeStyle;` + a short label |

## Icon slugs (verified working)

`react`, `amazonroute53`, `amazonec2`, `nginx`, `fastapi`, `pytorch`, `ollama`,
`amazonwebservices`, plus container-generic icons like `docker`. To use a new
one, verify it first — `webfetch https://cdn.jsdelivr.net/npm/simple-icons@14/icons/<slug>.svg`
(custom answer, format text); a 200 + `<svg` means it exists, otherwise try
naming variants. AWS-services use `amazon<service>` slugs. Never hardcode an
unverified slug into a generator.

## Docs conventions (this repo)

- Embed the PNG with `![Title](../assets/<name>.png){ width=900 }`
  (mkdocs `attr_list` is enabled; the path is **relative from the page's
  folder**, so from `docs/architecture/` it is `../assets/...`).
- Design-phase pages start with the banner `> **Status: design.**`.
- Under the image keep the block: "Editable source: `docs/assets/<name>.drawio`
  (open in draw.io — the app renders the icons)", the regenerate command
  (`cd scripts && npm install && node gen_<name>.mjs` + `node verify_icons.mjs`),
  and a note that the docs PNG is produced by the script's SVG renderer.
- Add a page to the nav under the right section in `mkdocs.yml`, and to the
  `## Page index` list of `docs/architecture/index.md` when appropriate.
- Docs pages are written in English.
- Finish with `uv run mkdocs build`; make sure there are **no new warnings
  from your files**.