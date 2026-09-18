import { describe, it, expect } from 'vitest'
import { frameGlyph } from '../features/write/joins'
import { fitFrame, fromCanvas, toCanvas } from '../features/write/glyphBox'

describe('frameGlyph', () => {
  it('Arabic initial: x from 0, advance, exit at the leftmost body point, the dot a mark', () => {
    const { strokes, joins } = frameGlyph('arabic', 'naskh', 'initial', [
      [[320, 600], [260, 560], [200, 602]], [[255, 700], [265, 700]],
    ])
    expect(strokes[0][0]).toEqual([120, 600])
    expect(joins).toEqual({ advance: 120, marks: 1, joins_next: true, exit: [0, 602] })
  })

  it('Arabic final is entered at its rightmost point and joins nothing after', () => {
    const { joins } = frameGlyph('arabic', 'naskh', 'final', [[[90, 600], [60, 600], [60, 150]]])
    expect(joins.entry).toEqual([30, 600])   // x shifted so the ink starts at 0
    expect(joins.joins_next).toBe(false)
    expect(joins.exit).toBeUndefined()
  })

  it('cursive: enters at the first stroke\'s leftmost point, leaves at the body\'s rightmost', () => {
    const { joins } = frameGlyph('cyrillic', 'cursive', 'lower', [
      [[10, 620], [50, 300], [90, 640]], [[40, 200], [60, 200]],
    ])
    expect(joins).toEqual({ advance: 80, marks: 1, joins_next: true, entry: [0, 620], exit: [80, 640] })
  })

  it('print keeps only the scale', () => {
    expect(frameGlyph('latin', 'print', 'lower', [[[0, 100], [0, 900]]]).joins).toEqual({ advance: 0, marks: 0 })
  })

  it('a lone short stroke is a body, never a mark', () => {
    expect(frameGlyph('arabic', 'naskh', 'isolated', [[[0, 600], [20, 600]]]).joins.marks).toBe(0)
  })
})

describe('frame round trip', () => {
  it('ink drawn over a glyph maps back into the same box', () => {
    const glyph = [[[0, 500], [300, 700]]]
    const f = fitFrame(glyph, 240, 0.1)!
    const back = fromCanvas(toCanvas(glyph, f), f)
    expect(back).toEqual(glyph)
  })
})
