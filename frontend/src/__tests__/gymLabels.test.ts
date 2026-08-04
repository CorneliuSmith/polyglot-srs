import { describe, it, expect } from 'vitest'
import { GYM_LABEL_KEYS } from '../features/gym/gymLabels'
import en from '../i18n/locales/en.json'
import ar from '../i18n/locales/ar.json'
import es from '../i18n/locales/es.json'
import fr from '../i18n/locales/fr.json'
import pt from '../i18n/locales/pt.json'
import ru from '../i18n/locales/ru.json'

const LOCALES = { ar, es, fr, pt, ru } as const
type Forms = Record<string, string>

describe('Gym form labels', () => {
  it('every mapped label has a key that exists in the English catalog', () => {
    const forms = (en as { gymForms: Forms }).gymForms
    for (const [label, key] of Object.entries(GYM_LABEL_KEYS)) {
      const leaf = key.replace(/^gymForms\./, '')
      expect(forms[leaf], `${label} → ${key}`).toBeDefined()
      // English renders exactly what the manifest ships — no drift.
      expect(forms[leaf]).toBe(label)
    }
  })

  it('is translated in every UI language, with nothing left blank', () => {
    const enForms = (en as { gymForms: Forms }).gymForms
    for (const [code, cat] of Object.entries(LOCALES)) {
      const forms = (cat as unknown as { gymForms: Forms }).gymForms
      expect(forms, `${code} gymForms`).toBeDefined()
      expect(Object.keys(forms).sort()).toEqual(Object.keys(enForms).sort())
      for (const [k, v] of Object.entries(forms)) {
        expect(v?.trim(), `${code}.${k}`).toBeTruthy()
      }
    }
  })

  it('translates the grammar terms the owner saw in English on the Gym', () => {
    // The exact labels from the Arabic-UI screenshot.
    for (const leaf of ['definiteArticle', 'indefiniteArticle', 'subjunctive',
                        'imperative', 'future', 'conditional', 'imperfect']) {
      for (const [code, cat] of Object.entries(LOCALES)) {
        const forms = (cat as unknown as { gymForms: Forms }).gymForms
        const enForms = (en as { gymForms: Forms }).gymForms
        expect(forms[leaf], `${code}.${leaf}`).not.toBe(enForms[leaf])
      }
    }
  })

  it('keeps course-language material verbatim in every locale', () => {
    // A label that is nothing but a course-language affix must survive
    // translation untouched — it is the form being drilled, not English.
    for (const [code, cat] of Object.entries(LOCALES)) {
      const forms = (cat as unknown as { gymForms: Forms }).gymForms
      expect(forms.i, `${code}.i`).toBe('-i')
      expect(forms.kan, `${code}.kan`).toBe('-kan')
      // Composite labels keep the affix, translate only the English around it.
      expect(forms.presentAr, `${code}.presentAr`).toContain('-ar')
    }
  })
})
