import Keyboard from 'react-simple-keyboard'
import 'react-simple-keyboard/build/css/index.css'
import russianLayout from 'simple-keyboard-layouts/build/layouts/russian'
import arabicLayout from 'simple-keyboard-layouts/build/layouts/arabic'
import turkishLayout from 'simple-keyboard-layouts/build/layouts/turkish'

interface OnScreenKeyboardProps {
  languageCode: 'ru' | 'ar' | 'tr'
  onKeyPress: (key: string) => void
  inputRef?: React.RefObject<HTMLInputElement | null>
}

const LAYOUTS = {
  ru: russianLayout.layout,
  ar: arabicLayout.layout,
  tr: turkishLayout.layout,
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
