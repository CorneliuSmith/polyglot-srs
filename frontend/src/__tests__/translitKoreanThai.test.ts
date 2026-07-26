import { describe, it, expect } from 'vitest'
import {
  composeScript,
  convertTranslit,
  finalizeTranslit,
  hasTranslit,
  translitGuide,
} from '../features/keyboards/translit'

/** Type a word one keystroke at a time, then submit — the real integration
 * contract (convert on every change, finalize on submit). */
function typeWord(code: string, word: string): string {
  let field = ''
  for (const ch of word) field = convertTranslit(code, field + ch)
  return finalizeTranslit(code, field)
}

describe('Korean (Hangul) transliteration', () => {
  it('is registered', () => {
    expect(hasTranslit('ko')).toBe(true)
    expect(translitGuide('ko').length).toBeGreaterThan(4)
  })

  it('assembles jamo into syllable blocks', () => {
    // consonant + vowel, then a closed syllable with a final.
    expect(typeWord('ko', 'ga')).toBe('가')
    expect(typeWord('ko', 'han')).toBe('한')
    expect(typeWord('ko', 'hanguk')).toBe('한국')
    expect(typeWord('ko', 'saram')).toBe('사람')
  })

  it('splits CVCV so the middle consonant opens the next syllable', () => {
    // hana must be 하나, never 한ㅏ or 하나's mis-parse 한+a.
    expect(typeWord('ko', 'hana')).toBe('하나')
    expect(typeWord('ko', 'nara')).toBe('나라')
  })

  it('reads "ng" as the final only when no vowel follows it', () => {
    // sarang: ng closes the word. hanguk: the n closes 한 and g opens 국.
    expect(typeWord('ko', 'sarang')).toBe('사랑')
    expect(typeWord('ko', 'hangeul')).toBe('한글')
  })

  it('seats a bare vowel on the silent placeholder', () => {
    expect(typeWord('ko', 'an')).toBe('안')
    expect(typeWord('ko', 'urea')).toContain('우')
  })

  it('distinguishes plain, aspirated and tense series', () => {
    expect(typeWord('ko', 'da')).toBe('다')   // ㄷ
    expect(typeWord('ko', 'ta')).toBe('타')   // ㅌ aspirated
    expect(typeWord('ko', 'tta')).toBe('따')  // ㄸ tense
    expect(typeWord('ko', 'ja')).toBe('자')
    expect(typeWord('ko', 'cha')).toBe('차')
  })

  it('handles compound vowels', () => {
    expect(typeWord('ko', 'wae')).toBe('왜')
    expect(typeWord('ko', 'yeoja')).toBe('여자')
    expect(typeWord('ko', 'uisa')).toBe('의사')
  })

  it('holds a just-typed trailing consonant pending, settles it on submit', () => {
    // It is genuinely undecided: "ba"+"p" could close 밥 or open 바포. So it
    // stays Latin until the next keystroke or submit decides — committing it
    // early is what used to flip the aspiration.
    expect(convertTranslit('ko', 'han')).toBe('하n')
    expect(finalizeTranslit('ko', 'han')).toBe('한')
    expect(convertTranslit('ko', 'g')).toBe('g')
    expect(finalizeTranslit('ko', 'g')).toBe('ㄱ')
  })

  it('a lax final stays lax when the next syllable opens (owner report)', () => {
    // The bug: the final's romanization was re-read in initial position, so
    // ㄱ/ㄷ/ㅂ came back as the ASPIRATED ㅋ/ㅌ/ㅍ.
    expect(typeWord('ko', 'gada')).toBe('가다')      // was 가타
    expect(typeWord('ko', 'guga')).toBe('구가')      // was 구카
    expect(typeWord('ko', 'baba')).toBe('바바')      // was 바파
    expect(typeWord('ko', 'hanguga')).toBe('한구가')
    // …while a genuinely aspirated initial after a closed syllable is kept.
    expect(typeWord('ko', 'bapo')).toBe('바포')
    expect(typeWord('ko', 'hanguka')).toBe('한구카')
  })

  it('round-trips finals that romanization cannot spell', () => {
    // An aspirated final (부엌) and a stacked one (없) must survive a
    // conversion pass untouched.
    for (const word of ['부엌', '없다', '옷', '밥', '국아', '한글']) {
      expect(convertTranslit('ko', word), word).toBe(word)
      expect(finalizeTranslit('ko', word), word).toBe(word)
    }
  })

  it('is idempotent on already-composed Hangul', () => {
    for (const word of ['한국', '사랑', '하나', '의사']) {
      expect(convertTranslit('ko', word)).toBe(word)
      expect(finalizeTranslit('ko', word)).toBe(word)
    }
  })
})

