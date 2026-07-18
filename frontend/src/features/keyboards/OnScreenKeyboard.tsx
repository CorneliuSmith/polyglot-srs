import { useState } from 'react'
import Keyboard from 'react-simple-keyboard'
import 'react-simple-keyboard/build/css/index.css'
import russianLayout from 'simple-keyboard-layouts/build/layouts/russian'
import arabicLayout from 'simple-keyboard-layouts/build/layouts/arabic'
import turkishLayout from 'simple-keyboard-layouts/build/layouts/turkish'
import greekLayout from 'simple-keyboard-layouts/build/layouts/greek'
import thaiLayout from 'simple-keyboard-layouts/build/layouts/thai'

export type KeyboardLanguage =
  | 'ru' | 'ar' | 'tr' | 'el' | 'yo' | 'ha'
  | 'es' | 'it' | 'fr' | 'de' | 'ca' | 'mi' | 'pt' | 'ro'

/** Languages that get an on-screen keyboard. Everything else (en, sw, xh —
 * plain Latin) uses the device keyboard; NEVER fall back to another
 * language's layout (Portuguese learners once got Cyrillic). */
export function hasKeyboardLayout(code: string): boolean {
  return code in LAYOUTS
}

interface OnScreenKeyboardProps {
  languageCode: KeyboardLanguage
  onKeyPress: (key: string) => void
  /** The keyboard's enter key — submit the answer. */
  onEnter?: () => void
  /** The keyboard's backspace key — delete before the cursor. */
  onBackspace?: () => void
  inputRef?: React.RefObject<HTMLInputElement | null>
}

// QWERTY plus an accent/special-character row — for Latin-script languages the
// learner just needs the characters that aren't on a US keyboard.
const withAccents = (accentRow: string) => ({
  default: [
    'q w e r t y u i o p',
    'a s d f g h j k l',
    'z x c v b n m {space}',
    accentRow,
  ],
})

// No published Yoruba layout exists for simple-keyboard — QWERTY plus the
// underdotted letters and precomposed tone-marked vowels learners can't
// type on a bare keyboard.
const yorubaLayout = {
  default: [
    'q w e r t y u i o p',
    'a s d f g h j k l',
    'z x c v b n m {space}',
    'ẹ ọ ṣ á à é è í ì gb',
    'ó ò ú ù ẹ́ ẹ̀ ọ́ ọ̀ ń ǹ',
  ],
}

// Hausa Boko orthography: QWERTY plus the hooked consonants and glottal ʼy
// that aren't on a standard keyboard.
const hausaLayout = {
  default: [
    'q w e r t y u i o p',
    'a s d f g h j k l',
    'z x c v b n m {space}',
    'ɓ ɗ ƙ ƴ ʼy ʼ',
  ],
}

// The stock Arabic layout hides every haraka and hamza-carrying letter
// (أ إ آ) behind shift — invisible to learners. Surface them as an
// always-visible row: tanween, short vowels, shadda, sukun, then the
// hamza forms. The ".com @" row is web junk in a language drill.
const HARAKAT_ROW = 'ً ٌ ٍ َ ُ ِ ّ ْ ء أ إ آ'
// A lone combining mark is nearly invisible on a keycap — display each
// haraka on a tatweel carrier (ـَ) while still inserting the bare mark.
const HARAKAT_DISPLAY: Record<string, string> = Object.fromEntries(
  'ً ٌ ٍ َ ُ ِ ّ ْ'.split(' ').map((ch) => [ch, `ـ${ch}`]),
)
const arabicWithHarakat = {
  default: [
    ...arabicLayout.layout.default.slice(0, -1),
    HARAKAT_ROW,
    '{space}',
  ],
  shift: [
    ...arabicLayout.layout.shift.slice(0, -1),
    HARAKAT_ROW,
    '{space}',
  ],
}

const LAYOUTS: Record<string, { default: string[] } | { [k: string]: string[] }> = {
  ru: russianLayout.layout,
  ar: arabicWithHarakat,
  tr: turkishLayout.layout,
  yo: yorubaLayout,
  ha: hausaLayout,
  es: withAccents('á é í ó ú ñ ü ¿ ¡'),
  it: withAccents('à è é ì í î ò ó ù'),
  fr: withAccents('é è ê à â ç î ï ô û ù œ'),
  de: withAccents('ä ö ü ß'),
  ca: withAccents('à è é í ï ò ó ú ü ç'),
  mi: withAccents('ā ē ī ō ū'),
  pt: withAccents('ã õ á é í ó ú â ê ô à ç'),
  ro: withAccents('ă â î ș ț'),
  el: greekLayout.layout,
  th: thaiLayout.layout,
}

export default function OnScreenKeyboard({
  languageCode,
  onKeyPress,
  onEnter,
  onBackspace,
}: OnScreenKeyboardProps) {
  // Layer state: shift is one-shot (like a phone keyboard), lock is sticky.
  // Hooks live above the early return — hooks must run on every render.
  const [layoutName, setLayoutName] = useState<'default' | 'shift'>('default')
  const [locked, setLocked] = useState(false)
  const layout = LAYOUTS[languageCode]
  if (!layout) return null

  const hasShiftLayer = 'shift' in layout

  const handleKeyPress = (button: string) => {
    // Special keys act, not insert. Everything else previously included
    // enter and backspace being silently swallowed — Russian/Arabic
    // learners literally could not submit from this keyboard.
    if (button === '{enter}') {
      onEnter?.()
      return
    }
    if (button === '{bksp}') {
      onBackspace?.()
      return
    }
    if (button === '{space}') {
      onKeyPress(' ')
      return
    }
    // Shift/caps SWITCH LAYERS — the Arabic shift layer carries the
    // harakat and hamza letters (أ إ آ), so an inert shift key made
    // them untypeable (beta report: "can't add diacritics").
    if (button === '{shift}' && hasShiftLayer) {
      setLayoutName((prev) => (prev === 'shift' ? 'default' : 'shift'))
      setLocked(false)
      return
    }
    if (button === '{lock}' && hasShiftLayer) {
      const engage = !(layoutName === 'shift' && locked)
      setLayoutName(engage ? 'shift' : 'default')
      setLocked(engage)
      return
    }
    if (button.startsWith('{') && button.endsWith('}')) {
      return // tab & friends: inert on purpose
    }
    onKeyPress(button)
    // One-shot shift drops back after a single character.
    if (layoutName === 'shift' && !locked) setLayoutName('default')
  }

  return (
    <div className="w-full border-t border-gray-200 pt-4 max-w-lg mx-auto" data-testid="on-screen-keyboard">
      <Keyboard
        layout={layout}
        layoutName={hasShiftLayer ? layoutName : 'default'}
        display={HARAKAT_DISPLAY}
        mergeDisplay
        onKeyPress={handleKeyPress}
        theme="hg-theme-default"
      />
    </div>
  )
}
