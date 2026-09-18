import { describe, it, expect, beforeEach } from 'vitest'
import { applyLanguageTheme, languageThemeVars, LANG_THEME_CACHE_KEY } from '../lib/languageColors'

describe('language palette cache for the first frame', () => {
  beforeEach(() => {
    localStorage.removeItem(LANG_THEME_CACHE_KEY)
    document.documentElement.removeAttribute('style')
  })

  it('applying a language writes the variables and caches them by code', () => {
    applyLanguageTheme('ar')
    const vars = languageThemeVars('ar')
    expect(document.documentElement.style.getPropertyValue('--lang-primary')).toBe(vars['--lang-primary'])
    const cached = JSON.parse(localStorage.getItem(LANG_THEME_CACHE_KEY)!)
    expect(cached.code).toBe('ar')
    expect(cached.vars['--lang-primary']).toBe(vars['--lang-primary'])
    expect(Object.keys(cached.vars).every((k) => k.startsWith('--lang-'))).toBe(true)
  })

  it('signing out (no language) clears the cache so the next first frame is the default', () => {
    applyLanguageTheme('ru')
    applyLanguageTheme(undefined)
    expect(localStorage.getItem(LANG_THEME_CACHE_KEY)).toBeNull()
  })
})
