import type { Glyph } from '../../api/strokes'
import { BOX } from './glyphBox'

/**
 * The composer (docs/plans/handwriting.md, §4.2): a word or sentence's
 * stroke template, built from the reviewed letter forms by the script's
 * rules. The supply is unlimited once the letters exist — every card,
 * every example line — and the same Learn → Trace → Write steps apply.
 *
 * The composed frame is BOX high and as wide as the text needs. Letters
 * sit in cells along a line; the strokes are in writing order (first
 * letter first), so a right-to-left script's first letter has the
 * largest x. Each point remembers which letter it belongs to (`owners`),
 * because a joined cursive run is one continuous stroke shared by
 * several letters — the matcher hands back a verdict per letter, not per
 * stroke, from that.
 *
 *  - Cyrillic / Latin cursive: when both neighbours have a form and the
 *    left one joins, its last stroke runs on into the next letter's first
 *    (exit → entry), the way the hand does.
 *  - Arabic: each letter's positional form from its neighbours' joining
 *    class; the joining stroke is part of the form, so nothing is added.
 *  - Hangul: a syllable decomposes into its jamo, each scaled into its
 *    cell of the block (lead left or top by the vowel's orientation, the
 *    tail below); each jamo is a letter of its own for the verdict.
 *  - Everything else: placement, in cells, left to right or right to
 *    left. Combining marks are not composed (nobody authors them).
 */
export type Pt = number[]

export interface ComposedLetter {
  /** The letter as it appears in the text (a jamo for Hangul). */
  char: string
  form: string
  glyph: Glyph | null
  /** Cell in the composed frame. */
  x: number
  y: number
  w: number
  h: number
}

export interface Composed {
  text: string
  width: number
  height: number
  strokes: Pt[][]
  /** Letter index per point, parallel to `strokes`. */
  owners: number[][]
  letters: ComposedLetter[]
  /** Letters with no reviewed form — the text cannot be traced. */
  missing: string[]
}

export const SCRIPT_OF: Record<string, string> = {
  ru: 'cyrillic', el: 'greek', ar: 'arabic', fa: 'arabic',
  he: 'hebrew', hi: 'devanagari', th: 'thai', ko: 'hangul',
}
export function scriptOf(code: string | undefined): string {
  return SCRIPT_OF[code ?? ''] ?? 'latin'
}
const CASED = new Set(['cyrillic', 'greek', 'latin'])
const RTL = new Set(['arabic', 'hebrew'])
/** Arabic letters that never join to the left (the next letter). */
const NON_JOINING_LEFT = new Set('اأإآدذرزوةىءؤژ')

/** Advance per letter cell as a fraction of the height. */
const ADVANCE = 0.72
const SPACE = 0.4
const LINE_HEIGHT = 1.0

const LEADS = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
const VOWELS = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
const TAILS = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ',
  'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
const VERTICAL_VOWELS = new Set('ㅏㅐㅑㅒㅓㅔㅕㅖㅣ')
const HORIZONTAL_VOWELS = new Set('ㅗㅛㅜㅠㅡ')

/** Text as the cells a hand writes: base letters with their combining
 * marks attached, spaces collapsed, everything else dropped. */
export function cells(text: string): string[] {
  const out: string[] = []
  for (const ch of text.normalize('NFC')) {
    if (out.length && out[out.length - 1] !== ' ' && /\p{M}/u.test(ch)) {
      out[out.length - 1] += ch
    } else if (/\p{L}/u.test(ch)) {
      out.push(ch)
    } else if (out.length && out[out.length - 1] !== ' ') {
      out.push(' ')
    }
  }
  while (out.length && out[out.length - 1] === ' ') out.pop()
  return out
}

function arabicForms(base: string[]): string[] {
  return base.map((ch, i) => {
    if (ch === ' ') return ''
    const prevJoins = i > 0 && base[i - 1] !== ' ' && !NON_JOINING_LEFT.has(base[i - 1])
    const joinsNext = i + 1 < base.length && base[i + 1] !== ' ' && !NON_JOINING_LEFT.has(ch)
    return prevJoins && joinsNext ? 'medial' : prevJoins ? 'final' : joinsNext ? 'initial' : 'isolated'
  })
}

interface Placed { char: string; form: string; key: string; x: number; y: number; w: number; h: number }

function jamoOf(ch: string): { lead: string; vowel: string; tail: string } | null {
  const cp = ch.codePointAt(0) ?? 0
  if (cp < 0xac00 || cp > 0xd7a3) return null
  const i = cp - 0xac00
  return { lead: LEADS[Math.floor(i / (21 * 28))], vowel: VOWELS[Math.floor((i % (21 * 28)) / 28)], tail: TAILS[i % 28] }
}

