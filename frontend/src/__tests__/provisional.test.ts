import { describe, it, expect } from 'vitest'
import { withProvisional, isProvisionalId } from '../features/write/strokes/provisional'
import type { Glyph } from '../api/strokes'
import arabic from '../features/write/strokes/arabic.json'

const bundledBa = (arabic as { glyphs: Omit<Glyph, 'id'>[] }).glyphs.find(
  (g) => g.glyph === 'ب' && g.form === 'initial' && g.style === 'naskh',
)!

function serverRow(over: Partial<Glyph>): Glyph {
  return {
    id: 'row-1', script: 'arabic', glyph: 'ب', form: 'initial', style: 'naskh',
    strokes: [[[0, 0], [100, 100]]], joins: {}, hints: ['old'], source: 'provisional', reviewed: true,
    ...over,
  }
}

describe('withProvisional', () => {
  it('fills forms the server lacks with bundled ids the server will not accept', () => {
    const out = withProvisional('arabic', 'naskh', [])
    expect(out.length).toBeGreaterThan(100)
    expect(out.every((g) => isProvisionalId(g.id))).toBe(true)
  })

  it("replaces a provisional server row's shape with the newer bundle, keeping its id", () => {
    const [ba] = withProvisional('arabic', 'naskh', [serverRow({})])
    expect(ba.id).toBe('row-1')
    expect(ba.strokes).toEqual(bundledBa.strokes)
    expect(ba.joins).toEqual(bundledBa.joins)
    expect(ba.hints).toEqual(bundledBa.hints)
  })

  it("never touches a speaker's row", () => {
    const row = serverRow({ source: 'workshop' })
    const [ba] = withProvisional('arabic', 'naskh', [row])
    expect(ba).toBe(row)
    expect(ba.strokes).toEqual([[[0, 0], [100, 100]]])
  })

  it('leaves scripts without a bundle alone', () => {
    const rows = [serverRow({ script: 'tifinagh' })]
    expect(withProvisional('tifinagh', 'print', rows)).toBe(rows)
  })
})
