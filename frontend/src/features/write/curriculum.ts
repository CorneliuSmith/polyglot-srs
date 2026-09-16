import type { Alphabet } from '../../api/strokes'
import { scriptOf } from './composer'

/**
 * The learning path (docs/plans/handwriting.md, §13): a script's writing
 * course as an ordered list of lessons, built from the alphabet — so it
 * exists for every course the day the alphabet does, and the strokes
 * fill it in as they are authored.
 *
 * The shape is the one handwriting courses have always had: a few
 * letters at a time; then what those letters do in a word — Arabic's
 * positional forms, cursive's joins, a cased script's capitals — drilled
 * on short made-up strings; then real words that use only what has been
 * taught (the server filters the course's words by letter); sentences
 * once the alphabet is done. Groups are by shape family for Arabic and by
 * familiarity for Cyrillic; other scripts go in alphabet order, six at a
 * time.
 */
export type LessonKind = 'letters' | 'forms' | 'capitals' | 'joins' | 'words' | 'sentences'

export interface Lesson {
  id: string
  kind: LessonKind
  /** The letters this lesson is about (display). */
  group: string[]
  /** Form keys (`glyph|form`) taught here — letters, forms, capitals. */
  forms: string[]
  /** Fixed strings to trace — the joins and forms drills. */
  drills: string[]
  /** Every letter taught by the end of this lesson — the prompt filter. */
  letters: string[]
}

const ARABIC_GROUPS = [
  ['ا', 'ب', 'ت', 'ث'], ['ج', 'ح', 'خ'], ['د', 'ذ', 'ر', 'ز'], ['س', 'ش', 'ص', 'ض'],
  ['ط', 'ظ', 'ع', 'غ'], ['ف', 'ق', 'ك', 'ل'], ['م', 'ن', 'ه', 'و', 'ي'],
]
const CYRILLIC_GROUPS = [
  ['а', 'о', 'м', 'т', 'к', 'с'], ['е', 'н', 'р', 'в', 'у', 'х'], ['и', 'й', 'л', 'п', 'б', 'г'],
  ['д', 'з', 'ж', 'ч', 'ш', 'щ'], ['ц', 'ф', 'ы', 'э', 'ю', 'я'], ['ъ', 'ь', 'ё'],
]
const VOWELS = new Set('аоиеуыэюяё')

function groupsFor(script: string, letters: string[]): string[][] {
  const preset = script === 'arabic' ? ARABIC_GROUPS : script === 'cyrillic' ? CYRILLIC_GROUPS : null
  const have = new Set(letters)
  const groups: string[][] = []
  const placed = new Set<string>()
  if (preset) {
    for (const g of preset) {
      const own = g.filter((l) => have.has(l))
      if (own.length) {
        groups.push(own)
        own.forEach((l) => placed.add(l))
      }
    }
  }
  const rest = letters.filter((l) => !placed.has(l))
  for (let i = 0; i < rest.length; i += 6) groups.push(rest.slice(i, i + 6))
  return groups
}

export function buildPath(alphabet: Alphabet, style: string): Lesson[] {
  const script = alphabet.script
  const formsOf = new Map(alphabet.letters.map((l) => [l.glyph, l.forms]))
  const groups = groupsFor(script, alphabet.letters.map((l) => l.glyph))
  const lessons: Lesson[] = []
  const taught: string[] = []
  const cursive = style === 'cursive' && (script === 'cyrillic' || script === 'latin')

  groups.forEach((group, gi) => {
    const n = gi + 1
    const before = [...taught]
    taught.push(...group)
    const letters = [...taught]
    const single = (l: string) => {
      const f = formsOf.get(l) ?? ['letter']
      return f.includes('isolated') ? 'isolated' : f.includes('lower') ? 'lower' : f[0]
    }
    lessons.push({
      id: `letters-${n}`, kind: 'letters', group, letters,
      forms: group.map((l) => `${l}|${single(l)}`), drills: [],
    })
    if (script === 'arabic') {
      // The positional forms, drilled on the letter repeated (initial,
      // medial, final in one string) and on pairs with a learned joiner.
      const forms = group.flatMap((l) =>
        (formsOf.get(l) ?? []).filter((f) => f !== 'isolated').map((f) => `${l}|${f}`))
      const joiner = [...before, ...group].find((l) => (formsOf.get(l) ?? []).includes('initial'))
      const drills: string[] = []
      for (const l of group) {
        const f = formsOf.get(l) ?? []
        if (f.includes('medial')) drills.push(`${l}${l}${l}`)
        else if (joiner && joiner !== l) drills.push(`${joiner}${l}`)
      }
      for (let i = 0; i + 1 < group.length; i++) drills.push(`${group[i]}${group[i + 1]}`)
      lessons.push({ id: `forms-${n}`, kind: 'forms', group, letters, forms, drills })
    }
    if (group.some((l) => (formsOf.get(l) ?? []).includes('upper'))) {
      lessons.push({
        id: `capitals-${n}`, kind: 'capitals', group, letters,
        forms: group.filter((l) => (formsOf.get(l) ?? []).includes('upper')).map((l) => `${l}|upper`),
        drills: [],
      })
    }
    if (cursive) {
      // Joins: each new letter between learned ones, a vowel for choice.
      const partners = letters.filter((l) => VOWELS.has(l))
      const pool = partners.length ? partners : letters
      const drills: string[] = []
      group.forEach((l, i) => {
        const p = pool[i % pool.length]
        if (p !== l) drills.push(`${l}${p}`, `${p}${l}${p}`)
        else if (pool.length > 1) drills.push(`${l}${pool[(i + 1) % pool.length]}`)
      })
      lessons.push({ id: `joins-${n}`, kind: 'joins', group, letters, forms: [], drills })
    }
    lessons.push({ id: `words-${n}`, kind: 'words', group, letters, forms: [], drills: [] })
  })
  lessons.push({ id: 'sentences', kind: 'sentences', group: [], letters: [...taught], forms: [], drills: [] })
  return lessons
}

/** Which lessons are finished: a lesson with authored forms finishes
 * itself when every one of them is known; everything else (drills,
 * words, sentences, and letter lessons nobody has authored yet) is
 * finished when marked. */
export function lessonDone(
  lesson: Lesson,
  authoredKnown: Map<string, boolean>,
  marked: Set<string>,
): boolean {
  if (marked.has(lesson.id)) return true
  const authored = lesson.forms.filter((k) => authoredKnown.has(k))
  return authored.length > 0 && authored.every((k) => authoredKnown.get(k))
}

export function nextLesson(lessons: Lesson[], done: (l: Lesson) => boolean): number {
  const i = lessons.findIndex((l) => !done(l))
  return i < 0 ? lessons.length : i
}

export { scriptOf }
