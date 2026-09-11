/**
 * A handwriting-style face per script, for the compare view: the expected
 * text rendered as a written hand rather than a print face, so the learner
 * checks their shapes against something a person would write. Loaded from
 * Google Fonts on demand — one stylesheet per family, only when Write
 * opens for a course that needs it.
 *
 * The font is a tracing guide and a comparison, never the stroke source;
 * the authored templates of later phases are what teach the strokes.
 * Scripts with no handwriting face on Google Fonts (Hebrew cursive, Greek)
 * fall back to the browser's generic cursive family — noted in DEBT.md.
 */
export interface HandFont {
  family: string
  /** The Google Fonts `family=` value; absent when nothing is loaded. */
  google?: string
}

const ARABIC_SCRIPT = new Set(['ar', 'fa'])
const NO_FACE = new Set(['he', 'el'])

export function handFontFor(code: string | undefined): HandFont {
  if (!code) return { family: 'cursive' }
  if (ARABIC_SCRIPT.has(code)) return { family: "'Aref Ruqaa'", google: 'Aref+Ruqaa:wght@400' }
  if (code === 'hi') return { family: 'Kalam', google: 'Kalam:wght@400' }
  if (code === 'ko') return { family: "'Nanum Pen Script'", google: 'Nanum+Pen+Script' }
  if (code === 'th') return { family: 'Sriracha', google: 'Sriracha' }
  if (NO_FACE.has(code)) return { family: 'cursive' }
  // Caveat covers Latin and Cyrillic, which is every remaining course.
  return { family: 'Caveat', google: 'Caveat:wght@500' }
}

/** Whether the course's hand has a print/cursive distinction worth a
 * toggle in this phase. Arabic is joined by nature; Hangul, Thai and
 * Devanagari handwriting are print-shaped; Hebrew's cursive is a separate
 * alphabet the assessor is told about by the style flag once its face
 * exists. */
export function hasCursiveToggle(code: string | undefined): boolean {
  if (!code) return false
  return !new Set(['ar', 'fa', 'ko', 'th', 'hi', 'he']).has(code)
}

/** Whether a course's writers use cursive by default (Russian: yes — print
 * is what you read, not what you write). */
export function defaultStyle(code: string | undefined): 'print' | 'cursive' {
  return code === 'ru' ? 'cursive' : 'print'
}

const loaded = new Set<string>()

export function ensureHandFont(font: HandFont): void {
  if (!font.google || loaded.has(font.google)) return
  loaded.add(font.google)
  if (typeof document === 'undefined') return
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = `https://fonts.googleapis.com/css2?family=${font.google}&display=swap`
  link.setAttribute('data-hand-font', font.google)
  document.head.appendChild(link)
}
