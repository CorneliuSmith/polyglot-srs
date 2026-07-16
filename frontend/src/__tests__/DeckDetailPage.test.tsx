import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import DeckDetailPage from '../features/decks/DeckDetailPage'

vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useParams: () => ({ deckId: 'deck-1' }),
  useNavigate: () => vi.fn(),
}))
vi.mock('../api/review', () => ({
  getDeckItems: vi.fn(),
  getLearnDecks: vi.fn(),
  getVocabItem: vi.fn(),
  setDeckSubscription: vi.fn(() => Promise.resolve()),
}))
vi.mock('../api/curriculum', () => ({ getCurriculumPoint: vi.fn() }))
vi.mock('../api/contribute', () => ({
  getMyRoles: vi.fn(() => Promise.resolve({ roles: [] })),
  flagPointIssue: vi.fn(),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(() => Promise.resolve([])),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-es'),
}))

import { getDeckItems, getLearnDecks, setDeckSubscription } from '../api/review'

const mockItems = getDeckItems as ReturnType<typeof vi.fn>
const mockDecks = getLearnDecks as ReturnType<typeof vi.fn>
const mockSub = setDeckSubscription as ReturnType<typeof vi.fn>

const listing = {
  id: 'deck-1', title: 'A1 Grammar Path', list_type: 'grammar',
  level: 'A1', items: [],
}

const deckRow = (subscribed: boolean) => ({
  id: 'deck-1', list_type: 'grammar', level: 'A1', title: 'A1 Grammar Path',
  total: 20, learned: 5, subscribed,
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/decks/deck-1']}>
        <DeckDetailPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DeckDetailPage queue button', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockItems.mockResolvedValue(listing)
  })

  it('a deck already in the queue shows In queue, not Add', async () => {
    mockDecks.mockResolvedValue([deckRow(true)])
    renderPage()
    expect(await screen.findByRole('button', { name: /in queue/i })).toBeDefined()
    expect(screen.queryByRole('button', { name: /add to queue/i })).toBeNull()
  })

  it('an unqueued deck shows Add to queue and adds on click', async () => {
    mockDecks.mockResolvedValue([deckRow(false)])
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /add to queue/i }))
    await waitFor(() =>
      expect(mockSub).toHaveBeenCalledWith('deck-1', true),
    )
  })

  it('clicking In queue removes the deck from the queue', async () => {
    mockDecks.mockResolvedValue([deckRow(true)])
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /in queue/i }))
    await waitFor(() =>
      expect(mockSub).toHaveBeenCalledWith('deck-1', false),
    )
  })
})
