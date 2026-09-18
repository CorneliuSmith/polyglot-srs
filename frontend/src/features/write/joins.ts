import type { Glyph } from '../../api/strokes'
import { BOX } from './glyphBox'

type Pt = number[]

function pathLen(s: Pt[]): number {
  let n = 0
  for (let i = 1; i < s.length; i++) n += Math.hypot(s[i][0] - s[i - 1][0], s[i][1] - s[i - 1][1])
  return n
}

/** A trailing stroke this short is a dot or a small mark. */
const MARK_LEN = BOX * 0.06

/**
 * A form's joins from its strokes, the way scripts/strokes/gen_from_fonts.py
 * writes them for the generated library: x shifted so the ink starts at 0,
 * `advance` the ink width, `marks` the trailing dot strokes, and the entry
 * and exit points the word composer lands one letter on the next with —
 * Arabic leaves at its leftmost body point and is entered at its
 * rightmost; a joined cursive hand enters at the first stroke's leftmost
 * point and leaves at the body's rightmost. Used when a speaker traces
 * over a font-derived form, so their letter keeps composing into words.
 */
export function frameGlyph(
  script: string,
  style: string,
  form: string,
  strokes: number[][][],
): { strokes: number[][][]; joins: Glyph['joins'] } {
  if (strokes.length === 0) return { strokes, joins: {} }
  const minX = Math.min(...strokes.flat().map((p) => p[0]))
  const shifted = strokes.map((s) => s.map(([x, y]) => [x - minX, y]))
  let marks = 0
  while (marks < shifted.length - 1 && pathLen(shifted[shifted.length - 1 - marks]) < MARK_LEN) marks++
  const all = shifted.flat()
  const body = shifted.slice(0, shifted.length - marks).flat()
  const joins: Glyph['joins'] = { advance: Math.max(...all.map((p) => p[0])), marks }
  const leftHigh = (pts: Pt[]) => pts.reduce((a, b) => (b[0] < a[0] || (b[0] === a[0] && b[1] > a[1]) ? b : a))
  const rightHigh = (pts: Pt[]) => pts.reduce((a, b) => (b[0] > a[0] || (b[0] === a[0] && b[1] > a[1]) ? b : a))
  if (script === 'arabic') {
    joins.joins_next = form === 'initial' || form === 'medial'
    if (joins.joins_next) joins.exit = leftHigh(body)
    if (form === 'medial' || form === 'final') joins.entry = rightHigh(body)
  } else if (style === 'cursive' && (script === 'cyrillic' || script === 'latin')) {
    joins.joins_next = true
    joins.entry = shifted[0].reduce((a, b) => (b[0] < a[0] || (b[0] === a[0] && b[1] < a[1]) ? b : a))
    joins.exit = body.reduce((a, b) => (b[0] > a[0] || (b[0] === a[0] && b[1] > a[1]) ? b : a))
  }
  return { strokes: shifted, joins }
}
