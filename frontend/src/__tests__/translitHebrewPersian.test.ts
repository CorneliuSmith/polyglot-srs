import { describe, it, expect } from 'vitest'
import {
  convertTranslit,
  finalizeTranslit,
  hasTranslit,
  translitGuide,
} from '../features/keyboards/translit'

/** Both scripts leave short vowels unwritten, so what a learner types is only
 * fully resolved at submit — assert on finalizeTranslit, the way the answer
 * actually reaches the grader. */
const fin = (code: string, s: string) => finalizeTranslit(code, s)

describe('Hebrew transliteration', () => {
  it('is offered for Hebrew', () => {
    expect(hasTranslit('he')).toBe(true)
  })

  it('writes real words, not vowel-for-vowel', () => {
    // The trap this scheme exists to avoid: spelling every vowel would give
    // שאלומ for shalom. Hebrew omits short vowels; ktiv male keeps long o/u.
    expect(fin('he', 'shalom')).toBe('שלום')
    expect(fin('he', 'sefer')).toBe('ספר')
    expect(fin('he', 'yeled')).toBe('ילד')
    expect(fin('he', 'gadol')).toBe('גדול')
  })

  it('seats a word-initial vowel on alef, with its mater for i/o/u', () => {
    expect(fin('he', 'ish')).toBe('איש')
    expect(fin('he', 'or')).toBe('אור')
    expect(fin('he', 'echad')).toBe('אחד')
    expect(fin('he', 'ani')).toBe('אני')
  })

  it('folds the five final forms at the end of a word', () => {
    expect(fin('he', 'yom')).toBe('יום') // mem  → ם
    expect(fin('he', 'ken')).toBe('כן') // nun  → ן
    expect(fin('he', 'erets')).toBe('ארץ') // tsadi → ץ
    expect(fin('he', 'melekh')).toBe('מלך') // kaf  → ך
  })

  it('keeps the medial form when the word continues', () => {
    // mem medial in מים, final in the same word's end.
    expect(fin('he', 'mayim')).toBe('מים')
  })

  it('spells a word-final a/e with he', () => {
    expect(fin('he', 'torah')).toBe('תורה')
  })

  it('handles digraphs', () => {
    expect(fin('he', 'shabat')).toContain('ש')
    expect(fin('he', 'chag')).toContain('ח')
  })

  it('leaves a trailing vowel pending while typing', () => {
    // Undecided until the next keystroke — mirrors the Arabic scheme.
    expect(convertTranslit('he', 'shalo')).toBe('שלo')
    expect(fin('he', 'shalo')).toBe('שלו')
  })

  it('publishes a key guide', () => {
    expect(translitGuide('he').length).toBeGreaterThan(3)
  })
})

describe('Persian transliteration', () => {
  it('is offered for Persian', () => {
    expect(hasTranslit('fa')).toBe(true)
  })

  it('writes everyday words', () => {
    expect(fin('fa', 'salaam')).toBe('سلام')
    expect(fin('fa', 'ketaab')).toBe('کتاب')
    expect(fin('fa', 'khoob')).toBe('خوب')
    expect(fin('fa', 'man')).toBe('من')
    expect(fin('fa', 'shab')).toBe('شب')
    expect(fin('fa', 'doost')).toBe('دوست')
  })

  it('uses the Persian-only letters', () => {
    expect(fin('fa', 'chaay')).toBe('چای') // چ
    expect(fin('fa', 'gol')).toContain('گ')
    expect(fin('fa', 'pedar')).toContain('پ')
    expect(fin('fa', 'zhaale')).toContain('ژ')
  })

  it('seats a word-initial long a on alef-madda', () => {
    expect(fin('fa', 'aab')).toBe('آب')
  })

  it('types the ZWNJ from a hyphen, so mi- attaches correctly', () => {
    // می‌روم is one word split by a zero-width non-joiner: neither می روم
    // (space) nor میروم (joined) is correct.
    const out = fin('fa', 'mi-ravam')
    expect(out).toBe('می‌روم')
    expect(out).toContain('‌')
  })

  it('leaves short vowels unwritten in the middle', () => {
    // "shab" keeps no vowel letter between ش and ب.
    expect(fin('fa', 'shab')).toHaveLength(2)
  })

  it('publishes a key guide', () => {
    expect(translitGuide('fa').length).toBeGreaterThan(3)
  })
})
