import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SettingsPage from '../features/settings/SettingsPage'

// Mutable so a single test can study English (which reveals the
// English-only "learning English from" section); default is Spanish.
let mockPrefsActiveLanguageId = 'lang-es'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/profile', () => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
  // The rollout switch renders inside Settings; an account in no rollout
  // gets an empty list and the section never appears.
  getMyExperiments: vi.fn(() => Promise.resolve([])),
  chooseExperimentVariant: vi.fn(),
  getLanguages: vi.fn(() =>
    Promise.resolve([
      { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false },
      { id: 'lang-en', code: 'en', name: 'English', rtl: false },
      { id: 'lang-ar', code: 'ar', name: 'Arabic', rtl: true },
      { id: 'lang-ru', code: 'ru', name: 'Russian', rtl: false },
    ]),
  ),
}))
vi.mock('../api/dashboard', () => ({ getDashboardStats: vi.fn() }))
const {
  signOut, mockSetTheme, mockSetSessionSize, mockSetDailyLearnGoal,
  mockSetShowTashkeel, mockSetQwertyTranslit,
} = vi.hoisted(() => ({
  mockSetDailyLearnGoal: vi.fn(),
  signOut: vi.fn(() => Promise.resolve({ error: null })),
  mockSetTheme: vi.fn(),
  mockSetSessionSize: vi.fn(),
  mockSetShowTashkeel: vi.fn(),
  mockSetQwertyTranslit: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({
        activeLanguageId: mockPrefsActiveLanguageId,
        setActiveLanguageId: vi.fn(),
        theme: 'system',
        setTheme: mockSetTheme,
        sessionSize: 20,
        setSessionSize: mockSetSessionSize,
        accentsOptional: false,
        setAccentsOptional: vi.fn(),
        dailyLearnGoal: 20,
        setDailyLearnGoal: mockSetDailyLearnGoal,
        qwertyTranslit: {},
        setQwertyTranslit: mockSetQwertyTranslit,
        showTashkeel: true,
        setShowTashkeel: mockSetShowTashkeel,
      }),
  ),
}))
vi.mock('../lib/supabase', () => ({ supabase: { auth: { signOut } } }))
vi.mock('../api/review', () => ({
  resetProgress: vi.fn(),
  getLearnDecks: vi.fn(() => Promise.resolve([])),
}))
vi.mock('../api/onboarding', () => ({ setLearnerLevel: vi.fn() }))
vi.mock('../api/billing', async (orig) => ({
  ...(await orig<typeof import('../api/billing')>()),
  getPlanPrices: vi.fn(() =>
    Promise.resolve({ single: null, all: null, monetization: true })),
  startPlanCheckout: vi.fn(() => Promise.resolve({ granted: true, url: null })),
  openBillingPortal: vi.fn(() => Promise.resolve('https://stripe.example/portal')),
}))

import { getProfile, updateProfile } from '../api/profile'
import { getDashboardStats } from '../api/dashboard'
import { getLearnDecks, resetProgress } from '../api/review'
import { setLearnerLevel } from '../api/onboarding'

