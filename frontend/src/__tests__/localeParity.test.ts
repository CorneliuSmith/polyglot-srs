import { describe, it, expect } from 'vitest'
import { UI_LANGUAGES } from '../i18n'
import en from '../i18n/locales/en.json'
import ar from '../i18n/locales/ar.json'
import es from '../i18n/locales/es.json'
import fr from '../i18n/locales/fr.json'
import pt from '../i18n/locales/pt.json'
import ru from '../i18n/locales/ru.json'
import tr from '../i18n/locales/tr.json'

/**
 * Every UI language carries the WHOLE catalog.
 *
 * i18next falls back to English for a missing key, silently — so a
 * half-translated locale does not break, it just leaks English into a
 * page that is otherwise Turkish, and nobody finds out until a learner
 * reports it. This test is the thing that finds out.
 *
 * It has already earned itself: every non-English locale was missing
 * `path.drillCount` and `path.practiseForms`, added to the grammar path
 * long after those five catalogs were written.
 */
const CATALOGS: Record<string, unknown> = { ar, es, fr, pt, ru, tr }

type Leaf = Record<string, string>

function flatten(value: unknown, prefix = '', out: Leaf = {}): Leaf {
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object') flatten(v, key, out)
    else out[key] = String(v)
  }
  return out
}

/** i18next plural suffixes. Arabic needs six forms and Russian three, so a
 * locale carrying `streak_few` where English has only `streak_one` /
 * `streak_other` is correct, not drift. */
const PLURAL_SUFFIX = /_(zero|one|two|few|many|other)$/

const ENGLISH = flatten(en)

describe('locale parity', () => {
  it('every language in the switcher has a catalog wired up', () => {
    // The switcher offering a language i18next was never given is a blank
    // app in that language.
    for (const { code } of UI_LANGUAGES) {
      if (code === 'en') continue
      expect(CATALOGS[code], `${code} has no catalog`).toBeDefined()
    }
    expect(Object.keys(CATALOGS).length).toBe(UI_LANGUAGES.length - 1)
  })

  it.each(Object.keys(CATALOGS))('%s translates every English key', (code) => {
    const missing = Object.keys(ENGLISH).filter((k) => !(k in flatten(CATALOGS[code])))
    expect(missing, `${code} is missing ${missing.length} keys`).toEqual([])
  })

  it.each(Object.keys(CATALOGS))('%s leaves nothing blank', (code) => {
    const blank = Object.entries(flatten(CATALOGS[code]))
      .filter(([, v]) => !v.trim())
      .map(([k]) => k)
    expect(blank).toEqual([])
  })

  it.each(Object.keys(CATALOGS))('%s carries no key English does not have', (code) => {
    // Except plural forms, which are the whole reason i18next is here.
    const stray = Object.keys(flatten(CATALOGS[code])).filter((k) => {
      if (k in ENGLISH) return false
      const base = k.replace(PLURAL_SUFFIX, '')
      return !Object.keys(ENGLISH).some((e) => e.replace(PLURAL_SUFFIX, '') === base)
    })
    expect(stray, `${code} has keys nothing reads`).toEqual([])
  })

  it.each(Object.keys(CATALOGS))('%s invents no {{placeholder}}', (code) => {
    // A placeholder English does not have is always a bug: nothing supplies
    // it, so it renders literally as "{{count}}" in the middle of a
    // sentence.
    const names = (s: string) => new Set([...s.matchAll(/{{(\w+)}}/g)].map((m) => m[1]))
    const cat = flatten(CATALOGS[code])
    const bad = Object.keys(ENGLISH).filter(
      (k) => k in cat && [...names(cat[k])].some((n) => !names(ENGLISH[k]).has(n)),
    )
    expect(bad).toEqual([])
  })

  it.each(Object.keys(CATALOGS))('%s keeps the placeholders a singular sentence needs', (code) => {
    // Exact match, but only OUTSIDE plural forms. Inside them a language
    // may correctly spell the numeral as a word — Arabic's `_one` reads
    // "يوم واحد" (one day), with no {{count}} to interpolate — and English's
    // own `_one` strings are not the authority on that.
    const names = (s: string) =>
      [...new Set([...s.matchAll(/{{(\w+)}}/g)].map((m) => m[1]))].sort().join(',')
    const cat = flatten(CATALOGS[code])
    const bad = Object.keys(ENGLISH).filter(
      (k) => !PLURAL_SUFFIX.test(k) && k in cat && names(ENGLISH[k]) !== names(cat[k]),
    )
    expect(bad).toEqual([])
  })

  it.each(Object.keys(CATALOGS))('%s keeps every <tag> the sentence is built from', (code) => {
    // <b>, <share>, <w>, <d> … are Trans components. A missing tag drops
    // the element the sentence wraps around.
    const tags = (s: string) =>
      [...s.matchAll(/<(\/?\w+)>/g)].map((m) => m[1]).sort().join(',')
    const cat = flatten(CATALOGS[code])
    const bad = Object.keys(ENGLISH)
      .filter((k) => k in cat && tags(ENGLISH[k]) !== tags(cat[k]))
    expect(bad).toEqual([])
  })
})