/** Cells for one Hangul block at (x, y, size). */
function hangulCells(ch: string, x: number, y: number, size: number): Placed[] {
  const j = jamoOf(ch)
  if (!j) return [{ char: ch, form: 'letter', key: `${ch}|letter`, x, y, w: size, h: size }]
  const bodyH = j.tail ? size * 0.62 : size
  const out: Placed[] = []
  const pad = size * 0.04
  if (VERTICAL_VOWELS.has(j.vowel)) {
    out.push({ char: j.lead, form: 'letter', key: `${j.lead}|letter`, x: x + pad, y: y + pad, w: size * 0.5 - pad, h: bodyH - 2 * pad })
    out.push({ char: j.vowel, form: 'letter', key: `${j.vowel}|letter`, x: x + size * 0.55, y: y + pad, w: size * 0.4, h: bodyH - 2 * pad })
  } else if (HORIZONTAL_VOWELS.has(j.vowel)) {
    out.push({ char: j.lead, form: 'letter', key: `${j.lead}|letter`, x: x + size * 0.2, y: y + pad, w: size * 0.6, h: bodyH * 0.55 - pad })
    out.push({ char: j.vowel, form: 'letter', key: `${j.vowel}|letter`, x: x + pad, y: y + bodyH * 0.55, w: size - 2 * pad, h: bodyH * 0.45 - pad })
  } else {
    // A compound vowel wraps the lead: lead top-left, vowel over the rest.
    out.push({ char: j.lead, form: 'letter', key: `${j.lead}|letter`, x: x + pad, y: y + pad, w: size * 0.45, h: bodyH * 0.5 })
    out.push({ char: j.vowel, form: 'letter', key: `${j.vowel}|letter`, x: x + size * 0.1, y: y + pad, w: size * 0.85, h: bodyH - 2 * pad })
  }
  if (j.tail) {
    out.push({ char: j.tail, form: 'letter', key: `${j.tail}|letter`, x: x + size * 0.15, y: y + bodyH + pad, w: size * 0.7, h: size - bodyH - 2 * pad })
  }
  return out
}

/** Fit a glyph's box strokes into a cell, keeping the ink's aspect. */
function fit(strokes: Pt[][], cell: { x: number; y: number; w: number; h: number }): Pt[][] {
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
  // The glyph box is BOX square with the ink at 90%; a cell is narrower
  // than tall, so scale by height and let a wide letter spill a little.
  const scale = Math.min(cell.h / BOX, (cell.w * 1.25) / BOX)
  const ox = cell.x + (cell.w - w * scale) / 2
  const oy = cell.y + (cell.h - h * scale) / 2
  return strokes.map((s) => s.map(([x, y]) => [ox + (x - minX) * scale, oy + (y - minY) * scale]))
}

export function compose(
  text: string,
  code: string | undefined,
  style: string,
  glyphs: Glyph[],
): Composed {
  const script = scriptOf(code)
  const byKey = new Map(glyphs.map((g) => [`${g.glyph}|${g.form}`, g]))
  const cs = cells(text)
  const H = BOX
  const advance = H * ADVANCE
  const space = H * SPACE
  const placed: Placed[] = []

  const base = cs.map((c) => (c === ' ' ? ' ' : c[0]))
  const forms = script === 'arabic' ? arabicForms(base) : []
  const width = cs.reduce((w, c) => w + (c === ' ' ? space : script === 'hangul' ? H * 0.9 : advance), 0)
  let x = 0
  cs.forEach((c, i) => {
    if (c === ' ') { x += space; return }
    const cellW = script === 'hangul' ? H * 0.9 : advance
    const cx = RTL.has(script) ? width - x - cellW : x
    const cellY = H * (1 - LINE_HEIGHT) / 2
    if (script === 'hangul') {
      placed.push(...hangulCells(c[0], cx, cellY, cellW))
    } else if (script === 'arabic') {
      placed.push({ char: c, form: forms[i], key: `${c[0]}|${forms[i]}`, x: cx, y: cellY, w: cellW, h: H })
    } else if (CASED.has(script)) {
      const lower = c[0].toLowerCase()
      const form = c[0] !== lower ? 'upper' : 'lower'
      placed.push({ char: c, form, key: `${lower}|${form}`, x: cx, y: cellY, w: cellW, h: H })
    } else {
      placed.push({ char: c, form: 'letter', key: `${c[0]}|letter`, x: cx, y: cellY, w: cellW, h: H })
    }
    x += cellW
  })

  const letters: ComposedLetter[] = []
  const strokes: Pt[][] = []
  const owners: number[][] = []
  const missing: string[] = []
  const joined = style === 'cursive' && (script === 'cyrillic' || script === 'latin')
  let prevJoins = false
  placed.forEach((p, li) => {
    const g = byKey.get(p.key) ?? null
    letters.push({ char: p.char, form: p.form, glyph: g, x: p.x, y: p.y, w: p.w, h: p.h })
    if (!g) {
      if (!missing.includes(p.char)) missing.push(p.char)
      prevJoins = false
      return
    }
    const fitted = fit(g.strokes, p)
    fitted.forEach((s, si) => {
      if (si === 0 && prevJoins && strokes.length > 0 && joined) {
        // Run the previous letter's exit into this one's entry: one stroke.
        strokes[strokes.length - 1].push(...s)
        owners[owners.length - 1].push(...s.map(() => li))
      } else {
        strokes.push([...s])
        owners.push(s.map(() => li))
      }
    })
    const adjacent = li + 1 < placed.length && Math.abs(placed[li + 1].x - (p.x + p.w)) < 1
    prevJoins = joined && fitted.length > 0 && g.joins?.joins_next !== false && adjacent
  })
  return { text, width, height: H, strokes, owners, letters, missing }
}

/** Composed strokes scaled to draw into a canvas of the given width and
 * height, centred, keeping the aspect. */
export function fitComposed(
  c: Composed,
  cw: number,
  ch: number,
  margin = 0.06,
): { strokes: { x: number; y: number }[][]; scale: number; ox: number; oy: number } {
  const availW = cw * (1 - 2 * margin)
  const availH = ch * (1 - 2 * margin)
  const scale = Math.min(availW / Math.max(1, c.width), availH / c.height)
  const ox = (cw - c.width * scale) / 2
  const oy = (ch - c.height * scale) / 2
  return {
    strokes: c.strokes.map((s) => s.map(([x, y]) => ({ x: ox + x * scale, y: oy + y * scale }))),
    scale, ox, oy,
  }
}
