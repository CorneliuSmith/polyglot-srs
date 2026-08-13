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
})
