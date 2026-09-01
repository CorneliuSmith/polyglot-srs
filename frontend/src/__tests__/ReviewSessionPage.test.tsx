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
  markCardKnown: vi.fn(),
  refreshDueCards: vi.fn(() => Promise.resolve([])),
  // These sessions already read in the learner's language, so the
  // trailblazer wait never stands between them and their cards.
  getTrivia: vi.fn(() => Promise.resolve([])),
  markTriviaSeen: vi.fn(() => Promise.resolve()),
  getSessionReadiness: vi.fn(() =>
    Promise.resolve({
      locale: null,
      new_here: true,
      learn: { total: 0, ready: 0, pct: 1, ready_enough: true },
      review: { total: 0, ready: 0, pct: 1, ready_enough: true },
      pairs: [],
    }),
  ),
}))

// The deck fetch is gated on the profile having RESOLVED (the support
// locale is part of its key — see the C3 note in ReviewSessionPage), so
// the profile must answer deterministically here rather than by whatever
// a jsdom network error happens to do.
vi.mock('../api/audio', async (orig) => ({
  ...(await orig<typeof import('../api/audio')>()),
  // prefetch warms a cache; getTTSUrl is what the on-correct autoplay
  // actually fetches — mocked apart so the tests can tell them apart.
  prefetchTTS: vi.fn(),
  getTTSUrl: vi.fn(() => Promise.resolve(null)),
}))
vi.mock('../api/profile', async (orig) => ({
  ...(await orig<typeof import('../api/profile')>()),
  getLanguages: vi.fn(() => Promise.resolve([])),
  getProfile: vi.fn(() =>
    Promise.resolve({ support_locale: null, ui_language: 'en' }),
  ),
  updateProfile: vi.fn(),
}))

