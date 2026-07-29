import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

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
  getUnseenRecommendations: vi.fn(),
  markRecommendationsSeen: vi.fn(),
}))

import NewPicksPrompt from '../features/recommendations/NewPicksPrompt'
import {
  getUnseenRecommendations,
  markRecommendationsSeen,
} from '../api/recommendations'

const mockUnseen = getUnseenRecommendations as ReturnType<typeof vi.fn>
const mockSeen = markRecommendationsSeen as ReturnType<typeof vi.fn>

const batch = {
  id: 'b1',
  level: 'B1',
  created_at: '2026-07-26T00:00:00Z',
  items: [
    { type: 'book', title: 'Cien años', blurb: '', why: '', level: 'B1' },
    { type: 'film', title: 'Roma', blurb: '', why: '', level: 'B1' },
    { type: 'podcast', title: 'Radio Ambulante', blurb: '', why: '', level: 'B1' },
  ],
}

function renderPrompt() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <NewPicksPrompt />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('NewPicksPrompt', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSeen.mockResolvedValue(undefined)
  })

  it('says nothing when there is nothing new', async () => {
    mockUnseen.mockResolvedValue(null)
    renderPrompt()
    await waitFor(() => expect(mockUnseen).toHaveBeenCalled())
    expect(screen.queryByTestId('new-picks-prompt')).toBeNull()
  })

  it('surfaces an unseen batch with a preview', async () => {
    mockUnseen.mockResolvedValue(batch)
    renderPrompt()
    expect(await screen.findByTestId('new-picks-prompt')).toBeDefined()
    expect(screen.getByText('Cien años')).toBeDefined()
    expect(screen.getByText('Roma')).toBeDefined()
    // Only two are previewed; the rest are counted, not listed.
    expect(screen.queryByText('Radio Ambulante')).toBeNull()
    expect(screen.getByText(/and 1 more/)).toBeDefined()
  })

  it('opening the picks counts as seeing them', async () => {
    mockUnseen.mockResolvedValue(batch)
    renderPrompt()
    fireEvent.click(await screen.findByText(/See this week’s picks/))
    await waitFor(() => expect(mockSeen).toHaveBeenCalled())
    expect(mockNavigate).toHaveBeenCalledWith('/recommendations')
  })

  it('can be dismissed without opening', async () => {
    mockUnseen.mockResolvedValue(batch)
    renderPrompt()
    fireEvent.click(await screen.findByLabelText(/Dismiss/))
    await waitFor(() => expect(mockSeen).toHaveBeenCalled())
    // Optimistic: it goes away on click, not on the round trip.
    expect(screen.queryByTestId('new-picks-prompt')).toBeNull()
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('renders nothing for an empty batch rather than an empty card', async () => {
    mockUnseen.mockResolvedValue({ ...batch, items: [] })
    renderPrompt()
    await waitFor(() => expect(mockUnseen).toHaveBeenCalled())
    expect(screen.queryByTestId('new-picks-prompt')).toBeNull()
  })

  it('stays quiet when the endpoint fails', async () => {
    // An unavailable prompt must never break the dashboard it sits on.
    mockUnseen.mockRejectedValue(new Error('503'))
    renderPrompt()
    await waitFor(() => expect(mockUnseen).toHaveBeenCalled())
    expect(screen.queryByTestId('new-picks-prompt')).toBeNull()
  })
})
