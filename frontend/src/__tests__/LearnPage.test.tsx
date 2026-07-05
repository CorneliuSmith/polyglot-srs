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
vi.mock('../api/review', () => ({ startLearnSession: vi.fn() }))
vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../stores/prefsStore', () => ({ usePrefsStore: vi.fn(() => 'lang-es') }))

import { startLearnSession } from '../api/review'
import { getLanguages } from '../api/profile'

const mockLearn = startLearnSession as ReturnType<typeof vi.fn>
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

    // Page to lesson 2 (vocab): word + meaning + context sentence.
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(await screen.findByText(/2 of 2/)).toBeDefined()
    expect(screen.getByText('water')).toBeDefined()
    expect(screen.getByText('El agua está fría.')).toBeDefined()

    // Only after the last lesson can the quiz start.
    fireEvent.click(screen.getByRole('button', { name: /start reviewing/i }))
    expect(mockNavigate).toHaveBeenCalledWith('/review')
    expect(mockLearn).toHaveBeenCalledWith('lang-es', 'grammar')
  })

  it('passes the vocabulary card type from the query string', async () => {
    mockLearn.mockResolvedValue({ added: 1, items: ['uc-2'], lessons: [vocabLesson] })
    renderPage('/learn?type=vocabulary')
    await waitFor(() => expect(mockLearn).toHaveBeenCalledWith('lang-es', 'vocabulary'))
  })

  it('explains when there is nothing new to learn', async () => {
    mockLearn.mockResolvedValue({ added: 0, items: [], lessons: [] })
    renderPage()
    expect(await screen.findByText(/nothing new to learn/i)).toBeDefined()
  })
})
