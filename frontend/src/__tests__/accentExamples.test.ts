import { describe, it, expect } from 'vitest'
import { ACCENT_EXAMPLES, accentExampleFor } from '../lib/accentExamples'

/** Every language the app can be studied in (mirrors the NLP registry). */
const ALL_CODES = [
  'ru', 'ar', 'en', 'sw', 'tr', 'yo', 'ha', 'xh', 'es', 'it', 'fr', 'de',
  'ca', 'mi', 'ro', 'el', 'pt', 'hi', 'jam', 'nl', 'th', 'ko', 'la', 'id',
  'tl', 'he', 'fa',
]

/** Languages whose written form carries no marks to make optional — the
 *  toggle must not appear at all. */
const NO_MARKS = ['en', 'sw', 'xh', 'id', 'tl', 'jam', 'ha', 'hi', 'th', 'ko']

describe('accents-optional examples', () => {
  it('never explains itself with another language’s word', () => {
    for (const [code, ex] of Object.entries(ACCENT_EXAMPLES)) {
      expect(ex.loose, code).not.toBe('')
      expect(ex.strict, code).not.toBe('')
      expect(ex.gloss, code).not.toBe('')
    }
  })

  it('the loose form really is the strict one with its marks removed', () => {
    for (const [code, ex] of Object.entries(ACCENT_EXAMPLES)) {
      const folded = ex.strict.normalize('NFD').replace(/\p{M}/gu, '')
      expect(folded.toLowerCase(), `${code}: ${ex.strict} folds to ${folded}`)
        .toBe(ex.loose.toLowerCase())
    }
  })

  it('the two spellings are actually different', () => {
    // A pair that folds to itself would show the learner "x passes for x".
    for (const [code, ex] of Object.entries(ACCENT_EXAMPLES)) {
      expect(ex.loose, code).not.toBe(ex.strict)
    }
  })

  it('hides the toggle for languages with nothing to fold', () => {
    for (const code of NO_MARKS) {
      expect(accentExampleFor(code), code).toBeNull()
    }
  })

  it('covers every language that does have marks', () => {
    const expected = ALL_CODES.filter((c) => !NO_MARKS.includes(c))
    for (const code of expected) {
      expect(accentExampleFor(code), `no accent example for ${code}`).not.toBeNull()
    }
  })

  it('is null for an unknown or missing language', () => {
    expect(accentExampleFor(undefined)).toBeNull()
    expect(accentExampleFor(null)).toBeNull()
    expect(accentExampleFor('zz')).toBeNull()
  })
})
