import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PersonalDecksSection from '../features/decks/PersonalDecksSection'
import {
  getPersonalDecks,
  getPersonalCards,
  getPersonalTranslationStatus,
  translatePersonalCards,
  createPersonalCard,
  deletePersonalCard,
} from '../api/personalDecks'

vi.mock('../api/personalDecks', () => ({
  getPersonalDecks: vi.fn(),
  getPersonalCards: vi.fn(),
  createPersonalDeck: vi.fn(),
  renamePersonalDeck: vi.fn(),
  deletePersonalDeck: vi.fn(),
  filePersonalCard: vi.fn(),
  getPersonalTranslationStatus: vi.fn(),
  translatePersonalCards: vi.fn(),
  createPersonalCard: vi.fn(),
  deletePersonalCard: vi.fn(),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) =>
      o && 'count' in o ? `${k}:${o.count}` : k,
  }),
  Trans: ({ i18nKey }: { i18nKey: string }) => i18nKey,
}))

const mockDecks = vi.mocked(getPersonalDecks)
const mockCards = vi.mocked(getPersonalCards)
const mockStatus = vi.mocked(getPersonalTranslationStatus)
const mockTranslate = vi.mocked(translatePersonalCards)
const mockCreate = vi.mocked(createPersonalCard)
const mockDelete = vi.mocked(deletePersonalCard)

function renderSection() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  render(
    <QueryClientProvider client={client}>
      <PersonalDecksSection languageId="lang-1" />
    </QueryClientProvider>,
  )
}

const card = {
  id: 'c1',
  answer: 'büyük',
  sentence: 'Bu şehir çok {{answer}}.',
  translation: 'This city is very big.',
  deck_id: null,
}

describe('PersonalDecksSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDecks.mockResolvedValue([])
    mockCards.mockResolvedValue([])
    mockStatus.mockResolvedValue({
      locale: 'es', pending: 0, available: true, remaining: 40, unlimited: false,
    })
  })

  it('shows unfiled cards, so a saved card is never invisible for want of a folder', async () => {
    mockCards.mockResolvedValue([card])
    renderSection()
    // The unfiled group is a real group — cards saved from the Tutor or
    // Reader have no deck, and that must not hide them.
    await userEvent.click(await screen.findByText('decks.unfiled'))
    expect(await screen.findByText('büyük')).toBeInTheDocument()
  })

  it('states the count AND the cost before spending the learner allowance', async () => {
    mockCards.mockResolvedValue([card])
    mockStatus.mockResolvedValue({
      locale: 'es', pending: 3, available: true, remaining: 40, unlimited: false,
    })
    renderSection()

    await screen.findByTestId('personal-translate-offer')
    expect(screen.getByText('decks.translateOffer:3')).toBeInTheDocument()
    // The cost line is not optional — this spends the learner's own quota.
    expect(screen.getByText('decks.translateCost')).toBeInTheDocument()
    expect(mockTranslate).not.toHaveBeenCalled()

    mockTranslate.mockResolvedValue({ translated: 3, charged: true })
    await userEvent.click(screen.getByText('decks.translateAction'))
    await waitFor(() => expect(mockTranslate).toHaveBeenCalledWith('lang-1'))
    expect(await screen.findByTestId('personal-translate-done')).toBeInTheDocument()
  })

  it('offers nothing when every card already reads in the learner language', async () => {
    mockCards.mockResolvedValue([card])
    renderSection()
    await screen.findByTestId('personal-decks')
    expect(screen.queryByTestId('personal-translate-offer')).not.toBeInTheDocument()
  })

  it('offers nothing when no provider is configured', async () => {
    mockCards.mockResolvedValue([card])
    mockStatus.mockResolvedValue({
      locale: 'es', pending: 5, available: false, remaining: 40, unlimited: false,
    })
    renderSection()
    await screen.findByTestId('personal-decks')
    expect(screen.queryByTestId('personal-translate-offer')).not.toBeInTheDocument()
  })

  it('survives the endpoints failing outright (migration not applied)', async () => {
    mockDecks.mockRejectedValue(new Error('500'))
    mockCards.mockRejectedValue(new Error('500'))
    mockStatus.mockRejectedValue(new Error('500'))
    renderSection()
    // Still explains itself rather than taking the dashboard down with it.
    expect(await screen.findByTestId('personal-decks-empty')).toBeInTheDocument()
  })

  it('lets the learner write their own card', async () => {
    mockCards.mockResolvedValue([card])
    mockCreate.mockResolvedValue({ id: 'new-1' })
    renderSection()

    await userEvent.click(await screen.findByTestId('personal-card-add'))
    await userEvent.type(
      screen.getByLabelText('decks.cardSentenceLabel'), 'Bu ev çok guzel.')
    await userEvent.type(screen.getByLabelText('decks.cardAnswerLabel'), 'guzel')
    await userEvent.click(screen.getByText('decks.cardSave'))

    await waitFor(() =>
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({ answer: 'guzel', sentence: 'Bu ev çok guzel.' }),
      ),
    )
  })

  it('will not save a card with no sentence or no answer', async () => {
    mockCards.mockResolvedValue([card])
    renderSection()
    await userEvent.click(await screen.findByTestId('personal-card-add'))

    // Both fields are required — a card missing either cannot be reviewed.
    expect(screen.getByText('decks.cardSave')).toBeDisabled()
    await userEvent.type(
      screen.getByLabelText('decks.cardSentenceLabel'), 'Bu ev guzel.')
    expect(screen.getByText('decks.cardSave')).toBeDisabled()
    await userEvent.type(screen.getByLabelText('decks.cardAnswerLabel'), 'guzel')
    expect(screen.getByText('decks.cardSave')).toBeEnabled()
  })

  it('says what went wrong when the answer is not in the sentence', async () => {
    mockCards.mockResolvedValue([card])
    mockCreate.mockRejectedValue(new Error('422'))
    renderSection()

    await userEvent.click(await screen.findByTestId('personal-card-add'))
    await userEvent.type(
      screen.getByLabelText('decks.cardSentenceLabel'), 'Bu ev guzel.')
    await userEvent.type(screen.getByLabelText('decks.cardAnswerLabel'), 'kitap')
    await userEvent.click(screen.getByText('decks.cardSave'))

    expect(await screen.findByTestId('card-add-error')).toBeInTheDocument()
  })

  it('deletes a card, but only after confirming', async () => {
    mockCards.mockResolvedValue([card])
    mockDelete.mockResolvedValue(undefined)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderSection()

    await userEvent.click(await screen.findByText('decks.unfiled'))
    await userEvent.click(
      await screen.findByLabelText('decks.cardDeleteFor'))
    expect(mockDelete).not.toHaveBeenCalled()

    confirmSpy.mockReturnValue(true)
    await userEvent.click(screen.getByLabelText('decks.cardDeleteFor'))
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('c1'))
    confirmSpy.mockRestore()
  })
})
