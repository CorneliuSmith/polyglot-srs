import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import DecksPage from '../features/decks/DecksPage'

vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => vi.fn(),
}))
vi.mock('../api/review', () => ({
  getLearnDecks: vi.fn(),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(() => Promise.resolve([{ id: 'lang-es', code: 'es', name: 'Spanish' }])),
  getProfile: vi.fn(() => Promise.resolve({ plan_scope: 'all' })),
  updateProfile: vi.fn(() => Promise.resolve()),
}))
vi.mock('../api/personalDecks', () => ({
  getPersonalDecks: vi.fn(() => Promise.resolve([{ id: 'pd-1', name: 'My deck' }])),
  getPersonalCards: vi.fn(() =>
    Promise.resolve([
      // Regression: a card whose sentence is null used to crash the row with
      // "Cannot read properties of null (reading 'replace')" once expanded.
      { id: 'c1', deck_id: 'pd-1', answer: 'hola', sentence: null, translation: null },
    ]),
  ),
  createPersonalDeck: vi.fn(),
  deletePersonalDeck: vi.fn(),
  renamePersonalDeck: vi.fn(),
  filePersonalCard: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-es'),
}))

import { getLearnDecks } from '../api/review'
const mockDecks = getLearnDecks as ReturnType<typeof vi.fn>

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DecksPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DecksPage — imperfect personal-card data', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDecks.mockResolvedValue([
      { id: 'deck-1', list_type: 'vocabulary', level: 'A1', title: 'A1 Vocab', total: 20, learned: 5, subscribed: true },
    ])
  })

  it('expanding a personal deck with a null-sentence card does not crash', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /My deck/i }))
    // The card row renders (answer visible) instead of throwing.
    expect(await screen.findByText('hola')).toBeDefined()
  })
})
