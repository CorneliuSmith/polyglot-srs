import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import GrammarPathPage from '../features/curriculum/GrammarPathPage'

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/curriculum', () => ({
  getCurriculum: vi.fn(),
  getCurriculumPoint: vi.fn(),
  learnPoint: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({ usePrefsStore: vi.fn(() => 'lang-es') }))

import { getLanguages } from '../api/profile'
import { getCurriculum, getCurriculumPoint, learnPoint } from '../api/curriculum'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockGetCurriculum = getCurriculum as ReturnType<typeof vi.fn>
const mockGetPoint = getCurriculumPoint as ReturnType<typeof vi.fn>
const mockLearn = learnPoint as ReturnType<typeof vi.fn>

const points = [
  { id: 'p1', title: 'Subject pronouns', level: 'A1', function_note: 'Say who you are talking about', reviewed: true, learnable: true, learned: true },
  { id: 'p2', title: 'The verb ser', level: 'A1', function_note: 'Say who or what someone is', reviewed: true, learnable: true, learned: false },
  { id: 'p3', title: 'Past subjunctive', level: 'A2', function_note: null, reviewed: true, learnable: false, learned: false },
]

const serDetail = {
  id: 'p2', title: 'The verb ser', level: 'A1',
  function_note: 'Say who or what someone is',
  explanation: "'Ser' expresses permanent or defining qualities.",
  culture_note: null, reviewed: true, learned: false, learnable: true,
  references: [{ title: 'Plan Curricular del Instituto Cervantes', url: 'https://cvc.cervantes.es/x' }],
  examples: [{ sentence: 'Yo soy estudiante.', translation: 'I am a student.', hint: null }],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <GrammarPathPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('GrammarPathPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([{ id: 'lang-es', code: 'es', name: 'Spanish', rtl: false }])
    mockGetCurriculum.mockResolvedValue(points)
    mockGetPoint.mockResolvedValue(serDetail)
    mockLearn.mockResolvedValue({ added: true, card_id: 'uc-9' })
  })

  it('shows the ordered path grouped by level with can-do functions and status', async () => {
    renderPage()
    expect(await screen.findByText('Subject pronouns')).toBeDefined()
    expect(screen.getByText('Say who you are talking about')).toBeDefined()
    expect(screen.getAllByText('A1').length).toBeGreaterThan(0)
    expect(screen.getByText('In reviews ✓')).toBeDefined()      // learned badge
    expect(screen.getByText('Reading only')).toBeDefined()      // drill-less point
    expect(screen.getByText('1 of 3 in your reviews')).toBeDefined()
  })

  it('opens a point page and adds it to reviews', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('The verb ser'))

    // The readable point page: explanation, completed example, source link.
    expect(await screen.findByText(/permanent or defining qualities/)).toBeDefined()
    expect(screen.getByText('Yo soy estudiante.')).toBeDefined()
    expect(screen.getByRole('link', { name: /plan curricular/i })).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /add to my reviews/i }))
    await waitFor(() => expect(mockLearn).toHaveBeenCalledWith('p2'))
  })
})