vi.mock('../api/gym', () => ({
  recordGymAttempt: vi.fn(() => Promise.resolve()),
  generateGymDrills: vi.fn(),
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

import {
  getCramCards, getDueCards, getSessionReadiness, markCardKnown, validateAnswer,
  refreshDueCards, submitReview,
} from '../api/review'
import { generateGymDrills } from '../api/gym'
import { getTTSUrl } from '../api/audio'
import { getProfile } from '../api/profile'
import { usePrefsStore } from '../stores/prefsStore'

const mockGenerateGymDrills = generateGymDrills as ReturnType<typeof vi.fn>

const mockGetDueCards = getDueCards as ReturnType<typeof vi.fn>
const mockGetReadiness = getSessionReadiness as ReturnType<typeof vi.fn>
const mockGetCramCards = getCramCards as ReturnType<typeof vi.fn>
const mockValidateAnswer = validateAnswer as ReturnType<typeof vi.fn>
const mockSubmitReview = submitReview as ReturnType<typeof vi.fn>
const mockMarkCardKnown = markCardKnown as ReturnType<typeof vi.fn>
const mockRefreshDueCards = refreshDueCards as ReturnType<typeof vi.fn>
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

  it('Skip moves on without grading — nothing validated or submitted', async () => {
    mockGetDueCards.mockResolvedValue([
      { ...testCard, id: 'c1', sentence: 'First {{answer}}.' },
      { ...testCard, id: 'c2', sentence: 'Second {{answer}}.' },
    ])
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByText(/First/))
    fireEvent.click(screen.getByRole('button', { name: /skip/i }))
    expect(screen.getByText(/Second/)).toBeDefined()
    expect(mockValidateAnswer).not.toHaveBeenCalled()
    expect(mockSubmitReview).not.toHaveBeenCalled()
    // Skipping the last card ends the session.
    fireEvent.click(screen.getByRole('button', { name: /skip/i }))
    await waitFor(() => expect(screen.getByText('Session Complete')).toBeDefined())
  })

  it('Mark-as-known retires the card server-side and advances', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockMarkCardKnown.mockResolvedValue(undefined)
    mockGetDueCards.mockResolvedValue([
      { ...testCard, id: 'c1', sentence: 'First {{answer}}.' },
      { ...testCard, id: 'c2', sentence: 'Second {{answer}}.' },
    ])
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByText(/First/))
    fireEvent.click(screen.getByRole('button', { name: /i know this/i }))
    await waitFor(() => expect(mockMarkCardKnown).toHaveBeenCalledWith('c1'))
    await waitFor(() => expect(screen.getByText(/Second/)).toBeDefined())
    expect(mockSubmitReview).not.toHaveBeenCalled()
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
    // Built FRESH per render: in the app, zustand notifies subscribers and
    // the page re-renders itself. The mocked store has no subscription, so
    // the rerender stands in for it — and rerendering the SAME element lets
    // React bail out of the whole subtree, silently testing nothing. (This
    // test used to pass only because an unmocked profile fetch errored late
    // and forced a stray re-render at the right moment.)
    const makeTree = () => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ReviewSessionPage />
        </MemoryRouter>
      </QueryClientProvider>
    )
    const { rerender } = render(makeTree())
    await waitFor(() => {
      expect(mockGetDueCards.mock.calls.some((c) => c[0] === 'lang-english')).toBe(true)
    })
    lang = 'lang-swahili'
    rerender(makeTree())
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
    expect(mockGetCramCards).toHaveBeenCalledWith(['p1', 'p2'], undefined)
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

  it('restores a parked session (settings round-trip) at its exact position', async () => {
    // A snapshot parked by the ⚙ hop: two cards, the first already answered.
    sessionStorage.setItem(
      // Identity-keyed (language:locale): a park under another identity
      // must not resume — see 'sessionSnapshot.test.ts'. This one matches.
      'review-session:lang-123:en:/cram?points=p1,p2',
      JSON.stringify({
        cards: [
          { ...cramCard, id: 'cram-a', sentence: 'First {{answer}}.' },
          { ...cramCard, id: 'cram-b', sentence: 'Second {{answer}}.' },
        ],
        index: 1,
        results: [{ cardId: 'cram-a', answerResult: 'correct', timeTakenMs: 800 }],
        requeued: [],
        savedAt: Date.now(),
      }),
    )
    try {
      renderCram()
      // Resumes on card 2 of 2 — no refetched deck replaces the parked one.
      await waitFor(() => {
        expect(screen.getByText('Card 2 of 2')).toBeDefined()
      })
      expect(screen.getByText(/Second/)).toBeDefined()
      // The parking spot is single-use: consumed on restore.
      expect(
        sessionStorage.getItem('review-session:lang-123:en:/cram?points=p1,p2'),
      ).toBeNull()
    } finally {
      sessionStorage.clear()
    }
  })

  it('distinguishes the word audio from the full-sentence audio on feedback', async () => {
    renderCram()
    await waitFor(() => screen.getByRole('textbox'))
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => screen.getByTestId('feedback-panel'))
    // The word-pronunciation control and the whole-sentence control are now
    // labelled differently instead of two identical speaker icons.
    expect(screen.getByText('Hear the word')).toBeDefined()
    expect(screen.getByLabelText(/hear the full sentence/i)).toBeDefined()
    expect(screen.getByText('sentence')).toBeDefined()
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

  it('shows the Base form prompt always — no hint press needed', async () => {
    // The base form is the PROMPT for a Gym conjugation drill (the dictionary
    // word you conjugate FROM), so it's always visible in its own slot, even
    // with no hints revealed (hintLevel 0) — revealing it is not a hint.
    mockUsePrefsStore.mockImplementation(
      (selector: (s: Record<string, unknown>) => unknown) =>
        selector({
          activeLanguageId: 'lang-123',
          listeningMode: false,
          hintLevel: 0,
          qwertyTranslit: {},
        }),
    )
    renderCram()
    await screen.findByRole('textbox')
    // The baseline prompt renders below the drill with no hint press.
    expect(await screen.findByTestId('baseline-prompt')).toBeDefined()
  })

  it('opens the full chart automatically after a miss', async () => {
    mockValidateAnswer.mockResolvedValueOnce({ answer_result: 'wrong', feedback: null })
    renderCram()
    const input = await screen.findByRole('textbox')
    fireEvent.change(input, { target: { value: 'wrongword' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    // No peek click needed — the paradigm appears on its own after the miss,
    // and the toggle flips to "Hide the chart".
    await waitFor(() => expect(screen.getByTestId('gym-chart')).toBeDefined())
    expect(screen.getByText('слушаешь')).toBeDefined()
    expect(screen.getByRole('button', { name: /hide the chart/i })).toBeDefined()
  })
})

describe('ReviewSessionPage — background generation (WP41)', () => {
  const d1: DueCard = { ...testCard, id: 'cram-p-0', drill_id: 'd1' }
  const d2: DueCard = {
    ...testCard,
    id: 'cram-p-1',
    drill_id: 'd2',
    sentence: 'They {{answer}} home.',
  }

  function renderGen() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/cram?points=p1&mix=1&count=20&gen=1']}>
          <ReviewSessionPage cram />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  async function answerCurrent() {
    const input = await screen.findByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => screen.getByTestId('feedback-panel'))
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUsePrefsStore.mockImplementation(
      (selector: (s: { activeLanguageId: string }) => unknown) =>
        selector({ activeLanguageId: 'lang-123' }),
    )
    mockValidateAnswer.mockResolvedValue(mockValidateResponse)
    mockSubmitReview.mockResolvedValue(mockSubmitResponse)
  })

  it('kicks off generation in the background for the chosen points', async () => {
    mockGetCramCards.mockResolvedValue([d1])
    mockGenerateGymDrills.mockResolvedValue({
      generated: 0, charged: 0, remaining: 5, unlimited: false,
    })
    renderGen()
    await waitFor(() =>
      expect(mockGenerateGymDrills).toHaveBeenCalledWith(['p1']),
    )
  })

  it('weaves a freshly generated drill into the live session', async () => {
    // First fetch serves the seeded set; the post-generation re-draw (count 100)
    // returns the same drill plus the new one, which gets appended.
    mockGetCramCards.mockResolvedValueOnce([d1]).mockResolvedValue([d1, d2])
    mockGenerateGymDrills.mockResolvedValue({
      generated: 1, charged: 1, remaining: 4, unlimited: false,
    })
    renderGen()
    // Answer the one seeded drill…
    await answerCurrent()
    // …and instead of ending, the session flows into the appended fresh drill
    // (the cloze blank splits the sentence, so match its trailing fragment).
    await waitFor(() => expect(screen.getByText(/home\./i)).toBeDefined())
    expect(screen.queryByText('Session Complete')).toBeNull()
    // Finishing the fresh drill ends the session for real.
    await answerCurrent()
    await waitFor(() => expect(screen.getByText('Session Complete')).toBeDefined())
  })

  it('keeps the session at the requested count — weaves in, never extends', async () => {
    // Not short: two seeded cards for a count of two. A freshly generated drill
    // must REPLACE an upcoming card, not push the session to three — the learner
    // asked for two. Reaching the summary after exactly two answers proves it.
    const a = { ...testCard, id: 'cram-a', drill_id: 'a', sentence: 'Card A {{answer}}.' }
    const b = { ...testCard, id: 'cram-b', drill_id: 'b', sentence: 'Card B {{answer}}.' }
    const c = { ...testCard, id: 'cram-c', drill_id: 'c', sentence: 'Card C {{answer}}.' }
    mockGetCramCards.mockResolvedValueOnce([a, b]).mockResolvedValue([a, b, c])
    mockGenerateGymDrills.mockResolvedValue({
      generated: 1, charged: 1, remaining: 4, unlimited: false,
    })
    render(
      <QueryClientProvider
        client={new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })}
      >
        <MemoryRouter initialEntries={['/cram?points=p1&mix=1&count=2&gen=1']}>
          <ReviewSessionPage cram />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await answerCurrent()
    await answerCurrent()
    // If generation had extended the deck to three, a third card would still be
    // showing here instead of the summary.
    await waitFor(() => expect(screen.getByText('Session Complete')).toBeDefined())
    expect(screen.getByTestId('cards-reviewed').textContent).toContain('2')
  })

  it('shows the drafting wait only when the learner out-runs generation', async () => {
    mockGetCramCards.mockResolvedValue([d1])
    // Generation still in flight when the learner finishes the seeded drill.
    mockGenerateGymDrills.mockReturnValue(new Promise(() => {}))
    renderGen()
    await answerCurrent()
    await waitFor(() => expect(screen.getByTestId('cram-topup')).toBeDefined())
    expect(screen.queryByText('Session Complete')).toBeNull()
  })

  it('falls through to the summary when generation fails', async () => {
    mockGetCramCards.mockResolvedValue([d1])
    mockGenerateGymDrills.mockRejectedValue({ response: { status: 402 } })
    renderGen()
    await answerCurrent()
    await waitFor(() => expect(screen.getByText('Session Complete')).toBeDefined())
  })

  it('gives up the wait after the ceiling and serves existing questions', async () => {
    // Generation hangs. After GEN_WAIT_MS the session must top up with
    // EXISTING drills from the same forms instead of holding the learner.
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      mockGetCramCards.mockResolvedValueOnce([d1]).mockResolvedValue([d1, d2])
      mockGenerateGymDrills.mockReturnValue(new Promise(() => {}))
      renderGen()
      await answerCurrent()
      await waitFor(() => expect(screen.getByTestId('cram-topup')).toBeDefined())
      await vi.advanceTimersByTimeAsync(9000)
      // The existing (not generated) drill d2 arrives and the session resumes.
      await waitFor(() => expect(screen.getByText(/home\./i)).toBeDefined())
      expect(screen.queryByTestId('cram-topup')).toBeNull()
    } finally {
      vi.useRealTimers()
    }
  })

  it('ends the wait at the ceiling even when nothing else exists', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      mockGetCramCards.mockResolvedValue([d1]) // the re-draw finds nothing new
      mockGenerateGymDrills.mockReturnValue(new Promise(() => {}))
      renderGen()
      await answerCurrent()
      await waitFor(() => expect(screen.getByTestId('cram-topup')).toBeDefined())
      await vi.advanceTimersByTimeAsync(9000)
      await waitFor(() =>
        expect(screen.getByText('Session Complete')).toBeDefined(),
      )
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('due counts after a review', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUsePrefsStore.mockImplementation(
      (selector: (s: { activeLanguageId: string }) => unknown) =>
        selector({ activeLanguageId: 'lang-123' }),
    )
    mockGetDueCards.mockResolvedValue([testCard])
    mockValidateAnswer.mockResolvedValue(mockValidateResponse)
    mockSubmitReview.mockResolvedValue(mockSubmitResponse)
  })

  // The counts were only refreshed by the Finish button on the summary
  // screen. Leave a session any other way — the back gesture, the tab bar, a
  // tap straight to the dashboard — and the caches were still inside their
  // 60s staleTime with refetchOnWindowFocus off, so the due number sat at its
  // pre-session value with no event coming to correct it. That is the "major
  // delay": not slow, just never told.
  it('marks the dashboard and due counts stale as each card is submitted', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ReviewSessionPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => screen.getByRole('textbox'))

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => screen.getByTestId('feedback-panel'))
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))

    await waitFor(() => expect(mockSubmitReview).toHaveBeenCalled())
    await waitFor(() => {
      const keys = invalidate.mock.calls.map((c) => JSON.stringify(c[0]?.queryKey))
      expect(keys).toContain('["dashboard"]')
      expect(keys).toContain('["due-cards"]')
    })
  })

  it('does not refetch mid-session — one request per card would be absurd', async () => {
    // refetchType 'none' is what makes per-card invalidation affordable: it
    // marks the caches stale so the NEXT screen fetches fresh, without firing
    // a dashboard request after every single answer.
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ReviewSessionPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await waitFor(() => screen.getByRole('textbox'))

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'goes' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => screen.getByTestId('feedback-panel'))
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))

    await waitFor(() => expect(mockSubmitReview).toHaveBeenCalled())
    await waitFor(() => {
      const dashboardCalls = invalidate.mock.calls.filter(
        (c) => JSON.stringify(c[0]?.queryKey) === '["dashboard"]',
      )
      expect(dashboardCalls.length).toBeGreaterThan(0)
      expect(dashboardCalls.every((c) => c[0]?.refetchType === 'none')).toBe(true)
    })
  })
})

