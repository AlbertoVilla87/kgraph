// Shared layout engine for the architecture diagrams (deploy + app).
//
// Each generator script builds a DiagramBuilder (one element list = single
// source of truth) and asks it for TWO artifacts:
//   - draw.io XML   -> human-editable .drawio (draw.io app / diagrams.net)
//   - SVG           -> rasterized to PNG via sharp for the docs. The docs PNG
//                      never depends on the draw.io CLI because its headless
//                      exporter silently ignores embedded images.
// Icons are simple-icons vector paths (viewBox 24x24) recolored per brand.

import { writeFile } from 'node:fs/promises'
import sharp from 'sharp'

export const ICONS_BASE = 'https://cdn.jsdelivr.net/npm/simple-icons@14/icons'

export async function fetchIcons(slugs, brand, builtinIcons) {
  const results = await Promise.all(
    slugs.map(async (slug) => {
      const builtin = builtinIcons[slug]
      if (builtin) {
        const glyph = builtin.stroke
          ? `<path d="${builtin.d}" fill="none" stroke="${builtin.color}" stroke-width="${builtin.sw}"/>`
          : `<path d="${builtin.d}" fill="${builtin.color}"/>`
        const png = await sharp(Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">${glyph}</svg>`))
          .resize(64, 64)
          .png()
          .toBuffer()
        return [slug, { b64: png.toString('base64'), d: builtin.d, stroke: builtin.stroke, color: builtin.color, sw: builtin.sw }]
      }
      const res = await fetch(`${ICONS_BASE}/${slug}.svg`)
      if (!res.ok) throw new Error(`icon ${slug}: HTTP ${res.status}`)
      const svg = await res.text()
      // d: raw vector path for the SVG renderer (from a 24x24 coordinate space).
      const d = [...svg.matchAll(/<path[^>]*?d="([^"]+)"/g)].map((m) => m[1]).join(' ')
      // b64: colorized, rasterized PNG for the draw.io image cells.
      const colored = svg.replace('<path', `<path fill="${brand[slug]}"`)
      const png = await sharp(Buffer.from(colored)).resize(64, 64).png().toBuffer()
      return [slug, { b64: png.toString('base64'), d, stroke: false }]
    }),
  )
  return Object.fromEntries(results)
}

export class DiagramBuilder {
  constructor(brand = {}) {
    this.brand = brand
    this.els = []
    this.geometry = new Map()
    this.n = 0
    // So callers can destructure the builder methods (they use `this`).
    this.vertex = this.vertex.bind(this)
    this.box = this.box.bind(this)
    this.container = this.container.bind(this)
    this.icon = this.icon.bind(this)
    this.edge = this.edge.bind(this)
    this.text = this.text.bind(this)
    this.emitDrawio = this.emitDrawio.bind(this)
    this.emitSvg = this.emitSvg.bind(this)
  }

  nextId() {
    return `c${this.n++}`
  }

  vertex(props, x, y, w, h) {
    const id = this.nextId()
    this.els.push({ id, x, y, w, h, ...props })
    this.geometry.set(id, { x, y, w, h })
    return id
  }

  box(x, y, w, h, value, fill, stroke, opts = {}) {
    return this.vertex(
      { box: '1', value, fill, stroke, font: opts.font, dash: opts.dash, size: opts.size, textAlign: opts.textAlign, textX: opts.textX, shift: opts.shift, bold: opts.bold },
      x,
      y,
      w,
      h,
    )
  }

  container(x, y, w, h, title, fill, stroke, sub = '', opts = {}) {
    return this.vertex({ container: '1', value: title, sub, fill, stroke, dash: opts.dash, titleX: opts.titleX, titleY: opts.titleY }, x, y, w, h)
  }

  icon(x, y, w, h, slug, icons) {
    const meta = icons[slug] ?? {}
    return this.vertex({ icon: slug, iconB64: meta.b64, iconD: meta.d, stroke: meta.stroke, iconColor: meta.color ?? this.brand[slug] ?? '#000000', sw: meta.sw }, x, y, w, h)
  }

  edge(source, target, label, dash = false, opts = {}) {
    return this.vertex({ edge: '1', source, target, label, dash, src: opts.src ?? null, tgt: opts.tgt ?? null, route: opts.route ?? null, via: opts.via ?? null, labelPos: opts.labelPos ?? null }, 0, 0, 0, 0)
  }

  text(label, x, y, w, h, textStyle = 'title') {
    return this.vertex({ text: '1', value: label, textStyle }, x, y, w, h)
  }

  // -------------------------------------------------------------------------
  // draw.io emitter
  // -------------------------------------------------------------------------
  emitDrawio(pageW, pageH, diagramName) {
    const escapeXml = (v) => String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
    const body = this.els
      .map((el) => {
        const attrs = Object.entries(el)
          .filter(([k]) => ['vertex', 'parent', 'edge', 'source', 'target'].includes(k))
          .map(([k, v]) => `${k}="${v}"`)
        const props = `id="${el.id}" value="${escapeXml(this.drawioValue(el))}" style="${escapeXml(this.drawioStyle(el))}" ${attrs.join(' ')}`
        const g = this.geometry.get(el.id)
        if (el.edge) return `        <mxCell ${props}>\n          <mxGeometry relative="1" as="geometry"/>\n        </mxCell>`
        return `        <mxCell ${props}>\n          <mxGeometry x="${g.x}" y="${g.y}" width="${g.w}" height="${g.h}" as="geometry"/>\n        </mxCell>`
      })
      .join('\n')

    return `<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" agent="kgraph-scripts" version="31.3.2">
  <diagram id="${diagramName}" name="${diagramName}">
    <mxGraphModel dx="900" dy="500" grid="1" gridSize="10" guide="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="${pageW}" pageHeight="${pageH}" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
${body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>`
  }

  drawioValue(el) {
    if (el.container) return el.sub ? `${el.value}&#10;${el.sub}` : el.value
    return el.value ?? el.label ?? ''
  }

  drawioStyle(el) {
    if (el.text)
      return el.textStyle === 'title'
        ? 'text;html=1;align=left;verticalAlign=middle;fontSize=19;fontStyle=1;fontColor=#202020;fontFamily=Helvetica;'
        : el.textStyle === 'legend'
          ? 'text;html=1;align=left;verticalAlign=middle;fontSize=10;fontColor=#666666;'
          : 'text;html=1;align=left;verticalAlign=middle;fontSize=10;fontStyle=2;fontColor=#777777;' // tag
    if (el.icon)
      return `shape=image;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;verticalAlign=top;aspect=fixed;imageAspect=1;html=1;image=data:image/png;base64,${el.iconB64};`
    if (el.edge) {
      const s = this.geometry.get(el.source)
      const t = this.geometry.get(el.target)
      let exit = ''
      let entry = ''
      if (el.src) {
        exit = `exitX=${(((el.src[0] - s.x) / s.w) || 0).toFixed(2)};exitY=${(((el.src[1] - s.y) / s.h) || 0).toFixed(2)};`
        s.srcPt = el.src
      }
      if (el.tgt) {
        entry = `entryX=${(((el.tgt[0] - t.x) / t.w) || 0).toFixed(2)};entryY=${(((el.tgt[1] - t.y) / t.h) || 0).toFixed(2)};`
        t.tgtPt = el.tgt
      }
      return `edgeStyle=orthogonalEdgeStyle;rounded=0;curved=1;orthogonalLoop=1;jumpSize=6;html=1;fontSize=10;fontColor=#555555;strokeColor=#555555;${exit}${entry}${el.dash ? 'dashed=1;' : ''}`
    }
    if (el.container)
      return `rounded=1;whiteSpace=wrap;html=1;arcSize=5;fillColor=${el.fill};strokeColor=${el.stroke};fontColor=#202020;verticalAlign=top;align=center;fontSize=12;fontStyle=1;${el.dash ? 'dashed=1;' : ''}`
    const textAlignClause = el.textAlign === 'left'
      ? `align=left;spacingLeft=${Math.round(el.textX - el.x)};`
      : el.shift
        ? `align=center;spacingLeft=${Math.round(el.shift)};`
        : ''
    return `rounded=1;whiteSpace=wrap;html=1;arcSize=8;fillColor=${el.fill};strokeColor=${el.stroke};fontColor=${el.font || '#202020'};verticalAlign=bottom;align=center;fontSize=${el.size || 11};fontStyle=0;${textAlignClause}${el.dash ? 'dashed=1;' : ''}`
  }

  // -------------------------------------------------------------------------
  // SVG renderer (same layout) -> PNG via sharp
  // -------------------------------------------------------------------------
  edgeAnchors(from, to, src, tgt) {
    const ny = (r) => r.y + r.h / 2
    const nx = (r) => r.x + r.w / 2
    const p1 = src ?? (from.x + from.w <= to.x ? [from.x + from.w, ny(from)] : from.y + from.h <= to.y ? [nx(from), from.y + from.h] : to.x + to.w <= from.x ? [from.x, ny(from)] : [nx(from), from.y])
    const p2 = tgt ?? (from.x + from.w <= to.x ? [to.x, ny(to)] : from.y + from.h <= to.y ? [nx(to), to.y] : to.x + to.w <= from.x ? [to.x + to.w, ny(to)] : [nx(to), to.y + to.h])
    return [p1, p2]
  }

  arrowHead(x1, y1, x2, y2) {
    const dx = x2 - x1
    const dy = y2 - y1
    const len = Math.hypot(dx, dy)
    if (len < 1) return ''
    const ux = dx / len
    const uy = dy / len
    const bx = x2 - ux * 11
    const by = y2 - uy * 11
    const wx = uy * 4
    const wy = ux * 4
    return `<polygon points="${x2},${y2} ${bx + wx},${by - wy} ${bx - wx},${by + wy}" fill="#555555"/>`
  }

  esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }

  edgePathSegments(el, g1, g2) {
    const [p1, p2] = this.edgeAnchors(g1, g2, el.src, el.tgt)
    if (el.via) return [p1, ...el.via, p2]
    if (el.route === 'v') return [p1, [p1[0], p2[1]], p2]
    if (el.route === 'h') return [p1, [p2[0], p1[1]], p2]
    return [p1, p2]
  }

  emitSvg(pageW, pageH) {
    const parts = []
    parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${pageW}" height="${pageH}" viewBox="0 0 ${pageW} ${pageH}" font-family="Helvetica, Arial, sans-serif">`)

    for (const el of this.els) {
      const g = this.geometry.get(el.id)

      if (el.text) {
        const size = el.textStyle === 'title' ? 19 : 10
        const weight = el.textStyle === 'title' ? 700 : 400
        const color = el.textStyle === 'title' ? '#202020' : '#666666'
        parts.push(`<text x="${g.x}" y="${g.y + g.h / 2 + size / 2 - 2}" font-size="${size}" font-weight="${weight}" fill="${color}">${this.esc(el.value)}</text>`)
        continue
      }

      if (el.edge) {
        const pts = this.edgePathSegments(el, this.geometry.get(el.source), this.geometry.get(el.target))
        const path = pts.map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt[0]} ${pt[1]}`).join(' ')
        const dash = el.dash ? ' stroke-dasharray="6 4"' : ''
        parts.push(`<path d="${path}" fill="none" stroke="#555555" stroke-width="2"${dash}/>`)
        const [la, lb] = [pts[pts.length - 2], pts[pts.length - 1]]
        parts.push(this.arrowHead(la[0], la[1], lb[0], lb[1]))
        if (el.label) {
          let lx, ly
          if (el.labelPos) {
            ;[lx, ly] = el.labelPos
          } else {
            const midPt = pts[Math.floor((pts.length - 1) / 2)]
            const seg = [pts[Math.max(0, Math.floor((pts.length - 1) / 2) - 1)], midPt]
            const horizontal = Math.abs(seg[0][1] - seg[1][1]) < Math.abs(seg[0][0] - seg[1][0]) && pts.length >= 3
            lx = horizontal ? (seg[0][0] + seg[1][0]) / 2 + 6 : midPt[0] + 6
            ly = horizontal ? (seg[0][1] + seg[1][1]) / 2 - 6 : midPt[1] + 12
          }
          parts.push(`<text x="${lx}" y="${ly}" font-size="10" fill="#555555">${this.esc(el.label)}</text>`)
        }
        continue
      }

      if (el.icon) {
        // White chip + brand-colored simple-icons vector (viewBox 24x24).
        const r = g.w * 0.16
        parts.push(`<rect x="${g.x}" y="${g.y}" width="${g.w}" height="${g.h}" rx="${r}" fill="#ffffff" stroke="#d7dde3" stroke-width="1.5"/>`)
        const s = g.w / 24
        const color = el.iconColor ?? '#000000'
        if (el.stroke) {
          parts.push(`<g transform="translate(${g.x} ${g.y}) scale(${s})"><path d="${el.iconD}" fill="none" stroke="${color}" stroke-width="${el.sw}"/></g>`)
        } else {
          parts.push(`<g transform="translate(${g.x} ${g.y}) scale(${s})"><path d="${el.iconD}" fill="${color}"/></g>`)
        }
        continue
      }

      const rx = Math.min(0.08 * Math.min(g.w, g.h), 24)
      const dash = el.dash ? ' stroke-dasharray="6 4"' : ''
      parts.push(`<rect x="${g.x}" y="${g.y}" width="${g.w}" height="${g.h}" rx="${rx}" fill="${el.fill}" stroke="${el.stroke}" stroke-width="2" ${dash}/>`)

      if (el.container) {
        const tx = el.titleX ?? g.x + 10
        const ty = el.titleY ?? g.y + 18
        parts.push(`<text x="${tx}" y="${ty}" font-size="12" font-weight="700" fill="#202020">${this.esc(el.value)}</text>`)
        if (el.sub) parts.push(`<text x="${tx}" y="${g.y + 36}" font-size="10" fill="#555555">${this.esc(el.sub)}</text>`)
        continue
      }

      const lines = String(el.value).split('&#10;')
      const lineH = el.size || 11
      const left = el.textAlign === 'left'
      const cx = left ? el.textX : g.x + g.w / 2 + (el.shift || 0)
      const startY = g.y + g.h / 2 - ((lines.length - 1) * lineH) / 2 + lineH / 2
      const spans = lines.map((ln, i) => {
        const y = startY + i * lineH
        const weight = el.bold && i === 0 ? ' font-weight="600"' : ''
        return `<tspan x="${cx}" ${left ? '' : 'text-anchor="middle"'} y="${y}"${weight}>${this.esc(ln)}</tspan>`
      })
      parts.push(`<text x="${cx}" ${left ? '' : 'text-anchor="middle"'} font-size="${lineH}" fill="${el.font || '#202020'}">${spans.join('')}</text>`)
    }

    parts.push(`</svg>`)
    return parts.join('\n')
  }
}

export const BUILTIN_ICONS = {
  user: {
    d: 'M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0 2c-6 0-10 3.13-10 7v1h20v-1c0-3.87-4-7-10-7z',
    stroke: false,
    color: '#4a4a4a',
  },
  database: {
    d: 'M12 13C6.5 13 2 11.6 2 10s4.5-3 10-3 10 1.4 10 3-4.5 3-10 3zM2 10v4c0 1.6 4.5 3 10 3s10-1.4 10-3v-4M2 14v4c0 1.6 4.5 3 10 3s10-1.4 10-3v-4',
    stroke: true,
    color: '#4a4a4a',
    sw: 1.6,
  },
  tag: {
    d: 'M2 10.5V3a1 1 0 0 1 1-1h7.5a2 2 0 0 1 1.4.6l9.4 9.4a2 2 0 0 1 0 2.8l-6.5 6.5a2 2 0 0 1-2.8 0L2.6 11.9A2 2 0 0 1 2 10.5zM6 7a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0z',
    stroke: false,
    color: '#8C4FFF',
  },
}

export async function writePng(svgPath, svgContent, pageW, pageH, scale = 2) {
  const svg = await sharp(Buffer.from(svgContent)).resize(pageW * scale, pageH * scale).png().toBuffer()
  await writeFile(svgPath, svg)
  return svg
}