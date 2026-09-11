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
