import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ReviewSessionPage from '../features/review/ReviewSessionPage'
import type { DueCard, ValidateAnswerResponse, SubmitReviewResponse } from '../api/types'

// Mock the API modules
vi.mock('../api/review', () => ({
  getDueCards: vi.fn(),
  getCramCards: vi.fn(),
  validateAnswer: vi.fn(),
  submitReview: vi.fn(),
}))

// Mock the prefs store
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-123'),
}))

// Stub SpeakButton so tests can assert WHAT text each player would speak
// (the real one only reveals it by fetching audio on click).
vi.mock('../components/SpeakButton', () => ({
  default: ({ text, label }: { text: string; label?: string }) => (
    <button aria-label={label ?? 'speak'} data-text={text} />
  ),
}))

import { getCramCards, getDueCards, validateAnswer, submitReview } from '../api/review'
import { usePrefsStore } from '../stores/prefsStore'

const mockGetDueCards = getDueCards as ReturnType<typeof vi.fn>
const mockGetCramCards = getCramCards as ReturnType<typeof vi.fn>
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

describe('ReviewSessionPage — listening mode cue', () => {
  const listeningCard: DueCard = {
    ...testCard,
    hint: 'go — habit (she)',
    translation: 'She goes to the market.',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    // listeningMode on, no hint dots pressed — the cue must still show.
    mockUsePrefsStore.mockImplementation(
      (selector: (s: Record<string, unknown>) => unknown) =>
        selector({
          activeLanguageId: 'lang-123',
          listeningMode: true,
          hintLevel: 0,
          qwertyTranslit: {},
        }),
    )
    mockGetDueCards.mockResolvedValue([listeningCard])
    mockValidateAnswer.mockResolvedValue(mockValidateResponse)
    mockSubmitReview.mockResolvedValue(mockSubmitResponse)
  })

  it('reveals the expected-word hint by default while listening', async () => {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => {
      expect(screen.getByTestId('listening-drill')).toBeDefined()
    })
    // The drill hint (what to type) shows without pressing Hint…
    expect(screen.getByText('go — habit (she)')).toBeDefined()
    // …but the sentence itself stays hidden,
    expect(screen.queryByText(/to the market/)).toBeNull()
    // and the unrevealed translation layer stays hidden too.
    expect(screen.queryByText('She goes to the market.')).toBeNull()
  })

  it('shows the sentence SHAPE with the blank in place (beta report)', async () => {
    // Words hidden + gapped audio left nothing marking WHERE the missing
    // word falls — the skeleton masks every word but keeps the blank.
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => {
      expect(screen.getByTestId('listening-skeleton')).toBeDefined()
    })
    const skeleton = screen.getByTestId('listening-skeleton')
    expect(skeleton.textContent).toContain('▬▬')
    expect(skeleton.textContent).toContain('___')
    // no real words leak through the mask
    expect(skeleton.textContent).not.toMatch(/market|she|goes/i)
  })

  it('a failed answer check surfaces an error instead of dying silently', async () => {
    mockValidateAnswer.mockRejectedValue(new Error('network'))
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'anything' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(
      await screen.findByText(/couldn't check that answer/i),
    ).toBeDefined()
  })

  it('switching the ACTIVE language mid-session restarts with that language', async () => {
    // Beta bug: a session started in English kept serving English cards
    // under a "Swahili" label. The session must remount + refetch when the
    // active language changes.
    let lang = 'lang-english'
    mockUsePrefsStore.mockImplementation(
      (selector: (s: Record<string, unknown>) => unknown) =>
        selector({
          activeLanguageId: lang,
          listeningMode: false,
          hintLevel: 0,
          qwertyTranslit: {},
          sessionSize: 20,
          accentsOptional: false,
          setListeningMode: vi.fn(),
          setHintLevel: vi.fn(),
          setQwertyTranslit: vi.fn(),
        }),
    )
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const tree = (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ReviewSessionPage />
        </MemoryRouter>
      </QueryClientProvider>
    )
    const { rerender } = render(tree)
    await waitFor(() => {
      expect(mockGetDueCards.mock.calls.some((c) => c[0] === 'lang-english')).toBe(true)
    })
    lang = 'lang-swahili'
    rerender(tree)
    await waitFor(() => {
      expect(mockGetDueCards.mock.calls.some((c) => c[0] === 'lang-swahili')).toBe(true)
    })
  })

  it('answering-phase audio speaks the GAPPED sentence — never the answer', async () => {
    // Beta round 2: the full-sentence audio both leaked the answer and gave
    // no clue which word was missing. The pause marks the blank by ear.
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => {
      expect(screen.getByTestId('listening-player')).toBeDefined()
    })
    const player = screen.getByLabelText('Play the sentence')
    expect(player.getAttribute('data-text')).toBe('She … to the market.')
    expect(player.getAttribute('data-text')).not.toContain('goes')
  })
})

