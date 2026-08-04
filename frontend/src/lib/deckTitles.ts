import type { TFunction } from 'i18next'

/**
 * Deck titles as the seeder writes them are formulaic and always English —
 * "Catalan A1 Grammar Path", "A2 Grammar", "A1 Vocabulary", "Alphabet" —
 * carrying nothing the deck's own (list_type, level) fields don't already
 * say. The course name in front is redundant too: you're looking at that
 * course's deck list. So render the label from the structured fields and it
 * reads in the site language everywhere, with no per-language data to fill.
 *
 * A title that is NOT one of the seeded shapes (an admin's custom list) is
 * shown verbatim — deriving it would throw its meaning away.
 */
const SEEDED_GRAMMAR = /^(.+\s)?[ABC][0-2]\s+grammar(\s+path)?$/i
const SEEDED_VOCAB = /^(.+\s)?[ABC][0-2]\s+vocabulary$/i
const SEEDED_ALPHABET = /^alphabet$/i

export interface DeckLike {
  title?: string | null
  list_type?: string | null
  level?: string | null
}

export function deckTitle(deck: DeckLike, t: TFunction): string {
  const title = (deck.title ?? '').trim()
  if (SEEDED_ALPHABET.test(title)) return t('decks.titleAlphabet')
  // The level is the label's only variable; without one there is no seeded
  // shape to rebuild, so whatever the deck is called stands.
  if (deck.level) {
    if (SEEDED_GRAMMAR.test(title)) {
      return t('decks.titleGrammar', { level: deck.level })
    }
    if (SEEDED_VOCAB.test(title)) {
      return t('decks.titleVocab', { level: deck.level })
    }
  }
  return title
}
