import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PersonalDecksSection from '../features/decks/PersonalDecksSection'

vi.mock('../api/personalDecks', () => ({
  getPersonalDecks: vi.fn(),
  getPersonalCards: vi.fn(),
  createPersonalDeck: vi.fn(),
  renamePersonalDeck: vi.fn(),
  deletePersonalDeck: vi.fn(),
  filePersonalCard: vi.fn(),
}))

import {
  createPersonalDeck,
  filePersonalCard,
  getPersonalCards,
  getPersonalDecks,
} from '../api/personalDecks'

const mockGetDecks = getPersonalDecks as ReturnType<typeof vi.fn>
const mockGetCards = getPersonalCards as ReturnType<typeof vi.fn>
const mockCreate = createPersonalDeck as ReturnType<typeof vi.fn>
const mockFile = filePersonalCard as ReturnType<typeof vi.fn>

function renderSection() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <PersonalDecksSection languageId="lang-tr" />
    </QueryClientProvider>,
  )
}

describe('PersonalDecksSection', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders nothing when there are no decks and no personal cards', async () => {
    mockGetDecks.mockResolvedValue([])
    mockGetCards.mockResolvedValue([])
    renderSection()
    await waitFor(() => expect(mockGetCards).toHaveBeenCalled())
    expect(screen.queryByTestId('personal-decks')).toBeNull()
  })

  it('groups cards by deck and always shows an Unfiled bucket', async () => {
    mockGetDecks.mockResolvedValue([
      { id: 'd1', name: 'K-dramas', card_count: 1 },
    ])
    mockGetCards.mockResolvedValue([
      { id: 'c1', answer: 'başkent', sentence: '{{answer}} büyük', translation: null, deck_id: 'd1' },
      { id: 'c2', answer: 'müze', sentence: '{{answer}} açık', translation: null, deck_id: null },
    ])
    renderSection()
    expect(await screen.findByText('K-dramas')).toBeDefined()
    expect(screen.getByText('Unfiled')).toBeDefined()
  })

  it('creates a deck from the name field', async () => {
    mockGetDecks.mockResolvedValue([])
    mockGetCards.mockResolvedValue([
      { id: 'c1', answer: 'x', sentence: '{{answer}}', translation: null, deck_id: null },
    ])
    mockCreate.mockResolvedValue({ id: 'd-new' })
    renderSection()
    await screen.findByTestId('personal-decks')
    fireEvent.change(screen.getByPlaceholderText(/new deck name/i), {
      target: { value: 'Songs' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^create$/i }))
    await waitFor(() =>
      expect(mockCreate).toHaveBeenCalledWith('lang-tr', 'Songs'),
    )
  })

  it('files a card into a deck via its dropdown', async () => {
    mockGetDecks.mockResolvedValue([{ id: 'd1', name: 'K-dramas', card_count: 0 }])
    mockGetCards.mockResolvedValue([
      { id: 'c2', answer: 'müze', sentence: '{{answer}} açık', translation: null, deck_id: null },
    ])
    mockFile.mockResolvedValue(undefined)
    renderSection()
    fireEvent.click(await screen.findByText('Unfiled'))
    fireEvent.change(await screen.findByLabelText(/deck for müze/i), {
      target: { value: 'd1' },
    })
    await waitFor(() => expect(mockFile).toHaveBeenCalledWith('c2', 'd1'))
  })
})
