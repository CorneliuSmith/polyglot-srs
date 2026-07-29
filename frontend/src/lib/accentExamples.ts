/**
 * Per-language example for the "Accents optional" setting.
 *
 * The setting used to explain itself with a Spanish pair — “quien” passes for
 * “quién” — no matter what you were studying, and the toggle appeared even
 * for languages whose orthography has no marks at all (Indonesian, Tagalog,
 * Swahili…), where switching it changes nothing a learner will ever see.
 *
 * So: an example IN the language, or no toggle. A language is in this table
 * only if its normal written form actually carries marks that answer-checking
 * folds away.
 *
 * Deliberately NOT here:
 *   en, sw, xh, id, tl, jam — no diacritics in standard orthography.
 *   hi, th, ko             — matras / tone marks / jamo are not optional
 *                            decoration; dropping one spells a different word.
 *   ha                     — ɓ ɗ ƙ are distinct letters, not accented ones.
 */
export interface AccentExample {
  /** Written without its marks — what a learner types on a plain keyboard. */
  loose: string
  /** The fully marked spelling. */
  strict: string
  /** What the marked word means, so the pair reads as language not trivia. */
  gloss: string
}

export const ACCENT_EXAMPLES: Record<string, AccentExample> = {
  es: { loose: 'quien', strict: 'quién', gloss: 'who' },
  it: { loose: 'perche', strict: 'perché', gloss: 'because' },
  fr: { loose: 'eleve', strict: 'élève', gloss: 'pupil' },
  pt: { loose: 'esta', strict: 'está', gloss: 'is' },
  ca: { loose: 'mes', strict: 'més', gloss: 'more' },
  ro: { loose: 'masa', strict: 'masă', gloss: 'table' },
  de: { loose: 'Tur', strict: 'Tür', gloss: 'door' },
  nl: { loose: 'een', strict: 'één', gloss: 'one' },
  el: { loose: 'καλα', strict: 'καλά', gloss: 'well' },
  mi: { loose: 'maori', strict: 'māori', gloss: 'ordinary' },
  la: { loose: 'puella', strict: 'puellā', gloss: 'by the girl' },
  ru: { loose: 'елка', strict: 'ёлка', gloss: 'fir tree' },
  tr: { loose: 'gorusmek', strict: 'görüşmek', gloss: 'to meet' },
  yo: { loose: 'owo', strict: 'owó', gloss: 'money' },
  ar: { loose: 'كتب', strict: 'كَتَبَ', gloss: 'he wrote' },
  he: { loose: 'שלום', strict: 'שָׁלוֹם', gloss: 'peace' },
  fa: { loose: 'کتاب', strict: 'کِتاب', gloss: 'book' },
}

/** The example for a language, or null when it has no marks to make optional
 *  — in which case the toggle should not be rendered at all. */
export function accentExampleFor(
  code: string | undefined | null,
): AccentExample | null {
  if (!code) return null
  return ACCENT_EXAMPLES[code] ?? null
}
