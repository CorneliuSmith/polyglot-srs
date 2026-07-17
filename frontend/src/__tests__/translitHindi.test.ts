import { describe, it, expect } from 'vitest'
import { convertTranslit, finalizeTranslit, hasTranslit } from '../features/keyboards/translit'

/** Simulate typing a word one Latin key at a time, re-converting the whole
 * field each keystroke exactly as DrillCard does, then finalize at submit. */
function typeWord(word: string): string {
  let field = ''
  for (const ch of word) field = convertTranslit('hi', field + ch)
  return finalizeTranslit('hi', field)
}

describe('Hindi (Devanagari) transliteration input', () => {
  it('is registered as a transliteration language', () => {
    expect(hasTranslit('hi')).toBe(true)
  })

  it('builds syllables with matras and clusters', () => {
    expect(typeWord('namaste')).toBe('नमस्ते')
    expect(typeWord('kitaab')).toBe('किताब')
    // n before a consonant is a full न + virama cluster (हिन्दी); the
    // anusvara spelling हिंदी is typed explicitly with M (see below).
    expect(typeWord('hindii')).toBe('हिन्दी')
  })

  it('writes a word-final consonant bare (schwa spelling), not with halant', () => {
    expect(typeWord('raam')).toBe('राम')
    expect(typeWord('pustak')).toBe('पुस्तक')
    expect(typeWord('aap')).toBe('आप')
  })

  it('handles long vowels via doubling and independent word-initial vowels', () => {
    expect(typeWord('paanii')).toBe('पानी')
    expect(typeWord('aam')).toBe('आम')
  })

  it('maps retroflex capitals, the nukta flap R, and aspirate digraphs', () => {
    // Between two consonants the inherent 'a' is written (ITRANS convention):
    // laRakaa = लड़का, whereas laRkaa would be the ड़्क cluster.
    expect(typeWord('laRakaa')).toBe('लड़का') // R → ड़ (nukta flap)
    expect(typeWord('TamaaTar')).toBe('टमाटर') // T → ट (retroflex)
    expect(typeWord('khaanaa')).toBe('खाना')
    expect(typeWord('achchhaa')).toBe('अच्छा')
  })

  it('is idempotent on already-converted Devanagari', () => {
    expect(convertTranslit('hi', 'नमस्ते')).toBe('नमस्ते')
    expect(convertTranslit('hi', 'किताब')).toBe('किताब')
    expect(convertTranslit('hi', 'लड़का')).toBe('लड़का')
  })

  it('maps M to anusvara for nasalized spellings', () => {
    expect(typeWord('hiMdii')).toBe('हिंदी')
    expect(typeWord('hiMdii')).toContain('ं')
  })
})
