import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SettingsPage from '../features/settings/SettingsPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/profile', () => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
  getLanguages: vi.fn(() =>
    Promise.resolve([
      { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false },
      { id: 'lang-en', code: 'en', name: 'English', rtl: false },
    ]),
  ),
}))
vi.mock('../api/dashboard', () => ({ getDashboardStats: vi.fn() }))
const { signOut, mockSetTheme, mockSetSessionSize } = vi.hoisted(() => ({
  signOut: vi.fn(() => Promise.resolve({ error: null })),
  mockSetTheme: vi.fn(),
  mockSetSessionSize: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({
        activeLanguageId: 'lang-es',
        setActiveLanguageId: vi.fn(),
        theme: 'system',
        setTheme: mockSetTheme,
        sessionSize: 20,
        setSessionSize: mockSetSessionSize,
      }),
  ),
}))
vi.mock('../lib/supabase', () => ({ supabase: { auth: { signOut } } }))
vi.mock('../api/review', () => ({ resetProgress: vi.fn() }))

import { getProfile, updateProfile } from '../api/profile'
import { getDashboardStats } from '../api/dashboard'
import { resetProgress } from '../api/review'

const mockGetProfile = getProfile as ReturnType<typeof vi.fn>
const mockUpdate = updateProfile as ReturnType<typeof vi.fn>
const mockStats = getDashboardStats as ReturnType<typeof vi.fn>
const mockReset = resetProgress as ReturnType<typeof vi.fn>

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetProfile.mockResolvedValue({
      id: 'u1', batch_size: 5, ui_language: 'en', active_language_id: 'lang-es',
      support_locale: null, created_at: '', updated_at: '',
    })
    mockStats.mockResolvedValue({
      due_count: 4, streak_days: 3, cefr_progress: { A1: { learned: 12, total: 30 } },
    })
    mockUpdate.mockResolvedValue({})
  })

  it('shows progress from the analysis stats', async () => {
    renderPage()
    expect(await screen.findByText('12')).toBeDefined()  // cards learned (A1 learned)
    expect(screen.getByText('4')).toBeDefined()          // due now
    expect(screen.getByText('day streak')).toBeDefined()
  })

  it('changes the new-cards-per-session batch size', async () => {
    renderPage()
    const section = (
      await screen.findByText('New cards per session')
    ).closest('section') as HTMLElement
    fireEvent.click(within(section).getByRole('button', { name: '10' }))
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledWith({ batch_size: 10 }))
  })

  it('changes the cards-per-review-session size', async () => {
    renderPage()
    const section = (
      await screen.findByText('Cards per review session')
    ).closest('section') as HTMLElement
    fireEvent.click(within(section).getByRole('button', { name: '50' }))
    expect(mockSetSessionSize).toHaveBeenCalledWith(50)
  })

  it('switches the theme (WP13h)', async () => {
    renderPage()
    const dark = await screen.findByRole('button', { name: 'Dark' })
    // 'system' is the current pref (mock state), shown as pressed
    expect(
      screen.getByRole('button', { name: 'System' }).getAttribute('aria-pressed'),
    ).toBe('true')
    fireEvent.click(dark)
    expect(mockSetTheme).toHaveBeenCalledWith('dark')
  })

  it("sets the 'learning English from' support locale", async () => {
    renderPage()
    const select = (await screen.findByLabelText(
      'Learning English from',
    )) as HTMLSelectElement
    // options load async from getLanguages — wait for THIS select's Spanish
    await waitFor(() =>
      expect(
        Array.from(select.options).some((o) => o.value === 'es'),
      ).toBe(true),
    )
    expect(select.value).toBe('en') // default: English definitions
    fireEvent.change(select, { target: { value: 'es' } })
    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({ support_locale: 'es' }),
    )
    // English itself is not offered as a "from" language (it's the reset row)
    const labels = Array.from(select.options).map((o) => o.text)
    expect(labels.filter((l) => l.includes('English'))).toHaveLength(1)
  })

  it('signs out', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /sign out/i }))
    await waitFor(() => {
      expect(signOut).toHaveBeenCalled()
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    })
  })
})

describe('SettingsPage danger zone', () => {
  it('resets the active language only after the user confirms', async () => {
    mockReset.mockResolvedValue({ cards_deleted: 7 })
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPage()

    const button = await screen.findByRole('button', {
      name: /reset spanish studies/i,
    })
    fireEvent.click(button)
    expect(confirmSpy).toHaveBeenCalledOnce()
    expect(mockReset).not.toHaveBeenCalled()

    confirmSpy.mockReturnValue(true)
    fireEvent.click(button)
    await waitFor(() => expect(mockReset).toHaveBeenCalledWith('lang-es'))
    expect(await screen.findByText(/7 cards removed/)).toBeDefined()
    confirmSpy.mockRestore()
  })

  it('resets every language when the account-wide button is confirmed', async () => {
    mockReset.mockResolvedValue({ cards_deleted: 42 })
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()

    fireEvent.click(
      await screen.findByRole('button', { name: /reset all studies/i }),
    )
    await waitFor(() => expect(mockReset).toHaveBeenCalledWith(undefined))
    confirmSpy.mockRestore()
  })
})
