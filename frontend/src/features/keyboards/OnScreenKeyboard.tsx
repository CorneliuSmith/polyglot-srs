import Keyboard from 'react-simple-keyboard'
import 'react-simple-keyboard/build/css/index.css'
import russianLayout from 'simple-keyboard-layouts/build/layouts/russian'
import arabicLayout from 'simple-keyboard-layouts/build/layouts/arabic'
import turkishLayout from 'simple-keyboard-layouts/build/layouts/turkish'

interface OnScreenKeyboardProps {
  languageCode: 'ru' | 'ar' | 'tr' | 'yo' | 'ha'
  onKeyPress: (key: string) => void
  inputRef?: React.RefObject<HTMLInputElement | null>
}

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

const LAYOUTS = {
  ru: russianLayout.layout,
  ar: arabicLayout.layout,
  tr: turkishLayout.layout,
  yo: yorubaLayout,
  ha: hausaLayout,
}

export default function OnScreenKeyboard({ languageCode, onKeyPress }: OnScreenKeyboardProps) {
  const layout = LAYOUTS[languageCode] ?? russianLayout.layout

  const handleKeyPress = (button: string) => {
    // Filter out special function keys
    if (button.startsWith('{') && button.endsWith('}')) {
      return
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
