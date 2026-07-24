import { describe, it, expect } from 'vitest'
import {
  LANGUAGE_FACTS,
  LANGUAGE_FLAGS,
  LANGUAGE_SYNTAX,
  factsFor,
  flagsFor,
  syntaxFor,
} from '../features/about/languageFacts'
import { LETTERS } from '../features/letters/lettersData'

describe('languageFacts', () => {
  it('covers every language that has a Letters & Sounds guide', () => {
    // The two references should stay in lockstep so a learner never gets one
    // without the other.
    for (const code of Object.keys(LETTERS)) {
      expect(LANGUAGE_FACTS[code], `missing facts for ${code}`).toBeDefined()
    }
  })

  it('every entry is complete — no blank fields', () => {
    for (const [code, f] of Object.entries(LANGUAGE_FACTS)) {
      for (const field of [
        'tagline', 'family', 'speakers', 'whereSpoken', 'writingSystem',
        'wordOrder', 'history',
      ] as const) {
        expect(f[field]?.trim(), `${code}.${field}`).toBeTruthy()
      }
      expect(f.unique.length, `${code}.unique`).toBeGreaterThanOrEqual(3)
      expect(f.unique.every((u) => u.trim().length > 0)).toBe(true)
    }
  })

  it('factsFor is null-safe for unknown / missing codes', () => {
    expect(factsFor(undefined)).toBeNull()
    expect(factsFor(null)).toBeNull()
    expect(factsFor('zz')).toBeNull()
    expect(factsFor('es')).not.toBeNull()
  })

  it('every language has a glossed syntax example and flags', () => {
    for (const code of Object.keys(LANGUAGE_FACTS)) {
      const ex = LANGUAGE_SYNTAX[code]
      expect(ex?.length, `missing syntax for ${code}`).toBeGreaterThanOrEqual(1)
      for (const e of ex) {
        expect(e.words.length, `${code} words`).toBeGreaterThanOrEqual(2)
        expect(e.words.every((w) => w.w.trim() && w.g.trim())).toBe(true)
        expect(e.translation.trim(), `${code} translation`).toBeTruthy()
      }
      expect(LANGUAGE_FLAGS[code]?.trim(), `missing flags for ${code}`).toBeTruthy()
    }
  })

  it('syntaxFor / flagsFor are null-safe', () => {
    expect(syntaxFor(undefined)).toEqual([])
    expect(syntaxFor('zz')).toEqual([])
    expect(syntaxFor('de').length).toBeGreaterThan(0)
    expect(flagsFor(null)).toBe('')
    expect(flagsFor('ja')).toBe('')
    expect(flagsFor('es')).toContain('🇪🇸')
  })
})
