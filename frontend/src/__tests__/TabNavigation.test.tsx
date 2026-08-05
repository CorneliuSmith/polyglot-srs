import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import BottomNav from '../components/BottomNav'
import PracticePage from '../features/dashboard/PracticePage'
import MorePage from '../features/dashboard/MorePage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))

vi.mock('../api/gym', () => ({
  getGymManifest: vi.fn(() => Promise.resolve({ columns: [] })),
}))
vi.mock('../api/recommendations', () => ({
  getRecommendations: vi.fn(() =>
    Promise.resolve({ enabled: false, entitled: false, batches: [] }),
  ),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(() =>
    Promise.resolve([{ id: 'lang-es', code: 'es', name: 'Spanish', rtl: false }]),
  ),
  getProfile: vi.fn(() => Promise.resolve({ support_locale: null })),
  updateProfile: vi.fn(),
}))
vi.mock('../api/contribute', () => ({ getMyRoles: vi.fn(() => Promise.resolve({ roles: [] })) }))
vi.mock('../api/personalDecks', () => ({
  getPersonalDecks: vi.fn(() => Promise.resolve([])),
  getPersonalCards: vi.fn(() => Promise.resolve([])),
  createPersonalDeck: vi.fn(),
  renamePersonalDeck: vi.fn(),
  deletePersonalDeck: vi.fn(),
  filePersonalCard: vi.fn(),
  getPersonalTranslationStatus: vi.fn(() => Promise.resolve({})),
  translatePersonalCards: vi.fn(),
  createPersonalCard: vi.fn(),
  deletePersonalCard: vi.fn(),
}))
vi.mock('../features/recommendations/NewPicksPrompt', () => ({ default: () => null }))
vi.mock('../features/feedback/FeedbackButton', () => ({ default: () => null }))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn((s: (x: Record<string, unknown>) => unknown) =>
    s({ activeLanguageId: 'lang-es' }),
  ),
}))
vi.mock('../stores/viewAsStore', () => ({ useViewAsKey: () => 'self' }))
vi.mock('../api/dashboard', () => ({ getDashboardStats: vi.fn() }))

function renderAt(ui: React.ReactNode, path = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Tab navigation', () => {
  beforeEach(() => vi.clearAllMocks())

  it('offers the four sections and marks the current one', () => {
    renderAt(<BottomNav />, '/practice')
    for (const id of ['tab-study', 'tab-practice', 'tab-progress', 'tab-more']) {
      expect(screen.getByTestId(id)).toBeInTheDocument()
    }
    expect(screen.getByTestId('tab-practice')).toHaveAttribute('aria-current', 'page')
    expect(screen.getByTestId('tab-study')).not.toHaveAttribute('aria-current')
  })

  it('does not mark Study active on every route', () => {
    // '/' is a prefix of everything, so it has to be compared exactly or the
    // first tab lights up no matter where you are.
    renderAt(<BottomNav />, '/progress')
    expect(screen.getByTestId('tab-study')).not.toHaveAttribute('aria-current')
    expect(screen.getByTestId('tab-progress')).toHaveAttribute('aria-current', 'page')
  })

  it('navigates between sections', () => {
    renderAt(<BottomNav />, '/')
    fireEvent.click(screen.getByTestId('tab-progress'))
    expect(mockNavigate).toHaveBeenCalledWith('/progress')
  })
})

describe('PracticePage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('holds the optional destinations, so they are not competing with the daily loop', async () => {
    renderAt(<PracticePage />)
    expect(await screen.findByTestId('feature-tiles')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('tile-read'))
    expect(mockNavigate).toHaveBeenCalledWith('/read')
    fireEvent.click(screen.getByTestId('tile-tutor'))
    expect(mockNavigate).toHaveBeenCalledWith('/tutor')
    fireEvent.click(screen.getByTestId('row-grammar'))
    expect(mockNavigate).toHaveBeenCalledWith('/grammar')
  })

  it('hides the Gym for a language with no form categories', async () => {
    renderAt(<PracticePage />)
    await screen.findByTestId('feature-tiles')
    expect(screen.queryByTestId('tile-gym')).toBeNull()
  })

  it('shows the Gym once the language has forms to train', async () => {
    const { getGymManifest } = await import('../api/gym')
    vi.mocked(getGymManifest).mockResolvedValue({
      columns: [{ kind: 'verbs', label: 'Verbs', entries: [{}] }],
    } as never)
    renderAt(<PracticePage />)
    fireEvent.click(await screen.findByTestId('tile-gym'))
    expect(mockNavigate).toHaveBeenCalledWith('/gym')
  })
})

describe('MorePage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('groups the read-once reference material as a language guide', async () => {
    renderAt(<MorePage />)
    // These sat ABOVE the daily loop on the dashboard — read-once material
    // above the thing you do every day. One tap from the tab bar now.
    expect(await screen.findByTestId('language-guide')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('tile-letters'))
    expect(mockNavigate).toHaveBeenCalledWith('/letters')
    fireEvent.click(screen.getByTestId('tile-about'))
    expect(mockNavigate).toHaveBeenCalledWith('/about')
  })

  it('keeps the occasional pages reachable', async () => {
    renderAt(<MorePage />)
    fireEvent.click(await screen.findByTestId('row-decks'))
    expect(mockNavigate).toHaveBeenCalledWith('/decks')
    fireEvent.click(screen.getByTestId('row-account'))
    expect(mockNavigate).toHaveBeenCalledWith('/account')
  })

  it('hides the contributor link from learners without a role', async () => {
    renderAt(<MorePage />)
    await screen.findByTestId('row-decks')
    await waitFor(() =>
      expect(screen.queryByText(/contribute/i)).toBeNull(),
    )
  })
})

