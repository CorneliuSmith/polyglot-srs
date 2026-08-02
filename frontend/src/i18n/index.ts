/** Site-chrome internationalization (the UI's own language, NOT learning
 * content — that has its own locale system, `support_locale`).
 *
 * Detection order, first match wins:
 *   1. the user's explicit choice on this device (localStorage)
 *   2. the account's saved `ui_language` (synced when the profile loads,
 *      so a choice follows the user across devices)
 *   3. the browser's preferred languages (navigator.languages — the signal
 *      Wikipedia/Google use; IP geolocation answers "what country", not
 *      "what language", so we deliberately don't use it)
 *   4. English.
 *
 * Arabic flips the whole document to RTL (`dir` on <html>), the way a
 * native Arabic site reads. i18next (rather than hand-rolled lookup)
 * because plural rules are the trap — Arabic has six forms, Russian three.
 */
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import ar from './locales/ar.json'
import en from './locales/en.json'
import es from './locales/es.json'
import fr from './locales/fr.json'
import pt from './locales/pt.json'
import ru from './locales/ru.json'

/** Priority order per the rollout plan: Arabic, Spanish, Russian, French,
 * Portuguese — English first as the default. `native` is each language's
 * own name for itself, so a lost user can always find theirs (the reason
 * the switcher is a globe with names, not country flags). */
export const UI_LANGUAGES = [
  { code: 'en', native: 'English' },
  { code: 'ar', native: 'العربية' },
  { code: 'es', native: 'Español' },
  { code: 'ru', native: 'Русский' },
  { code: 'fr', native: 'Français' },
  { code: 'pt', native: 'Português' },
] as const

export type UiLanguageCode = (typeof UI_LANGUAGES)[number]['code']

const SUPPORTED = new Set<string>(UI_LANGUAGES.map((l) => l.code))
const STORAGE_KEY = 'polyglot-ui-language'

function storedChoice(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

/** First supported language from: device choice → browser preferences → en. */
export function detectUiLanguage(): UiLanguageCode {
  const stored = storedChoice()
  if (stored && SUPPORTED.has(stored)) return stored as UiLanguageCode
  for (const pref of navigator.languages ?? []) {
    const base = pref.toLowerCase().split('-')[0]
    if (SUPPORTED.has(base)) return base as UiLanguageCode
  }
  return 'en'
}

function applyDocumentAttrs(code: string) {
  document.documentElement.lang = code
  document.documentElement.dir = code === 'ar' ? 'rtl' : 'ltr'
}

/** Switch the UI language now. persistLocal=false is for profile sync,
 * where the account value must NOT become a device-level override. */
export function applyUiLanguage(
  code: string,
  { persistLocal = true }: { persistLocal?: boolean } = {},
) {
  if (!SUPPORTED.has(code)) return
  if (persistLocal) {
    try {
      localStorage.setItem(STORAGE_KEY, code)
    } catch {
      // Private-mode storage failures never block the switch itself.
    }
  }
  void i18n.changeLanguage(code)
  applyDocumentAttrs(code)
}

/** Called when the signed-in profile arrives: an explicit choice on THIS
 * device wins; otherwise the account's saved language follows the user
 * here. Unknown/absent values are ignored (older backend, 'en' default). */
export function syncUiLanguageFromProfile(uiLanguage: string | null | undefined) {
  if (storedChoice()) return
  if (uiLanguage && SUPPORTED.has(uiLanguage) && uiLanguage !== i18n.language) {
    applyUiLanguage(uiLanguage, { persistLocal: false })
  }
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
    es: { translation: es },
    ru: { translation: ru },
    fr: { translation: fr },
    pt: { translation: pt },
  },
  lng: detectUiLanguage(),
  fallbackLng: 'en',
  // React already escapes; double-escaping garbles apostrophes.
  interpolation: { escapeValue: false },
})
applyDocumentAttrs(i18n.language)

export default i18n
