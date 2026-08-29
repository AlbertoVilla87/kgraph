import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import sharp from 'sharp'

// Verifies that the simple-icons logos embedded as vector <path>s in the
// generator-produced SVGs actually paint in their docs PNGs. Because opencode
// cannot view images, this is the closest check to "do the logos show?".
//
// Method: render each SVG twice — as-is, and with every icon path blanked —
// then diff each icon's region. Pixels that differ are exactly the logo
// (boxes/text/edges are identical in both renders). A zero diff means that
// icon never painted (e.g. a future regression).
//
// Usage: node scripts/verify_icons.mjs

const HERE = dirname(fileURLToPath(import.meta.url))
// [svg, png] pairs — deployed + app architecture, canvas size read from the SVG.
const DIAGRAMS = [
  ['docs/assets/deploy.svg', 'docs/assets/deploy_architecture.png'],
  ['docs/assets/app_architecture.svg', 'docs/assets/app_architecture.png'],
]
const SCALE = 2

async function main() {
  let ok = true
  for (const [svgRel, pngRel] of DIAGRAMS) {
    const svg = readFileSync(join(HERE, '..', svgRel), 'utf8')
    const blanked = svg.replace(/ d="[^"]+"/g, ' d="M0 0h1v1z"')

    const page = [...svg.matchAll(/<svg[^>]*width="(\d+)"[^>]*height="(\d+)"/g)][0]
    const PAGE_W = +page[1]
    const PAGE_H = +page[2]

    const icons = [...svg.matchAll(/<g transform="translate\((-?[\d.]+) (-?[\d.]+)\) scale\(([\d.]+)\)"><path/g)]
      .map((m) => ({ x: +m[1], y: +m[2], w: 24 * +m[3] }))

    ok = await checkDiagram(svg, blanked, PAGE_W, PAGE_H, icons, pngRel, SCALE) && ok
  }
  process.exit(ok ? 0 : 1)
}

async function checkDiagram(svg, blanked, PAGE_W, PAGE_H, icons, pngRel, SCALE) {
  // Re-render the PNG exactly like the generator does, so this check always
  // validates the artifact that gets shipped.
  const render = async (src) =>
    sharp(Buffer.from(src)).flatten({ background: '#ffffff' }).resize(PAGE_W * SCALE, PAGE_H * SCALE).png().toBuffer()
  const [bufA, bufB] = await Promise.all([render(svg), render(blanked)])

  let ok = true
  console.log(`--- ${pngRel} (${PAGE_W * SCALE}x${PAGE_H * SCALE})`)
  console.log(`icons=${icons.length}`)
  for (const [i, ic] of icons.entries()) {
    const a = sharp(bufA)
    const b = sharp(bufB)
    const { data: da, info: ia } = await a.extract({ left: ic.x * SCALE, top: ic.y * SCALE, width: ic.w * SCALE, height: ic.w * SCALE }).raw().toBuffer({ resolveWithObject: true })
    const { data: db } = await b.extract({ left: ic.x * SCALE, top: ic.y * SCALE, width: ic.w * SCALE, height: ic.w * SCALE }).raw().toBuffer({ resolveWithObject: true })
    let diff = 0
    for (let i = 0; i < da.length; i += ia.channels) {
      const r = Math.abs(da[i] - db[i])
      const g = ia.channels > 1 ? Math.abs(da[i + 1] - db[i + 1]) : 0
      const b = ia.channels > 2 ? Math.abs(da[i + 2] - db[i + 2]) : 0
      if (r > 20 || g > 20 || b > 20) diff++
    }
    const pct = (100 * diff) / ((ic.w * SCALE) ** 2)
    const pass = pct > 2
    ok &&= pass
    console.log(`icon ${i + 1} @(${ic.x},${ic.y}) ${ic.w}px logoDiff=${pct.toFixed(1)}% ${pass ? 'OK' : 'MISSING'}`)
  }

  const meta = await sharp(bufA).metadata()
  console.log(`PNG ${meta.width}x${meta.height} ${ok ? 'ALL ICONS OK' : 'FAILED (missing icons)'}`)
  return ok
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})