describe('leaving the Trailblazer wait', () => {
  const englishCard: DueCard = {
    ...testCard,
    id: 'card-pre-fill',
    sentence: 'El coche {{answer}} nuevo.',
    translation: 'The car is new.',
  }
  const translatedCard: DueCard = {
    ...englishCard,
    translation: 'El coche es nuevo.',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUsePrefsStore.mockImplementation(
      (selector: (s: { activeLanguageId: string }) => unknown) =>
        selector({ activeLanguageId: 'lang-123' }),
    )
    // Under the bar: the wait screen stands between the learner and the deck.
    mockGetReadiness.mockResolvedValue({
      locale: 'es',
      new_here: true,
      learn: { total: 10, ready: 1, pct: 0.1, cards: 5, cards_ready: 0,
               start_cards: 1, ready_enough: false },
      review: { total: 10, ready: 1, pct: 0.1, cards: 5, cards_ready: 0,
                start_cards: 1, ready_enough: false },
      pairs: [],
    })
  })

  it('re-pulls the deck so the fill that just landed is what gets shown', async () => {
    // The deck is fetched on mount and frozen. Before this, the learner sat
    // through the whole wait, played the game, and then met the very English
    // they had been waiting to have translated.
    mockGetDueCards
      .mockResolvedValueOnce([englishCard])
      .mockResolvedValueOnce([translatedCard])

    renderWithProviders(<ReviewSessionPage />)

    const startAnyway = await screen.findByText('Start in English')
    await waitFor(() => expect(mockGetDueCards).toHaveBeenCalledTimes(1))

    fireEvent.click(startAnyway)

    // The deck is pulled again on the way out of the wait…
    await waitFor(() => expect(mockGetDueCards).toHaveBeenCalledTimes(2))
    // …and the session that renders is built from that second answer, not
    // the snapshot taken on mount.
    const input = await screen.findByRole('textbox')
    fireEvent.change(input, { target: { value: 'es' } })
    expect((input as HTMLInputElement).value).toBe('es')
  })

  it('never fetches the deck before the profile has resolved — and never twice', async () => {
    // The support locale is part of the deck's cache key and defaults to
    // 'en' while the profile is in flight. Ungated, the fetch raced the
    // profile: first request under the placeholder key, a second under the
    // corrected one — and the session kept whichever deck won. The learner
    // saw English flash into their language, or worse, kept the English.
    const { getProfile } = await import('../api/profile')
    let resolveProfile: (v: unknown) => void = () => {}
    ;(getProfile as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((r) => (resolveProfile = r)),
    )
    mockGetReadiness.mockResolvedValue({
      locale: 'es', new_here: true,
      learn: { total: 10, ready: 10, pct: 1, cards: 5, cards_ready: 5,
               start_cards: 1, ready_enough: true },
      review: { total: 10, ready: 10, pct: 1, cards: 5, cards_ready: 5,
                start_cards: 1, ready_enough: true },
      pairs: [],
    })
    mockGetDueCards.mockResolvedValue([translatedCard])

    renderWithProviders(<ReviewSessionPage />)
    // Profile still pending: not one deck request may exist yet.
    await new Promise((r) => setTimeout(r, 50))
    expect(mockGetDueCards).not.toHaveBeenCalled()

    resolveProfile({ support_locale: 'pt', ui_language: 'en' })
    await screen.findByRole('textbox')
    // Exactly one fetch — under the resolved identity, nothing discarded.
    expect(mockGetDueCards).toHaveBeenCalledTimes(1)
  })

  it('a deck parked under another identity is never restored', async () => {
    // The Settings round-trip is exactly when languages change. Keyed by
    // URL alone, the return trip restored the OLD language's deck into the
    // new session — the owner's "cards in the wrong language until
    // something forces a refresh".
    mockGetReadiness.mockResolvedValue({
      locale: 'es', new_here: true,
      learn: { total: 10, ready: 10, pct: 1, cards: 5, cards_ready: 5,
               start_cards: 1, ready_enough: true },
      review: { total: 10, ready: 10, pct: 1, cards: 5, cards_ready: 5,
                start_cards: 1, ready_enough: true },
      pairs: [],
    })
    const stalePark = JSON.stringify({
      cards: [{ ...englishCard, id: 'stale-ru',
                sentence: 'Это СТАРАЯ колода {{answer}}.' }],
      index: 0, results: [], requeued: [], savedAt: Date.now(),
    })
    // Parked under Russian; this session opens under lang-123:en. The
    // second entry is the PRE-identity key format — the regression this
    // pins: that key used to match every identity, including this one.
    sessionStorage.setItem('review-session:lang-ru:en:/', stalePark)
    sessionStorage.setItem('review-session:/', stalePark)
    try {
      mockGetDueCards.mockResolvedValue([translatedCard])
      renderWithProviders(<ReviewSessionPage />)
      await screen.findByRole('textbox')
      // The fresh deck was fetched; the foreign park never surfaced.
      expect(mockGetDueCards).toHaveBeenCalledTimes(1)
      expect(screen.queryByText(/СТАРАЯ/)).toBeNull()
    } finally {
      sessionStorage.clear()
    }
  })

  it('does not re-pull for a session that never waited', async () => {
    // Ready enough means no wait screen and no second fetch to pay for.
    mockGetReadiness.mockResolvedValue({
      locale: 'es',
      new_here: true,
      learn: { total: 10, ready: 10, pct: 1, cards: 5, cards_ready: 5,
               start_cards: 1, ready_enough: true },
      review: { total: 10, ready: 10, pct: 1, cards: 5, cards_ready: 5,
                start_cards: 1, ready_enough: true },
      pairs: [],
    })
    mockGetDueCards.mockResolvedValue([translatedCard])

    renderWithProviders(<ReviewSessionPage />)

    await screen.findByRole('textbox')
    expect(mockGetDueCards).toHaveBeenCalledTimes(1)
  })
})


