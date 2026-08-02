import { describe, it, expect } from 'vitest'
import { languageDisplayName, visibleLanguages } from '../lib/languages'
import type { Language } from '../api/types'

const es: Language = { id: 'es', code: 'es', name: 'Spanish', rtl: false, is_visible: true }
const hidden: Language = { id: 'he', code: 'he', name: 'Hebrew', rtl: true, is_visible: false }

describe('visibleLanguages', () => {
  it('keeps visible languages and drops hidden ones', () => {
    expect(visibleLanguages([es, hidden]).map((l) => l.id)).toEqual(['es'])
  })

  it('keeps a hidden language if it is the caller’s active one', () => {
    expect(visibleLanguages([es, hidden], 'he').map((l) => l.id)).toEqual(['es', 'he'])
  })

  it('treats a missing is_visible field as visible (older fixture/response)', () => {
    const noField = { id: 'fr', code: 'fr', name: 'French', rtl: false } as Language
    expect(visibleLanguages([noField]).map((l) => l.id)).toEqual(['fr'])
  })
})

describe('languageDisplayName', () => {
  it('localizes names via the browser CLDR data, capitalized', () => {
    expect(languageDisplayName('tr', 'Turkish', 'es')).toBe('Turco')
    expect(languageDisplayName('tr', 'Turkish', 'ru')).toBe('Турецкий')
    expect(languageDisplayName('es', 'Spanish', 'ar')).toBe('الإسبانية')
  })

  it('keeps the database name for English and for unknown tags', () => {
    expect(languageDisplayName('tr', 'Turkish', 'en')).toBe('Turkish')
    // "jam" (Jamaican Patois) has no CLDR entry — never show a bare code.
    expect(languageDisplayName('jam', 'Jamaican Patois', 'es')).toBe(
      'Jamaican Patois',
    )
  })
})
