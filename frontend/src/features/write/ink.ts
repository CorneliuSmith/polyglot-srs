/** The ink model shared by the canvas, the neatness panel and the export.
 * Points are in CSS pixels of the canvas the learner drew on; `t` is the
 * pointer timestamp. A stroke is one pen-down to pen-up. */
export interface InkPoint {
  x: number
  y: number
  t?: number
}

export type Stroke = InkPoint[]

export interface Box {
  minX: number
  minY: number
  maxX: number
  maxY: number
}

export function strokeBox(stroke: Stroke): Box {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const p of stroke) {
    if (p.x < minX) minX = p.x
    if (p.y < minY) minY = p.y
    if (p.x > maxX) maxX = p.x
    if (p.y > maxY) maxY = p.y
  }
  return { minX, minY, maxX, maxY }
}

export function inkBox(strokes: Stroke[]): Box | null {
  const boxes = strokes.filter((s) => s.length > 0).map(strokeBox)
  if (boxes.length === 0) return null
  return {
    minX: Math.min(...boxes.map((b) => b.minX)),
    minY: Math.min(...boxes.map((b) => b.minY)),
    maxX: Math.max(...boxes.map((b) => b.maxX)),
    maxY: Math.max(...boxes.map((b) => b.maxY)),
  }
}

/** Ink worth sending: at least one stroke with real extent. A single tap
 * or an empty canvas costs nothing — this is the on-device gate before
 * the model is asked anything. */
export function hasInk(strokes: Stroke[]): boolean {
  const box = inkBox(strokes)
  if (!box) return false
  return box.maxX - box.minX > 8 || box.maxY - box.minY > 8
}

/** Strokes as the server keeps them: integer [x, y, t] triples, at most
 * 64 points per stroke. The method of the writing — order, direction,
 * lifts, speed — survives; the byte count does not. Mirrors
 * backend/services/ink_method.compact. */
export function compactStrokes(strokes: Stroke[]): number[][][] {
  const MAX = 64
  const out: number[][][] = []
  for (const stroke of strokes.slice(0, 400)) {
    if (stroke.length < 2) continue
    let pts = stroke
    if (pts.length > MAX) {
      const step = (pts.length - 1) / (MAX - 1)
      pts = Array.from({ length: MAX }, (_, i) => stroke[Math.round(i * step)])
    }
    out.push(pts.map((p) => [Math.round(p.x), Math.round(p.y), Math.round(p.t ?? 0)]))
  }
  return out
}
