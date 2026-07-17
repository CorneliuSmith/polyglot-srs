/**
 * Language-aware hint disclosure.
 *
 * Each Hint press reveals the next layer a learner of THAT language needs:
 *
 *  - Non-Latin scripts (ru, ar, el): romanization first — you can't recall a
 *    word you can't sound out — then the gloss, then the translation, and the
 *    morphology recipe last.
 *  - Languages whose syntax doesn't map onto English word order (mi and the
 *    Bantu/Volta-Niger languages): the word-by-word gloss first — it shows
 *    how the sentence is BUILT — then the translation, then the recipe.
 *  - Everything else: translation (the lexical cue), then the recipe.
 *
 * Layers a card doesn't carry (no gloss authored yet, no transliteration)
 * are skipped, so the dots always match what's actually available.
 */

export type HintLayerField = 'transliteration' | 'gloss' | 'translation' | 'hint'

const SCRIPT_FIRST: HintLayerField[] = ['transliteration', 'gloss', 'translation', 'hint']
const GLOSS_FIRST: HintLayerField[] = ['gloss', 'translation', 'hint']
const DEFAULT_ORDER: HintLayerField[] = ['translation', 'hint']

const LAYER_ORDER: Record<string, HintLayerField[]> = {
  ru: SCRIPT_FIRST,
  ar: SCRIPT_FIRST,
  el: SCRIPT_FIRST,
  hi: SCRIPT_FIRST,
  mi: GLOSS_FIRST,
  sw: GLOSS_FIRST,
  yo: GLOSS_FIRST,
  xh: GLOSS_FIRST,
  ha: GLOSS_FIRST,
}

export interface HintLayerSource {
  transliteration?: string | null
  gloss?: string | null
  translation?: string | null
  hint?: string | null
}

export interface HintLayer {
  field: HintLayerField
  label: string
  text: string
}

const LABELS: Record<HintLayerField, string> = {
  transliteration: 'Reading',
  gloss: 'Word by word',
  translation: 'Translation',
  hint: 'Hint',
}

/** The ordered hint layers this card can actually reveal. */
export function hintLayersFor(languageCode: string, card: HintLayerSource): HintLayer[] {
  const order = LAYER_ORDER[languageCode] ?? DEFAULT_ORDER
  return order
    .filter((field) => (card[field] ?? '').toString().trim().length > 0)
    .map((field) => ({ field, label: LABELS[field], text: card[field] as string }))
}
