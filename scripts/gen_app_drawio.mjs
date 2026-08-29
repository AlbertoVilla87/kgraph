// Generates the Astrolabe application-architecture assets:
//   docs/assets/app_architecture.drawio    human-editable source (draw.io app)
//   docs/assets/app_architecture.svg       vector preview (mirror of the layout)
//   docs/assets/app_architecture.png       PNG used in the docs
//
// Complements deploy.drawio (infra/deplyment): this one shows the single
// FastAPI process, its in-memory state, the job+polling request flow and the
// pipeline composition — local models vs. the separate HTTP services.
// Same layout-driven engine as gen_deploy_drawio.mjs (see diagram_util.mjs).
//
// Usage: (from scripts/) node gen_app_drawio.mjs

import { mkdirSync } from 'node:fs'
import { writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { DiagramBuilder, BUILTIN_ICONS, fetchIcons, writePng } from './diagram_util.mjs'

const PAGE_W = 1500
const PAGE_H = 900
export const OUT_DIR = resolve(import.meta.dirname, '..', 'docs', 'assets')
const OUT_DRAWIO = resolve(OUT_DIR, 'app_architecture.drawio')
const OUT_SVG = resolve(OUT_DIR, 'app_architecture.svg')
const OUT_PNG = resolve(OUT_DIR, 'app_architecture.png')

// Brand hex values, grounded in simple-icons@14 metadata.
const BRAND = {
  react: '#61DAFB',
  fastapi: '#009688',
  ollama: '#000000',
  arxiv: '#B31B1B',
}

const ICON_SLUGS = [...Object.keys(BRAND), ...Object.keys(BUILTIN_ICONS)]

async function main() {
  const icons = await fetchIcons(ICON_SLUGS, BRAND, BUILTIN_ICONS)
  const db = new DiagramBuilder(BRAND)
  const { box, container, icon, edge, text } = db

  text('Astrolabe — application architecture (single FastAPI process · job + polling)', 40, 14, 1100, 22)

  // =========================================================
  //  CLIENT — browser SPA
  // =========================================================
  text('CLIENT', 40, 44, 100, 14, 'tag')

  const client = box(40, 80, 250, 150, '&#10;React SPA (browser)&#10;POST /analyze · GET /{id} · GET /{id}/result&#10;renders graph / stats', '#F4F9F2', '#009639', { size: 10, bold: true, shift: 22 })
  icon(214, 88, 24, 24, 'react', icons)

  // =========================================================
  //  FastAPI PROCESS — one uvicorn worker
  // =========================================================
  const process = container(340, 66, 860, 640, 'FastAPI process — uvicorn (single worker)', '#FFFDF8', '#B7791F', undefined, { titleX: 362, titleY: 86 })

  // API handlers + in-memory shared state (the job + polling contract).
  const api = box(370, 100, 420, 92, '/api/analysis/* — sync def (job + polling)&#10;POST /analyze · GET /{id} · GET /{id}/result', '#EEF7F5', '#009485', { size: 10, bold: true, shift: 22 })
  icon(744, 116, 26, 26, 'fastapi', icons)

  const state = box(850, 100, 310, 92, 'In-memory state — analyses: dict&#10;{id → status · progress · result}&#10;volatile — lost on restart', '#FAFAFA', '#BBBBBB', { dash: true, size: 10, bold: true })

  const worker = box(850, 240, 310, 62, 'Worker thread (daemon)&#10;threading.Thread → run_analysis()', '#FFFDF8', '#B7791F', { size: 10, bold: true })

  // Pipeline — one logical flow per run, dispatched on mode × discovery.
  const pipeline = container(370, 350, 790, 300, 'pipeline — one run · discovery {topic | citation} × mode {quick | deep}', '#FFFFFF', '#C0C0C0', undefined, { titleX: 390, titleY: 370 })

  const input = box(385, 392, 140, 64, 'INPUT&#10;topic | seed_url', '#F1F6FA', '#1E88E5', { size: 9, bold: true })
  const disc = box(543, 392, 140, 64, 'DISCOVERY&#10;topic | citation', '#F1F6FA', '#1E88E5', { size: 9, bold: true })
  const corpus = box(701, 392, 140, 64, 'CORPUS — quick | deep&#10;abstracts | full-text + segment', '#F1F6FA', '#1E88E5', { size: 9, bold: true })
  const extract = box(859, 392, 140, 64, 'EXTRACTION&#10;GLiNER · MiniLM · spaCy', '#EEF7F5', '#009485', { size: 9, bold: true })
  const merge = box(1017, 392, 140, 64, 'MERGE → topics · stats&#10;writes /result', '#F8F8F8', '#C9C9C9', { size: 9, bold: true })

  const models = box(859, 474, 298, 64, 'MODEL CACHE — serialized load&#10;threading.Lock · shared across runs', '#FFFFFF', '#C0C0C0', { size: 9 })

  // =========================================================
  //  SEPARATE SERVICES — HTTP (outside the process)
  // =========================================================
  text('SEPARATE SERVICES — HTTP (outside the process)', 40, 730, 420, 14, 'tag')

  const ollama = box(380, 740, 340, 60, 'Ollama — qwen3:0.6b · localhost:11434&#10;LLM inference (citation) · via LiteLLM', '#FAFAFA', '#BBBBBB', { dash: true, size: 9, bold: true, shift: 20 })
  icon(662, 748, 26, 26, 'ollama', icons)

  const arxiv = box(820, 740, 340, 60, 'arXiv API / ar5iv — HTTPS&#10;metadata · full-text fetch (httpx)', '#FAFAFA', '#BBBBBB', { dash: true, size: 9, shift: 20 })
  icon(1090, 748, 26, 26, 'arxiv', icons)

  // =========================================================
  //  Legend
  // =========================================================
  text('Legend', 40, 826, 80, 14, 'tag')
  box(58, 850, 14, 14, '', '#EEF7F5', '#009485')
  text('FastAPI handler', 78, 848, 120, 16, 'legend')
  box(190, 850, 14, 14, '', '#FFFDF8', '#B7791F')
  text('worker / pipeline process', 210, 848, 170, 16, 'legend')
  box(360, 850, 14, 14, '', '#F1F6FA', '#1E88E5')
  text('pipeline step', 380, 848, 100, 16, 'legend')
  box(470, 850, 14, 14, '', '#FAFAFA', '#BBBBBB', { dash: true })
  text('volatile / external — dashed border', 490, 848, 240, 16, 'legend')
  text('solid arrow = request / data flow · dashed arrow = thread · configuration · optional', 40, 872, 900, 14, 'legend')

  // =========================================================
  //  Edges
  // =========================================================
  // Request / response: job + polling over HTTPS.
  edge(client, api, 'POST /analyze · poll GET /{id}', false, { src: [290, 122], tgt: [370, 122], route: 'h' })
  edge(api, client, 'status · graph (result)', true, { src: [370, 176], tgt: [290, 176], route: 'h' })

  // Inside the process: handlers <-> state, thread spawn, worker -> pipeline.
  edge(api, state, 'read · write analyses[id]', false, { src: [790, 146], tgt: [850, 146], route: 'h', labelPos: [820, 166] })
  edge(api, worker, 'spawn daemon thread', false, { src: [560, 192], tgt: [970, 240], route: 'v' })
  edge(worker, pipeline, 'run_analysis()', false, { src: [1050, 302], tgt: [900, 350], route: 'v' })

  // Result lands in shared state (avoids the worker box: exits east, climbs
  // the free strip x1170 between state/worker (x≤1160) and the container edge).
  edge(merge, state, 'writes result', true, { src: [1157, 410], tgt: [1160, 146], via: [[1170, 410], [1170, 146]], labelPos: [1190, 300] })

  // Pipeline spine (step order reads left -> right; no labels on 18px hops).
  edge(input, disc)
  edge(disc, corpus)
  edge(corpus, extract)
  edge(extract, merge)
  edge(models, extract, '', false, { src: [929, 474], tgt: [929, 456], route: 'v' })

  // Network services (dashed: optional / separate process). The arXiv edge
  // snakes below MODEL CACHE so it never crosses a box.
  edge(disc, ollama, 'Qwen3 — LLM (citation)', true, { src: [650, 462], tgt: [650, 740], route: 'v', labelPos: [450, 700] })
  edge(corpus, arxiv, 'arXiv fetch — httpx', true, { src: [770, 462], via: [[770, 560], [990, 560]], tgt: [990, 740], labelPos: [1006, 690] })

  mkdirSync(OUT_DIR, { recursive: true })
  await writeFile(OUT_DRAWIO, db.emitDrawio(PAGE_W, PAGE_H, 'kgraph-app'))
  console.log(`wrote ${OUT_DRAWIO}`)

  const svg = db.emitSvg(PAGE_W, PAGE_H)
  await writeFile(OUT_SVG, svg)
  await writePng(OUT_PNG, svg, PAGE_W, PAGE_H)
  console.log(`wrote ${OUT_PNG}`)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})