import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import DecksPage from '../features/decks/DecksPage'
import AiTopicsPanel from '../features/contribute/AiTopicsPanel'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/review', () => ({
  getLearnDecks: vi.fn(),
  getTopicSummary: vi.fn(),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(() => Promise.resolve([{ id: 'lang-es', code: 'es', name: 'Spanish' }])),
  getProfile: vi.fn(() => Promise.resolve({ plan_scope: 'all' })),
  updateProfile: vi.fn(() => Promise.resolve()),
}))
vi.mock('../api/personalDecks', () => ({
  getPersonalDecks: vi.fn(() => Promise.resolve([])),
  getPersonalCards: vi.fn(() => Promise.resolve([])),
  createPersonalDeck: vi.fn(),
  deletePersonalDeck: vi.fn(),
  renamePersonalDeck: vi.fn(),
  filePersonalCard: vi.fn(),
}))
vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getAiTopics: vi.fn(),
  bulkConfirmTopics: vi.fn(() => Promise.resolve(3)),
  bulkRejectTopics: vi.fn(() => Promise.resolve(3)),
  confirmVocabTopic: vi.fn(() => Promise.resolve()),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-es'),
}))

import { getLearnDecks, getTopicSummary } from '../api/review'
import { bulkConfirmTopics, getAiTopics } from '../api/contribute'

const mockDecks = getLearnDecks as ReturnType<typeof vi.fn>
const mockTopics = getTopicSummary as ReturnType<typeof vi.fn>
const mockAiTopics = getAiTopics as ReturnType<typeof vi.fn>

const LEVEL_DECKS = [
  { id: 'deck-1', list_type: 'vocabulary', level: 'A1', title: 'A1 Vocab',
    total: 20, learned: 5, subscribed: true },
]
const TOPICS = [
  { topic: 'travel_transport', total: 30, learned: 2 },
  { topic: 'food_drink', total: 40, learned: 3 },
]

function renderWith(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('the Topic Lens on the Decks page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDecks.mockResolvedValue(LEVEL_DECKS)
    mockTopics.mockResolvedValue(TOPICS)
  })

  it('offers no toggle for a course with no sorted words', async () => {
    // A language whose classification hasn't run looks exactly like today.
    mockTopics.mockResolvedValue([])
    renderWith(<DecksPage />)
    expect(await screen.findByText('A1 Vocab')).toBeInTheDocument()
    expect(screen.queryByTestId('deck-view-toggle')).not.toBeInTheDocument()
  })

  it('swaps the vocabulary section to topic decks, in display order', async () => {
    renderWith(<DecksPage />)
    fireEvent.click(await screen.findByRole('tab', { name: /by topic/i }))
    expect(await screen.findByTestId('topic-card-food_drink')).toBeInTheDocument()
    // Food before travel — the curriculum's everyday-first order, not the
    // server's alphabetical one.
    const cards = screen.getAllByTestId(/topic-card-/)
    expect(cards[0].getAttribute('data-testid')).toBe('topic-card-food_drink')
    // The level cards are gone until toggled back; grammar has no topics
    // and level view returns intact.
    expect(screen.queryByText('A1 Vocab')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: /by level/i }))
    expect(await screen.findByText('A1 Vocab')).toBeInTheDocument()
  })

  it('a topic deck learns through the topic-scoped route', async () => {
    renderWith(<DecksPage />)
    fireEvent.click(await screen.findByRole('tab', { name: /by topic/i }))
    const card = await screen.findByTestId('topic-card-food_drink')
    fireEvent.click(card.querySelector('button')!)
    expect(mockNavigate).toHaveBeenCalledWith(
      '/learn?type=vocabulary&topic=food_drink',
    )
  })
})

describe('the topic review panel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAiTopics.mockResolvedValue({
      counts: [{ topic: 'food_drink', pending: 3 }],
      words: [{ id: 'v1', word: 'pan', part_of_speech: 'noun',
                topic: 'food_drink', definition: 'bread' }],
      can_publish: true,
    })
  })

  it('renders nothing at all when nothing is pending', async () => {
    mockAiTopics.mockResolvedValue({ counts: [], words: [], can_publish: true })
    renderWith(<AiTopicsPanel languageId="lang-es" />)
    await waitFor(() => expect(mockAiTopics).toHaveBeenCalled())
    expect(screen.queryByTestId('ai-topics-panel')).not.toBeInTheDocument()
  })

  it('a reviewer opens a bucket, reads its words, and signs it', async () => {
    renderWith(<AiTopicsPanel languageId="lang-es" />)
    expect(await screen.findByText('3 pending')).toBeInTheDocument()
    // Sample before signing: the words are behind the bucket header.
    fireEvent.click(screen.getByRole('button', { name: /food & drink/i }))
    expect(await screen.findByText('pan')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('topics-confirm-food_drink'))
    await waitFor(() =>
      expect(bulkConfirmTopics).toHaveBeenCalledWith('lang-es', 'food_drink'),
    )
  })

  it('a tester sees the queue but holds no controls', async () => {
    mockAiTopics.mockResolvedValue({
      counts: [{ topic: 'food_drink', pending: 3 }],
      words: [], can_publish: false,
    })
    renderWith(<AiTopicsPanel languageId="lang-es" />)
    await screen.findByTestId('ai-topics-panel')
    expect(screen.queryByTestId('topics-confirm-food_drink')).not.toBeInTheDocument()
    expect(screen.queryByTestId('topics-reject-all')).not.toBeInTheDocument()
  })
})
