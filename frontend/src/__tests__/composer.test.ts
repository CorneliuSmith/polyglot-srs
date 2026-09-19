import { describe, expect, it } from 'vitest'
import type { Glyph } from '../api/strokes'
import { cells, compose, fitComposed } from '../features/write/composer'
import { matchComposed } from '../features/write/matcher'
import type { Stroke } from '../features/write/ink'

const g = (glyph: string, form: string, strokes: number[][][], joins: Glyph['joins'] = {}): Glyph => ({
  id: `${glyph}-${form}`, script: 'x', glyph, form, style: 'print', strokes, joins, hints: [], source: 'test', reviewed: true,
})
// A tall stroke and a square loop: two letters nobody could confuse.
const L = [[[500, 100], [500, 900]]]
const O = [[[300, 300], [700, 300], [700, 700], [300, 700], [300, 300]]]
const V = [[[200, 100], [500, 900], [800, 100]]]

describe('cells', () => {
  it('keeps letters with their marks, collapses spaces, drops punctuation', () => {
    expect(cells('  Où va-t-il ?  ')).toEqual(['O', 'ù', ' ', 'v', 'a', ' ', 't', ' ', 'i', 'l'])
    expect(cells('بِسْم')).toEqual(['بِ', 'سْ', 'م'])
  })
})

describe('compose', () => {
  it('places letters in cells left to right and names what is missing', () => {
    const c = compose('lov', 'es', 'print', [g('l', 'lower', L), g('o', 'lower', O)])
    expect(c.letters.map((l) => l.char)).toEqual(['l', 'o', 'v'])
    expect(c.letters[0].x).toBeLessThan(c.letters[1].x)
    expect(c.missing).toEqual(['v'])
    expect(c.strokes).toHaveLength(2)
    expect(c.owners[1].every((o) => o === 1)).toBe(true)
  })

  it('upper case is its own form', () => {
    const c = compose('Lo', 'es', 'print', [g('l', 'upper', L), g('o', 'lower', O)])
    expect(c.letters.map((l) => l.form)).toEqual(['upper', 'lower'])
    expect(c.missing).toEqual([])
  })

  it('joins cursive neighbours into one running stroke, owned letter by letter', () => {
    const c = compose('lo l', 'ru', 'cursive', [g('l', 'lower', L), g('o', 'lower', O)])
    // "lo" is one stroke; the space breaks the join, so the last l is its own.
    expect(c.strokes).toHaveLength(2)
    expect(new Set(c.owners[0])).toEqual(new Set([0, 1]))
    expect(c.letters).toHaveLength(3)
    expect(c.owners[1].every((o) => o === 2)).toBe(true)
  })

  it('picks Arabic positional forms from the neighbours and runs right to left', () => {
    const lib = [g('ب', 'initial', L), g('ي', 'medial', V), g('ت', 'final', O), g('ا', 'isolated', L)]
    const c = compose('بيت', 'ar', 'naskh', lib)
    expect(c.letters.map((l) => l.form)).toEqual(['initial', 'medial', 'final'])
    expect(c.missing).toEqual([])
    expect(c.letters[0].x).toBeGreaterThan(c.letters[2].x)
    // A non-joining letter breaks the chain: after ا the next letter starts fresh.
    const d = compose('ات', 'ar', 'naskh', [...lib, g('ت', 'isolated', O)])
    expect(d.letters.map((l) => l.form)).toEqual(['isolated', 'isolated'])
  })

  it('takes a Hangul syllable apart into its jamo, each in its cell of the block', () => {
    const lib = [g('ㅎ', 'letter', O), g('ㅏ', 'letter', L), g('ㄴ', 'letter', V)]
    const c = compose('한', 'ko', 'print', lib)
    expect(c.letters.map((l) => l.char)).toEqual(['ㅎ', 'ㅏ', 'ㄴ'])
    expect(c.missing).toEqual([])
    const [h, a, n] = c.letters
    expect(h.x).toBeLessThan(a.x)          // lead left of a vertical vowel
    expect(n.y).toBeGreaterThan(h.y + h.h - 1) // tail below the body
    expect(compose('고', 'ko', 'print', [g('ㄱ', 'letter', L)]).missing).toEqual(['ㅗ'])
  })
})

