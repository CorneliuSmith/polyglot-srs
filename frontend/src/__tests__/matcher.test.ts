import { describe, it, expect } from 'vitest'
import { dtw, matchStrokes, resample } from '../features/write/matcher'

// A template: a vertical bar then a crossbar (a printed "t"), in the box.
const T = [
  [[500, 100], [500, 900]],
  [[300, 400], [700, 400]],
]

function shifted(strokes: number[][][], dx: number, dy: number, k = 1) {
  return strokes.map((s) => s.map(([x, y]) => [x * k + dx, y * k + dy]))
}

describe('matcher', () => {
  it('resamples by arc length', () => {
    const r = resample([[0, 0], [100, 0]], 5)
    expect(r.map((p) => Math.round(p[0]))).toEqual([0, 25, 50, 75, 100])
    expect(dtw(r, r)).toBe(0)
  })

  it('accepts the same strokes drawn smaller, elsewhere', () => {
    const r = matchStrokes(shifted(T, 3000, -200, 0.3), T)
    expect(r.ok).toBe(true)
    expect(r.strokes.every((v) => v.ok)).toBe(true)
  })

  it('names a stroke drawn the wrong way', () => {
    const backwards = [[[500, 900], [500, 100]], T[1]]
    const r = matchStrokes(backwards, T)
    expect(r.ok).toBe(false)
    expect(r.strokes[0].reason).toBe('direction')
    expect(r.strokes[1].ok).toBe(true)
  })

  it('names a missing and an extra stroke', () => {
    expect(matchStrokes([T[0]], T).strokes[1].reason).toBe('missing')
    expect(matchStrokes([...T, [[100, 800], [900, 800]]], T).strokes[2].reason).toBe('extra')
  })

  it('names strokes drawn in the wrong order', () => {
    const r = matchStrokes([T[1], T[0]], T)
    expect(r.ok).toBe(false)
    expect(r.strokes.map((v) => v.reason)).toEqual(['order', 'order'])
  })

  it('names a stroke of the wrong shape, and is looser for tracing', () => {
    const wobbly = [[[500, 100], [700, 500], [500, 900]], T[1]]
    expect(matchStrokes(wobbly, T, { tolerance: 0.08 }).strokes[0].reason).toBe('shape')
    expect(matchStrokes(wobbly, T, { tolerance: 0.3 }).strokes[0].ok).toBe(true)
  })
})
