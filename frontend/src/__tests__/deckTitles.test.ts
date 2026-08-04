import { describe, it, expect } from 'vitest'
import { deckTitle } from '../lib/deckTitles'

// Stand-in for i18next's t: renders the key plus its interpolation so the
// assertions read as "this went through translation", not "this string".
const t = ((key: string, opts?: { level?: string }) =>
  opts?.level ? `${key}:${opts.level}` : key) as never

describe('deckTitle', () => {
  it('rebuilds the seeded grammar shapes from level + type', () => {
    // Every course seeds "{Language} {LEVEL} Grammar Path" (a few say just
    // "Grammar") — the course name is redundant in that course's deck list.
    for (const title of [
      'Catalan A1 Grammar Path',
      'A2 Grammar Path',
      'Xhosa B1 Grammar',
    ]) {
      expect(
        deckTitle({ title, list_type: 'grammar', level: 'A1' }, t),
      ).toBe('decks.titleGrammar:A1')
    }
  })

  it('rebuilds the seeded vocabulary shape', () => {
    expect(
      deckTitle({ title: 'A1 Vocabulary', list_type: 'vocabulary', level: 'A1' }, t),
    ).toBe('decks.titleVocab:A1')
  })

  it('keeps the Alphabet deck its own thing, not "A0 Vocabulary"', () => {
    expect(
      deckTitle({ title: 'Alphabet', list_type: 'vocabulary', level: 'A0' }, t),
    ).toBe('decks.titleAlphabet')
  })

  it('leaves a custom deck title alone — deriving would lose its meaning', () => {
    expect(
      deckTitle(
        { title: 'Business Spanish essentials', list_type: 'vocabulary', level: 'B2' },
        t,
      ),
    ).toBe('Business Spanish essentials')
  })

  it('leaves a levelless deck alone (no seeded shape to rebuild)', () => {
    expect(
      deckTitle({ title: 'A1 Vocabulary', list_type: 'vocabulary', level: null }, t),
    ).toBe('A1 Vocabulary')
  })

  it('is safe with missing fields', () => {
    expect(deckTitle({}, t)).toBe('')
    expect(deckTitle({ title: null, level: 'A1' }, t)).toBe('')
  })
})