function inkFrom(strokes: { x: number; y: number }[][]): Stroke[] {
  return strokes.map((s) => s.map((p, i) => ({ x: p.x, y: p.y, t: i * 10 })))
}

describe('matchComposed', () => {
  const lib = [g('l', 'lower', L), g('o', 'lower', O)]
  const word = compose('lo', 'es', 'print', lib)
  const frame = fitComposed(word, 300, 150)

  it('traced exactly through the frame: every letter matches', () => {
    const r = matchComposed(inkFrom(frame.strokes), word, { frame, tolerance: 0.12 })
    expect(r.ok).toBe(true)
    expect(r.letters.map((l) => l.ok)).toEqual([true, true])
  })

  it('a scribbled letter fails by name, the rest stand', () => {
    const ink = inkFrom([frame.strokes[0], frame.strokes[1].map((p, i) => ({ x: p.x + (i % 2 ? 40 : -40), y: p.y + 30 }))])
    const r = matchComposed(ink, word, { frame, tolerance: 0.12 })
    expect(r.ok).toBe(false)
    expect(r.letters[0].ok).toBe(true)
    expect(r.letters[1].ok).toBe(false)
    expect(r.letters[1].reason).toBe('shape')
  })

  it('open-ended: half the word covers the first letter only', () => {
    const r = matchComposed(inkFrom([frame.strokes[0]]), word, { frame, tolerance: 0.15, openEnd: true })
    expect(r.letters[0].covered && r.letters[0].ok).toBe(true)
    expect(r.letters[1].covered).toBe(false)
  })

  it('from memory, at another size and place, the ink is fitted to the template', () => {
    const ink = inkFrom(frame.strokes.map((s) => s.map((p) => ({ x: 40 + p.x * 1.7, y: 200 + p.y * 1.4 }))))
    const r = matchComposed(ink, word, { tolerance: 0.12 })
    expect(r.letters.map((l) => l.ok)).toEqual([true, true])
  })

  it('a letter the ink skipped is missing, not merely misshapen', () => {
    const three = compose('lol', 'es', 'print', lib)
    const f = fitComposed(three, 400, 150)
    const r = matchComposed(inkFrom([f.strokes[0], f.strokes[2]]), three, { frame: f, tolerance: 0.12 })
    expect(r.letters[1].ok).toBe(false)
    expect(r.letters[1].reason).toBe('missing')
  })

  it('letters without a template are reported missing before anything is judged', () => {
    const c = compose('lx', 'es', 'print', lib)
    const r = matchComposed(inkFrom(fitComposed(c, 300, 150).strokes), c, {})
    expect(r.letters[1].reason).toBe('missing')
    expect(r.ok).toBe(false)
  })
})

