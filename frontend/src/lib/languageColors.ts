/** Per-language identity palettes drawn from each language's flag/country,
 * applied app-wide while that language is active (LanguageThemeApplier sets
 * the `--lang-*` CSS variables; Tailwind tokens `bg-lang`, `text-lang`,
 * `bg-lang-soft`, `bg-lang-dark`, `text-lang-on`, `bg-lang-accent` read
 * them). Several flags genuinely share color families (four blue-flagged
 * languages, three green); shades are spread within each family so the
 * palettes stay distinguishable.
 *
 * Notes on the less obvious picks: Catalan uses the Andorran flag (the one
 * state where Catalan is the sole official language); Portuguese uses
 * Brazil per the path's Brazilian-register default; Hausa uses Niger to
 * disambiguate from Yoruba's Nigeria; Māori uses the tino rangatiratanga
 * palette (red/black/white, owner-specified, with fern green as accent).
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
  /** True when primary is light enough to need dark text on it. */
  darkText?: boolean
}

const THEMES: Record<string, LanguageTheme> = {
  es: { primary: '#AD1519', dark: '#7A0E11', accent: '#F1BF00', soft: '#FDECEC', on: '#FFFFFF' },
  fr: { primary: '#0055A4', dark: '#003E78', accent: '#EF4135', soft: '#E8F1FA', on: '#FFFFFF' },
  de: { primary: '#D89000', dark: '#8A5C00', accent: '#DD0000', soft: '#FCF3DF', on: '#FFFFFF' },
  it: { primary: '#008C45', dark: '#00602F', accent: '#CD212A', soft: '#E6F5EC', on: '#FFFFFF' },
  pt: { primary: '#009739', dark: '#046A38', accent: '#FEDD00', soft: '#E4F3EA', on: '#FFFFFF' },
  ca: { primary: '#FCDD09', dark: '#B89F00', accent: '#DA121A', soft: '#FEFAE0', on: '#1F2937', darkText: true },
  ro: { primary: '#002B7F', dark: '#001F5C', accent: '#FCD116', soft: '#E7ECF6', on: '#FFFFFF' },
  el: { primary: '#0D5EAF', dark: '#0A4682', accent: '#7BAFD4', soft: '#E7F0F9', on: '#FFFFFF' },
  ru: { primary: '#0033A0', dark: '#002573', accent: '#D52B1E', soft: '#E6EBF7', on: '#FFFFFF' },
  tr: { primary: '#E30A17', dark: '#A80811', accent: '#B0B7C3', soft: '#FDE9EA', on: '#FFFFFF' },
  ar: { primary: '#165B33', dark: '#0E3F23', accent: '#D4AF37', soft: '#E8F1EC', on: '#FFFFFF' },
  en: { primary: '#012169', dark: '#01174B', accent: '#C8102E', soft: '#E6E9F2', on: '#FFFFFF' },
  sw: { primary: '#00A3DD', dark: '#0079A5', accent: '#1EB53A', soft: '#E5F6FC', on: '#FFFFFF' },
  yo: { primary: '#008751', dark: '#005C37', accent: '#62BD8E', soft: '#E5F5EE', on: '#FFFFFF' },
  ha: { primary: '#E05206', dark: '#A83E05', accent: '#0DB02B', soft: '#FCEEE6', on: '#FFFFFF' },
  xh: { primary: '#FFB612', dark: '#B7810B', accent: '#007749', soft: '#FFF8E7', on: '#1F2937', darkText: true },
  // Owner-specified tino rangatiratanga palette:
  // #CC0000 / #000000 / #FFFFFF / #BCBCBC / #778E46
  mi: { primary: '#CC0000', dark: '#000000', accent: '#778E46', soft: '#F4F0F0', on: '#FFFFFF' },
  // India saffron / green, with the Ashoka-chakra navy as accent.
  hi: { primary: '#FF9933', dark: '#CC6E1F', accent: '#138808', soft: '#FFF3E6', on: '#1F2937', darkText: true },
  // Jamaica: green primary, black as the dark shade, flag gold as the accent.
  jam: { primary: '#009B3A', dark: '#000000', accent: '#FED100', soft: '#E5F5EC', on: '#FFFFFF' },
  // The Netherlands: national oranje with the flag's cobalt as accent.
  nl: { primary: '#FF7900', dark: '#C25B00', accent: '#21468B', soft: '#FFF1E3', on: '#FFFFFF' },
  // Thailand: flag crimson with the central navy band as accent.
  th: { primary: '#A51931', dark: '#7A1224', accent: '#2D2A4A', soft: '#F8E8EB', on: '#FFFFFF' },
  // Taegukgi blue with the red as accent.
  ko: { primary: '#003478', dark: '#002357', accent: '#C60C30', soft: '#E6EDF6', on: '#FFFFFF' },
  // Israel: Magen David blue, a warm Jerusalem-stone gold as accent.
  he: { primary: '#0038B8', dark: '#00256E', accent: '#C9A227', soft: '#E7ECF9', on: '#FFFFFF' },
  // Latin: no living-vernacular flag exists, so an imperial-Rome palette
  // (deep red, laurel gold) stands in — see CircleFlag.tsx's la.svg note.
  la: { primary: '#7B1113', dark: '#4A0A0B', accent: '#D4AF37', soft: '#F7EDE2', on: '#FFFFFF' },
  // Iran: flag green with the flag red as accent.
  fa: { primary: '#239F40', dark: '#1A7530', accent: '#DA0000', soft: '#E7F5EA', on: '#FFFFFF' },
  // Indonesia: flag red with a batik gold accent (the flag is red/white only).
  id: { primary: '#CE1126', dark: '#8E0B1A', accent: '#D4A017', soft: '#FBE9EC', on: '#FFFFFF' },
  // Philippines: Katipunan blue with the sun's gold as accent.
  tl: { primary: '#0038A8', dark: '#002569', accent: '#FCD116', soft: '#E6ECF8', on: '#FFFFFF' },
}

