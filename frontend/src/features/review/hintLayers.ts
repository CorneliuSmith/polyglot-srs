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
 * The Gym adds one more, ALWAYS first when present: the **base form** — the
 * dictionary/lemma of the word being drilled (infinitive, nominative
 * singular, …). Inflection practice is "given this word, produce this form",
 * so the base form is the cue you work FROM, not a last resort.
 *
 * Layers a card doesn't carry (no gloss authored yet, no transliteration, no
 * base form outside the Gym) are skipped, so the dots always match what's
 * actually available.
 */

export type HintLayerField = 'base' | 'transliteration' | 'phonetics' | 'gloss' | 'translation' | 'hint'

// The disclosure order is the same everywhere: reading, then word-by-word,
// then the sentence translation, then the word's own meaning. Each step is a
// bigger concession than the last.
//
// There is exactly one axis of variation — whether the course has a script the
// learner cannot sound out. A Latin-script course has no reading to show, so
// it starts at the gloss.
//
// It used to have three orders, and the third silently dropped the gloss:
// DEFAULT_ORDER was ['translation', 'hint']. That removed the word-by-word
// line from FOURTEEN courses — every Romance and Germanic course, plus tr, la,
// id, tl, jam and en — so 3,609 example sentences and 3,459 drills in those
// courses had no route to a learner at all. It also made the layer look
// deliberately excluded rather than accidentally missing, which is how it
// survived: authoring for those courses was ruled out on the strength of a
// bug.
// `phonetics` sits directly beneath the reading: the romanisation says which
// letters, phonetics says how to say them. Only Thai carries it today — RTGS
// drops tone entirely and Thai is tonal — and courses without one skip the
// layer, so this order is safe for all eight.
const WITH_READING: HintLayerField[] = ['transliteration', 'phonetics', 'gloss', 'translation', 'hint']
const NO_READING: HintLayerField[] = ['gloss', 'translation', 'hint']

// Courses whose script a learner cannot sound out cold. Everything else falls
// through to NO_READING and still shows the gloss.
const SCRIPT_COURSES = new Set(['ru', 'ar', 'el', 'hi', 'ko', 'th', 'he', 'fa'])

export interface HintLayerSource {
  /** Dictionary/lemma form the drill exercises — Gym cards only. */
  base?: string | null
  transliteration?: string | null
  /** Pronunciation beneath the reading — tone marks Thai's RTGS cannot carry. */
  phonetics?: string | null
  gloss?: string | null
  translation?: string | null
  hint?: string | null
  /** Fields the server could prove are NOT in the learner's language —
   * usually an English fallback served because their rendering doesn't
   * exist yet. Absent means nothing to report. */
  locale_mismatch?: string[] | null
  // The server compared the translation it served against the locale the
  // learner asked for. Authoritative where locale_mismatch cannot be:
  // that guard is script-based, so it is silent for every Latin-script
  // locale — a Spanish learner was shown Greek and Romanian under
  // "TRADUCCIÓN" with nothing flagged, because both are simply "not the
  // expected script" only when the expected script is known.
  translation_pending?: boolean | null
  /** What the learner has to produce. Used only to keep the authored hint
   * from handing it to them — see the guard in hintLayersFor. */
  correct_answer?: string | null
}

export interface HintLayer {
  field: HintLayerField
  label: string
  text: string
  /** True when this text is not in the learner's language. The label says
   * so, rather than the card claiming an English sentence is "الترجمة". */
  foreign?: boolean
}

import i18n from '../../i18n'

// i18n keys, resolved at call time so the labels follow the site language.
const LABELS: Record<HintLayerField, string> = {
  base: 'review.layerBase',
  transliteration: 'review.layerReading',
  phonetics: 'review.layerPhonetics',
  gloss: 'review.layerGloss',
  translation: 'review.layerTranslation',
  hint: 'review.layerHint',
}

/**
 * The always-shown Gym prompt must never GIVE the answer. Two authored-hint
 * faults leak it:
 *   1. a spelled-out recipe — "to watch — add -es" (→ watches),
 *      "to study — y changes to -ies" (→ studies);
 *   2. the base form itself equalling the answer — "to speak" (→ speak).
 * Strip a trailing recipe clause, then blank the prompt entirely if it still
 * contains the answer as a whole word. Legitimate cues ("preparar, tú",
 * "go — past") are left untouched. The learner recalls a blanked one from the
 * sentence plus the optional meaning hint.
 */
const RECIPE_TAIL = /\b(add|drop|changes?|becomes?|remove)\b|→|->|(?:^|\s)[-–][^\s-]/iu