describe('translations landing mid-session', () => {
  // A returning learner is never made to wait, and a new one starts on the
  // first ready card — so most of a session's translations can still be
  // landing while it runs. Upcoming cards are re-served on every advance;
  // the card on screen is left exactly as the learner saw it.
  const lane = (pct: number) => ({
    total: 10, ready: Math.round(pct * 10), pct, cards: 5,
    cards_ready: Math.round(pct * 5), start_cards: 1, ready_enough: true,
  })
  const first: DueCard = { ...testCard, id: 'c1', sentence: 'First {{answer}}.',
                           translation: 'First (English).' }
  const second: DueCard = { ...testCard, id: 'c2', sentence: 'Second {{answer}}.',
                            translation: 'Second (English).' }
  const third: DueCard = { ...testCard, id: 'c3', sentence: 'Third {{answer}}.',
                           translation: 'Third (English).' }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUsePrefsStore.mockImplementation(
      (selector: (s: { activeLanguageId: string }) => unknown) =>
        selector({ activeLanguageId: 'lang-123' }),
    )
    mockGetDueCards.mockResolvedValue([first, second, third])
  })

  it('re-serves only the cards still ahead, and swaps them in place', async () => {
    mockGetReadiness.mockResolvedValue({
      locale: 'es', new_here: false, learn: lane(1), review: lane(0.4), pairs: [],
    })
    mockRefreshDueCards.mockImplementation((_lang: string, ids: string[]) =>
      Promise.resolve(
        ids.map((id) =>
          id === 'c2' ? { ...second, sentence: 'Segunda {{answer}}.' } : null,
        ).filter(Boolean),
      ),
    )
    renderWithProviders(<ReviewSessionPage />)
    await screen.findByText(/First/)

    // The mount refresh asks for everything past the first card…
    await waitFor(() =>
      expect(mockRefreshDueCards).toHaveBeenCalledWith('lang-123', ['c2', 'c3']),
    )
    // …and the card on screen is untouched by it.
    expect(screen.getByText(/First/)).toBeDefined()

    // Advancing shows the swapped card, and re-asks for what is still ahead.
    fireEvent.click(screen.getByRole('button', { name: /skip/i }))
    await screen.findByText(/Segunda/)
    await waitFor(() =>
      expect(mockRefreshDueCards).toHaveBeenLastCalledWith('lang-123', ['c3']),
    )
  })

  it('never refreshes a session that already reads in the learner\'s language', async () => {
    mockGetReadiness.mockResolvedValue({
      locale: 'es', new_here: false, learn: lane(1), review: lane(1), pairs: [],
    })
    renderWithProviders(<ReviewSessionPage />)
    await screen.findByText(/First/)
    fireEvent.click(screen.getByRole('button', { name: /skip/i }))
    await screen.findByText(/Second/)
    expect(mockRefreshDueCards).not.toHaveBeenCalled()
  })

  it('a failed refresh leaves the English already in the deck', async () => {
    mockGetReadiness.mockResolvedValue({
      locale: 'es', new_here: false, learn: lane(1), review: lane(0.4), pairs: [],
    })
    mockRefreshDueCards.mockRejectedValue(new Error('offline'))
    renderWithProviders(<ReviewSessionPage />)
    await screen.findByText(/First/)
    await waitFor(() => expect(mockRefreshDueCards).toHaveBeenCalled())
    fireEvent.click(screen.getByRole('button', { name: /skip/i }))
    await screen.findByText(/Second/)
  })
})

