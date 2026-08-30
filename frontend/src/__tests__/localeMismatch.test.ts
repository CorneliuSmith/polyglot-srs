/**
 * A hint layer must never label foreign text as the learner's language.
 *
 * The report: an Arabic-reading learner studying Turkish saw
 * "This city is very big and millions of people live there." under the
 * heading الترجمة. The text is served on purpose (it is the only
 * semantic cue on a cloze), but calling it "the translation" tells the
 * learner their language failed rather than that it has not landed yet.
 */
import { describe, it, expect } from 'vitest'
import { hintLayersFor } from '../features/review/hintLayers'
import i18n from '../i18n'

const REPORTED = {
  translation: 'This city is very big and millions of people live there.',
  hint: 'büyük',
}

describe('a flagged field is labelled with the language it is in', () => {
  it('marks the layer foreign and changes its label', () => {
    const layers = hintLayersFor('tr', { ...REPORTED, locale_mismatch: ['translation'] })
    const translation = layers.find((l) => l.field === 'translation')!
    expect(translation.foreign).toBe(true)
    expect(translation.label).not.toBe(i18n.t('review.layerTranslation'))
    // The text itself is still served — withholding it leaves the cloze
    // with no cue at all.
    expect(translation.text).toBe(REPORTED.translation)
  })

  it('leaves unflagged layers exactly as they were', () => {
    const layers = hintLayersFor('tr', { ...REPORTED, locale_mismatch: ['translation'] })
    const hint = layers.find((l) => l.field === 'hint')!
    expect(hint.foreign).toBeUndefined()
    expect(hint.label).toBe(i18n.t('review.layerHint'))
  })

  it('is inert when the server reports nothing', () => {
    for (const card of [REPORTED, { ...REPORTED, locale_mismatch: [] }]) {
      const layers = hintLayersFor('tr', card)
      expect(layers.every((l) => l.foreign === undefined)).toBe(true)
      expect(layers.find((l) => l.field === 'translation')!.label).toBe(
        i18n.t('review.layerTranslation'),
      )
    }
  })

  it('survives an older server that never sends the field', () => {
    const layers = hintLayersFor('tr', REPORTED)
    expect(layers.length).toBeGreaterThan(0)
    expect(layers.find((l) => l.field === 'translation')!.text).toBe(REPORTED.translation)
  })
})

describe('the label exists in every shipped locale', () => {
  // A missing key renders the raw key id to the learner, which is worse
  // than the bug being fixed.
  const LOCALES = ['en', 'ar', 'es', 'fr', 'pt', 'ru']

  it.each(LOCALES)('%s has review.layerNotTranslated and it interpolates', (locale) => {
    const value = i18n.getFixedT(locale)('review.layerNotTranslated', { label: 'X' })
    expect(value).not.toBe('review.layerNotTranslated')
    expect(value).toContain('X')
  })

  it.each(LOCALES)('%s does not claim the fallback is English', (locale) => {
    // The label once said "(English — not yet translated)" in every locale.
    // True for course content, false for PERSONAL cards, whose fallback is
    // whatever language the card's author typed — the owner saw their own
    // Spanish captioned "на английском" and read it as data corruption.
    // The label may say the text isn't in your language; it must not guess
    // which language it IS in.
    const value = i18n.getFixedT(locale)('review.layerNotTranslated', { label: 'X' })
    expect(value.toLowerCase()).not.toMatch(
      /english|inglés|anglais|inglês|английск|الإنجليزية/,
    )
  })
})

describe('a translation in the wrong language is labelled, whatever the script', () => {
  it('flags a Latin-script fallback that script detection cannot see', () => {
    // The screenshot: a Spanish learner shown Greek and Romanian under
    // "TRADUCCIÓN". locale_mismatch is script-based and silent for Latin
    // locales, so the server's own locale comparison has to drive this.
    const layers = hintLayersFor('en', {
      translation: 'Ești unul dintre noi.',
      translation_pending: true,
      hint: 'one of us',
    })
    const translation = layers.find((l) => l.field === 'translation')
    expect(translation?.foreign).toBe(true)
    expect(translation?.label).not.toBe(i18n.t('review.layerTranslation'))
  })

  it('leaves a real match alone', () => {
    const layers = hintLayersFor('en', {
      translation: '¿Y qué vamos a hacer?',
      translation_pending: false,
      hint: 'to do',
    })
    const translation = layers.find((l) => l.field === 'translation')
    expect(translation?.foreign).toBeUndefined()
    expect(translation?.label).toBe(i18n.t('review.layerTranslation'))
  })

  it('still honours the script guard when it does fire', () => {
    const layers = hintLayersFor('en', {
      translation: 'Και τι θα κάνουμε;',
      locale_mismatch: ['translation'],
      hint: 'to do',
    })
    expect(layers.find((l) => l.field === 'translation')?.foreign).toBe(true)
  })
})
