import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LanguagePicker from '../components/LanguagePicker'

const { mockSetActive } = vi.hoisted(() => ({ mockSetActive: vi.fn() }))
let mockActiveId: string | null = 'lang-es'

vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(),
  getProfile: vi.fn(),
  updateProfile: vi.fn(() => Promise.resolve({})),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({
        activeLanguageId: mockActiveId,
        setActiveLanguageId: mockSetActive,
      }),
  ),
}))

import { getLanguages, getProfile, updateProfile } from '../api/profile'

const mockLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockProfile = getProfile as ReturnType<typeof vi.fn>
const mockUpdate = updateProfile as ReturnType<typeof vi.fn>

const LANGS = [
  { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false },
  { id: 'lang-ar', code: 'ar', name: 'Arabic', rtl: true },
  { id: 'lang-ru', code: 'ru', name: 'Russian', rtl: false },
]

function renderPicker() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <LanguagePicker />
    </QueryClientProvider>,
  )
}

describe('LanguagePicker (circle-flag listbox)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockActiveId = 'lang-es'
    mockLanguages.mockResolvedValue(LANGS)
    mockProfile.mockResolvedValue({ plan_scope: 'all', plan_language_id: null })
  })

  it('shows the active language with its circle flag on the trigger', async () => {
    renderPicker()
    const trigger = await screen.findByRole('button', {
      name: /select active language/i,
    })
    expect(trigger.textContent).toContain('Spanish')
    expect(screen.getByTestId('flag-es')).toBeDefined()
    // Closed by default — no listbox in the tree.
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('opens a listbox where every option carries its flag; picking saves', async () => {
    renderPicker()
    fireEvent.click(
      await screen.findByRole('button', { name: /select active language/i }),
    )
    const listbox = screen.getByRole('listbox')
    expect(listbox).toBeDefined()
    expect(screen.getAllByRole('option')).toHaveLength(3)
    // Flags: trigger's es + option es/ar/ru.
    expect(screen.getAllByTestId('flag-es').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByTestId('flag-ar')).toBeDefined()
    expect(screen.getByTestId('flag-ru')).toBeDefined()

    fireEvent.click(screen.getByRole('option', { name: /arabic/i }))
    expect(mockSetActive).toHaveBeenCalledWith('lang-ar')
    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({ active_language_id: 'lang-ar' }),
    )
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('keyboard: arrows move, Enter picks, Escape closes', async () => {
    renderPicker()
    const trigger = await screen.findByRole('button', {
      name: /select active language/i,
    })
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    const listbox = await screen.findByRole('listbox')
    // Highlight starts on the selected language (index 0) — one down = Arabic.
    fireEvent.keyDown(listbox, { key: 'ArrowDown' })
    fireEvent.keyDown(listbox, { key: 'Enter' })
    expect(mockSetActive).toHaveBeenCalledWith('lang-ar')

    // Reopen and dismiss.
    fireEvent.click(trigger)
    fireEvent.keyDown(screen.getByRole('listbox'), { key: 'Escape' })
    expect(screen.queryByRole('listbox')).toBeNull()
    expect(mockSetActive).toHaveBeenCalledTimes(1)
  })

  it('a single-language plan locks the other options', async () => {
    mockProfile.mockResolvedValue({
      plan_scope: 'single',
      plan_language_id: 'lang-es',
    })
    renderPicker()
    const trigger = await screen.findByRole('button', {
      name: /select active language/i,
    })
    // The profile query resolves async — wait for the locked state to land.
    await waitFor(() => {
      fireEvent.click(trigger)
      const arabic = screen.getByRole('option', { name: /arabic/i })
      expect(arabic.getAttribute('aria-disabled')).toBe('true')
    })
    fireEvent.click(screen.getByRole('option', { name: /arabic/i }))
    expect(mockSetActive).not.toHaveBeenCalled()
    expect(
      screen.getAllByText(/all-languages plan/i).length,
    ).toBeGreaterThanOrEqual(1)
  })

  it('shows the loading shimmer until languages arrive', async () => {
    mockLanguages.mockReturnValue(new Promise(() => {}))
    renderPicker()
    expect(screen.getByLabelText(/loading languages/i)).toBeDefined()
  })
})
