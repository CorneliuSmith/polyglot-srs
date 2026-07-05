import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ReviewSessionPage from '../features/review/ReviewSessionPage'
import type { DueCard, ValidateAnswerResponse, SubmitReviewResponse } from '../api/types'

// Mock the API modules
vi.mock('../api/review', () => ({
  getDueCards: vi.fn(),
  validateAnswer: vi.fn(),
  submitReview: vi.fn(),
}))

// Mock the prefs store
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-123'),
}))

import { getDueCards, validateAnswer, submitReview } from '../api/review'
import { usePrefsStore } from '../stores/prefsStore'

const mockGetDueCards = getDueCards as ReturnType<typeof vi.fn>
const mockValidateAnswer = validateAnswer as ReturnType<typeof vi.fn>
const mockSubmitReview = submitReview as ReturnType<typeof vi.fn>
const mockUsePrefsStore = usePrefsStore as unknown as ReturnType<typeof vi.fn>

const testCard: DueCard = {
  id: 'card-abc',
  card_type: 'grammar',
  card_id: 'grammar-abc',
  sentence: 'She {{answer}} to the market.',
  correct_answer: 'goes',
  language_code: 'en',
  morphology: {},
  alternatives: ['go', 'went'],
  ease_factor: 2.5,
  interval: 1,
  repetitions: 0,
  streak: 0,
  lapses: 0,
  next_review: '2026-03-15T00:00:00Z',
}

const mockValidateResponse: ValidateAnswerResponse = {
  answer_result: 'correct',
  feedback: null,
}

const mockSubmitResponse: SubmitReviewResponse = {
  next_review: '2026-03-22T00:00:00Z',
  interval: 7,
  stability: 7.2,
  difficulty: 5.1,
  state: 'review',
  quality: 4,
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReviewSessionPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUsePrefsStore.mockImplementation((selector: (s: { activeLanguageId: string }) => unknown) =>
      selector({ activeLanguageId: 'lang-123' })
    )
    mockGetDueCards.mockResolvedValue([testCard])
    mockValidateAnswer.mockResolvedValue(mockValidateResponse)
    mockSubmitReview.mockResolvedValue(mockSubmitResponse)
  })

  it('shows loading state while fetching cards', () => {
    // getDueCards that never resolves
    mockGetDueCards.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<ReviewSessionPage />)
    expect(screen.getByText(/loading cards/i)).toBeDefined()
  })

  it('shows empty state when no cards are due', async () => {
    mockGetDueCards.mockResolvedValue([])
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => {
      expect(screen.getByText(/no cards due/i)).toBeDefined()
    })
  })

  it('renders the drill card sentence with input', async () => {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => {
      expect(screen.getByText(/to the market/i)).toBeDefined()
    })
    expect(screen.getByRole('textbox')).toBeDefined()
  })

  it('shows progress indicator', async () => {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => {
      expect(screen.getByText(/card 1 of 1/i)).toBeDefined()
    })
  })

  it('calls validateAnswer when answer is submitted', async () => {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      const calls = mockValidateAnswer.mock.calls
      expect(calls.length).toBeGreaterThan(0)
      expect(calls[0][0]).toMatchObject({
        language_code: 'en',
        user_input: 'goes',
        correct_answer: 'goes',
        card_context: {
          morphology: {},
          alternatives: ['go', 'went'],
        },
      })
    })
  })

  it('shows FeedbackPanel after validateAnswer returns', async () => {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      expect(screen.getByTestId('feedback-panel')).toBeDefined()
    })
  })

  it('CRITICAL (REV-03): clicking rating button calls submitReview with correct arguments', async () => {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))

    // Type and submit answer
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    // Wait for feedback panel to appear
    await waitFor(() => {
      expect(screen.getByTestId('feedback-panel')).toBeDefined()
    })

    // Click Continue (auto-records the NLP grade)
    const continueButton = screen.getByRole('button', { name: /continue/i })
    fireEvent.click(continueButton)

    // Verify submitReview called with correct args (REV-03 coverage)
    await waitFor(() => {
      const calls = mockSubmitReview.mock.calls
      expect(calls.length).toBeGreaterThan(0)
      expect(calls[0][0]).toMatchObject({
        card_id: 'card-abc',
        answer_result: 'correct',
        time_taken_ms: expect.any(Number),
      })
    })
  })

  it('a wrong judgement offers Bunpro-style re-entry without recording a grade', async () => {
    mockValidateAnswer.mockResolvedValueOnce({ answer_result: 'wrong', feedback: null })
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'gose' } })  // a slip
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => screen.getByTestId('feedback-panel'))

    fireEvent.click(screen.getByRole('button', { name: /undo/i }))

    // Back to answering the SAME card, previous input restored for editing,
    // and nothing was submitted to the backend.
    const retryInput = await screen.findByRole('textbox')
    expect((retryInput as HTMLInputElement).value).toBe('gose')
    expect(mockSubmitReview).not.toHaveBeenCalled()

    fireEvent.change(retryInput, { target: { value: 'goes' } })
    fireEvent.keyDown(retryInput, { key: 'Enter' })
    await waitFor(() => screen.getByTestId('feedback-panel'))
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => {
      expect(mockSubmitReview).toHaveBeenCalledTimes(1)
      expect(mockSubmitReview.mock.calls[0][0].answer_result).toBe('correct')
    })
  })

  it('shows SessionSummary after all cards are rated', async () => {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => screen.getByTestId('feedback-panel'))

    const continueButton = screen.getByRole('button', { name: /continue/i })
    fireEvent.click(continueButton)

    await waitFor(() => {
      expect(screen.getByText('Session Complete')).toBeDefined()
    })
  })

  it('session summary shows accuracy and cards reviewed', async () => {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => screen.getByTestId('feedback-panel'))
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))

    await waitFor(() => {
      expect(screen.getByTestId('accuracy')).toBeDefined()
      expect(screen.getByTestId('cards-reviewed')).toBeDefined()
    })
  })
})
