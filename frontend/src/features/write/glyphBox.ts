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

/** The glyph drawn as large as the canvas allows: the ink's own box fitted
 * with a margin, aspect kept. Font-derived glyphs live in the script's em
 * box (an ب is a third of it), so a single letter needs this to fill a
 * preview; authored glyphs already fill their box and come out the same. */
export function fromGlyphBoxFit(strokes: number[][][], size: number, margin = 0.1): Stroke[] {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const s of strokes) for (const [x, y] of s) {
    if (x < minX) minX = x
    if (y < minY) minY = y
    if (x > maxX) maxX = x
    if (y > maxY) maxY = y
  }
  if (!isFinite(minX)) return []
  const w = Math.max(1, maxX - minX)
  const h = Math.max(1, maxY - minY)
  const avail = size * (1 - 2 * margin)
  const scale = avail / Math.max(w, h)
  const ox = (size - w * scale) / 2
  const oy = (size - h * scale) / 2
  return strokes.map((s) => s.map(([x, y]) => ({ x: ox + (x - minX) * scale, y: oy + (y - minY) * scale })))
}

