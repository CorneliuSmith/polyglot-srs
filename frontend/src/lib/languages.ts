import type { Language } from '../api/types'

/** Learner-facing language lists (onboarding, the active-language picker)
 * filter to admin-visible languages — but never drop the CALLER's currently
 * active language, even if an admin hides it later, so nobody gets stranded
 * with a picker that can't show what they're already studying. A language
 * missing `is_visible` (an older cached response, a test fixture) defaults
 * to visible — only an explicit `false` hides it. */
export function visibleLanguages(
  languages: Language[],
  activeLanguageId?: string | null,
): Language[] {
  return languages.filter(
    (l) => l.is_visible !== false || l.id === activeLanguageId,
  )
}

/** The name of language *code* in the reader's UI language, via the
 * browser's built-in CLDR names (Intl.DisplayNames) — "Turkish" becomes
 * "turco"/"турецкий"/"التركية" with no authored data. English keeps the
 * database name verbatim; unknown tags (e.g. "jam") and engines without
 * the data fall back to the database name too. */
export function languageDisplayName(
  code: string,
  fallback: string,
  uiLanguage: string,
): string {
  const base = (uiLanguage ?? 'en').split('-')[0]
  if (base === 'en') return fallback
  try {
    const name = new Intl.DisplayNames([base], { type: 'language' }).of(code)
    if (name && name.toLowerCase() !== code.toLowerCase()) {
      // Several locales return lowercase ("turco"); list context wants caps.
      return name.charAt(0).toLocaleUpperCase(base) + name.slice(1)
    }
  } catch {
    // Invalid tag or no CLDR data on this engine — the English name stands.
  }
  return fallback
}