const mockGetProfile = getProfile as ReturnType<typeof vi.fn>
const mockUpdate = updateProfile as ReturnType<typeof vi.fn>
const mockStats = getDashboardStats as ReturnType<typeof vi.fn>
const mockReset = resetProgress as ReturnType<typeof vi.fn>
const mockDecks = getLearnDecks as ReturnType<typeof vi.fn>
const mockSetLevel = setLearnerLevel as ReturnType<typeof vi.fn>

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
    mockPrefsActiveLanguageId = 'lang-es'
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

  it('changes the daily learn goal, including "whole queue" = 0', async () => {
    renderPage()
    const section = (
      await screen.findByText('Daily learn goal')
    ).closest('section') as HTMLElement
    fireEvent.click(within(section).getByRole('button', { name: '50' }))
    expect(mockSetDailyLearnGoal).toHaveBeenCalledWith(50)
    fireEvent.click(within(section).getByRole('button', { name: 'Whole queue' }))
    expect(mockSetDailyLearnGoal).toHaveBeenCalledWith(0)
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
    mockPrefsActiveLanguageId = 'lang-en' // English-only section
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
    // Nothing chosen displays as what it IS — Automatic (follows the
    // interface language) — not as a silent "English" that misstates the
    // stored NULL. The picker never lies about the state again.
    expect(select.value).toBe('auto')
    fireEvent.change(select, { target: { value: 'es' } })
    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({ support_locale: 'es' }),
    )
    // English itself is not offered as a "from" language (it's an explicit
    // help-language choice, listed once above the real languages)
    const labels = Array.from(select.options).map((o) => o.text)
    expect(labels.filter((l) => l.includes('English'))).toHaveLength(1)
  })

  it('offers the way back to automatic', async () => {
    // The escape hatch's other half: a frozen or regretted choice must be
    // clearable. 'auto' is the reset sentinel the backend stores as NULL —
    // after which the help language follows the interface again.
    mockPrefsActiveLanguageId = 'lang-en'
    renderPage()
    const select = (await screen.findByLabelText(
      'Learning English from',
    )) as HTMLSelectElement
    await waitFor(() =>
      expect(
        Array.from(select.options).some((o) => o.value === 'auto'),
      ).toBe(true),
    )
    fireEvent.change(select, { target: { value: 'auto' } })
    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({ support_locale: 'auto' }),
    )
  })

  it('shows the plan and upgrades single → all (WP16)', async () => {
    const { getPlanPrices, startPlanCheckout } = await import('../api/billing')
    ;(getPlanPrices as ReturnType<typeof vi.fn>).mockResolvedValue({
      single: { amount_cents: 500, currency: 'usd', interval: 'month' },
      all: { amount_cents: 900, currency: 'usd', interval: 'month' },
      monetization: true,
    })
    mockGetProfile.mockResolvedValue({
      batch_size: 5, ui_language: 'en', active_language_id: 'lang-es',
      support_locale: null, plan_scope: 'single', plan_language_id: 'lang-es',
    })
    renderPage()

    expect(await screen.findByText(/single language — spanish/i)).toBeDefined()
    // Stripe-sourced price on the button, never hardcoded.
    const upgrade = await screen.findByRole('button', {
      name: /upgrade to all languages — \$9\.00\/month/i,
    })
    fireEvent.click(upgrade)
    await waitFor(() =>
      expect(startPlanCheckout).toHaveBeenCalledWith('all'),
    )
  })

  it('all-languages accounts see no upgrade button', async () => {
    mockGetProfile.mockResolvedValue({
      batch_size: 5, ui_language: 'en', active_language_id: 'lang-es',
      support_locale: null, plan_scope: 'all', plan_language_id: null,
    })
    renderPage()
    expect(await screen.findByText('All languages')).toBeDefined()
    expect(screen.queryByRole('button', { name: /upgrade/i })).toBeNull()
  })

  it('shows the current level from deck subscriptions and changes it (Kate)', async () => {
    // Kate's bug: placed A1, stuck at A1, no visible way out. The Your-level
    // section derives the level from subscribed decks and re-seats them.
    mockDecks.mockResolvedValue([
      { id: 'd1', list_type: 'grammar', level: 'A1', title: 'A1 Grammar', subscribed: true, total: 10, learned: 3 },
      { id: 'd2', list_type: 'vocabulary', level: 'A1', title: 'A1 Vocab', subscribed: true, total: 10, learned: 3 },
      { id: 'd3', list_type: 'grammar', level: 'B1', title: 'B1 Grammar', subscribed: false, total: 10, learned: 0 },
    ])
    mockSetLevel.mockResolvedValue({ level: 'B1', subscribed: 4, unsubscribed: 0 })
    renderPage()
    const section = await screen.findByTestId('level-section')
    // Highest subscribed deck level = A1 → its pill is pressed.
    await waitFor(() =>
      expect(
        within(section).getByRole('button', { name: 'A1' }).getAttribute('aria-pressed'),
      ).toBe('true'),
    )
    expect(
      within(section).getByRole('button', { name: 'B1' }).getAttribute('aria-pressed'),
    ).toBe('false')

    fireEvent.click(within(section).getByRole('button', { name: 'B1' }))
    await waitFor(() =>
      expect(mockSetLevel).toHaveBeenCalledWith('lang-es', 'B1'),
    )
    expect(await within(section).findByText(/4 decks added/i)).toBeDefined()
  })

  it('hides the language-specific section for Latin-script languages', async () => {
    renderPage()
    await screen.findByText('Daily learn goal') // page settled
    expect(screen.queryByTestId('language-specific')).toBeNull()
  })

  it('Arabic gets tashkeel + QWERTY toggles in Arabic options', async () => {
    mockPrefsActiveLanguageId = 'lang-ar'
    renderPage()
    const section = await screen.findByTestId('language-specific')
    expect(within(section).getByText('Arabic options')).toBeDefined()

    const tashkeel = within(section).getByRole('switch', {
      name: /short vowels/i,
    })
    // Default ON — vocalized forms show until the learner opts out.
    expect(tashkeel.getAttribute('aria-checked')).toBe('true')
    fireEvent.click(tashkeel)
    expect(mockSetShowTashkeel).toHaveBeenCalledWith(false)

    const qwerty = within(section).getByRole('switch', {
      name: /qwerty/i,
    })
    expect(qwerty.getAttribute('aria-checked')).toBe('true')
    fireEvent.click(qwerty)
    expect(mockSetQwertyTranslit).toHaveBeenCalledWith('ar', false)
  })

  it('Russian gets the QWERTY toggle but no tashkeel toggle', async () => {
    mockPrefsActiveLanguageId = 'lang-ru'
    renderPage()
    const section = await screen.findByTestId('language-specific')
    expect(within(section).getByText('Russian options')).toBeDefined()
    expect(
      within(section).queryByRole('switch', { name: /short vowels/i }),
    ).toBeNull()
    fireEvent.click(
      within(section).getByRole('switch', { name: /qwerty/i }),
    )
    expect(mockSetQwertyTranslit).toHaveBeenCalledWith('ru', false)
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
  beforeEach(() => {
    mockPrefsActiveLanguageId = 'lang-es'
  })
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
