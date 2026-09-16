import { describe, expect, it } from 'vitest'
import type { Alphabet } from '../api/strokes'
import { buildPath, lessonDone, nextLesson } from '../features/write/curriculum'

const arabic: Alphabet = {
  code: 'ar', script: 'arabic', styles: ['naskh', 'ruqah'],
  letters: [
    { glyph: 'ا', romanization: 'aa', sound: '', forms: ['isolated', 'final'] },
    { glyph: 'ب', romanization: 'b', sound: '', forms: ['isolated', 'final', 'initial', 'medial'] },
    { glyph: 'ت', romanization: 't', sound: '', forms: ['isolated', 'final', 'initial', 'medial'] },
    { glyph: 'د', romanization: 'd', sound: '', forms: ['isolated', 'final'] },
    { glyph: 'پ', romanization: 'p', sound: '', forms: ['isolated', 'final', 'initial', 'medial'] },
  ],
}
const russian: Alphabet = {
  code: 'ru', script: 'cyrillic', styles: ['cursive', 'print'],
  letters: ['а', 'о', 'м', 'т', 'к', 'с', 'е', 'н'].map((g) => ({ glyph: g, romanization: g, sound: '', forms: ['lower', 'upper'] })),
}

describe('buildPath', () => {
  it('Arabic: letters by family, then their forms drilled, then words; sentences last; extras at the end', () => {
    const path = buildPath(arabic, 'naskh')
    expect(path.map((l) => l.id)).toEqual([
      'letters-1', 'forms-1', 'words-1', 'letters-2', 'forms-2', 'words-2', 'letters-3', 'forms-3', 'words-3', 'sentences',
    ])
    expect(path[0].group).toEqual(['ا', 'ب', 'ت'])
    expect(path[0].forms).toEqual(['ا|isolated', 'ب|isolated', 'ت|isolated'])
    // Forms: the positional ones, drilled on the letter repeated and pairs.
    expect(path[1].forms).toEqual(['ا|final', 'ب|final', 'ب|initial', 'ب|medial', 'ت|final', 'ت|initial', 'ت|medial'])
    expect(path[1].drills).toEqual(['با', 'ببب', 'تتت', 'اب', 'بت'])
    expect(path[2].letters).toEqual(['ا', 'ب', 'ت'])
    // د joins only to the right: drilled after a learned joiner.
    expect(path[4].drills).toContain('بد')
    expect(path[6].group).toEqual(['پ'])
    expect(path[9].kind).toBe('sentences')
    expect(path[9].letters).toHaveLength(5)
  })

  it('Cyrillic cursive: letters, capitals, joins on vowels, words; print has no joins', () => {
    const cursive = buildPath(russian, 'cursive')
    expect(cursive.map((l) => l.kind)).toEqual([
      'letters', 'capitals', 'joins', 'words', 'letters', 'capitals', 'joins', 'words', 'sentences',
    ])
    expect(cursive[0].forms).toEqual(['а|lower', 'о|lower', 'м|lower', 'т|lower', 'к|lower', 'с|lower'])
    expect(cursive[1].forms).toEqual(['а|upper', 'о|upper', 'м|upper', 'т|upper', 'к|upper', 'с|upper'])
    expect(cursive[2].drills).toContain('ма')
    expect(cursive[2].drills).toContain('ото')
    expect(buildPath(russian, 'print').map((l) => l.kind)).not.toContain('joins')
  })
})

describe('lessonDone / nextLesson', () => {
  const path = buildPath(arabic, 'naskh')
  it('a letter lesson finishes when its authored forms are known; marks cover the rest', () => {
    const known = new Map([['ا|isolated', true], ['ب|isolated', true], ['ت|isolated', false]])
    expect(lessonDone(path[0], known, new Set())).toBe(false)
    known.set('ت|isolated', true)
    expect(lessonDone(path[0], known, new Set())).toBe(true)
    // Nothing authored: only a mark finishes it.
    expect(lessonDone(path[3], new Map(), new Set())).toBe(false)
    expect(lessonDone(path[3], new Map(), new Set(['letters-2']))).toBe(true)
    expect(nextLesson(path, (l) => lessonDone(l, known, new Set(['forms-1'])))).toBe(2)
    expect(nextLesson(path, () => true)).toBe(path.length)
  })
})
