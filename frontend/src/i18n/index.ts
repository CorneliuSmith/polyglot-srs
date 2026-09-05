/** Site-chrome internationalization (the UI's own language, NOT learning
 * content — that has its own locale system, `support_locale`).
 *
 * ONE rule for signed-in accounts: the account's `ui_language` is the
 * language, on every device, and the last change anywhere wins. It used to
 * be "an explicit choice on this device wins forever", which is how the
 * owner's phone ran in Russian while their computer ran in English — and
 * the SERVER, which follows the account, translated review cards into
 * Russian for the English screen. A device may only outrank the account
 * for the few seconds after the user taps the globe there, while that tap
 * is still being saved.
 *
 * localStorage is a first-paint cache and the signed-out preference, not
 * an override. Before the profile arrives (and on the login page) the
 * order is: cached value → the browser's preferred languages
 * (navigator.languages — the signal Wikipedia/Google use; IP geolocation
 * answers "what country", not "what language") → English.
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
import tr from './locales/tr.json'

/** Priority order per the rollout plan: Arabic, Spanish, Russian, French,
 * Portuguese — English first as the default. Turkish came later, on the
 * owner's ask (5 Sep 2026); it is a course language with a large diaspora
 * that reaches B1 through family and stalls, which is the wedge the launch
 * plan names. `native` is each language's own name for itself, so a lost
 * user can always find theirs (the reason the switcher is a globe with
 * names, not country flags). */
export const UI_LANGUAGES = [
  { code: 'en', native: 'English' },
  { code: 'ar', native: 'العربية' },
  { code: 'es', native: 'Español' },
  { code: 'ru', native: 'Русский' },
  { code: 'fr', native: 'Français' },
  { code: 'pt', native: 'Português' },
  { code: 'tr', native: 'Türkçe' },
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

/** When the user last changed the language ON THIS DEVICE. For the few
 * seconds it takes their tap to reach the profile, a profile read from
 * before the tap may still land here — and must not bounce them back. */
let lastExplicitChangeAt = 0
const EXPLICIT_GRACE_MS = 15_000

/** Test-only: module state survives between tests, and a globe tap in one
 * test must not hold the grace window open for the next. */
export function __resetUiLanguageSyncForTests() {
  lastExplicitChangeAt = 0
}

/** Switch the UI language now. `explicit` marks a user decision (the
 * globe) as opposed to the profile sync following the account. */
export function applyUiLanguage(
  code: string,
  { explicit = true }: { explicit?: boolean } = {},
) {
  if (!SUPPORTED.has(code)) return
  if (explicit) lastExplicitChangeAt = Date.now()
  try {
    localStorage.setItem(STORAGE_KEY, code)
  } catch {
    // Private-mode storage failures never block the switch itself.
  }
  void i18n.changeLanguage(code)
  applyDocumentAttrs(code)
}

/** Called when the signed-in profile arrives: the ACCOUNT wins.
 *
 * This used to defer to any stored device choice, which split accounts
 * across devices permanently — and worse, split the device from the
 * server: the backend derives the help language for review cards from
 * ui_language, so the server was translating for the account's language
 * while the screen showed the device's. One authority ends both.
 *
 * The cache is updated too, so the next first paint on this device is
 * already right. Unknown/absent values are ignored (older backend).
 */
export function syncUiLanguageFromProfile(uiLanguage: string | null | undefined) {
  if (!uiLanguage || !SUPPORTED.has(uiLanguage)) return
  // A globe tap made seconds ago on THIS device outranks a profile read
  // that may predate it; the tap's own save then makes the two agree.
  if (Date.now() - lastExplicitChangeAt < EXPLICIT_GRACE_MS) return
  if (uiLanguage !== i18n.language) {
    applyUiLanguage(uiLanguage, { explicit: false })
  } else {
    try {
      localStorage.setItem(STORAGE_KEY, uiLanguage)
    } catch {
      // cache only
    }
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
    tr: { translation: tr },
  },
  lng: detectUiLanguage(),
  fallbackLng: 'en',
  // React already escapes; double-escaping garbles apostrophes.
  interpolation: { escapeValue: false },
})
applyDocumentAttrs(i18n.language)

export default i18n
