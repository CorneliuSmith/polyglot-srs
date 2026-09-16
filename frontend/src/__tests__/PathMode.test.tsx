import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PathMode from '../features/write/PathMode'

HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext

vi.mock('../api/write', () => ({ getWritePath: vi.fn(), markLesson: vi.fn(), getWritePrompts: vi.fn() }))
vi.mock('../api/strokes', () => ({
  getAlphabet: vi.fn(), getGlyphs: vi.fn(), getLettersProgress: vi.fn(),
  recordLetterAttempt: vi.fn(), recordLetterAttempts: vi.fn(),
}))
import { getWritePath, markLesson, getWritePrompts } from '../api/write'
import { getAlphabet, getGlyphs, getLettersProgress } from '../api/strokes'
const m = (f: unknown) => f as ReturnType<typeof vi.fn>

const BAR = [[500, 100], [500, 900]]
const GLYPHS = [
  { id: 'g-alif', script: 'arabic', glyph: 'ا', form: 'isolated', style: 'naskh', strokes: [BAR], joins: {}, hints: [], source: 'w', reviewed: true },
  { id: 'g-ba', script: 'arabic', glyph: 'ب', form: 'isolated', style: 'naskh', strokes: [BAR], joins: {}, hints: [], source: 'w', reviewed: true },
]

function renderPath() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <PathMode languageId="lang-ar" code="ar" style="naskh" glyphs={GLYPHS} fontFamily="cursive" />
    </QueryClientProvider>,
  )
}

describe('PathMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    m(getAlphabet).mockResolvedValue({
      code: 'ar', script: 'arabic', styles: ['naskh'],
      letters: [
        { glyph: 'ا', romanization: 'aa', sound: '', forms: ['isolated', 'final'] },
        { glyph: 'ب', romanization: 'b', sound: '', forms: ['isolated', 'final', 'initial', 'medial'] },
      ],
    })
    m(getGlyphs).mockResolvedValue({ script: 'arabic', exemplars: [], glyphs: GLYPHS })
    m(getLettersProgress).mockResolvedValue([{ glyph_id: 'g-alif', attempts: 3, passes: 3, best_score: 1, known: true }])
    m(getWritePath).mockResolvedValue([])
    m(getWritePrompts).mockResolvedValue([])
    m(markLesson).mockImplementation(async (a: { lessonId: string }) => [a.lessonId])
  })

  it('lists the lessons, opens the next one with its letters, and counts what is done', async () => {
    renderPath()
    await screen.findByTestId('path-lessons')
    // Letters ا ب (ب not yet known) is the next lesson and opens by itself.
    expect(screen.getByTestId('lesson-letters-1')).toHaveAttribute('data-state', 'next')
    expect(screen.getByTestId('lesson-open')).toBeInTheDocument()
    const strip = await screen.findByTestId('letters-strip')
    expect(strip.children).toHaveLength(2)
    expect(screen.getByText(/0 of 4/)).toBeInTheDocument()
  })

  it('finishes a letter lesson by itself once every authored form is known', async () => {
    m(getLettersProgress).mockResolvedValue([
      { glyph_id: 'g-alif', attempts: 3, passes: 3, best_score: 1, known: true },
      { glyph_id: 'g-ba', attempts: 3, passes: 3, best_score: 1, known: true },
    ])
    renderPath()
    await waitFor(() => expect(screen.getByTestId('lesson-letters-1')).toHaveAttribute('data-state', 'done'))
    expect(screen.getByTestId('lesson-forms-1')).toHaveAttribute('data-state', 'next')
    expect(screen.getByText(/1 of 4/)).toBeInTheDocument()
  })

  it('marks a word lesson done by hand, and the next opens', async () => {
    renderPath()
    await screen.findByTestId('path-lessons')
    fireEvent.click(screen.getByTestId('lesson-words-1'))
    expect(await screen.findByTestId('trace-empty')).toHaveTextContent(/No words in the course/)
    fireEvent.click(screen.getByTestId('lesson-mark-done'))
    await waitFor(() => expect(markLesson).toHaveBeenCalledWith(
      expect.objectContaining({ lessonId: 'words-1', done: true }),
    ))
    await waitFor(() => expect(screen.getByTestId('lesson-words-1')).toHaveAttribute('data-state', 'done'))
    fireEvent.click(screen.getByTestId('lesson-next'))
    expect(screen.getByTestId('lesson-sentences')).toHaveAttribute('aria-expanded', 'true')
  })
})
