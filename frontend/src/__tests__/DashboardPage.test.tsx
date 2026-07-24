import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import DueCount from '../features/dashboard/DueCount'
import StreakBadge from '../features/dashboard/StreakBadge'
import CEFRProgress from '../features/dashboard/CEFRProgress'

describe('DueCount', () => {
  it('renders the due count number', () => {
    render(<DueCount count={42} />)
    expect(screen.getByText('42')).toBeDefined()
  })

  it('renders the "Cards Due" label', () => {
    render(<DueCount count={0} />)
    expect(screen.getByText(/cards due/i)).toBeDefined()
  })

  it('renders zero count', () => {
    render(<DueCount count={0} />)
    expect(screen.getByText('0')).toBeDefined()
  })
})

describe('StreakBadge', () => {
  it('renders streak days when greater than 0', () => {
    render(<StreakBadge days={7} />)
    expect(screen.getByText('7')).toBeDefined()
    expect(screen.getByText(/day streak/i)).toBeDefined()
  })

  it('renders start message when days is 0', () => {
    render(<StreakBadge days={0} />)
    expect(screen.getByText(/start your streak/i)).toBeDefined()
  })

  it('renders a streak of 1 day', () => {
    render(<StreakBadge days={1} />)
    expect(screen.getByText('1')).toBeDefined()
  })
})

describe('CEFRProgress', () => {
  // Mirrors the backend contract: cefr_progress maps each level to
  // {learned, total} counts (see backend/repositories/dashboard.py).
  const progress = {
    A1: { learned: 100, total: 100 },
    A2: { learned: 75, total: 100 },
    B1: { learned: 50, total: 100 },
    B2: { learned: 25, total: 100 },
    C1: { learned: 10, total: 100 },
    C2: { learned: 0, total: 100 },
  }

  it('renders all 6 CEFR levels', () => {
    render(<CEFRProgress progress={progress} />)
    expect(screen.getByText('A1')).toBeDefined()
    expect(screen.getByText('A2')).toBeDefined()
    expect(screen.getByText('B1')).toBeDefined()
    expect(screen.getByText('B2')).toBeDefined()
    expect(screen.getByText('C1')).toBeDefined()
    expect(screen.getByText('C2')).toBeDefined()
  })

  it('renders percentage text for each level', () => {
    render(<CEFRProgress progress={progress} />)
    expect(screen.getByText('100%')).toBeDefined()
    expect(screen.getByText('75%')).toBeDefined()
    expect(screen.getByText('50%')).toBeDefined()
    expect(screen.getByText('25%')).toBeDefined()
    expect(screen.getByText('10%')).toBeDefined()
    // There will be two 0% — one for C2 and any missing keys
    const zeros = screen.getAllByText('0%')
    expect(zeros.length).toBeGreaterThanOrEqual(1)
  })

  it('renders all levels even when some have no progress', () => {
    render(<CEFRProgress progress={{}} />)
    // All 6 levels should appear even with empty progress
    expect(screen.getByText('A1')).toBeDefined()
    expect(screen.getByText('C2')).toBeDefined()
  })

  it('renders progress bars via role attribute', () => {
    render(<CEFRProgress progress={progress} />)
    const bars = screen.getAllByRole('progressbar')
    expect(bars).toHaveLength(6)
  })
})

// ── DeckRow: Learn starts, the expansion manages ───────────────────────────

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/review', () => ({
  getDeckPreview: vi.fn(() =>
    Promise.resolve({ items: [{ item: 'ser', detail: 'to be' }] }),
  ),
  setDeckSubscription: vi.fn(() => Promise.resolve()),
  resetDeckProgress: vi.fn(() => Promise.resolve()),
  getLearnDecks: vi.fn(),
}))
vi.mock('../api/dashboard', () => ({ getDashboardStats: vi.fn() }))
vi.mock('../api/contribute', () => ({
  getMyRoles: vi.fn(() => Promise.resolve({ roles: [] })),
  getReviewPrompt: vi.fn(() => Promise.resolve({ due: false })),
}))
vi.mock('../api/onboarding', () => ({
  getOnboardingStatus: vi.fn(() => Promise.resolve({ onboarded: true })),
}))
vi.mock('../api/gym', () => ({
  getGymManifest: vi.fn(() => Promise.resolve({ columns: [] })),
}))
let mockDailyLearnGoal = 20
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({
        activeLanguageId: 'lang-es',
        walkthroughDone: true,
        dailyLearnGoal: mockDailyLearnGoal,
        installPromptDismissed: true,
        setInstallPromptDismissed: vi.fn(),
        whatsNewSeen: [],
      }),
  ),
}))
vi.mock('../components/LanguagePicker', () => ({ default: () => <div /> }))

import DashboardPage, { DeckRow } from '../features/dashboard/DashboardPage'
import { setDeckSubscription, getLearnDecks } from '../api/review'
import { getDashboardStats } from '../api/dashboard'

const baseDeck = {
  id: 'deck-1', list_type: 'grammar' as const, level: 'A1',
  title: 'A1 Grammar Path', total: 20, learned: 5, subscribed: true,
}

function renderRow(deck = baseDeck, onLearn = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DeckRow deck={deck} onLearn={onLearn} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return onLearn
}

