import { describe, it, expect } from 'vitest'
import { visibleLanguages } from '../lib/languages'
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
