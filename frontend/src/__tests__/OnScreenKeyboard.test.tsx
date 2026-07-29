import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock react-simple-keyboard and its CSS before importing the component.
// The mock exposes the active layer and the layout JSON so tests can see
// what the component actually hands the keyboard.
vi.mock('react-simple-keyboard', () => ({
  default: ({
    onKeyPress,
    layoutName,
    layout,
  }: {
    onKeyPress: (key: string) => void
    layoutName?: string
    layout: object
  }) => (
    <div
      data-testid="keyboard-mock"
      data-layout-name={layoutName ?? 'default'}
      data-layout-json={JSON.stringify(layout)}
    >
      <button type="button" onClick={() => onKeyPress('а')}>а</button>
      <button type="button" onClick={() => onKeyPress('ب')}>ب</button>
      <button type="button" onClick={() => onKeyPress('{enter}')}>enter</button>
      <button type="button" onClick={() => onKeyPress('{bksp}')}>bksp</button>
      <button type="button" onClick={() => onKeyPress('{space}')}>space</button>
      <button type="button" onClick={() => onKeyPress('{shift}')}>shift</button>
      <button type="button" onClick={() => onKeyPress('{lock}')}>lock</button>
    </div>
  ),
}))

vi.mock('react-simple-keyboard/build/css/index.css', () => ({}))

vi.mock('simple-keyboard-layouts/build/layouts/russian', () => ({
  default: { layout: { default: ['а б в'], shift: ['А Б В'] } },
}))

vi.mock('simple-keyboard-layouts/build/layouts/arabic', () => ({
  default: {
    layout: {
      default: ['ا ب ت', '.com @ {space}'],
      shift: ['أ إ آ', '.com @ {space}'],
    },
  },
}))

// Import component after mocks are set up
const { default: OnScreenKeyboard, hasKeyboardLayout } = await import(
  '../features/keyboards/OnScreenKeyboard'
)

