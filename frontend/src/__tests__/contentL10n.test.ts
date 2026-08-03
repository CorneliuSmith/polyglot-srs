import { describe, it, expect } from 'vitest'
import {
  LANGUAGE_FACTS,
  LANGUAGE_SYNTAX,
  factsFor,
  syntaxFor,
} from '../features/about/languageFacts'
import { FACTS_L10N, SYNTAX_L10N } from '../features/about/factsL10n'
import { LETTERS, lettersFor } from '../features/letters/lettersData'
import { LETTERS_L10N } from '../features/letters/lettersL10n'

// The five authored UI languages. English is the base, not an overlay.
const LOCALES = ['es', 'pt', 'fr', 'ru', 'ar'] as const

describe('About-page facts localization', () => {
  it('every course is authored in every UI language — no silent fallback', () => {
    for (const locale of LOCALES) {
      for (const code of Object.keys(LANGUAGE_FACTS)) {
        const overlay = FACTS_L10N[locale]?.[code]
        expect(overlay, `${locale} facts for ${code}`).toBeDefined()
        // Complete, not stubbed: same fields the base guarantees.
        for (const field of [
          'tagline', 'family', 'speakers', 'whereSpoken', 'writingSystem',
          'wordOrder', 'history',
        ] as const) {
          expect(overlay![field]?.trim(), `${locale}.${code}.${field}`).toBeTruthy()
        }
        expect(overlay!.unique.length, `${locale}.${code}.unique`)
          .toBeGreaterThanOrEqual(3)
      }
    }
  })

  it('factsFor resolves the overlay, and reloading in another UI language changes the text', () => {
    for (const locale of LOCALES) {
      const localized = factsFor('es', locale)!
      expect(localized.tagline).not.toBe(LANGUAGE_FACTS.es.tagline)
    }
    // English (and unknown UI tags) keep the base.
    expect(factsFor('es', 'en')).toBe(LANGUAGE_FACTS.es)
  })
})

describe('About-page syntax examples localization', () => {
  it('every glossed example set is authored per locale, sentences untouched', () => {
    for (const locale of LOCALES) {
      for (const [code, base] of Object.entries(LANGUAGE_SYNTAX)) {
        const overlay = SYNTAX_L10N[locale]?.[code]
        expect(overlay, `${locale} syntax for ${code}`).toBeDefined()
        expect(overlay!.length, `${locale}.${code} example count`)
          .toBe(base.length)
        overlay!.forEach((ex, i) => {
          // The course-language material is byte-identical to the base…
          expect(ex.sentence).toBe(base[i].sentence)
          expect(ex.words.map((w) => w.w)).toEqual(base[i].words.map((w) => w.w))
          expect(Boolean(ex.rtl)).toBe(Boolean(base[i].rtl))
          // …and the reader-language material is present.
          expect(ex.translation?.trim(), `${locale}.${code}[${i}]`).toBeTruthy()
          expect(ex.words.every((w) => w.g.trim().length > 0)).toBe(true)
        })
      }
    }
  })

  it('syntaxFor switches with the UI language', () => {
    const base = syntaxFor('es', 'en')
    for (const locale of LOCALES) {
      const localized = syntaxFor('es', locale)
      expect(localized.length).toBeGreaterThan(0)
      expect(localized[0].translation).not.toBe(base[0].translation)
    }
  })
})

describe('Letters & Sounds localization', () => {
  it('every covered course is authored in every UI language, structure intact', () => {
    for (const locale of LOCALES) {
      for (const [code, base] of Object.entries(LETTERS)) {
        const overlay = LETTERS_L10N[locale]?.[code]
        expect(overlay, `${locale} letters for ${code}`).toBeDefined()
        expect(overlay!.sections.length, `${locale}.${code} sections`)
          .toBe(base.sections.length)
        overlay!.sections.forEach((section, si) => {
          const bs = base.sections[si]
          expect(section.rows.length, `${locale}.${code}[${si}] rows`)
            .toBe(bs.rows.length)
          expect(Boolean(section.positions)).toBe(Boolean(bs.positions))
          expect(Boolean(section.italics)).toBe(Boolean(bs.italics))
          expect(section.title?.trim()).toBeTruthy()
          section.rows.forEach((row, ri) => {
            // Playable example words are course-language data — untouched.
            expect(row.example, `${locale}.${code}[${si}][${ri}].example`)
              .toBe(bs.rows[ri].example)
            expect(row.roman ?? null).toBe(bs.rows[ri].roman ?? null)
            expect(row.sound?.trim(), `${locale}.${code}[${si}][${ri}].sound`)
              .toBeTruthy()
          })
        })
      }
    }
  })

  it('sound descriptions are re-anchored, not left in English', () => {
    // Sampling the page from the owner's screenshot: the Spanish course's
    // sound descriptions must actually change per UI language.
    for (const locale of LOCALES) {
      const base = LETTERS.es.sections[0].rows[0].sound
      const localized = LETTERS_L10N[locale].es.sections[0].rows[0].sound
      expect(localized, `${locale} es vowel sound`).not.toBe(base)
    }
  })

  it('lettersFor switches with the UI language and keeps English as base', () => {
    for (const locale of LOCALES) {
      expect(lettersFor('es', locale)).toBe(LETTERS_L10N[locale].es)
    }
    expect(lettersFor('es', 'en')).toBe(LETTERS.es)
    expect(lettersFor('es', 'de')).toBe(LETTERS.es) // no de overlay → base
  })
})
