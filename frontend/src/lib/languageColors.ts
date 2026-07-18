/** Per-language identity palettes drawn from each language's flag/country,
 * applied app-wide while that language is active (LanguageThemeApplier sets
 * the `--lang-*` CSS variables; Tailwind tokens `bg-lang`, `text-lang`,
 * `bg-lang-soft`, `bg-lang-dark`, `text-lang-on`, `bg-lang-accent` read
 * them). Several flags genuinely share color families (four blue-flagged
 * languages, three green), so the flag emoji — not the color — is the
 * primary identity mark; shades are spread within each family.
 *
 * Notes on the less obvious picks: Catalan uses the Andorran flag (the one
 * state where Catalan is the sole official language) over a senyera that
 * has no emoji; Portuguese uses Brazil per the path's Brazilian-register
 * default; Hausa uses Niger to disambiguate from Yoruba's Nigeria; Māori
 * uses the tino rangatiratanga palette (red/black/white, owner-specified,
 * with fern green as accent).
 */
export interface LanguageTheme {
  /** Flag-derived identity color: solid buttons, progress, active states. */
  primary: string
  /** Darker companion: hover states, the Learn tile, strong text. */
  dark: string
  /** Second flag color: highlights, streaks, decorative touches. */
  accent: string
  /** Soft tint for chips/backgrounds. */
  soft: string
  /** Text color ON primary (white unless primary is light). */
  on: string
  /** Flag emoji shown next to the language name. */
  emoji: string
  /** True when primary is light enough to need dark text on it. */
  darkText?: boolean
}

const THEMES: Record<string, LanguageTheme> = {
  es: { primary: '#AD1519', dark: '#7A0E11', accent: '#F1BF00', soft: '#FDECEC', on: '#FFFFFF', emoji: '🇪🇸' },
  fr: { primary: '#0055A4', dark: '#003E78', accent: '#EF4135', soft: '#E8F1FA', on: '#FFFFFF', emoji: '🇫🇷' },
  de: { primary: '#D89000', dark: '#8A5C00', accent: '#DD0000', soft: '#FCF3DF', on: '#FFFFFF', emoji: '🇩🇪' },
  it: { primary: '#008C45', dark: '#00602F', accent: '#CD212A', soft: '#E6F5EC', on: '#FFFFFF', emoji: '🇮🇹' },
  pt: { primary: '#009739', dark: '#046A38', accent: '#FEDD00', soft: '#E4F3EA', on: '#FFFFFF', emoji: '🇧🇷' },
  ca: { primary: '#FCDD09', dark: '#B89F00', accent: '#DA121A', soft: '#FEFAE0', on: '#1F2937', emoji: '🇦🇩', darkText: true },
  ro: { primary: '#002B7F', dark: '#001F5C', accent: '#FCD116', soft: '#E7ECF6', on: '#FFFFFF', emoji: '🇷🇴' },
  el: { primary: '#0D5EAF', dark: '#0A4682', accent: '#7BAFD4', soft: '#E7F0F9', on: '#FFFFFF', emoji: '🇬🇷' },
  ru: { primary: '#0033A0', dark: '#002573', accent: '#D52B1E', soft: '#E6EBF7', on: '#FFFFFF', emoji: '🇷🇺' },
  tr: { primary: '#E30A17', dark: '#A80811', accent: '#B0B7C3', soft: '#FDE9EA', on: '#FFFFFF', emoji: '🇹🇷' },
  ar: { primary: '#165B33', dark: '#0E3F23', accent: '#D4AF37', soft: '#E8F1EC', on: '#FFFFFF', emoji: '🇸🇦' },
  en: { primary: '#012169', dark: '#01174B', accent: '#C8102E', soft: '#E6E9F2', on: '#FFFFFF', emoji: '🇬🇧' },
  sw: { primary: '#00A3DD', dark: '#0079A5', accent: '#1EB53A', soft: '#E5F6FC', on: '#FFFFFF', emoji: '🇹🇿' },
  yo: { primary: '#008751', dark: '#005C37', accent: '#62BD8E', soft: '#E5F5EE', on: '#FFFFFF', emoji: '🇳🇬' },
  ha: { primary: '#E05206', dark: '#A83E05', accent: '#0DB02B', soft: '#FCEEE6', on: '#FFFFFF', emoji: '🇳🇪' },
  xh: { primary: '#FFB612', dark: '#B7810B', accent: '#007749', soft: '#FFF8E7', on: '#1F2937', emoji: '🇿🇦', darkText: true },
  // Owner-specified tino rangatiratanga palette:
  // #CC0000 / #000000 / #FFFFFF / #BCBCBC / #778E46
  mi: { primary: '#CC0000', dark: '#000000', accent: '#778E46', soft: '#F4F0F0', on: '#FFFFFF', emoji: '🇳🇿' },
  // India saffron / green, with the Ashoka-chakra navy as accent.
  hi: { primary: '#FF9933', dark: '#CC6E1F', accent: '#138808', soft: '#FFF3E6', on: '#1F2937', emoji: '🇮🇳', darkText: true },
  // Jamaica: green primary, black as the dark shade, flag gold as the accent.
  jam: { primary: '#009B3A', dark: '#000000', accent: '#FED100', soft: '#E5F5EC', on: '#FFFFFF', emoji: '🇯🇲' },
  // The Netherlands: national oranje with the flag's cobalt as accent.
  nl: { primary: '#FF7900', dark: '#C25B00', accent: '#21468B', soft: '#FFF1E3', on: '#FFFFFF', emoji: '🇳🇱' },
  // Thailand: flag crimson with the central navy band as accent.
  th: { primary: '#A51931', dark: '#7A1224', accent: '#2D2A4A', soft: '#F8E8EB', on: '#FFFFFF', emoji: '🇹🇭' },
}

