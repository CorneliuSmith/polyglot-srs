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
