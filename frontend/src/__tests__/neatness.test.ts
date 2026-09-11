import { describe, it, expect } from 'vitest'
import { clusterStrokes, neatness } from '../features/write/neatness'
import { hasInk } from '../features/write/ink'
import type { Stroke } from '../features/write/ink'

/** A vertical bar from (x, top) down to (x, top+h), leaning by `lean` px
 * over its height. */
function bar(x: number, top: number, h: number, lean = 0): Stroke {
  const pts: Stroke = []
  for (let i = 0; i <= 10; i++) {
    pts.push({ x: x + (lean * i) / 10, y: top + (h * i) / 10 })
  }
  return pts
}

/** A row of bars, evenly spaced, same height, on one line. */
function neatRow(n = 6, gap = 30): Stroke[] {
  return Array.from({ length: n }, (_, i) => bar(20 + i * gap, 100, 40))
}

describe('neatness', () => {
  it('calls a tidy row steady on every measure', () => {
    const r = neatness(neatRow())
    expect(r).toMatchObject({ baseline: 'good', size: 'good', slant: 'good', spacing: 'good' })
    expect(r.clusters).toBe(6)
  })

  it('has nothing to say about too little ink', () => {
    // Two letters is not a line; one stroke is not a hand.
    expect(neatness(neatRow(2)).baseline).toBe('na')
    expect(neatness([bar(10, 10, 40)]).spacing).toBe('na')
  })

  it('reads a sloping line as a wandering baseline', () => {
    const sloping = Array.from({ length: 6 }, (_, i) => bar(20 + i * 30, 100 + i * 12, 40))
    expect(neatness(sloping).baseline).toBe('poor')
    // ...and a bumpy one too, even when the fitted slope is flat.
    const bumpy = Array.from({ length: 6 }, (_, i) => bar(20 + i * 30, 100 + (i % 2) * 18, 40))
    expect(neatness(bumpy).baseline).not.toBe('good')
  })

  it('reads letters of wildly different heights as uneven', () => {
    const sizes = Array.from({ length: 6 }, (_, i) =>
      bar(20 + i * 30, 140 - (i % 2 ? 80 : 20), i % 2 ? 80 : 20),
    )
    expect(neatness(sizes).size).toBe('poor')
  })

  it('reads a mix of upright and leaning strokes as an inconsistent slant', () => {
    const mixed = Array.from({ length: 6 }, (_, i) => bar(20 + i * 30, 100, 40, i % 2 ? 25 : -25))
    expect(neatness(mixed).slant).toBe('poor')
    // A consistent lean is fine — slant is about consistency, not angle.
    const leaning = Array.from({ length: 6 }, (_, i) => bar(20 + i * 30, 100, 40, 15))
    expect(neatness(leaning).slant).toBe('good')
  })

  it('reads irregular gaps as uneven spacing', () => {
    // Strokes closer than 15 % of the letter height (6 px here) are one
    // letter: three pairs become three clusters, and two gaps are too few
    // to judge.
    const pairs = [20, 23, 90, 93, 200, 203].map((x) => bar(x, 100, 40))
    expect(neatness(pairs).clusters).toBe(3)
    expect(neatness(pairs).spacing).toBe('na')
    // Gaps of 10, 100, 12, 110 are not one rhythm.
    const ragged = [20, 30, 130, 142, 252].map((x) => bar(x, 100, 40))
    expect(neatness(ragged).clusters).toBe(5)
    expect(neatness(ragged).spacing).toBe('poor')
  })

  it('groups the strokes of one letter into one cluster', () => {
    // A cross: a vertical bar and a horizontal bar through it.
    const cross: Stroke[] = [
      bar(50, 100, 40),
      [{ x: 40, y: 120 }, { x: 60, y: 120 }],
      bar(120, 100, 40),
    ]
    expect(clusterStrokes(cross)).toHaveLength(2)
  })

  it('does not count a tap as ink', () => {
    expect(hasInk([[{ x: 5, y: 5 }, { x: 6, y: 6 }]])).toBe(false)
    expect(hasInk([bar(10, 10, 40)])).toBe(true)
  })
})
