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
