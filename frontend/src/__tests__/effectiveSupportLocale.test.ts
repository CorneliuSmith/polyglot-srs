import { describe, it, expect } from 'vitest'
import { effectiveSupportLocale } from '../api/profile'

/**
 * The frontend twin of backend repositories/profile.py — the one rule for
 * which language the learner reads help in. Session pages key their card
 * queries and their restart-on-change watchers off this value, so it must
 * rank exactly like the server does: an explicit choice wins, otherwise
 * the interface language. Two rules would mean the pages could disagree
 * with the content they fetch — which is the mixed-language screen this
 * replaced.
 */
describe('effectiveSupportLocale', () => {
  it('an explicit choice wins over the interface', () => {
    expect(
      effectiveSupportLocale({ support_locale: 'fr', ui_language: 'en' }),
    ).toBe('fr')
  })

  it('automatic follows the interface', () => {
    expect(
      effectiveSupportLocale({ support_locale: null, ui_language: 'fr' }),
    ).toBe('fr')
  })

  it('explicit English survives a foreign interface', () => {
    // The choice 'en' used to be inexpressible — it doubled as the reset
    // value. Now it ranks like any other decision.
    expect(
      effectiveSupportLocale({ support_locale: 'en', ui_language: 'fr' }),
    ).toBe('en')
  })

  it('no profile yet means English, not undefined', () => {
    // Query keys embed this value before the profile loads; it must be a
    // stable string, never a hole in the key.
    expect(effectiveSupportLocale(undefined)).toBe('en')
    expect(effectiveSupportLocale(null)).toBe('en')
  })
})