describe('DeckRow', () => {
  beforeEach(() => vi.clearAllMocks())

  it('Learn starts learning; management stays behind the expansion', async () => {
    const onLearn = renderRow()

    // The management controls are hidden until the chevron is opened.
    expect(screen.queryByTestId('deck-options')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /^learn$/i }))
    expect(onLearn).toHaveBeenCalledWith(baseDeck)

    fireEvent.click(screen.getByRole('button', { name: /deck options/i }))
    const options = await screen.findByTestId('deck-options')
    expect(options.textContent).toContain('Remove from queue')
    expect(options.textContent).toContain('Browse all items')
    expect(options.textContent).toContain('Reset progress')
    // The contents preview loads inside the expansion.
    expect(await screen.findByText('ser')).toBeDefined()
  })

  it('unqueued decks add from the expansion', async () => {
    renderRow({ ...baseDeck, subscribed: false, learned: 0 })
    fireEvent.click(screen.getByRole('button', { name: /deck options/i }))
    fireEvent.click(await screen.findByRole('button', { name: /add to queue/i }))
    await waitFor(() =>
      expect(setDeckSubscription).toHaveBeenCalledWith('deck-1', true),
    )
  })

  it('disables Learn only when the deck is complete', () => {
    renderRow({ ...baseDeck, learned: 20 })
    const learn = screen.getByRole('button', { name: /^learn$/i }) as HTMLButtonElement
    expect(learn.disabled).toBe(true)
  })
})

// ── Command-center tiles: the big button STARTS, the chevron expands ───────

const mockStats = getDashboardStats as ReturnType<typeof vi.fn>
const mockDecks = getLearnDecks as ReturnType<typeof vi.fn>

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Dashboard tiles', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDailyLearnGoal = 20
    mockStats.mockResolvedValue({
      due_count: 99,
      due_grammar: 60,
      due_vocab: 39,
      learned_today: 3,
      streak_days: 3,
      cefr_progress: {},
    })
    mockDecks.mockResolvedValue([
      { id: 'deck-1', list_type: 'grammar', level: 'A1', title: 'A1 Grammar',
        total: 20, learned: 5, subscribed: true },
      { id: 'deck-2', list_type: 'vocabulary', level: 'A1', title: 'A1 Vocab',
        total: 30, learned: 30, subscribed: true },
    ])
  })

  it('the Learn tile draws from the whole queue (unscoped) so the backend round-robins', async () => {
    renderDashboard()
    fireEvent.click(
      await screen.findByRole('button', { name: /learned today/i }),
    )
    // Type comes from the next queued deck with items left (grammar); no level
    // is passed, so the batch round-robins across every subscribed grammar deck
    // instead of draining deck-1 first.
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/learn?type=grammar'),
    )
  })

  it('interleaves when both grammar and vocab have items left (type=both)', async () => {
    mockDecks.mockResolvedValue([
      { id: 'deck-1', list_type: 'grammar', level: 'A1', title: 'A1 Grammar',
        total: 20, learned: 5, subscribed: true },
      { id: 'deck-2', list_type: 'vocabulary', level: 'A1', title: 'A1 Vocab',
        total: 30, learned: 10, subscribed: true },
    ])
    renderDashboard()
    fireEvent.click(
      await screen.findByRole('button', { name: /learned today/i }),
    )
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/learn?type=both'),
    )
  })

  it('shows The Gym tile only when the language has form categories', async () => {
    const { getGymManifest } = await import('../api/gym')
    const mockGym = getGymManifest as ReturnType<typeof vi.fn>
    renderDashboard()
    await screen.findByText(/learned today/i)
    expect(screen.queryByText('The Gym')).toBeNull()

    cleanup()
    mockGym.mockResolvedValue({
      columns: [{ kind: 'verbs', label: 'Verbs', entries: [{}] }],
    })
    renderDashboard()
    fireEvent.click(await screen.findByRole('button', { name: /the gym/i }))
    expect(mockNavigate).toHaveBeenCalledWith('/gym')
  })

  it('the Learn tile shows daily-goal progress, not the whole queue', async () => {
    renderDashboard()
    // 3 learned today of the default 20-goal; the queue moves to the sublabel
    expect(await screen.findByText('3 / 20')).toBeDefined()
    expect(screen.getByText(/learned today · 15 queued/)).toBeDefined()
  })

  it('a met goal celebrates and goal 0 falls back to the queue count', async () => {
    mockStats.mockResolvedValue({
      due_count: 99, due_grammar: 60, due_vocab: 39,
      learned_today: 25, streak_days: 3, cefr_progress: {},
    })
    renderDashboard()
    // overflow reads honestly: 25 / 20, not a clamped 20 / 20
    expect(await screen.findByText('25 / 20')).toBeDefined()
    expect(screen.getByText(/daily goal done/)).toBeDefined()

    cleanup()
    mockDailyLearnGoal = 0
    renderDashboard()
    expect(await screen.findByText('15')).toBeDefined()
    expect(screen.getByText(/new items queued/)).toBeDefined()
  })

  it('the Learn chevron expands the deck rows without starting a session', async () => {
    renderDashboard()
    fireEvent.click(
      await screen.findByRole('button', { name: /learn queue decks/i }),
    )
    expect(await screen.findByText('A1 · Grammar')).toBeDefined()
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('the Review tile starts all reviews', async () => {
    renderDashboard()
    fireEvent.click(await screen.findByRole('button', { name: /all reviews/i }))
    expect(mockNavigate).toHaveBeenCalledWith('/review')
  })

  it('the Review chevron reveals Grammar Only / Vocab Only with live counts', async () => {
    renderDashboard()
    fireEvent.click(
      await screen.findByRole('button', { name: /review options/i }),
    )
    const options = await screen.findByTestId('review-options')
    expect(options.textContent).toContain('Grammar Only')
    expect(options.textContent).toContain('60')
    expect(options.textContent).toContain('Vocab Only')
    expect(options.textContent).toContain('39')
    expect(mockNavigate).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /grammar only/i }))
    expect(mockNavigate).toHaveBeenCalledWith('/review?type=grammar')
  })
})
