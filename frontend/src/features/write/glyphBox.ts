import { inkBox } from './ink'
import type { Stroke } from './ink'

/** Strokes as the library stores them: the canvas's ink normalised into a
 * 1000×1000 box, keeping the ink's aspect (centred on the shorter axis),
 * as integer [x, y] pairs. The library is device-independent; the
 * learner's matcher normalises its own ink the same way. */
export const BOX = 1000

export function toGlyphBox(strokes: Stroke[]): number[][][] {
  const box = inkBox(strokes)
  if (!box) return []
  const w = Math.max(1, box.maxX - box.minX)
  const h = Math.max(1, box.maxY - box.minY)
  const scale = (BOX * 0.9) / Math.max(w, h)
  const ox = (BOX - w * scale) / 2
  const oy = (BOX - h * scale) / 2
  return strokes
    .filter((s) => s.length >= 2)
    .map((s) => s.map((p) => [
      Math.round(ox + (p.x - box.minX) * scale),
      Math.round(oy + (p.y - box.minY) * scale),
    ]))
}

/** The reverse, for drawing a stored glyph into a canvas of the given
 * size with a margin. */
export function fromGlyphBox(strokes: number[][][], size: number, margin = 0.08): Stroke[] {
  const scale = (size * (1 - 2 * margin)) / BOX
  const off = size * margin
  return strokes.map((s) => s.map(([x, y]) => ({ x: off + x * scale, y: off + y * scale })))
}
