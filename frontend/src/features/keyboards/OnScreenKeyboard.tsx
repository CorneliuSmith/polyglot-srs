import Keyboard from 'react-simple-keyboard'
import 'react-simple-keyboard/build/css/index.css'
import russianLayout from 'simple-keyboard-layouts/build/layouts/russian'
import arabicLayout from 'simple-keyboard-layouts/build/layouts/arabic'
import turkishLayout from 'simple-keyboard-layouts/build/layouts/turkish'

export type KeyboardLanguage =
  | 'ru' | 'ar' | 'tr' | 'yo' | 'ha'
  | 'es' | 'it' | 'fr' | 'de' | 'ca' | 'mi'

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

const LAYOUTS: Record<string, { default: string[] } | { [k: string]: string[] }> = {
  ru: russianLayout.layout,
  ar: arabicLayout.layout,
  tr: turkishLayout.layout,
  yo: yorubaLayout,
  ha: hausaLayout,
  es: withAccents('á é í ó ú ñ ü ¿ ¡'),
  it: withAccents('à è é ì í î ò ó ù'),
  fr: withAccents('é è ê à â ç î ï ô û ù œ'),
  de: withAccents('ä ö ü ß'),
  ca: withAccents('à è é í ï ò ó ú ü ç'),
  mi: withAccents('ā ē ī ō ū'),
}

export default function OnScreenKeyboard({
  languageCode,
  onKeyPress,
  onEnter,
  onBackspace,
}: OnScreenKeyboardProps) {
  const layout = LAYOUTS[languageCode] ?? russianLayout.layout

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
    if (button.startsWith('{') && button.endsWith('}')) {
      return // shift/caps/tab: inert on purpose (answers are lowercase)
    }
    onKeyPress(button)
  }

  return (
    <div className="w-full border-t border-gray-200 pt-4 max-w-lg mx-auto" data-testid="on-screen-keyboard">
      <Keyboard
        layout={layout}
        onKeyPress={handleKeyPress}
        theme="hg-theme-default"
      />
    </div>
  )
}
