/**
 * The input-path mechanics around the converters: jamo-aware backspace,
 * the Korean syllable break, auto-capitalize tolerance, keycap labels —
 * and every literal row of the in-app key guide actually producing what it
 * promises (the th guide shipped a row whose keys produced something else
 * entirely, and nothing caught it).
 */
import { describe, it, expect } from 'vitest'
import {
  KO_KEYCAP_DISPLAY,
  backspaceUnit,
  composeScript,
  convertTranslit,
  deleteLastUnit,
  finalizeTranslit,
  translitGuide,
} from '../features/keyboards/translit'

describe('deleteLastUnit (jamo-aware backspace)', () => {
  it('peels one jamo per press, IME-style', () => {
    expect(deleteLastUnit('ko', '한')).toBe('하')
    expect(deleteLastUnit('ko', '하')).toBe('ㅎ')
    expect(deleteLastUnit('ko', 'ㅎ')).toBe('')
  })

  it('a stacked final gives back its first consonant', () => {
    expect(deleteLastUnit('ko', '없')).toBe('업')
    expect(deleteLastUnit('ko', '업')).toBe('어')
    expect(deleteLastUnit('ko', '어')).toBe('ㅇ')
  })

  it('only the LAST syllable is touched', () => {
    expect(deleteLastUnit('ko', '한국')).toBe('한구')
  })

  it('non-syllable characters delete whole, in any language', () => {
    expect(deleteLastUnit('ko', '하n')).toBe('하')
    expect(deleteLastUnit('ru', 'привет')).toBe('приве')
    expect(deleteLastUnit('ko', '')).toBe('')
  })
})

describe('backspaceUnit (the Backspace-key wrapper)', () => {
  it('peels when the char before the caret is a Hangul syllable', () => {
    expect(backspaceUnit('ko', '한국', 2, 2)).toEqual({ text: '한구', caret: 2 })
    expect(backspaceUnit('ko', '한국', 1, 1)).toEqual({ text: '하국', caret: 1 })
  })

  it('defers to native delete for selections, other scripts, plain chars', () => {
    expect(backspaceUnit('ko', '한국', 0, 2)).toBeNull() // selection
    expect(backspaceUnit('ru', 'привет', 6, 6)).toBeNull()
    expect(backspaceUnit('ko', 'abc', 3, 3)).toBeNull()
    expect(backspaceUnit('ko', '한', 0, 0)).toBeNull() // nothing before caret
  })
})

describe('Korean syllable break (-)', () => {
  it('separates syllables that would otherwise merge', () => {
    expect(finalizeTranslit('ko', 'han-a')).toBe('한아')
    expect(finalizeTranslit('ko', 'hana')).toBe('하나')
  })

  it('stays visible while typing so pending letters cannot re-merge', () => {
    // Typed g, -, g: without the visible break "gg" would read as tense ㄲ.
    expect(convertTranslit('ko', 'g-g')).toBe('g-g')
    expect(finalizeTranslit('ko', 'g-g')).toBe('ㄱㄱ')
  })
})

describe('auto-capitalize tolerance (ko/th have no capitals)', () => {
  it('a phone-capitalized first letter still converts', () => {
    expect(finalizeTranslit('ko', 'Han')).toBe('한')
    expect(finalizeTranslit('th', 'Maa')).toBe('มา')
  })
})

describe('Korean keycap labels', () => {
  it('conjoining jamo display as compatibility jamo', () => {
    expect(KO_KEYCAP_DISPLAY['ᄀ']).toBe('ㄱ') // ᄀ
    expect(KO_KEYCAP_DISPLAY['ᅡ']).toBe('ㅏ') // ᅡ
    expect(KO_KEYCAP_DISPLAY['ᄒ']).toBe('ㅎ')
    expect(KO_KEYCAP_DISPLAY['ᅵ']).toBe('ㅣ')
  })

  it('the composer still fuses what those keys insert', () => {
    expect(composeScript('ko', '하ᄂ')).toBe('한')
  })
})

describe('alphabet-deck letter cards are typeable (he/fa)', () => {
  // Mirrors the romanization column of seed_alphabet.py: typing the card's
  // shown key must produce the letter itself. Hebrew's foldable letters
  // finalize to their FINAL form — the seeder gives those cards the pair as
  // an alternative, so both spellings grade correct.
  const HEBREW: [string, string][] = [
    ['a', 'א'], ['b', 'ב'], ['g', 'ג'], ['d', 'ד'], ['h', 'ה'], ['v', 'ו'],
    ['z', 'ז'], ['ch', 'ח'], ['T', 'ט'], ['y', 'י'], ['k', 'ך'], ['l', 'ל'],
    ['m', 'ם'], ['n', 'ן'], ['s', 'ס'], ["'", 'ע'], ['p', 'ף'], ['ts', 'ץ'],
    ['q', 'ק'], ['r', 'ר'], ['sh', 'ש'], ['t', 'ת'],
  ]
  // The borrowed Arabic letters (ث ص ض ظ ط ح غ ذ) merged into plain s/z/t/h
  // and are reachable only on the on-screen keyboard — not listed here.
  const PERSIAN: [string, string][] = [
    ['aa', 'آ'], ['a', 'ا'], ['b', 'ب'], ['p', 'پ'], ['t', 'ت'], ['j', 'ج'],
    ['ch', 'چ'], ['kh', 'خ'], ['d', 'د'], ['r', 'ر'], ['z', 'ز'], ['zh', 'ژ'],
    ['s', 'س'], ['sh', 'ش'], ["'", 'ع'], ['f', 'ف'], ['q', 'ق'], ['k', 'ک'],
    ['g', 'گ'], ['l', 'ل'], ['m', 'م'], ['n', 'ن'], ['v', 'و'], ['h', 'ه'],
    ['y', 'ی'],
  ]

  it.each(HEBREW)('he: typing "%s" produces %s', (keys, letter) => {
    expect(finalizeTranslit('he', keys)).toBe(letter)
  })

  it.each(PERSIAN)('fa: typing "%s" produces %s', (keys, letter) => {
    expect(finalizeTranslit('fa', keys)).toBe(letter)
  })
})

describe('the key guide keeps its promises', () => {
  // Rows whose `keys` are literally typeable and whose `out` is the exact
  // field result — the worked examples at the bottom of each guide.
  const EXAMPLES: [string, string][] = [
    ['hi', 'namaste'],
    ['th', 'maa'],
    ['th', 'maa2'],
    ['th', 'khao'],
    ['ko', 'hanguk'],
    ['ko', 'an'],
    ['ko', 'han-a'],
  ]

  it.each(EXAMPLES)('%s: "%s" produces what the guide shows', (code, keys) => {
    const row = translitGuide(code).find((r) => r.keys === keys)
    expect(row, `guide row "${keys}" missing for ${code}`).toBeDefined()
    expect(finalizeTranslit(code, keys)).toBe(row!.out)
  })
})
