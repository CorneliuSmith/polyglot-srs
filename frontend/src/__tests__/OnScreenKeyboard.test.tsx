import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock react-simple-keyboard and its CSS before importing the component
vi.mock('react-simple-keyboard', () => ({
  default: ({ onKeyPress }: { onKeyPress: (key: string) => void }) => (
    <div data-testid="keyboard-mock">
      <button type="button" onClick={() => onKeyPress('а')}>а</button>
      <button type="button" onClick={() => onKeyPress('ب')}>ب</button>
      <button type="button" onClick={() => onKeyPress('{enter}')}>enter</button>
      <button type="button" onClick={() => onKeyPress('{bksp}')}>bksp</button>
      <button type="button" onClick={() => onKeyPress('{space}')}>space</button>
    </div>
  ),
}))

vi.mock('react-simple-keyboard/build/css/index.css', () => ({}))

vi.mock('simple-keyboard-layouts/build/layouts/russian', () => ({
  default: { layout: { default: ['а б в'], shift: ['А Б В'] } },
}))

vi.mock('simple-keyboard-layouts/build/layouts/arabic', () => ({
  default: { layout: { default: ['ا ب ت'], shift: ['ا ب ت'] } },
}))

// Import component after mocks are set up
const { default: OnScreenKeyboard } = await import('../features/keyboards/OnScreenKeyboard')

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
