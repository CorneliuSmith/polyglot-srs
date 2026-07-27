import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LanguageVisibilityPanel from '../features/contribute/LanguageVisibilityPanel'

const { mockSetActive } = vi.hoisted(() => ({ mockSetActive: vi.fn() }))

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/contribute', () => ({ setLanguageVisibility: vi.fn() }))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ setActiveLanguageId: mockSetActive }),
  ),
}))

import { getLanguages } from '../api/profile'
import { setLanguageVisibility } from '../api/contribute'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockSetVisibility = setLanguageVisibility as ReturnType<typeof vi.fn>

const LANGS = [
  { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false, is_visible: true },
  { id: 'lang-he', code: 'he', name: 'Hebrew', rtl: true, is_visible: false },
]

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <LanguageVisibilityPanel />
    </QueryClientProvider>,
  )
}

describe('LanguageVisibilityPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue(LANGS)
    mockSetVisibility.mockResolvedValue(undefined)
  })

  it('shows every language with its current visibility state', async () => {
    renderPanel()
    expect(await screen.findByText('Spanish')).toBeDefined()
    expect(screen.getByText('Hebrew')).toBeDefined()
    const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[]
    expect(checkboxes[0].checked).toBe(true)
    expect(checkboxes[1].checked).toBe(false)
  })

  it('toggling a checkbox calls setLanguageVisibility', async () => {
    renderPanel()
    await screen.findByText('Hebrew')
    const heCheckbox = screen.getByLabelText(/hebrew visible to learners/i)
    fireEvent.click(heCheckbox)
    await waitFor(() =>
      expect(mockSetVisibility).toHaveBeenCalledWith('lang-he', true),
    )
  })

  it('clicking a language name switches the active language (the way in for admins)', async () => {
    renderPanel()
    fireEvent.click(await screen.findByText('Hebrew'))
    expect(mockSetActive).toHaveBeenCalledWith('lang-he')
  })
})
