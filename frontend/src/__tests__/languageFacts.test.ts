import { describe, it, expect } from 'vitest'
import { LANGUAGE_FACTS, factsFor } from '../features/about/languageFacts'
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
})
