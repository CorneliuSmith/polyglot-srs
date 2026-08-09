import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import RecommendationsPage from '../features/recommendations/RecommendationsPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (sel: (s: Record<string, unknown>) => unknown) =>
      sel({ activeLanguageId: 'lang-es' }),
  ),
}))
vi.mock('../api/recommendations', async (orig) => ({
  ...(await orig<typeof import('../api/recommendations')>()),
  getRecommendations: vi.fn(),
  refreshRecommendations: vi.fn(),
  // The embedded profile editor (RecoSettings) fetches these.
  getRecoProfile: vi.fn(() =>
    Promise.resolve({ enabled: true, about: '', genres: [], media_types: [] }),
  ),
  updateRecoProfile: vi.fn(),
}))

import { getRecommendations, refreshRecommendations } from '../api/recommendations'
const mockGet = getRecommendations as ReturnType<typeof vi.fn>
const mockRefresh = refreshRecommendations as ReturnType<typeof vi.fn>

const batch = {
  id: 'b1',
  level: 'B1',
  created_at: '2026-07-20T00:00:00Z',
  items: [
    { type: 'book', title: 'Cien años', creator: 'GGM', year: '1967',
      blurb: 'A classic novel.', why: 'Matches your love of history.', level: 'B1' },
    { type: 'film', title: 'Roma', creator: 'Cuarón', year: '2018',
      blurb: 'A tender drama.', why: 'Clear dialogue at your level.', level: 'B1' },
  ],
}

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RecommendationsPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('prompts to set it up when the feature is off', async () => {
    mockGet.mockResolvedValue({ enabled: false, entitled: false, stale: true, batches: [] })
    renderPage()
    expect(await screen.findByText(/set it up in settings/i)).toBeDefined()
    expect(mockRefresh).not.toHaveBeenCalled()
  })

  it('shows a Plus upsell when enabled but not entitled', async () => {
    mockGet.mockResolvedValue({ enabled: true, entitled: false, stale: true, batches: [] })
    renderPage()
    expect(await screen.findByText(/Plus feature/i)).toBeDefined()
    // Never auto-generates without entitlement.
    expect(mockRefresh).not.toHaveBeenCalled()
  })

  it('auto-drafts this week when due, then shows the picks', async () => {
    mockGet.mockResolvedValue({ enabled: true, entitled: true, stale: true, batches: [] })
    mockRefresh.mockResolvedValue({ generated: true, batch })
    renderPage()
    // force=false: the passive weekly draft, which the server no-ops when a
    // batch isn't actually due.
    await waitFor(() => expect(mockRefresh).toHaveBeenCalledWith('lang-es', false))
  })

  it('offers picks on demand, without waiting out the weekly window', async () => {
    mockGet.mockResolvedValue({
      enabled: true, entitled: true, stale: false, batches: [batch],
    })
    mockRefresh.mockResolvedValue({ generated: true, batch })
    renderPage()

    const button = await screen.findByTestId('reco-refresh-now')
    fireEvent.click(button)
    // force=true — bypasses staleness so the learner gets something now.
    await waitFor(() =>
      expect(mockRefresh).toHaveBeenCalledWith('lang-es', true),
    )
  })

  it('invites a first batch rather than saying there is nothing', async () => {
    mockGet.mockResolvedValue({
      enabled: true, entitled: true, stale: false, batches: [],
    })
    renderPage()
    expect(await screen.findByText('Get my picks')).toBeDefined()
  })

  it('offers no on-demand button without entitlement', async () => {
    mockGet.mockResolvedValue({
      enabled: true, entitled: false, stale: false, batches: [],
    })
    renderPage()
    await screen.findByText(/Plus feature/i)
    expect(screen.queryByTestId('reco-refresh-now')).toBeNull()
  })

  it('explains a rate-limited on-demand request instead of failing silently', async () => {
    mockGet.mockResolvedValue({
      enabled: true, entitled: true, stale: false, batches: [batch],
    })
    mockRefresh.mockRejectedValue({ response: { status: 429 } })
    renderPage()

    fireEvent.click(await screen.findByTestId('reco-refresh-now'))
    expect(
      await screen.findByText(/asked for a few fresh batches already/i),
    ).toBeDefined()
  })

  it('embeds the taste-profile editor — the same data Settings edits', async () => {
    /* Owner: "info in their profile should match what they said in their
     * profile and vice-versa" — one component, one API, two surfaces. */
    mockGet.mockResolvedValue({
      enabled: true, entitled: true, stale: false, batches: [batch],
    })
    renderPage()
    expect(await screen.findByText('Cien años')).toBeDefined()
    expect(await screen.findByText(/about you/i)).toBeDefined()
  })

  it('renders the current batch and history', async () => {
    const older = { ...batch, id: 'b0', created_at: '2026-07-10T00:00:00Z' }
    mockGet.mockResolvedValue({
      enabled: true, entitled: true, stale: false, batches: [batch, older],
    })
    renderPage()
    expect(await screen.findByText(/this week’s picks/i)).toBeDefined()
    // Title appears in both the current batch and the (identical) history one.
    expect(screen.getAllByText('Cien años').length).toBe(2)
    expect(screen.getByText(/earlier recommendations/i)).toBeDefined()
    // Not stale → no auto-generate.
    expect(mockRefresh).not.toHaveBeenCalled()
  })
})
