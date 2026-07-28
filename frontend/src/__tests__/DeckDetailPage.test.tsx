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
  resetCardProgress: vi.fn(() => Promise.resolve()),
}))
vi.mock('../api/curriculum', () => ({
  getCurriculumPoint: vi.fn(() => Promise.resolve(null)),
}))
vi.mock('../api/contribute', () => ({
  getMyRoles: vi.fn(() => Promise.resolve({ roles: [] })),
  flagPointIssue: vi.fn(),
  canSuggestForLanguage: vi.fn(() => false),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(() => Promise.resolve([])),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-es'),
}))

import {
  getDeckItems,
  getLearnDecks,
  resetCardProgress,
  setDeckSubscription,
} from '../api/review'

const mockItems = getDeckItems as ReturnType<typeof vi.fn>
const mockDecks = getLearnDecks as ReturnType<typeof vi.fn>
const mockSub = setDeckSubscription as ReturnType<typeof vi.fn>
const mockReset = resetCardProgress as ReturnType<typeof vi.fn>

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

describe('DeckDetailPage per-card progress (owner: individual reset)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDecks.mockResolvedValue([deckRow(true)])
    mockItems.mockResolvedValue({
      ...listing,
      items: [
        {
          id: 'gp-new', kind: 'grammar', item: 'New point', detail: null,
          level: 'A1', reviewed: true, status: 'new', user_card_id: null,
        },
        {
          id: 'gp-known', kind: 'grammar', item: 'Known point', detail: null,
          level: 'A1', reviewed: true, status: 'known', user_card_id: 'uc-known',
        },
      ],
    })
  })

  it('shows a status chip only for cards with progress', async () => {
    renderPage()
    await screen.findByText('New point')
    expect(screen.getByText('Known point')).toBeDefined()
    expect(screen.getByText('Known')).toBeDefined()
    // 'New' never renders a chip — nothing to show for a never-learned card.
    expect(screen.queryByText('New')).toBeNull()
  })

  it('offers Reset only once a row with progress is expanded, and calls the API on confirm', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await screen.findByText('Known point')

    // No reset button visible before expanding either row.
    expect(screen.queryByRole('button', { name: /reset progress/i })).toBeNull()

    fireEvent.click(screen.getByText('Known point'))
    const resetBtn = await screen.findByRole('button', { name: /reset progress/i })
    fireEvent.click(resetBtn)

    expect(confirmSpy).toHaveBeenCalled()
    await waitFor(() => expect(mockReset).toHaveBeenCalledWith('uc-known'))

    confirmSpy.mockRestore()
  })

  it('a never-learned card has no Reset button even when expanded', async () => {
    renderPage()
    await screen.findByText('New point')
    fireEvent.click(screen.getByText('New point'))
    // Let the row's detail query settle before asserting absence.
    await waitFor(() => expect(screen.getByText('New point')).toBeDefined())
    expect(screen.queryByRole('button', { name: /reset progress/i })).toBeNull()
  })

  it('does not reset if the confirm dialog is declined', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPage()
    await screen.findByText('Known point')
    fireEvent.click(screen.getByText('Known point'))
    fireEvent.click(await screen.findByRole('button', { name: /reset progress/i }))
    expect(mockReset).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })
})
