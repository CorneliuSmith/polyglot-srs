import { describe, it, expect } from 'vitest'
import { languageTheme } from '../lib/languageColors'

describe('languageTheme', () => {
  it('maps every seeded language to a flag color and emoji', () => {
    for (const code of ['es','fr','de','it','pt','ca','ro','el','ru','tr','ar','en','sw','yo','ha','xh','mi']) {
      const t = languageTheme(code)
      expect(t.primary).toMatch(/^#[0-9A-F]{6}$/i)
      expect(t.emoji.length).toBeGreaterThan(0)
    }
  })

  it('light primaries are flagged for dark text', () => {
    expect(languageTheme('ca').darkText).toBe(true)
    expect(languageTheme('xh').darkText).toBe(true)
    expect(languageTheme('fr').darkText).toBeUndefined()
  })

  it('falls back to the app default for unknown codes', () => {
    expect(languageTheme('zz').primary).toBe('#4F46E5')
    expect(languageTheme(undefined).emoji).toBe('🌐')
  })
})

describe('stageRamp', () => {
  it('walks the Māori ramp through the owner-specified palette', async () => {
    const { stageRamp } = await import('../lib/languageColors')
    const ramp = stageRamp('mi')
    expect(ramp.map((s) => s.bg.toUpperCase())).toEqual([
      '#BCBCBC', // beginner: their grey
      '#778E46', // adept: fern green
      '#CC0000', // seasoned: tino red
      '#700000', // expert: red darkened
      '#000000', // master: black
    ])
    // grey tile takes dark text; the rest take white
    expect(ramp[0].text).toBe('#1F2937')
    expect(ramp.slice(1).every((s) => s.text === '#FFFFFF')).toBe(true)
  })

  it('gives every language five colors with readable text', async () => {
    const { stageRamp } = await import('../lib/languageColors')
    for (const code of ['es','fr','de','it','pt','ca','ro','el','ru','tr','ar','en','sw','yo','ha','xh']) {
      const ramp = stageRamp(code)
      expect(ramp).toHaveLength(5)
      expect(new Set(ramp.map((s) => s.bg)).size).toBe(5)
    }
  })
})