describe('BottomNav during a session', () => {
  it('gets out of the way on the screens that own the whole view', () => {
    // A fixed bar would sit over the answer box and the on-screen keyboard,
    // and inviting someone to leave mid-review is not a kindness.
    for (const path of ['/learn', '/review', '/cram', '/gym', '/read', '/tutor']) {
      const { unmount } = renderAt(<BottomNav />, path)
      expect(screen.queryByTestId('bottom-nav')).toBeNull()
      unmount()
    }
  })

  it('still shows on the four section routes', () => {
    for (const path of ['/', '/practice', '/progress', '/more']) {
      const { unmount } = renderAt(<BottomNav />, path)
      expect(screen.getByTestId('bottom-nav')).toBeInTheDocument()
      unmount()
    }
  })
})

describe('Reaching the four sections without a tab bar', () => {
  beforeEach(() => vi.clearAllMocks())

  // BottomNav is md:hidden, on the stated grounds that "the header's inline
  // nav already does this job" on desktop. It did not — that row lists
  // Decks, Tutor, Read, Gym, Search and Account, which are destinations
  // INSIDE the sections, not the sections. So a desktop learner could not
  // open Practice, Progress or More at all, and the Study page looked
  // abandoned because most of what used to be on it had moved there.
  it('offers every section from a section page', async () => {
    renderAt(<PracticePage />)
    expect(await screen.findByTestId('section-nav')).toBeInTheDocument()
    for (const id of [
      'section-study', 'section-practice', 'section-progress', 'section-more',
    ]) {
      expect(screen.getByTestId(id)).toBeInTheDocument()
    }
  })

  it('marks the section you are actually in', async () => {
    renderAt(<MorePage />, '/more')
    await screen.findByTestId('section-nav')
    expect(screen.getByTestId('section-more')).toHaveAttribute('aria-current', 'page')
    // '/' is a prefix of everything, so Study must be compared exactly.
    expect(screen.getByTestId('section-study')).not.toHaveAttribute('aria-current')
  })

  it('navigates between sections', async () => {
    renderAt(<PracticePage />, '/practice')
    await screen.findByTestId('section-nav')
    fireEvent.click(screen.getByTestId('section-progress'))
    expect(mockNavigate).toHaveBeenCalledWith('/progress')
  })
})

describe('The interface-language escape hatch', () => {
  it('puts the globe on every section', async () => {
    // Someone stranded in a language they cannot read has to be able to
    // change it from wherever they are — they cannot navigate to a
    // specific page for it, because they cannot read the way there.
    for (const ui of [<PracticePage key="p" />, <MorePage key="m" />]) {
      const { unmount } = renderAt(ui)
      expect(
        await screen.findByTestId('ui-language-switcher'),
      ).toBeInTheDocument()
      unmount()
    }
  })

  it('does not put the STUDY language picker on every section', async () => {
    // A different kind of choice: deliberate, infrequent, and legible by
    // definition. It belongs on Study, not following the learner around.
    for (const ui of [<PracticePage key="p" />, <MorePage key="m" />]) {
      const { unmount } = renderAt(ui)
      await screen.findByTestId('ui-language-switcher')
      expect(screen.queryByTestId('language-picker')).toBeNull()
      unmount()
    }
  })
})

describe('ProgressPage empty state', () => {
  it('explains itself instead of rendering a column of zeros', async () => {
    const { getDashboardStats } = await import('../api/dashboard')
    vi.mocked(getDashboardStats).mockResolvedValue({
      streak_days: 0,
      cefr_progress: { A1: { learned: 0, total: 10 } },
      forecast: [{ date: '2026-08-05', count: 0 }],
      activity: [{ date: '2026-08-05', vocab: 0, grammar: 0 }],
      stages: { vocab: { Beginner: 0 }, grammar: { Beginner: 0 } },
      profile: { items_studied: 0 },
    } as never)
    const { default: ProgressPage } = await import('../features/dashboard/ProgressPage')
    renderAt(<ProgressPage />)
    expect(await screen.findByTestId('progress-empty')).toBeInTheDocument()
  })

  it('shows the real cards as soon as anything has been studied', async () => {
    const { getDashboardStats } = await import('../api/dashboard')
    vi.mocked(getDashboardStats).mockResolvedValue({
      streak_days: 2,
      cefr_progress: { A1: { learned: 4, total: 10 } },
      forecast: [{ date: '2026-08-05', count: 3 }],
      activity: [{ date: '2026-08-05', vocab: 2, grammar: 1 }],
      stages: { vocab: { Beginner: 4 }, grammar: { Beginner: 1 } },
      profile: { items_studied: 7 },
    } as never)
    const { default: ProgressPage } = await import('../features/dashboard/ProgressPage')
    renderAt(<ProgressPage />)
    await waitFor(() =>
      expect(screen.queryByTestId('progress-empty')).toBeNull(),
    )
  })
})
