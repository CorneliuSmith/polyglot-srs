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

  it('renders a trailing consonant as the batchim at once (owner ruling)', () => {
    // "Consider it batchim unless the next character proves otherwise":
    // 한 renders on the n keystroke, not 하n. Only a consonant with no
    // syllable before it still waits as Latin.
    expect(convertTranslit('ko', 'han')).toBe('한')
    expect(convertTranslit('ko', 'bap')).toBe('밥')
    expect(convertTranslit('ko', 'g')).toBe('g')
    expect(finalizeTranslit('ko', 'g')).toBe('ㄱ')
  })

  it('a vowel re-opens the committed batchim, carrying the letter as-is', () => {
    // The owner's example: 밥 + a → 바바 — the ㅂ moves into the next
    // syllable unchanged. An aspirated initial after a closed syllable is
    // spelled explicitly (kha/tha/pha/cha) or with the - break.
    expect(typeWord('ko', 'bapa')).toBe('바바')
    expect(typeWord('ko', 'bapo')).toBe('바보')
    expect(typeWord('ko', 'hanguka')).toBe('한구가')
    expect(typeWord('ko', 'hangukha')).toBe('한구카')
    expect(typeWord('ko', 'ba-ka')).toBe('바카')
  })

  it('the n|ng split stays revisable after the batchim commits', () => {
    // 방 mid-word: the ㅇ was committed as the final, but a vowel proves it
    // was n + g all along — 반가, not 바아. This is what decoding finals to
    // lax romanization buys.
    expect(typeWord('ko', 'banga')).toBe('반가')
    expect(convertTranslit('ko', convertTranslit('ko', 'ban') + 'g')).toBe('방')
  })

  it('a lax final stays lax when the next syllable opens (owner report)', () => {
    // The bug: the final's romanization was re-read in initial position, so
    // ㄱ/ㄷ/ㅂ came back as the ASPIRATED ㅋ/ㅌ/ㅍ.
    expect(typeWord('ko', 'gada')).toBe('가다')      // was 가타
    expect(typeWord('ko', 'guga')).toBe('구가')      // was 구카
    expect(typeWord('ko', 'baba')).toBe('바바')      // was 바파
    expect(typeWord('ko', 'hanguga')).toBe('한구가')
  })

  it('tense and aspirated finals still build letter-by-letter', () => {
    // Each keystroke commits the plain batchim first; the doubling k or the
    // h then upgrades it in place.
    expect(typeWord('ko', 'bakk')).toBe('밖')
    expect(typeWord('ko', 'iss')).toBe('있')
    expect(typeWord('ko', 'bueokh')).toBe('부엌')
    expect(typeWord('ko', 'aph')).toBe('앞')
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

/** On-screen keyboard path: it emits CONJOINING jamo, and composeScript runs
 * the whole field through the encoder after every tap. */
function tapJamo(keys: string[]): string {
  let field = ''
  for (const k of keys) field = composeScript('ko', field + k)
  return finalizeTranslit('ko', field)
}

describe('Korean stacked (compound) finals', () => {
  // Eleven finals hold TWO consonants in one syllable's bottom slot. They
  // could be decoded but never assembled, so the second consonant fell out
  // of the block and sat beside it — 없 came out 업ㅅ, 앉 came out 안ㅈ.
  // 없 alone ("there isn't") is among the most-used words in the language.
  it('assembles them from romanization', () => {
    expect(typeWord('ko', 'eops')).toBe('없')  // ㅄ
    expect(typeWord('ko', 'anj')).toBe('앉')   // ㄵ
    expect(typeWord('ko', 'dalk')).toBe('닭')  // ㄺ
    expect(typeWord('ko', 'salm')).toBe('삶')  // ㄻ
  })

  it('assembles them from on-screen jamo taps', () => {
    expect(tapJamo(['ᄋ', 'ᅥ', 'ᄇ', 'ᄉ'])).toBe('없')
    expect(tapJamo(['ᄋ', 'ᅡ', 'ᄂ', 'ᄌ'])).toBe('앉')
    expect(tapJamo(['ᄃ', 'ᅡ', 'ᄅ', 'ᄀ'])).toBe('닭')
  })

  it('keeps the stack when the next syllable opens with a consonant', () => {
    // 없어 — the ㅇ is a written initial, so both consonants stay put.
    expect(tapJamo(['ᄋ', 'ᅥ', 'ᄇ', 'ᄉ', 'ᄋ', 'ᅥ'])).toBe('없어')
  })

  it('SPLITS the stack when a vowel follows, like a real IME', () => {
    // A vowel claims the second consonant as its own initial: 없 + ㅏ is
    // 업사, never 없아. Getting this wrong is what a naive "just stack them"
    // implementation does, and it strands the vowel outside any block.
    expect(tapJamo(['ᄋ', 'ᅥ', 'ᄇ', 'ᄉ', 'ᅡ'])).toBe('업사')
  })

  it('leaves single finals and open syllables alone', () => {
    // The regression risk: every ordinary word runs through the same branch.
    expect(typeWord('ko', 'hanguk')).toBe('한국')
    expect(typeWord('ko', 'hangeul')).toBe('한글')
    expect(typeWord('ko', 'gada')).toBe('가다')
    expect(typeWord('ko', 'anta')).toBe('안타')
    expect(tapJamo(['ᄒ', 'ᅡ', 'ᄂ', 'ᄀ', 'ᅮ', 'ᄀ'])).toBe('한국')
  })

  it('round-trips a stacked final that is already on screen', () => {
    for (const word of ['없', '앉', '닭', '삶', '없어']) {
      expect(convertTranslit('ko', word)).toBe(word)
      expect(finalizeTranslit('ko', word)).toBe(word)
    }
  })
})
