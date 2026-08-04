import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import LearnPage from '../features/review/LearnPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/review', () => ({
  startLearnSession: vi.fn(),
  confirmLearnSession: vi.fn(),
  validateAnswer: vi.fn(),
  markCardKnown: vi.fn(),
  // The trailblazer gate runs before the batch is drawn. These sessions
  // are already in the learner's language, so they never see the wait.
  getSessionReadiness: vi.fn(() =>
    Promise.resolve({
      locale: null,
      threshold: 0.6,
      learn: { total: 0, ready: 0, pct: 1, ready_enough: true },
      review: { total: 0, ready: 0, pct: 1, ready_enough: true },
      pairs: [],
    }),
  ),
  refreshLessons: vi.fn(() => Promise.resolve([])),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(),
  getProfile: vi.fn(() => Promise.resolve({ support_locale: null })),
  updateProfile: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({ usePrefsStore: vi.fn(() => 'lang-es') }))

import {
  confirmLearnSession,
  getSessionReadiness,
  markCardKnown,
  refreshLessons,
  startLearnSession,
  validateAnswer,
} from '../api/review'
import { getLanguages } from '../api/profile'
import { usePrefsStore } from '../stores/prefsStore'

const mockLearn = startLearnSession as ReturnType<typeof vi.fn>
const mockConfirm = confirmLearnSession as ReturnType<typeof vi.fn>
const mockValidate = validateAnswer as ReturnType<typeof vi.fn>
const mockKnown = markCardKnown as ReturnType<typeof vi.fn>
const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockReadiness = getSessionReadiness as ReturnType<typeof vi.fn>
const mockRefresh = refreshLessons as ReturnType<typeof vi.fn>

function readiness(pct: number, ready_enough: boolean) {
  const lane = { total: 10, ready: Math.round(pct * 10), pct, ready_enough }
  return { locale: 'pt', threshold: 0.6, learn: lane, review: lane, pairs: [] }
}

const grammarLesson = {
  card_id: 'uc-1',
  card_type: 'grammar' as const,
  title: 'The verb ser (to be) — present',
  reading: null,
  part_of_speech: null,
  definition: null,
  usage_note: null,
  morphology: null,
  explanation: "'Ser' expresses permanent or defining qualities.",
  culture_note: 'Spanish has two verbs for to be.',
  reviewed: true,
  references: [{ title: 'Wikipedia: ser and estar', url: 'https://example.org/ser' }],
  examples: [{ sentence: 'Yo soy estudiante.', translation: 'I am a student.', hint: null }],
  quiz: {
    sentence: 'Yo {{answer}} estudiante.',
    answer: 'soy',
    translation: 'I am a student.',
    hint: null,
    morphology: null,
    alternatives: [],
  },
}

const vocabLesson = {
  card_id: 'uc-2',
  card_type: 'vocabulary' as const,
  title: 'agua',
  reading: null,
  part_of_speech: 'noun',
  definition: 'water',
  usage_note: null,
  morphology: null,
  explanation: null,
  culture_note: null,
  reviewed: true,
  references: [],
  examples: [{ sentence: 'El agua está fría.', translation: 'The water is cold.', hint: null }],
  quiz: {
    sentence: 'El {{answer}} está fría.',
    answer: 'agua',
    translation: 'The water is cold.',
    hint: 'water',
    morphology: null,
    alternatives: [],
  },
}

function renderPage(path = '/learn?type=grammar') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <LearnPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LearnPage (teach-before-quiz)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([{ id: 'lang-es', code: 'es', name: 'Spanish', rtl: false }])
    // Ready by default, so only the tests that are ABOUT the wait see it.
    // (clearAllMocks resets calls, not implementations — without this a
    // gated test leaks its readiness into every test after it.)
    mockReadiness.mockResolvedValue(readiness(1, true))
    mockRefresh.mockResolvedValue([])
  })

  it('presents each new item as a lesson before the quiz', async () => {
    mockLearn.mockResolvedValue({
      added: 2,
      items: ['uc-1', 'uc-2'],
      lessons: [grammarLesson, vocabLesson],
    })
    renderPage()

    // Lesson 1: the grammar point is TAUGHT — explanation, example, source.
    expect(await screen.findByText(/1 of 2/)).toBeDefined()
    expect(screen.getByText(/permanent or defining qualities/)).toBeDefined()
    expect(screen.getByText('Yo soy estudiante.')).toBeDefined()
    expect(screen.getByRole('link', { name: /wikipedia: ser/i })).toBeDefined()

    // Advancing is gated on answering the check sentence correctly.
    const nextBtn = screen.getByRole('button', { name: /next/i }) as HTMLButtonElement
    expect(nextBtn.disabled).toBe(true)

    mockValidate.mockResolvedValue({ answer_result: 'correct', feedback: null })
    mockConfirm.mockResolvedValue({ confirmed: 1 })
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'soy' } })
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }))
    // A correct first check queues THIS card for review.
    await waitFor(() => expect(mockConfirm).toHaveBeenCalledWith(['uc-1']))
    expect(await screen.findByText(/added to your reviews/i)).toBeDefined()

    // Page to lesson 2 (vocab): word + meaning + context sentence.
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(await screen.findByText(/2 of 2/)).toBeDefined()
    expect(screen.getByText('water')).toBeDefined()
    expect(screen.getByText('El agua está fría.')).toBeDefined()

    // The quiz can only start once the last lesson's check is passed.
    const startBtn = screen.getByRole('button', { name: /start reviewing/i }) as HTMLButtonElement
    expect(startBtn.disabled).toBe(true)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'agua' } })
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }))
    await waitFor(() => expect(mockConfirm).toHaveBeenCalledWith(['uc-2']))

    fireEvent.click(screen.getByRole('button', { name: /start reviewing/i }))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/review'))
    expect(mockLearn).toHaveBeenCalledWith('lang-es', 'grammar', undefined)
  })

  it('offers the on-screen keyboard during the quiz (beta report)', async () => {
    // Alphabet-vocab languages had no keyboard access while learning; the
    // review session had it, learn didn't. es has a layout (Latin accents),
    // so the toggle renders here just as it does in review.
    mockLearn.mockResolvedValue({ added: 1, items: ['uc-1'], lessons: [grammarLesson] })
    renderPage()
    await screen.findByText(/1 of 1/)
    // Keyboard is shown by default → a "Hide Keyboard" toggle is present.
    expect(
      screen.getByRole('button', { name: /keyboard/i }),
    ).toBeDefined()
  })

  it('Enter advances after a passed check (keyboard-only flow)', async () => {
    mockLearn.mockResolvedValue({
      added: 2,
      items: ['uc-1', 'uc-2'],
      lessons: [grammarLesson, vocabLesson],
    })
    renderPage()
    expect(await screen.findByText(/1 of 2/)).toBeDefined()

    // Enter does nothing while the check is unanswered.
    fireEvent.keyDown(document, { key: 'Enter' })
    expect(screen.getByText(/1 of 2/)).toBeDefined()

    mockValidate.mockResolvedValue({ answer_result: 'correct', feedback: null })
    mockConfirm.mockResolvedValue({ confirmed: 1 })
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'soy' } })
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }))
    await screen.findByText(/added to your reviews/i)

    // The input is disabled now — Enter on the document pages forward.
    fireEvent.keyDown(document, { key: 'Enter' })
    expect(await screen.findByText(/2 of 2/)).toBeDefined()

    // Pass the last check, then Enter starts reviewing.
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'agua' } })
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }))
    await waitFor(() => expect(mockConfirm).toHaveBeenCalledWith(['uc-2']))
    fireEvent.keyDown(document, { key: 'Enter' })
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/review'))
  })

  it('an accent-only miss passes AMBER, not green (accents pref off)', async () => {
    // validateAnswer already applied the accents-optional remap: a surviving
    // 'correct_sloppy' means the pref is OFF and the accents were wrong.
    mockLearn.mockResolvedValue({
      added: 1,
      items: ['uc-2'],
      lessons: [vocabLesson],
    })
    renderPage()
    await screen.findByText(/1 of 1/)

    mockValidate.mockResolvedValue({
      answer_result: 'correct_sloppy',
      feedback: 'Almost — check the accents. Expected: agua',
    })
    mockConfirm.mockResolvedValue({ confirmed: 1 })
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'agua' } })
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }))

    // Right word → still queued for review…
    await waitFor(() => expect(mockConfirm).toHaveBeenCalledWith(['uc-2']))
    // …but the message is the amber accents warning, not the green ✓.
    expect(await screen.findByText(/check the accents/i)).toBeDefined()
    expect(screen.queryByText(/✓ Correct/)).toBeNull()
  })

  it('first miss nudges a retry without revealing; second miss reveals', async () => {
    // Owner: the lesson above the quiz holds everything needed, so the FIRST
    // wrong answer gets a fading "try again" toast, not the answer. A second
    // miss reveals as before, and moving on stays unlocked either way (the
    // card simply never enters reviews — it will be re-taught next session).
    mockLearn.mockResolvedValue({
      added: 1,
      items: ['uc-1'],
      lessons: [grammarLesson],
    })
    renderPage()
    await screen.findByText(/1 of 1/)

    const startBtnBefore = screen.getByRole('button', { name: /start reviewing/i }) as HTMLButtonElement
    expect(startBtnBefore.disabled).toBe(true)

    mockValidate.mockResolvedValue({ answer_result: 'wrong', feedback: null })
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'eres' } })
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }))

    // First miss: the toast invites a retry; the answer stays hidden.
    const toast = await screen.findByTestId('retry-toast')
    expect(toast.textContent).toMatch(/try again/i)
    expect(screen.queryByRole('alert')).toBeNull()
    expect(document.body.textContent).not.toContain(
      `the answer is ${grammarLesson.quiz.answer}`,
    )
    // …the card is NOT confirmed into reviews…
    expect(mockConfirm).not.toHaveBeenCalled()
    // …but the learner is not trapped even on the first miss.
    const startBtn = screen.getByRole('button', { name: /start reviewing/i }) as HTMLButtonElement
    expect(startBtn.disabled).toBe(false)

    // Second miss: reveal, so nobody is ever stuck guessing.
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'era' } })
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }))
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toMatch(/not quite/i)
    expect(alert.textContent).toContain(grammarLesson.quiz.answer)
  })

  it('"I already know this" retires the card without a quiz answer (owner request)', async () => {
    mockLearn.mockResolvedValue({
      added: 2,
      items: ['uc-1', 'uc-2'],
      lessons: [grammarLesson, vocabLesson],
    })
    mockKnown.mockResolvedValue(undefined)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await screen.findByText(/1 of 2/)

    // Next is locked until the card is resolved somehow.
    const nextBtn = screen.getByRole('button', { name: /next/i }) as HTMLButtonElement
    expect(nextBtn.disabled).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: /already know this/i }))
    await waitFor(() => expect(mockKnown).toHaveBeenCalledWith('uc-1'))

    // Retired, not queued: confirmLearnSession (the "passed" path) never fires.
    expect(mockConfirm).not.toHaveBeenCalled()
    expect(await screen.findByText(/marked as known/i)).toBeDefined()
    expect(screen.queryByText(/added to your reviews/i)).toBeNull()

    // The quiz input is disabled and Next unlocks, same as a real pass would.
    expect((screen.getByRole('textbox') as HTMLInputElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: /next/i }) as HTMLButtonElement).disabled).toBe(
      false,
    )

    confirmSpy.mockRestore()
  })

  it('does not retire the card if the confirm dialog is declined', async () => {
    mockLearn.mockResolvedValue({ added: 1, items: ['uc-1'], lessons: [grammarLesson] })
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPage()
    await screen.findByText(/1 of 1/)

    fireEvent.click(screen.getByRole('button', { name: /already know this/i }))
    expect(mockKnown).not.toHaveBeenCalled()
    expect(screen.getByRole('textbox')).toBeDefined()

    confirmSpy.mockRestore()
  })

  it('passes the vocabulary card type from the query string', async () => {
    mockLearn.mockResolvedValue({ added: 1, items: ['uc-2'], lessons: [vocabLesson] })
    renderPage('/learn?type=vocabulary')
    await waitFor(() => expect(mockLearn).toHaveBeenCalledWith('lang-es', 'vocabulary', undefined))
  })

  it('renders the error state without crashing (hooks precede returns)', async () => {
    // React #300 regression: the Enter-advance effect must run on EVERY
    // render, including the isError one — a beta tester hit the crash live.
    mockLearn.mockRejectedValue(new Error('boom'))
    renderPage()
    expect(await screen.findByText(/could not prepare|went wrong|try again/i)).toBeDefined()
  })

  it('explains when there is nothing new to learn', async () => {
    mockLearn.mockResolvedValue({ added: 0, items: [], lessons: [] })
    renderPage()
    expect(await screen.findByText(/nothing new to learn/i)).toBeDefined()
  })

  it('holds an under-ready session behind the trailblazer wait, and never draws the batch until asked', async () => {
    // The learn POST CREATES cards, so the gate must come first — drawing a
    // batch the learner then abandons would strand it as suspended.
    mockReadiness.mockResolvedValue(readiness(0.2, false))
    mockLearn.mockResolvedValue({ added: 2, items: ['uc-1', 'uc-2'], lessons: [] })
    renderPage()

    await screen.findByText(/first here/i)
    expect(mockLearn).not.toHaveBeenCalled()

    fireEvent.click(screen.getByText(/Start in English/i))
    await waitFor(() => expect(mockLearn).toHaveBeenCalled())
  })

  it('swaps content into the learner language mid-session, without a restart', async () => {
    // A session started under-ready re-serves its payloads as the loop lands
    // translations; the English already on screen is replaced in place.
    mockReadiness.mockResolvedValue(readiness(0.2, false))
    mockLearn.mockResolvedValue({
      added: 1,
      items: ['uc-1'],
      lessons: [grammarLesson],
    })
    mockRefresh.mockResolvedValue([
      { ...grammarLesson, title: '[Português] The verb ser' },
    ])
    renderPage()

    fireEvent.click(await screen.findByText(/Start in English/i))
    await waitFor(() => expect(mockRefresh).toHaveBeenCalledWith(['uc-1']))
    await screen.findByText('[Português] The verb ser')
  })

  it('Arabic vocalized reading follows the short-vowels setting', async () => {
    // Real-selector store mock: the tashkeel gate needs showTashkeel and an
    // Arabic active language at the same time.
    const state: Record<string, unknown> = {
      activeLanguageId: 'lang-ar',
      qwertyTranslit: {},
      setQwertyTranslit: vi.fn(),
      showTashkeel: false,
      hintLevel: 9,
      listeningMode: false,
      accentsOptional: false,
    }
    const mockPrefs = usePrefsStore as unknown as ReturnType<typeof vi.fn>
    mockPrefs.mockImplementation((sel: (s: unknown) => unknown) => sel(state))
    mockGetLanguages.mockResolvedValue([
      { id: 'lang-ar', code: 'ar', name: 'Arabic', rtl: true },
    ])
    const arLesson = {
      ...vocabLesson,
      title: 'كتب',
      reading: 'كَتَبَ',
      quiz: { ...vocabLesson.quiz, answer: 'كتب' },
    }
    mockLearn.mockResolvedValue({ added: 1, items: ['uc-2'], lessons: [arLesson] })

    // OFF: the bare word shows, the vocalized form does not.
    const view = renderPage('/learn?type=vocabulary')
    await screen.findByText(/1 of 1/)
    expect(screen.getByText('كتب')).toBeDefined()
    expect(screen.queryByText('كَتَبَ')).toBeNull()
    view.unmount()

    // ON (the default): the vocalized form appears under the word.
    state.showTashkeel = true
    renderPage('/learn?type=vocabulary')
    await screen.findByText(/1 of 1/)
    expect(screen.getByText('كَتَبَ')).toBeDefined()

    mockPrefs.mockImplementation(() => 'lang-es')
  })
})
