// Generates the AWS target-deployment architecture assets for Astrolabe:
//   docs/assets/deploy.drawio              human-editable source (draw.io app)
//   docs/assets/deploy.svg                 vector preview (mirror of the layout)
//   docs/assets/deploy_architecture.png    PNG used in the docs
//
// Layout-driven: the element list below feeds BOTH emitters (draw.io XML and
// SVG rasterized to PNG via sharp) through DiagramBuilder (diagram_util.mjs).
// The docs PNG never depends on the draw.io CLI because its headless exporter
// silently IGNORES embedded images; the desktop app renders them, so the
// .drawio keeps PNG data-URIs for humans.
//
// Icons are simple-icons vector paths (viewBox 24x24) recolored with each
// brand's hex (verified from simple-icons v14 metadata) on a white chip.
// Icons without a simple-icons glyph use a hand-authored BUILTIN_ICONS vector.
//
// Usage: (from scripts/) node gen_deploy_drawio.mjs  (regenerate + keep docs in sync)

import { mkdirSync } from 'node:fs'
import { writeFile, readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { DiagramBuilder, BUILTIN_ICONS, fetchIcons, writePng } from './diagram_util.mjs'

const PAGE_W = 1500
const PAGE_H = 1010
export const OUT_DIR = resolve(import.meta.dirname, '..', 'docs', 'assets')
const OUT_DRAWIO = resolve(OUT_DIR, 'deploy.drawio')
const OUT_SVG = resolve(OUT_DIR, 'deploy.svg')
const OUT_PNG = resolve(OUT_DIR, 'deploy_architecture.png')

// Brand hex values, grounded in simple-icons@14 metadata (see _data/simple-icons.json).
const BRAND = {
  react: '#61DAFB',
  amazonroute53: '#8C4FFF',
  amazonec2: '#FF9900',
  amazonwebservices: '#232F3E',
  amazoncloudwatch: '#FF4F8B',
  amazoniam: '#DD344C',
  nginx: '#009639',
  fastapi: '#009688',
  ollama: '#000000',
  github: '#181717',
  docker: '#2496ED',
  arxiv: '#B31B1B',
  huggingface: '#FFD21E',
}

const ICON_SLUGS = [...Object.keys(BRAND), ...Object.keys(BUILTIN_ICONS)]

async function main() {
  const icons = await fetchIcons(ICON_SLUGS, BRAND, BUILTIN_ICONS)
  const db = new DiagramBuilder(BRAND)
  const { box, container, icon, edge, text } = db
  const CX = 40

  text('Astrolabe — deployment & CI/CD (AWS, design phase)', CX, 14, 1100, 22)

  // =========================================================
  //  ZONE 1 · EXTERNAL (runtime sources & the caller)
  // =========================================================
  text('EXTERNAL', CX, 44, 140, 14, 'tag')

  const client = box(CX, 64, 190, 82, 'User — browser', '#F5F5F5', '#707070', { shift: 22 })
  icon(52, 88, 28, 28, 'user', icons)

  const arxiv = box(1270, 64, 190, 82, 'arXiv API / ar5iv&#10;metadata · full text — runtime', '#FAFAFA', '#BBBBBB', { dash: true, shift: 24, size: 10 })
  icon(1282, 88, 28, 28, 'database', icons)

  // =========================================================
  //  ZONE 2 · AWS (managed services + the EC2 host)
  // =========================================================
  const cloud = container(CX, 200, 1420, 548, 'Amazon Web Services — AWS Cloud', '#FFFFFF', '#232F3E', undefined, { dash: true, titleX: 58, titleY: 216 })
  const cloudIcon = icon(60, 220, 24, 24, 'amazonwebservices', icons)

  // Managed services, left column.
  const r53 = box(46, 250, 168, 82, 'Route 53 — DNS only&#10;name → Elastic IP', '#EAF3FD', '#1E88E5', { shift: 20 })
  icon(58, 278, 36, 36, 'amazonroute53', icons)

  const cloudwatch = box(46, 520, 168, 96, 'CloudWatch&#10;logs · metrics · alerts', '#EAF3FD', '#1E88E5', { shift: 20 })
  icon(58, 546, 36, 36, 'amazoncloudwatch', icons)

  // ECR — private registry, right column; aligned under the build pipeline.
  const ecr = box(1210, 560, 210, 90, 'ECR — private registry&#10;:vX.Y.Z · :latest', '#EAF3FD', '#1E88E5', { shift: 20 })
  icon(1222, 584, 36, 36, 'tag', icons)

  // EC2 host (Docker Compose) — the runtime core.
  const ec2 = container(322, 232, 852, 512, 'EC2 — t3.xlarge (4 vCPU / 16 GiB)', '#FDF8F6', '#E8652C', undefined, { titleX: 344, titleY: 250 })

  // Security Group straddles the EC2 border: it is the filter any inbound
  // HTTPS arrow crosses before reaching nginx.
  box(300, 296, 92, 96, 'Security Group&#10;443 → nginx&#10;22 closed (SSM)', '#FFFFFF', '#C9C9C9', { size: 10 })

  const compose = container(440, 292, 640, 276, 'Docker Compose — runtime stack', '#FFFDF8', '#B7791F', undefined, { titleX: 460, titleY: 308 })

  const nginx = box(480, 316, 540, 52, 'nginx — React SPA + reverse proxy&#10;serves dist/ · proxy /api → FastAPI', '#F4F9F2', '#009639', { size: 10, bold: true })
  icon(920, 322, 26, 26, 'nginx', icons)
  icon(952, 323, 24, 24, 'react', icons)

  const backend = box(480, 388, 540, 108, 'backend — FastAPI (uvicorn)&#10;GLiNER entities · Qwen canonicalization&#10;models baked · torch on CPU', '#EEF7F5', '#009485', { size: 10, bold: true })
  icon(920, 396, 26, 26, 'fastapi', icons)

  const ollama = box(480, 520, 540, 46, 'Ollama — Qwen3 0.6b&#10;citation mode (optional)', '#F7F7F8', '#737373', { dash: true, size: 10, shift: 22 })
  icon(920, 528, 26, 26, 'ollama', icons)

  // Ephemeral storage + single-point-of-failure note (deliberate decisions).
  box(440, 590, 640, 54, 'data/ — ephemeral scratch&#10;PDFs fetched per run · discarded · no EBS volume', '#FAFAFA', '#BBBBBB', { dash: true, size: 10 })
  box(440, 664, 640, 44, 'Single point of failure — one VM, no autoscaling (deliberate: in-memory state + cold start)&#10;instance stopped / started manually to save cost', '#FFF7F5', '#C0392B', { dash: true, size: 9 })

  // =========================================================
  //  ZONE 3 · BUILD / DEPLOY — CI/CD (outside runtime)
  // =========================================================
  text('BUILD / DEPLOY — CI/CD (outside runtime)', CX, 780, 700, 14, 'tag')

  box(CX, 802, 150, 64, 'Secrets — .env&#10;via SSM (gitignored)', '#FFFFFF', '#C9C9C9', { dash: true, size: 10 })
  box(210, 802, 190, 64, 'Healthcheck (post-deploy)&#10;poll /api/health — awaits cold start', '#FFFFFF', '#8C4FFF', { dash: true, size: 10 })

  const oidc = box(440, 802, 210, 64, 'OIDC — GitHub assumes&#10;IAM role · no static keys', '#EAF3FD', '#1E88E5', { size: 10, shift: 20 })
  icon(456, 824, 30, 30, 'amazoniam', icons)

  const github = box(690, 806, 210, 56, 'GitHub Actions — CI&#10;tag → build vX.Y.Z', '#F8F8F8', '#C9C9C9', { size: 10, shift: 22 })
  icon(706, 826, 30, 30, 'github', icons)

  const hf = box(950, 806, 210, 56, 'Hugging Face Hub&#10;model cache (build time)', '#FAFAFA', '#BBBBBB', { dash: true, size: 10, shift: 22 })
  icon(966, 826, 30, 30, 'huggingface', icons)

  const dockerimg = box(1210, 806, 210, 56, 'Docker image — models baked&#10;built by GitHub Actions', '#F8F8F8', '#C9C9C9', { size: 10, shift: 22 })
  icon(1226, 826, 30, 30, 'docker', icons)

  // =========================================================
  //  Legend
  // =========================================================
  text('Legend', CX, 926, 80, 14, 'tag')
  box(58, 950, 14, 14, '', '#EAF3FD', '#1E88E5')
  text('AWS managed service', 78, 948, 150, 16, 'legend')
  box(230, 950, 14, 14, '', '#FDF8F6', '#E8652C')
  text('EC2 host', 250, 948, 100, 16, 'legend')
  box(340, 950, 14, 14, '', '#F4F9F2', '#009639')
  text('nginx', 360, 948, 80, 16, 'legend')
  box(430, 950, 14, 14, '', '#EEF7F5', '#009485')
  text('FastAPI / backend', 450, 948, 130, 16, 'legend')
  box(580, 950, 14, 14, '', '#FFFFFF', '#BBBBBB', { dash: true })
  text('dashed border = optional / ephemeral / external', 600, 948, 320, 16, 'legend')
  text('solid arrow = runtime / build data flow · dashed arrow = optional or configuration step', CX, 972, 900, 14, 'legend')

  // =========================================================
  //  Edges — runtime first, then build-time
  // =========================================================
  // DNS + inbound HTTPS: the HTTPS arrow deliberately crosses the Security
  // Group box, which sits on the EC2 border.
  edge(client, r53, 'DNS lookup', false, { src: [150, 146], tgt: [150, 250], route: 'v' })
  edge(client, nginx, 'HTTPS · 443', false, { src: [230, 146], tgt: [480, 330], route: 'v' })
  edge(r53, ec2, 'name → EIP', false, { src: [214, 262], tgt: [322, 262], route: 'h' })
  edge(r53, ec2, 'post-deploy /api/health poll', true, { src: [214, 300], tgt: [322, 300], route: 'h' })

  // Inside the host + observability + registries.
  edge(nginx, backend, 'proxy /api')
  edge(backend, ollama, 'Qwen3 — citation (optional)', true)
  edge(arxiv, backend, 'fetch metadata · full text', false, { src: [1365, 146], tgt: [1020, 430], route: 'v' })
  edge(ec2, cloudwatch, 'logs · metrics · alerts', false, { src: [322, 568], tgt: [214, 568], route: 'h' })
  edge(ecr, ec2, 'pull · compose up', false, { src: [1210, 605], tgt: [1174, 605], route: 'h' })

  // CI/CD wiring: role assumption, image build, push and SSM deploy.
  edge(github, oidc, 'assume IAM role (OIDC)', false, { src: [690, 834], tgt: [650, 834], route: 'h', labelPos: [658, 826] })
  edge(hf, dockerimg, 'download models (baked at build)', true, { src: [1160, 834], tgt: [1210, 834], route: 'h' })
  edge(github, dockerimg, 'build image', false, { src: [900, 862], tgt: [1315, 862], via: [[900, 884], [1315, 884]], labelPos: [1090, 876] })
  edge(dockerimg, ecr, 'push :vX.Y.Z + :latest', false, { src: [1315, 806], tgt: [1315, 650], route: 'v' })
  edge(oidc, ec2, 'deploy — SSM send-command', true, { src: [545, 802], tgt: [545, 744], route: 'v', labelPos: [556, 770] })

  // Host icon drawn last so the compose boundary never covers it.
  icon(1138, 238, 26, 26, 'amazonec2', icons)

  mkdirSync(OUT_DIR, { recursive: true })
  await writeFile(OUT_DRAWIO, db.emitDrawio(PAGE_W, PAGE_H, 'kgraph-deploy'))
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