describe('composeScript — on-screen keyboard jamo', () => {
  it('fuses the conjoining jamo the Korean layout emits', () => {
    // U+1112 ᄒ + U+1161 ᅡ + U+11AB ᆫ  ->  한
    expect(composeScript('ko', '한')).toBe('한')
    // Initial + medial with no final.
    expect(composeScript('ko', '가')).toBe('가')
  })

  it('accepts compatibility jamo too (the letters page / clipboard)', () => {
    expect(composeScript('ko', 'ㅎㅏㄴ')).toBe('한')
  })

  it('leaves every other script untouched', () => {
    expect(composeScript('ru', 'привет')).toBe('привет')
    expect(composeScript('th', 'มา')).toBe('มา')
    expect(composeScript('es', 'hola')).toBe('hola')
    expect(composeScript('hi', 'नाम')).toBe('नाम')
  })
})

describe('Thai transliteration', () => {
  it('is registered', () => {
    expect(hasTranslit('th')).toBe(true)
    expect(translitGuide('th').length).toBeGreaterThan(4)
  })

  it('wraps trailing and lengthening vowels around the consonant', () => {
    expect(typeWord('th', 'maa')).toBe('มา')
    expect(typeWord('th', 'ma')).toBe('มะ')
    expect(typeWord('th', 'dii')).toBe('ดี')
    expect(typeWord('th', 'duu')).toBe('ดู')
  })

  it('writes leading vowels BEFORE the consonant they follow in speech', () => {
    // เ, แ, โ, ไ are typed after their consonant but written before it.
    expect(typeWord('th', 'me')).toBe('เม')
    expect(typeWord('th', 'mae')).toBe('แม')
    expect(typeWord('th', 'mo')).toBe('โม')
    expect(typeWord('th', 'mai')).toBe('ไม')
  })

  it('surrounds the consonant for compound vowels', () => {
    expect(typeWord('th', 'mia')).toBe('เมีย')
    expect(typeWord('th', 'mao')).toBe('เมา')
  })

  it('places tone marks on the initial consonant', () => {
    // máa (horse) = ม + mai tho + า
    expect(typeWord('th', 'maa2')).toBe('ม้า')
    expect(typeWord('th', 'mai2')).toBe('ไม้')
  })

  it('appends final consonants after the vowel', () => {
    expect(typeWord('th', 'maak')).toBe('มาก')
    expect(typeWord('th', 'khaan')).toBe('ขาน')
  })

  it('takes digraph consonants as one letter', () => {
    expect(typeWord('th', 'khaa')).toBe('ขา')
    expect(typeWord('th', 'chaa')).toBe('ชา')
    expect(typeWord('th', 'thaa')).toBe('ทา')
    expect(typeWord('th', 'phaa')).toBe('พา')
    expect(typeWord('th', 'ngaa')).toBe('งา')
  })

  it('seats a vowel with no consonant on the carrier', () => {
    expect(typeWord('th', 'aa')).toBe('อา')
  })

  it('leaves a lone consonant pending while typing, resolves on submit', () => {
    expect(convertTranslit('th', 'm')).toBe('m')
    expect(finalizeTranslit('th', 'm')).toBe('ม')
  })

  it('is idempotent on already-converted Thai', () => {
    for (const word of ['มา', 'เมีย', 'ม้า', 'มาก', 'ขา']) {
      expect(convertTranslit('th', word)).toBe(word)
      expect(finalizeTranslit('th', word)).toBe(word)
    }
  })
})