describe('sentence audio when the learner got the word', () => {
  const mockTTS = getTTSUrl as ReturnType<typeof vi.fn>
  const mockGetProfile = getProfile as ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.clearAllMocks()
    mockUsePrefsStore.mockImplementation(
      (selector: (s: { activeLanguageId: string }) => unknown) =>
        selector({ activeLanguageId: 'lang-123' }),
    )
    mockGetDueCards.mockResolvedValue([testCard])
    mockValidateAnswer.mockResolvedValue(mockValidateResponse)
    mockSubmitReview.mockResolvedValue(mockSubmitResponse)
    mockTTS.mockResolvedValue(null)
    // clearAllMocks clears calls, not implementations — without this, one
    // test's off-profile would leak into the next.
    mockGetProfile.mockResolvedValue({ support_locale: null, ui_language: 'en' })
  })

  async function submit(value = 'goes') {
    renderWithProviders(<ReviewSessionPage />)
    await waitFor(() => screen.getByRole('textbox'))
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(mockValidateAnswer).toHaveBeenCalled())
  }

  it('reads the FULL sentence, blank filled in, when the answer is right', async () => {
    await submit()
    await waitFor(() =>
      expect(mockTTS).toHaveBeenCalledWith('en', 'She goes to the market.'),
    )
  })

  it('plays on amber too — hearing it said properly IS the accent correction', async () => {
    mockValidateAnswer.mockResolvedValue({
      answer_result: 'correct_sloppy',
      feedback: 'Almost — check the accents.',
    })
    await submit('goes')
    await waitFor(() =>
      expect(mockTTS).toHaveBeenCalledWith('en', 'She goes to the market.'),
    )
  })

  it('stays quiet on a wrong answer — that screen is a correction to read', async () => {
    mockValidateAnswer.mockResolvedValue({
      answer_result: 'wrong',
      feedback: null,
    })
    await submit('go')
    expect(mockTTS).not.toHaveBeenCalled()
  })

  it('stays quiet on a wrong FORM — the right word, inflected wrong', async () => {
    // Orange is not amber: the learner produced the wrong form, so the text
    // is what teaches. Guards the boundary the amber case just moved.
    mockValidateAnswer.mockResolvedValue({
      answer_result: 'wrong_form',
      feedback: 'Close — wrong tense.',
    })
    await submit('going')
    expect(mockTTS).not.toHaveBeenCalled()
  })

  it('the account can turn it off, and off means no fetch at all', async () => {
    mockGetProfile.mockResolvedValue({
      support_locale: null,
      ui_language: 'en',
      sentence_audio_on_correct: false,
    })
    await submit()
    expect(mockTTS).not.toHaveBeenCalled()
  })

  it('an older backend that lacks the setting reads as on', async () => {
    // The feature is the default, the toggle is the escape — and migration
    // 20261001 not being applied must not silently disable it.
    await submit()
    await waitFor(() => expect(mockTTS).toHaveBeenCalled())
  })
})
