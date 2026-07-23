import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
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

  it('shows a tutor+ upsell when enabled but not entitled', async () => {
    mockGet.mockResolvedValue({ enabled: true, entitled: false, stale: true, batches: [] })
    renderPage()
    expect(await screen.findByText(/tutor\+ feature/i)).toBeDefined()
    // Never auto-generates without entitlement.
    expect(mockRefresh).not.toHaveBeenCalled()
  })

  it('auto-drafts this week when due, then shows the picks', async () => {
    mockGet.mockResolvedValue({ enabled: true, entitled: true, stale: true, batches: [] })
    mockRefresh.mockResolvedValue({ generated: true, batch })
    renderPage()
    await waitFor(() => expect(mockRefresh).toHaveBeenCalledWith('lang-es'))
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
