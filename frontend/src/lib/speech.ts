// Map our ISO 639-1 language codes to BCP-47 locales so the browser picks the
// right voice for speech synthesis. pt is pt-BR per the path's Brazilian
// register default.
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
  ro: 'ro-RO',
  el: 'el-GR',
  pt: 'pt-BR',
}

export function toBcp47(code: string): string {
  return BCP47[code] ?? code
}

export function speechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

// getVoices() is EMPTY until the browser fires voiceschanged (Chrome loads
// them async) — a click in the first seconds used to fail silently. Cache
// the list and keep it fresh.
let voices: SpeechSynthesisVoice[] = []

function refreshVoices() {
  // optional-chained: test doubles and older engines lack getVoices
  if (speechSupported()) voices = window.speechSynthesis.getVoices?.() ?? []
}

if (speechSupported()) {
  refreshVoices()
  window.speechSynthesis.addEventListener?.('voiceschanged', refreshVoices)
}

/** Best installed voice for the language: exact locale match first, then any
 * voice in the language (e.g. pt-PT when pt-BR isn't installed). */
export function voiceFor(languageCode: string): SpeechSynthesisVoice | null {
  if (voices.length === 0) refreshVoices()
  const target = toBcp47(languageCode).toLowerCase()
  const prefix = target.split('-')[0]
  return (
    voices.find((v) => v.lang.toLowerCase() === target) ??
    voices.find((v) => v.lang.toLowerCase().replace('_', '-').startsWith(prefix)) ??
    null
  )
}