const FALLBACK: LanguageTheme = {
  primary: '#4F46E5', // the app's indigo default (signed-out, unknown code)
  dark: '#4338CA',
  accent: '#818CF8',
  soft: '#EEF2FF',
  on: '#FFFFFF',
  emoji: '🌐',
}

export function languageTheme(code: string | undefined | null): LanguageTheme {
  return (code && THEMES[code]) || FALLBACK
}

// ── Stage ramp ──────────────────────────────────────────────────────────
// The five SRS stages walk THROUGH the flag palette (the Māori sample:
// grey → fern green → red → dark red → black): beginner is a neutral grey
// everywhere ("not yet colored in"), adept takes the accent (the flag's
// second color), seasoned the primary, and expert/master darken toward
// black. Languages with multi-color flags get genuinely multi-color tiles.

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function mix(hex: string, withHex: string, pct: number): string {
  const a = hexToRgb(hex)
  const b = hexToRgb(withHex)
  const c = a.map((v, i) => Math.round(v * pct + b[i] * (1 - pct)))
  return '#' + c.map((v) => v.toString(16).padStart(2, '0')).join('')
}

/** Dark or white text for readability on the given background. */
function onColor(hex: string): string {
  const [r, g, b] = hexToRgb(hex)
  return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? '#1F2937' : '#FFFFFF'
}

export interface StageColor {
  bg: string
  text: string
}

const BEGINNER_GREY = '#BCBCBC'

export function stageRamp(code: string | undefined | null): StageColor[] {
  const t = languageTheme(code)
  const bgs = [
    BEGINNER_GREY,
    t.accent,
    t.primary,
    mix(t.primary, '#000000', 0.55),
    mix(t.dark, '#000000', 0.45),
  ]
  return bgs.map((bg) => ({ bg, text: onColor(bg) }))
}

/** Writes the active language's palette into the `--lang-*` CSS variables
 * that the Tailwind `lang` color tokens read. */
export function applyLanguageTheme(code: string | undefined | null): void {
  const t = languageTheme(code)
  const root = document.documentElement.style
  root.setProperty('--lang-primary', t.primary)
  root.setProperty('--lang-primary-dark', t.dark)
  root.setProperty('--lang-accent', t.accent)
  root.setProperty('--lang-soft', t.soft)
  root.setProperty('--lang-on-primary', t.on)
  stageRamp(code).forEach((s, i) => {
    root.setProperty(`--lang-stage-${i + 1}`, s.bg)
    root.setProperty(`--lang-stage-${i + 1}-on`, s.text)
  })
}
