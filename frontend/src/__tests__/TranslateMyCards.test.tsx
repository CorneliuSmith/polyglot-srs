/**
 * "Not translated, just noted" — labelling the English was only half a fix.
 *
 * A personal card is the learner's own private sentence, so the background
 * auto-translate loop never sweeps it: the fill spends THEIR allowance.
 * The ask existed, but only on the Decks page — which nobody opens while
 * a review card is in front of them, so a flagged card stayed English
 * forever. These pin the ask being available where the gap is noticed,
 * and the two states where offering it would be wrong.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TranslateMyCards from '../features/review/TranslateMyCards'
import {
  getPersonalTranslationStatus,
  translatePersonalCards,
} from '../api/personalDecks'

vi.mock('../api/personalDecks', () => ({
  getPersonalTranslationStatus: vi.fn(),
  translatePersonalCards: vi.fn(),
}))

const mockStatus = vi.mocked(getPersonalTranslationStatus)
const mockTranslate = vi.mocked(translatePersonalCards)

function renderIt() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <TranslateMyCards languageId="lang-1" />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('the ask appears where the gap is noticed', () => {
  it('offers the fill and names the cost before spending it', async () => {
    mockStatus.mockResolvedValue({
      locale: 'ar', pending: 12, available: true, remaining: 40, unlimited: false,
    })
    renderIt()
    const button = await screen.findByTestId('translate-mine')
    // The count is quoted, so one unit visibly buys the whole backlog.
    expect(button.textContent).toContain('12')
    expect(mockTranslate).not.toHaveBeenCalled()
  })

  it('fills on tap and reports what landed', async () => {
    mockStatus.mockResolvedValue({
      locale: 'ar', pending: 12, available: true, remaining: 40, unlimited: false,
    })
    mockTranslate.mockResolvedValue({ translated: 12, charged: true })
    renderIt()
    await userEvent.click(await screen.findByTestId('translate-mine'))
    await waitFor(() => expect(mockTranslate).toHaveBeenCalledWith('lang-1'))
    expect(await screen.findByTestId('translate-mine-done')).toBeInTheDocument()
  })

  it('says so instead of dying when the fill fails', async () => {
    mockStatus.mockResolvedValue({
      locale: 'ar', pending: 3, available: true, remaining: 40, unlimited: false,
    })
    mockTranslate.mockRejectedValue(new Error('503'))
    renderIt()
    await userEvent.click(await screen.findByTestId('translate-mine'))
    await waitFor(() =>
      expect(screen.getByText(/couldn't translate/i)).toBeInTheDocument(),
    )
  })
})

describe('it is not offered when it cannot work', () => {
  it('stays hidden when translation is unavailable', async () => {
    mockStatus.mockResolvedValue({
      locale: 'ar', pending: 5, available: false, remaining: 40, unlimited: false,
    })
    renderIt()
    await waitFor(() => expect(mockStatus).toHaveBeenCalled())
    // A button that cannot work is worse than no button.
    expect(screen.queryByTestId('translate-mine')).not.toBeInTheDocument()
  })

  it('stays hidden when nothing is pending', async () => {
    mockStatus.mockResolvedValue({
      locale: 'ar', pending: 0, available: true, remaining: 40, unlimited: false,
    })
    renderIt()
    await waitFor(() => expect(mockStatus).toHaveBeenCalled())
    expect(screen.queryByTestId('translate-mine')).not.toBeInTheDocument()
  })

  it('survives the status call failing outright', async () => {
    mockStatus.mockRejectedValue(new Error('500'))
    renderIt()
    await waitFor(() => expect(mockStatus).toHaveBeenCalled())
    expect(screen.queryByTestId('translate-mine')).not.toBeInTheDocument()
  })
})
