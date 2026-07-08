import { describe, it, expect } from 'vitest'
import {
  convertTranslit,
  finalizeTranslit,
  finalizeInput,
  hasTranslit,
  isTranslitEnabled,
  translitGuide,
} from '../features/keyboards/translit'

/** Simulate real typing: each keystroke re-converts the whole input value. */
function type(code: string, text: string): string {
  return [...text].reduce((acc, ch) => convertTranslit(code, acc + ch), '')
}

describe('convertTranslit — Russian', () => {
  it('converts pasted words in one go', () => {
    expect(convertTranslit('ru', 'privet')).toBe('привет')
    expect(convertTranslit('ru', 'shkola')).toBe('школа')
    expect(convertTranslit('ru', 'khorosho')).toBe('хорошо')
    expect(convertTranslit('ru', 'yolka')).toBe('ёлка')
    expect(convertTranslit('ru', 'chitat')).toBe('читат')
  })

  it('completes digraphs typed across keystrokes', () => {
    expect(type('ru', 'shkola')).toBe('школа')
    expect(type('ru', 'zhena')).toBe('жена')
    expect(type('ru', 'chas')).toBe('час')
    expect(type('ru', 'yolka')).toBe('ёлка')
    expect(type('ru', 'ya')).toBe('я')
    expect(type('ru', 'shchi')).toBe('щи')
  })

  it('handles soft/hard signs and э', () => {
    expect(type('ru', "mat'")).toBe('мать')
    expect(type('ru', "pod''ezd")).toBe('подъезд')
    expect(type('ru', "e'to")).toBe('это')
  })

  it('preserves case', () => {
    expect(type('ru', 'Moskva')).toBe('Москва')
    expect(type('ru', 'Shkola')).toBe('Школа')
  })

  it('is idempotent on converted text', () => {
    expect(convertTranslit('ru', 'привет')).toBe('привет')
  })
})

describe('convertTranslit — Greek', () => {
  it('converts words and applies final sigma', () => {
    expect(type('el', 'kalos')).toBe('καλος')
    expect(type('el', 'kalos').endsWith('ς')).toBe(true)
    expect(type('el', 'spiti')).toBe('σπιτι')
    expect(type('el', 'thelo')).toBe('θελω'.replace('ω', 'ο')) // o → ο (w is ω)
    expect(type('el', 'thelw')).toBe('θελω')
    expect(type('el', 'psomi')).toBe('ψωμι'.replace('ω', 'ο'))
  })

  it('un-finalizes sigma when the word continues', () => {
    expect(type('el', 'kalosini')).toBe('καλοσινι')
    expect(type('el', 'kalosini')).not.toContain('ς')
  })

  it('handles digraphs typed across keystrokes', () => {
    expect(type('el', 'chara')).toBe('χαρα')
    expect(type('el', 'thalassa')).toBe('θαλασσα')
  })
})

describe('convertTranslit — Arabic', () => {
  it('writes long vowels, drops medial short vowels', () => {
    expect(type('ar', 'kitaab')).toBe('كتاب')
    expect(type('ar', 'fii')).toBe('في')
    expect(type('ar', 'shams')).toBe('شمس')
    expect(type('ar', 'kabiir')).toBe('كبير')
  })

  it('seats word-initial vowels on alif', () => {
    expect(finalizeTranslit('ar', type('ar', 'ana'))).toBe('انا')
  })

  it('maps emphatics from capitals and chat digits', () => {
    expect(type('ar', 'Sabaa7')).toBe('صباح')
    expect(type('ar', 'SabaaH')).toBe('صباح')
    expect(type('ar', '3arab')).toBe('عرب')
    expect(type('ar', '7ub')).toBe('حب')
  })

  it('a pending vowel keeps digraph letters apart (سهل, not شل)', () => {
    expect(type('ar', 'sahl')).toBe('سهل')
  })

  it('leaves a trailing short vowel pending, finalize resolves it', () => {
    const typed = type('ar', 'fi')
    expect(typed).toBe('فi') // undecided until submit
    expect(finalizeTranslit('ar', typed)).toBe('في')
    expect(finalizeTranslit('ar', type('ar', 'hadha'))).toBe('هذا')
  })

  it('writes word-final ah as taa marbuta', () => {
    expect(type('ar', 'madrasah')).toBe('مدرسة')
  })
})

describe('helpers', () => {
  it('hasTranslit covers exactly the non-Latin scripts', () => {
    expect(hasTranslit('ru')).toBe(true)
    expect(hasTranslit('ar')).toBe(true)
    expect(hasTranslit('el')).toBe(true)
    expect(hasTranslit('es')).toBe(false)
    expect(hasTranslit('tr')).toBe(false)
  })

  it('is enabled by default, off when the pref says so', () => {
    expect(isTranslitEnabled('ru', {})).toBe(true)
    expect(isTranslitEnabled('ru', { ru: false })).toBe(false)
    expect(isTranslitEnabled('es', {})).toBe(false)
  })

  it('finalizeInput respects the pref', () => {
    expect(finalizeInput('ar', 'فi', {})).toBe('في')
    expect(finalizeInput('ar', 'فi', { ar: false })).toBe('فi')
  })

  it('every supported language ships a key guide', () => {
    for (const code of ['ru', 'ar', 'el']) {
      expect(translitGuide(code).length).toBeGreaterThan(4)
    }
    expect(translitGuide('es')).toEqual([])
  })
})
