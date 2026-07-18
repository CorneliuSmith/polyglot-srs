import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Walkthrough from '../features/onboarding/Walkthrough'

const setWalkthroughDone = vi.fn()
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: (sel: (s: unknown) => unknown) =>
    sel({ setWalkthroughDone }),
}))

describe('Walkthrough', () => {
  beforeEach(() => vi.clearAllMocks())

  it('slides through the features and finishes', () => {
    const onClose = vi.fn()
    render(<Walkthrough onClose={onClose} />)
    expect(screen.getByText(/quick tour/i)).toBeDefined()
    // step to the tutor slide
    for (let n = 0; n < 3; n++) fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText(/Practice vs\. Reference/i)).toBeDefined()
    expect(screen.getByText(/nothing saved/i)).toBeDefined()
  })

  it('"don\'t show again" (default on) persists dismissal via Get started', () => {
    const onClose = vi.fn()
    render(<Walkthrough onClose={onClose} />)
    for (let n = 0; n < 5; n++) fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Get started'))
    expect(setWalkthroughDone).toHaveBeenCalledWith(true)
    expect(onClose).toHaveBeenCalled()
  })

  it('closing with "don\'t show again" unchecked does NOT persist', () => {
    const onClose = vi.fn()
    render(<Walkthrough onClose={onClose} />)
    fireEvent.click(screen.getByLabelText(/Don.t show again/i)) // uncheck
    fireEvent.click(screen.getByLabelText(/Close tour/i))
    expect(setWalkthroughDone).not.toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })
})
