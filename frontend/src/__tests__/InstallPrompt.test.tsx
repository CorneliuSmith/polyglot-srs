import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import InstallPrompt from '../components/InstallPrompt'

const setDismissed = vi.fn()
let mockDismissed = false
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: (sel: (s: unknown) => unknown) =>
    sel({
      installPromptDismissed: mockDismissed,
      setInstallPromptDismissed: setDismissed,
    }),
}))

type PromptEvent = Event & { prompt: () => Promise<void> }

describe('InstallPrompt', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDismissed = false
  })

  it('renders nothing without an install event on non-iOS', () => {
    const { container } = render(<InstallPrompt />)
    expect(container.firstChild).toBeNull()
  })

  it('shows Install after beforeinstallprompt; installing dismisses', async () => {
    render(<InstallPrompt />)
    const ev = new Event('beforeinstallprompt') as PromptEvent
    ev.prompt = vi.fn().mockResolvedValue(undefined)
    await act(async () => {
      window.dispatchEvent(ev)
    })
    expect(screen.getByTestId('install-prompt')).toBeDefined()
    fireEvent.click(screen.getByText('Install'))
    expect(ev.prompt).toHaveBeenCalled()
    expect(setDismissed).toHaveBeenCalledWith(true)
  })

  it('the × dismisses persistently', async () => {
    render(<InstallPrompt />)
    const ev = new Event('beforeinstallprompt') as PromptEvent
    ev.prompt = vi.fn()
    await act(async () => {
      window.dispatchEvent(ev)
    })
    fireEvent.click(screen.getByLabelText('Dismiss install prompt'))
    expect(setDismissed).toHaveBeenCalledWith(true)
  })

  it('renders nothing when previously dismissed', async () => {
    mockDismissed = true
    const { container } = render(<InstallPrompt />)
    const ev = new Event('beforeinstallprompt') as PromptEvent
    ev.prompt = vi.fn()
    await act(async () => {
      window.dispatchEvent(ev)
    })
    expect(container.firstChild).toBeNull()
  })
})