describe('OnScreenKeyboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders keyboard for Russian language code', () => {
    render(<OnScreenKeyboard languageCode="ru" onKeyPress={() => {}} />)
    expect(screen.getByTestId('on-screen-keyboard')).toBeDefined()
    expect(screen.getByTestId('keyboard-mock')).toBeDefined()
  })

  it('renders keyboard for Arabic language code', () => {
    render(<OnScreenKeyboard languageCode="ar" onKeyPress={() => {}} />)
    expect(screen.getByTestId('on-screen-keyboard')).toBeDefined()
    expect(screen.getByTestId('keyboard-mock')).toBeDefined()
  })

  it('calls onKeyPress callback when a key is pressed', () => {
    const onKeyPress = vi.fn()
    render(<OnScreenKeyboard languageCode="ru" onKeyPress={onKeyPress} />)
    const keyBtn = screen.getByText('а')
    keyBtn.click()
    expect(onKeyPress).toHaveBeenCalledWith('а')
  })

  it('calls onKeyPress with Arabic character when Arabic key pressed', () => {
    const onKeyPress = vi.fn()
    render(<OnScreenKeyboard languageCode="ar" onKeyPress={onKeyPress} />)
    const keyBtn = screen.getByText('ب')
    keyBtn.click()
    expect(onKeyPress).toHaveBeenCalledWith('ب')
  })

  it('Arabic gets an always-visible harakat + hamza row (no .com junk)', () => {
    // Beta report: "we are not able to add diacritics" — the stock layout
    // hid every haraka and hamza letter behind an inert shift key.
    render(<OnScreenKeyboard languageCode="ar" onKeyPress={() => {}} />)
    const json = screen
      .getByTestId('keyboard-mock')
      .getAttribute('data-layout-json')!
    for (const ch of ['َ', 'ُ', 'ِ', 'ّ', 'ْ', 'ء', 'أ', 'إ', 'آ']) {
      expect(json).toContain(ch)
    }
    expect(json).not.toContain('.com')
  })

  it('Hindi, Thai and Korean all have layouts (owner request)', () => {
    for (const code of ['hi', 'th', 'ko'] as const) {
      expect(hasKeyboardLayout(code), code).toBe(true)
    }
  })

  it('Hebrew, Persian and Latin all have layouts (owner request)', () => {
    for (const code of ['he', 'fa', 'la'] as const) {
      expect(hasKeyboardLayout(code), code).toBe(true)
    }
    // id/tl are plain Latin script — they use the device keyboard, and must
    // never silently borrow another language's layout.
    for (const code of ['id', 'tl'] as const) {
      expect(hasKeyboardLayout(code), code).toBe(false)
    }
  })

  it('the Hebrew layout carries the alphabet incl. final forms', () => {
    render(<OnScreenKeyboard languageCode="he" onKeyPress={() => {}} />)
    const json = screen
      .getByTestId('keyboard-mock')
      .getAttribute('data-layout-json')!
    for (const ch of ['א', 'ב', 'ש', 'ת', 'ך', 'ם', 'ן', 'ף', 'ץ']) {
      expect(json).toContain(ch)
    }
    expect(json).not.toContain('.com')
  })

  it('the Persian layout carries its four extra letters and a ZWNJ key', () => {
    render(<OnScreenKeyboard languageCode="fa" onKeyPress={() => {}} />)
    const json = screen
      .getByTestId('keyboard-mock')
      .getAttribute('data-layout-json')!
    // پ چ ژ گ are exactly what Persian adds to the Arabic inventory.
    for (const ch of ['پ', 'چ', 'ژ', 'گ']) {
      expect(json).toContain(ch)
    }
    // Without the nim-fasele, می‌روم cannot be typed correctly at all.
    expect(json).toContain('‌')
    expect(json).not.toContain('.com')
  })

  it('the Latin layout offers macron vowels', () => {
    render(<OnScreenKeyboard languageCode="la" onKeyPress={() => {}} />)
    const json = screen
      .getByTestId('keyboard-mock')
      .getAttribute('data-layout-json')!
    for (const ch of ['ā', 'ē', 'ī', 'ō', 'ū']) {
      expect(json).toContain(ch)
    }
  })

  it('the Hindi layout carries Devanagari consonants and matras', () => {
    render(<OnScreenKeyboard languageCode="hi" onKeyPress={() => {}} />)
    const json = screen
      .getByTestId('keyboard-mock')
      .getAttribute('data-layout-json')!
    // consonants, the vowel signs that ride on them, and the halant.
    for (const ch of ['क', 'म', 'न', 'ा', 'ि', 'ी', '्']) {
      expect(json, ch).toContain(ch)
    }
  })

  it('the Thai layout carries consonants, vowel signs and tone marks', () => {
    render(<OnScreenKeyboard languageCode="th" onKeyPress={() => {}} />)
    const json = screen
      .getByTestId('keyboard-mock')
      .getAttribute('data-layout-json')!
    for (const ch of ['ก', 'ม', 'า', 'ิ', 'ุ', 'เ', '่', '้']) {
      expect(json, ch).toContain(ch)
    }
  })

  it('the Korean layout carries jamo for the caller to compose', () => {
    render(<OnScreenKeyboard languageCode="ko" onKeyPress={() => {}} />)
    const json = screen
      .getByTestId('keyboard-mock')
      .getAttribute('data-layout-json')!
    // Conjoining jamo (U+1100 initials / U+1161 medials) — composeScript
    // turns the run into syllable blocks at the insertion point.
    for (const ch of ['\u1100', '\u1102', '\u1161', '\u1175']) {
      expect(json, ch).toContain(ch)
    }
  })

  it('shift switches layers one-shot; lock is sticky', () => {
    const onKeyPress = vi.fn()
    render(<OnScreenKeyboard languageCode="ar" onKeyPress={onKeyPress} />)
    const layer = () =>
      screen.getByTestId('keyboard-mock').getAttribute('data-layout-name')
    expect(layer()).toBe('default')

    // One-shot: shift engages, a character press drops back.
    fireEvent.click(screen.getByText('shift'))
    expect(layer()).toBe('shift')
    fireEvent.click(screen.getByText('ب'))
    expect(onKeyPress).toHaveBeenCalledWith('ب')
    expect(layer()).toBe('default')

    // Sticky: lock stays through characters, unlocks on second press.
    fireEvent.click(screen.getByText('lock'))
    fireEvent.click(screen.getByText('ب'))
    expect(layer()).toBe('shift')
    fireEvent.click(screen.getByText('lock'))
    expect(layer()).toBe('default')
  })

  it('shift stays inert for layouts without a shift layer', () => {
    const onKeyPress = vi.fn()
    render(<OnScreenKeyboard languageCode="es" onKeyPress={onKeyPress} />)
    fireEvent.click(screen.getByText('shift'))
    expect(
      screen.getByTestId('keyboard-mock').getAttribute('data-layout-name'),
    ).toBe('default')
    expect(onKeyPress).not.toHaveBeenCalled()
  })

  it('enter submits and backspace deletes instead of being swallowed', () => {
    // Regression: special keys were filtered out entirely — Russian and
    // Arabic learners could not submit from the on-screen keyboard.
    const onKeyPress = vi.fn()
    const onEnter = vi.fn()
    const onBackspace = vi.fn()
    render(
      <OnScreenKeyboard
        languageCode="ru"
        onKeyPress={onKeyPress}
        onEnter={onEnter}
        onBackspace={onBackspace}
      />,
    )
    screen.getByText('enter').click()
    screen.getByText('bksp').click()
    screen.getByText('space').click()
    expect(onEnter).toHaveBeenCalledTimes(1)
    expect(onBackspace).toHaveBeenCalledTimes(1)
    expect(onKeyPress).toHaveBeenCalledWith(' ')
    expect(onKeyPress).not.toHaveBeenCalledWith('{enter}')
    expect(onKeyPress).not.toHaveBeenCalledWith('{bksp}')
  })
})
