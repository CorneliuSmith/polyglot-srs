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
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(),
  getProfile: vi.fn(() => Promise.resolve({ support_locale: null })),
  updateProfile: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({ usePrefsStore: vi.fn(() => 'lang-es') }))

import { confirmLearnSession, startLearnSession, validateAnswer } from '../api/review'
import { getLanguages } from '../api/profile'

const mockLearn = startLearnSession as ReturnType<typeof vi.fn>
const mockConfirm = confirmLearnSession as ReturnType<typeof vi.fn>
const mockValidate = validateAnswer as ReturnType<typeof vi.fn>
const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>

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

  it('keeps the card out of reviews until the check is answered correctly', async () => {
    mockLearn.mockResolvedValue({
      added: 1,
      items: ['uc-1'],
      lessons: [grammarLesson],
    })
    renderPage()
    await screen.findByText(/1 of 1/)

    mockValidate.mockResolvedValue({ answer_result: 'wrong', feedback: null })
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'eres' } })
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }))

    expect(await screen.findByText(/not quite/i)).toBeDefined()
    expect(mockConfirm).not.toHaveBeenCalled()
    const startBtn = screen.getByRole('button', { name: /start reviewing/i }) as HTMLButtonElement
    expect(startBtn.disabled).toBe(true)
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
})
