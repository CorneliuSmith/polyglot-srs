// Map our ISO 639-1 language codes to BCP-47 locales so the browser picks the
// right voice for speech synthesis.
const BCP47: Record<string, string> = {
  ru: 'ru-RU',
  ar: 'ar-SA',
  en: 'en-US',
  sw: 'sw-KE',
  tr: 'tr-TR',
  yo: 'yo-NG',
  ha: 'ha-NG',
  xh: 'xh-ZA',
  es: 'es-ES',
  it: 'it-IT',
  fr: 'fr-FR',
  de: 'de-DE',
  ca: 'ca-ES',
  mi: 'mi-NZ',
}

export function toBcp47(code: string): string {
  return BCP47[code] ?? code
}

export function speechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}
