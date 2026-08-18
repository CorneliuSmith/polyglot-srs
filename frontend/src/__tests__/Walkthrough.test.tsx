import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Walkthrough from '../features/onboarding/Walkthrough'
import { TOUR_VERSION } from '../features/onboarding/tour'

const setWalkthroughDone = vi.fn()
const setWalkthroughVersion = vi.fn()
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: (sel: (s: unknown) => unknown) =>
    sel({ setWalkthroughDone, setWalkthroughVersion }),
}))

describe('Walkthrough', () => {
  beforeEach(() => vi.clearAllMocks())

  it('slides through the features and finishes', () => {
    const onClose = vi.fn()
    render(<Walkthrough onClose={onClose} />)
    expect(screen.getByText(/quick tour/i)).toBeDefined()
    // step to the tutor slide (welcome, get-to-know, learn/review, gym, tutor)
    for (let n = 0; n < 4; n++) fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText(/Practice vs\. Reference/i)).toBeDefined()
    expect(screen.getByText(/nothing saved/i)).toBeDefined()
  })

  it('"don\'t show again" (default on) persists dismissal via Get started', () => {
    const onClose = vi.fn()
    render(<Walkthrough onClose={onClose} />)
    // welcome, language, learn/review, gym, tutor, read, speak → own text
    for (let n = 0; n < 7; n++) fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Get started'))
    expect(setWalkthroughDone).toHaveBeenCalledWith(true)
    expect(setWalkthroughVersion).toHaveBeenCalledWith(TOUR_VERSION)
    expect(onClose).toHaveBeenCalled()
  })

  it('closing with "don\'t show again" unchecked does NOT persist', () => {
    const onClose = vi.fn()
    render(<Walkthrough onClose={onClose} />)
    fireEvent.click(screen.getByLabelText(/Don.t show again/i)) // uncheck
    fireEvent.click(screen.getByLabelText(/Close tour/i))
    expect(setWalkthroughDone).not.toHaveBeenCalled()
    // The EDITION is still recorded: they saw this tour, they just didn't ask
    // to be spared the next first-run. Otherwise a bumped version would
    // reopen it on the very next dashboard visit.
    expect(setWalkthroughVersion).toHaveBeenCalledWith(TOUR_VERSION)
    expect(onClose).toHaveBeenCalled()
  })
})
