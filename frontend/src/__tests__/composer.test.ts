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
