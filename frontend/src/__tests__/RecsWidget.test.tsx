import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type React from 'react'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))

vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn((sel: (s: Record<string, unknown>) => unknown) =>
    sel({ activeLanguageId: 'lang-es' }),
  ),
}))

vi.mock('../api/recommendations', async (orig) => ({
  ...(await orig<typeof import('../api/recommendations')>()),
  getRecommendations: vi.fn(),
}))

import RecsWidget from '../features/dashboard/RecsWidget'
import { getRecommendations } from '../api/recommendations'

const mockGet = getRecommendations as ReturnType<typeof vi.fn>

function renderWidget(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const ITEMS = [
  { type: 'book', title: 'Cien años de soledad', creator: 'García Márquez',
    year: '1967', blurb: 'A family saga.', why: 'Magical realism at your B1.',
    level: 'B1' },
  { type: 'podcast', title: 'Radio Ambulante', blurb: 'Stories.',
    why: 'Clear narration.', level: 'B1' },
]

function state(over: Record<string, unknown> = {}) {
  return {
    enabled: true,
    entitled: true,
    stale: false,
    batches: [
      { id: 'b1', items: ITEMS, level: 'B1', created_at: '2026-08-30T00:00:00Z' },
      // An older batch that must NOT be what the widget shows.
      { id: 'b0', items: [{ ...ITEMS[0], title: 'Last week’s pick' }],
        level: 'B1', created_at: '2026-08-23T00:00:00Z' },
    ],
    ...over,
  }
}

describe('the picks widget', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGet.mockResolvedValue(state())
  })

  it('scrolls the LATEST batch, not the whole history', async () => {
    renderWidget(<RecsWidget />)
    expect(await screen.findByText('Cien años de soledad')).toBeInTheDocument()
    expect(screen.getByText('Radio Ambulante')).toBeInTheDocument()
    // The previous week's batch belongs on the page, not in the glance.
    expect(screen.queryByText('Last week’s pick')).not.toBeInTheDocument()
  })

  it('is a real scroll region, reachable without a mouse', async () => {
    renderWidget(<RecsWidget />)
    const scroll = await screen.findByTestId('recs-scroll')
    expect(scroll.className).toContain('overflow-x-auto')
    expect(scroll.getAttribute('tabindex')).toBe('0')
    expect(scroll.getAttribute('aria-label')).toBeTruthy()
  })

  it('opens the full page from a card', async () => {
    renderWidget(<RecsWidget />)
    fireEvent.click(await screen.findByText('Cien años de soledad'))
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/recommendations'),
    )
  })

  it('ends the scroll with a way in rather than a wall', async () => {
    renderWidget(<RecsWidget />)
    fireEvent.click(await screen.findByTestId('recs-see-all'))
    expect(mockNavigate).toHaveBeenCalledWith('/recommendations')
  })

  it('points at the setting when picks are switched off', async () => {
    mockGet.mockResolvedValue(state({ enabled: false, batches: [] }))
    renderWidget(<RecsWidget />)
    expect(await screen.findByText(/turn on recommendations/i)).toBeInTheDocument()
    expect(screen.queryByTestId('recs-scroll')).not.toBeInTheDocument()
  })

  it('never pitches a price at an unentitled account', async () => {
    // The monetization master switch may be off entirely; a widget slot owes
    // the reader a direction, not an upsell.
    mockGet.mockResolvedValue(state({ entitled: false, batches: [] }))
    renderWidget(<RecsWidget />)
    await screen.findByText(/turn on recommendations/i)
    expect(screen.queryByText(/plus/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/upgrade/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument()
  })

  it('says a draft is running rather than showing an empty row', async () => {
    mockGet.mockResolvedValue(state({ batches: [], generating: true }))
    renderWidget(<RecsWidget />)
    expect(await screen.findByText(/putting together/i)).toBeInTheDocument()
  })

  it('says so plainly when there are no picks yet', async () => {
    mockGet.mockResolvedValue(state({ batches: [] }))
    renderWidget(<RecsWidget />)
    expect(await screen.findByText(/no recommendations yet/i)).toBeInTheDocument()
  })

  it('survives a batch whose items are missing entirely', async () => {
    // The server has shipped batches without items before; a widget that
    // throws takes the whole Study page with it.
    mockGet.mockResolvedValue(
      state({ batches: [{ id: 'b1', level: null, created_at: 'x' }] }),
    )
    renderWidget(<RecsWidget />)
    expect(await screen.findByText(/no recommendations yet/i)).toBeInTheDocument()
  })
})
