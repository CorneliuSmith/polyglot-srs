import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
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
  getLearnDecks: vi.fn(() => Promise.resolve([])),
  getVocabItem: vi.fn(() =>
    Promise.resolve({ word: 'hola', part_of_speech: 'interj', definition: 'hi', morphology: null, examples: [] }),
  ),
  setDeckSubscription: vi.fn(() => Promise.resolve()),
}))
vi.mock('../api/curriculum', () => ({ getCurriculumPoint: vi.fn() }))
// Spread the real contribute module so SuggestChange's helpers exist; only
// stub the network calls and make the caller staff.
vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getMyRoles: vi.fn(() =>
    Promise.resolve({ roles: [{ role: 'reviewer', language_id: null }], is_admin: false }),
  ),
  flagPointIssue: vi.fn(),
  createChangeRequest: vi.fn(() => Promise.resolve({ id: 'cr-1' })),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(() => Promise.resolve([{ id: 'lang-es', code: 'es', name: 'Spanish' }])),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-es'),
}))

import { getDeckItems } from '../api/review'
const mockItems = getDeckItems as ReturnType<typeof vi.fn>

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

describe('DeckDetailPage inline suggestion (staff)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockItems.mockResolvedValue({
      id: 'deck-1', title: 'A1 Vocab', list_type: 'vocabulary', level: 'A1',
      items: [{ id: 'v1', kind: 'vocabulary', item: 'hola', detail: 'hi', level: 'A1', reviewed: true }],
    })
  })

  it('offers "Suggest a change" on an expanded vocab row', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /hola/i }))
    expect(
      await screen.findByRole('button', { name: /suggest a change/i }),
    ).toBeDefined()
  })
})