const FALLBACK: LanguageTheme = {
  primary: '#4F46E5', // the app's indigo default (signed-out, unknown code)
  dark: '#4338CA',
  accent: '#818CF8',
  soft: '#EEF2FF',
  on: '#FFFFFF',
}

export function languageTheme(code: string | undefined | null): LanguageTheme {
  return (code && THEMES[code]) || FALLBACK
}

// ── Ground glyph ────────────────────────────────────────────────────────
// The "Language as Ground" skin (C) puts one enormous character from the
// course's script behind the page. Each is the language's own letter — a
// character distinctive TO that language, not just its script, where one
// exists (ES Ñ, DE ß, AR ض — "the language of ḍād" is what Arabic calls
// itself). Latin-script courses without a signature letter fall back to
// the code's first letter, which at 36rem and 8% opacity reads as texture,
// not text.
const GROUND_GLYPHS: Record<string, string> = {
  es: 'Ñ', fr: 'Ç', de: 'ß', it: 'È', pt: 'Ã', ca: 'Ŀ', ro: 'Ă',
  el: 'Ω', ru: 'Я', tr: 'Ğ', ar: 'ض', en: 'Æ', sw: 'J', yo: 'Ẹ',
  ha: 'Ƙ', xh: 'X', mi: 'Ā', hi: 'अ', jam: 'J', nl: 'Ĳ', th: 'ก',
  ko: '한', he: 'א', la: 'Æ', fa: 'پ', id: 'I', tl: 'K',
}

export function groundGlyph(code: string | undefined | null): string {
  if (code && GROUND_GLYPHS[code]) return GROUND_GLYPHS[code]
  return (code || 'a').charAt(0).toUpperCase()
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
  // CSS `content:` needs a quoted string — the quotes are part of the value.
  root.setProperty('--lang-glyph', JSON.stringify(groundGlyph(code)))
  stageRamp(code).forEach((s, i) => {
    root.setProperty(`--lang-stage-${i + 1}`, s.bg)
    root.setProperty(`--lang-stage-${i + 1}-on`, s.text)
  })
}
