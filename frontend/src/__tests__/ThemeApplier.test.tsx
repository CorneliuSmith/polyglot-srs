import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, cleanup } from '@testing-library/react'
import ThemeApplier from '../components/ThemeApplier'
import type { Theme } from '../stores/prefsStore'

vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(),
}))

import { usePrefsStore } from '../stores/prefsStore'

const mockUsePrefsStore = usePrefsStore as unknown as ReturnType<typeof vi.fn>

function setTheme(theme: Theme) {
  mockUsePrefsStore.mockImplementation(
    (selector: (s: { theme: Theme }) => unknown) => selector({ theme }),
  )
}

describe('ThemeApplier (WP13h)', () => {
  afterEach(() => {
    cleanup()
    document.documentElement.classList.remove('dark')
  })

  it('adds .dark for the dark preference', () => {
    setTheme('dark')
    render(<ThemeApplier />)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('removes .dark for the light preference', () => {
    document.documentElement.classList.add('dark')
    setTheme('light')
    render(<ThemeApplier />)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('system follows the OS preference via matchMedia', () => {
    const mediaMock = {
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }
    vi.stubGlobal('matchMedia', vi.fn(() => mediaMock))
    setTheme('system')
    render(<ThemeApplier />)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    // ...and it subscribes for live OS changes.
    expect(mediaMock.addEventListener).toHaveBeenCalledWith(
      'change', expect.any(Function),
    )
    vi.unstubAllGlobals()
  })
})