describe('compose at the script scale (font-derived glyphs)', () => {
  // Glyphs in the em box with joins, as gen_from_fonts.py writes them:
  // x from the left ink edge, `advance` the ink width, a shared baseline.
  const em = (glyph: string, form: string, strokes: number[][][], joins: Glyph['joins'] & { advance: number }): Glyph =>
    ({ ...g(glyph, form, strokes), joins })
  const ba = em('ب', 'initial', [[[120, 600], [60, 560], [0, 602]]], { advance: 120, joins_next: true, exit: [0, 602] })
  const alifFinal = em('ا', 'final', [[[90, 600], [60, 600]], [[60, 150], [60, 610]]], { advance: 90, joins_next: false, entry: [90, 600] })
  const alif = em('ا', 'isolated', [[[14, 150], [14, 610]]], { advance: 28, joins_next: false })

  it('an initial ب and a final ا meet: the entry sits on the exit', () => {
    const c = compose('با', 'ar', 'naskh', [ba, alifFinal, alif])
    expect(c.missing).toEqual([])
    const [b, a] = c.letters
    // Right to left: ب is to the right of ا, and ا's entry (its rightmost
    // point) lands exactly on ب's exit (its leftmost point).
    expect(b.x).toBeGreaterThan(a.x)
    const bExit = b.x + 0
    const aEntry = a.x + 90
    expect(Math.abs(aEntry - bExit)).toBeLessThan(0.5)
    // Shared em frame: nothing is re-fitted vertically.
    expect(c.strokes[0][0][1]).toBe(600)
    expect(c.height).toBe(1000)
  })

  it('a non-joining letter leaves a gap, and a space a wider one', () => {
    const c = compose('ا ا', 'ar', 'naskh', [ba, alifFinal, alif])
    const [first, second] = c.letters
    expect(first.x - (second.x + second.w)).toBeGreaterThan(200)
    const d = compose('اا', 'ar', 'naskh', [ba, alifFinal, alif])
    expect(d.letters[0].x - (d.letters[1].x + d.letters[1].w)).toBeCloseTo(50, 0)
  })

  it('cursive Latin: each letter starts where the last one ended', () => {
    const l = em('l', 'lower', [[[0, 620], [40, 300], [80, 640]]], { advance: 80, joins_next: true, entry: [0, 620], exit: [80, 640] })
    const o = em('o', 'lower', [[[0, 640], [30, 500], [70, 640], [90, 620]]], { advance: 90, joins_next: true, entry: [0, 640], exit: [90, 620] })
    const c = compose('lo', 'es', 'cursive', [l, o])
    expect(c.letters[1].x).toBe(c.letters[0].x + 80)
    expect(c.width).toBe(170)
  })

  it('joined Arabic letters run on as one stroke, each point owned by its letter', () => {
    const c = compose('با', 'ar', 'naskh', [ba, alifFinal, alif])
    // ب's body and ا's connector are one stroke; ا's upright is its own.
    expect(c.strokes).toHaveLength(2)
    expect(c.owners[0]).toEqual([0, 0, 0, 1, 1])
    expect(c.owners[1]).toEqual([1, 1])
    // ا's entry point follows ب's exit point in the same stroke.
    const s = c.strokes[0]
    expect(Math.abs(s[3][0] - s[2][0])).toBeLessThan(0.5)
    // A letter that does not join starts a new stroke.
    expect(compose('اا', 'ar', 'naskh', [ba, alifFinal, alif]).strokes).toHaveLength(2)
  })

  it('dots and marks of every letter come after every body, in letter order', () => {
    // ب with its dot (joins.marks = 1), then ا: the word is body, body, dot.
    const baDot = em('ب', 'initial', [[[120, 600], [60, 560], [0, 602]], [[55, 700], [65, 700]]],
      { advance: 120, joins_next: true, exit: [0, 602], marks: 1 })
    const c = compose('با', 'ar', 'naskh', [baDot, alifFinal, alif])
    // ب's body and ا's two strokes: the first runs into ب's, so three
    // strokes of body, then the dot.
    expect(c.strokes).toHaveLength(3)
    expect(c.owners.map((o) => o[0])).toEqual([0, 1, 0])
    expect(c.strokes[2][0][1]).toBe(700)
  })

  it('an open-ended trace that stops before the dots still covers the first letter', () => {
    // با: ب's body runs into ا, then back for ب's dot. A learner tracing
    // the bodies has finished both letters — the dot must not hold ب open
    // (owner: "the b is not picked up").
    const baDot = em('ب', 'initial', [[[120, 600], [60, 560], [0, 602]], [[55, 700], [65, 700]]],
      { advance: 120, joins_next: true, exit: [0, 602], marks: 1 })
    const c = compose('با', 'ar', 'naskh', [baDot, alifFinal, alif])
    expect(c.marks).toEqual([false, false, true])
    const bodies = c.strokes.slice(0, 2).map((st) => st.map(([x, y]) => ({ x, y })))
    const r = matchComposed(bodies, c, { tolerance: 0.12, openEnd: true })
    expect(r.letters[0].ok).toBe(true)
    expect(r.letters[1].ok).toBe(true)
  })

  it('cells do the same: the i-dot and the t-cross are written after the word', () => {
    const i = { ...g('i', 'lower', [[[500, 300], [500, 900]], [[490, 150], [510, 150]]]), joins: { marks: 1 } }
    const t = { ...g('t', 'lower', [[[500, 100], [500, 900]], [[300, 400], [700, 400]]]), joins: { marks: 1 } }
    const c = compose('it', 'es', 'print', [i, t])
    expect(c.owners.map((o) => o[0])).toEqual([0, 1, 0, 1])
  })

  it('falls back to cells when any glyph lacks a scale', () => {
    const c = compose('lo', 'es', 'print', [g('l', 'lower', L), g('o', 'lower', O)])
    expect(c.letters[0].w).toBeGreaterThan(500) // the old fixed cell
  })
})