export function safePrompt(text: string, answer: string | null | undefined): string {
  let base = (text ?? '').trim()
  if (!base) return ''
  const split = base.match(/^(.*?)\s+[—–-]\s+(.+)$/u)
  if (split && RECIPE_TAIL.test(split[2])) base = split[1].trim()
  const ans = (answer ?? '').trim().toLowerCase()
  if (ans) {
    // Letters, COMBINING MARKS, and the apostrophes/hyphens that sit inside a
    // word. \p{L}+ alone silently weakened this for every abugida and abjad:
    // Devanagari रही is र + ह + the combining vowel sign ी, which is category
    // Mn, so it tokenised as रह and never matched its own answer. Same for
    // Tagalog 'y, where the word begins with an apostrophe. Three of the 8,049
    // authored hints reached a learner with the answer in them because of it.
    // BOTH granularities. Whole words so a hyphenated answer like Indonesian
    // `buku-buku` matches, and the pieces so German `Man` still matches inside
    // `man-passive` — taking only the joined form regressed exactly that.
    const lower = base.toLowerCase()
    const joined: string[] = lower.match(/[\p{L}\p{M}]+(?:['’\u002d][\p{L}\p{M}]+)*/gu) ?? []
    const parts: string[] = lower.match(/[\p{L}\p{M}]+/gu) ?? []
    if (joined.includes(ans) || parts.includes(ans)) return ''
    // ...and the answer may itself lead with a mark or apostrophe, which no
    // token boundary will ever start on.
    if (/^[^\p{L}\p{M}]/u.test(ans) && base.toLowerCase().includes(ans)) return ''
  }
  return base
}

/** The ordered hint layers this card can actually reveal. Base form (when the
 * card carries one — i.e. in the Gym) always leads.
 *
 * `showGlosses` is the account setting (`user_profiles.show_glosses`), OFF
 * by default: the Leipzig notation is unfamiliar enough that meeting it
 * unasked is what learners reported as confusing. Off means the gloss is
 * not OFFERED — it drops out of the order entirely, so the hint dots
 * shorten by one rather than leaving a rung that reveals nothing.
 *
 * Filtering here rather than at each call site is what makes the setting
 * hold on every surface that reveals a layer, including whichever one is
 * written next — and the parameter defaults to OFF for the same reason, so
 * a caller that forgets to pass it withholds the layer rather than showing
 * it to someone who never asked. */
export function hintLayersFor(
  languageCode: string,
  card: HintLayerSource,
  { showGlosses = false }: { showGlosses?: boolean } = {},
): HintLayer[] {
  const order: HintLayerField[] = [
    'base',
    ...(SCRIPT_COURSES.has(languageCode) ? WITH_READING : NO_READING),
  ].filter((f): f is HintLayerField => showGlosses || f !== 'gloss')
  // A field the server flagged is shown, but never under a label that
  // claims it is the learner's language: an Arabic speaker was told
  // "الترجمة" over an English sentence. Withholding it instead would
  // leave a cloze with no semantic cue at all, so it is labelled as not
  // theirs and the demand queue fills it for next time. The label
  // deliberately does NOT name which language it IS in: course-content
  // fallbacks are English, but a PERSONAL card falls back to whatever
  // language its author typed — the owner saw Spanish captioned "на
  // английском", which reads as data corruption when it's only a caption.
  const mismatched = new Set(card.locale_mismatch ?? [])
  if (card.translation_pending) mismatched.add('translation')
  return order
    .map((field) => ({ field, text: layerText(field, card) }))
    .filter(({ text }) => text.length > 0)
    .map(({ field, text }) => {
      const foreign = mismatched.has(field)
      return {
        field,
        label: foreign
          ? i18n.t('review.layerNotTranslated', { label: i18n.t(LABELS[field]) })
          : i18n.t(LABELS[field]),
        text,
        ...(foreign ? { foreign: true } : {}),
      }
    })
}

/**
 * One layer's text, with the answer-leak guard applied to the authored hint.
 *
 * The guard used to live at the Gym's call site alone, which meant the same
 * hint the Gym carefully blanked was handed over verbatim in a graded review
 * session and as the listening-mode cue. 256 of the 8,049 authored drill
 * hints contain the answer as a whole word — "haben, wir" for the answer
 * *haben*, "since (ja que)" for *que* — so on those cards the hint WAS the
 * answer, and learners noticed and said so.
 *
 * Running it here instead means every surface that renders a layer is
 * covered by construction, including whichever one gets written next. A
 * blanked hint drops out below rather than showing an empty row, and the
 * dots stay in step with what is actually revealable.
 *
 * Only the authored hint is guarded. A translation that happens to contain
 * the answer is a different thing — it is the meaning cue the exercise is
 * built on, and blanking it would leave a cloze with nothing to go on.
 */
function layerText(field: HintLayerField, card: HintLayerSource): string {
  const raw = (card[field] ?? '').toString().trim()
  if (field !== 'hint' || !raw) return raw
  return safePrompt(raw, card.correct_answer)
}