describe('ReviewSessionPage — Quick Cram (WP13f)', () => {
  const cramCard: DueCard = {
    ...testCard,
    id: 'cram-grammar-abc-0',
  }

  function renderCram() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/cram?points=p1,p2']}>
          <ReviewSessionPage cram />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUsePrefsStore.mockImplementation(
      (selector: (s: { activeLanguageId: string }) => unknown) =>
        selector({ activeLanguageId: 'lang-123' }),
    )
    mockGetCramCards.mockResolvedValue([cramCard])
    mockValidateAnswer.mockResolvedValue(mockValidateResponse)
    mockSubmitReview.mockResolvedValue(mockSubmitResponse)
  })

  it('drills the requested points and NEVER submits a review', async () => {
    renderCram()
    await waitFor(() => screen.getByRole('textbox'))
    expect(mockGetCramCards).toHaveBeenCalledWith(['p1', 'p2'])
    expect(mockGetDueCards).not.toHaveBeenCalled()
    expect(screen.getByText(/quick cram · not recorded/i)).toBeDefined()

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => screen.getByTestId('feedback-panel'))
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Summary reached, and the whole session stayed off the books.
    await waitFor(() => {
      expect(screen.getByText('Session Complete')).toBeDefined()
    })
    expect(screen.getByText(/nothing was recorded/i)).toBeDefined()
    expect(mockSubmitReview).not.toHaveBeenCalled()
  })

  it('shows the cram-specific empty state when the points have no drills', async () => {
    mockGetCramCards.mockResolvedValue([])
    renderCram()
    await waitFor(() => {
      expect(screen.getByText(/nothing to cram/i)).toBeDefined()
    })
  })
})

describe('ReviewSessionPage — Gym chart peek (WP25c)', () => {
  const gymCard: DueCard = {
    ...testCard,
    id: 'cram-grammar-abc-0',
    sentence: 'Я {{answer}} музыку.',
    correct_answer: 'слушаю',
    language_code: 'ru',
    morphology: {
      charts: [{ title: 'Present', rows: [['я', 'слушаю'], ['ты', 'слушаешь']] }],
    },
    chart_word: 'слушать',
    chart_usage_note: 'Imperfective; the pair of послушать.',
  }

  function renderCram() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/cram?points=p1&mix=1']}>
          <ReviewSessionPage cram />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
    // qwertyTranslit must exist: the ru card mounts the translit hook.
    mockUsePrefsStore.mockImplementation(
      (selector: (s: Record<string, unknown>) => unknown) =>
        selector({
          activeLanguageId: 'lang-123',
          listeningMode: false,
          hintLevel: 0,
          qwertyTranslit: {},
        }),
    )
    mockGetCramCards.mockResolvedValue([gymCard])
    mockValidateAnswer.mockResolvedValue(mockValidateResponse)
    mockSubmitReview.mockResolvedValue(mockSubmitResponse)
  })

  it('chart is hidden until peeked, then shows forms + deviation note', async () => {
    renderCram()
    const peek = await screen.findByRole('button', {
      name: /peek at the chart — слушать/i,
    })
    // Hidden initially — the whole point of the collapsed panel.
    expect(screen.queryByTestId('gym-chart')).toBeNull()

    fireEvent.click(peek)
    expect(screen.getByTestId('gym-chart')).toBeDefined()
    expect(screen.getByText('слушаешь')).toBeDefined()
    expect(screen.getByText(/imperfective; the pair of/i)).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /hide the chart/i }))
    expect(screen.queryByTestId('gym-chart')).toBeNull()
  })

  it('graded reviews never offer the peek (it would leak the answer)', async () => {
    mockGetDueCards.mockResolvedValue([{ ...gymCard, id: 'card-real' }])
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))
    expect(screen.queryByText(/peek at the chart/i)).toBeNull()
  })
})
