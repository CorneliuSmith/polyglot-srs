import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LettersMode from '../features/write/LettersMode'

HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext
if (typeof window !== 'undefined' && !('PointerEvent' in window)) {
  class PointerEventShim extends MouseEvent {
    pointerId: number
    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init)
      this.pointerId = init.pointerId ?? 0
    }
  }
  ;(window as unknown as { PointerEvent: typeof PointerEventShim }).PointerEvent = PointerEventShim
}

vi.mock('../api/strokes', () => ({
  getAlphabet: vi.fn(),
  getGlyphs: vi.fn(),
  getLettersProgress: vi.fn(),
  recordLetterAttempt: vi.fn(),
}))
import { getAlphabet, getGlyphs, getLettersProgress, recordLetterAttempt } from '../api/strokes'
const mockAlphabet = getAlphabet as ReturnType<typeof vi.fn>
const mockGlyphs = getGlyphs as ReturnType<typeof vi.fn>
const mockProgress = getLettersProgress as ReturnType<typeof vi.fn>
const mockRecord = recordLetterAttempt as ReturnType<typeof vi.fn>

// A "т"-like template: a vertical bar then a crossbar.
const BAR = [[500, 100], [500, 900]]
const CROSS = [[300, 400], [700, 400]]

function renderMode() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <LettersMode languageId="lang-ru" code="ru" style="print" />
    </QueryClientProvider>,
  )
}

/** Draw a template stroke onto the 260 px canvas (the box maps 0.08–0.92). */
function drawTemplate(canvas: HTMLElement, stroke: number[][]) {
  const px = (v: number) => 260 * 0.08 + (v / 1000) * 260 * 0.84
  const [a, b] = stroke
  fireEvent.pointerDown(canvas, { pointerId: 1, clientX: px(a[0]), clientY: px(a[1]) })
  fireEvent.pointerMove(canvas, { pointerId: 1, clientX: px((a[0] + b[0]) / 2), clientY: px((a[1] + b[1]) / 2) })
  fireEvent.pointerMove(canvas, { pointerId: 1, clientX: px(b[0]), clientY: px(b[1]) })
  fireEvent.pointerUp(canvas, { pointerId: 1, clientX: px(b[0]), clientY: px(b[1]) })
}

describe('LettersMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAlphabet.mockResolvedValue({
      code: 'ru', script: 'cyrillic', styles: ['cursive', 'print'],
      letters: [
        { glyph: 'т', romanization: 't', sound: '', forms: ['lower', 'upper'] },
        { glyph: 'о', romanization: 'o', sound: '', forms: ['lower', 'upper'] },
      ],
    })
    mockGlyphs.mockResolvedValue({
      script: 'cyrillic',
      glyphs: [
        { id: 'g-t', script: 'cyrillic', glyph: 'т', form: 'lower', style: 'print',
          strokes: [BAR, CROSS], joins: {}, hints: ['down', 'across'], source: 'workshop', reviewed: true },
        { id: 'g-o', script: 'cyrillic', glyph: 'о', form: 'lower', style: 'print',
          strokes: [[[500, 200], [700, 500], [500, 800], [300, 500], [500, 200]]], joins: {}, hints: [],
          source: 'workshop', reviewed: true },
      ],
      exemplars: [],
    })
    mockProgress.mockResolvedValue([{ glyph_id: 'g-o', attempts: 3, passes: 3, best_score: 1, known: true }])
    mockRecord.mockResolvedValue({ glyph_id: 'g-t', attempts: 1, passes: 1, best_score: 1, known: false })
  })

  it('shows the strip in alphabet order with known letters marked, and the hints', async () => {
    renderMode()
    const strip = await screen.findByTestId('letters-strip')
    // Every form of every letter: the two authored ones solid, the rest dashed.
    expect(strip.children).toHaveLength(4)
    expect(strip.children[0]).toHaveTextContent('т')
    expect(strip.children[1]).toHaveTextContent('Т')
    expect(strip.children[1]).toHaveAttribute('data-authored', 'no')
    expect(strip.children[1].className).toContain('dashed')
    expect(strip.children[2].className).toContain('green')
    expect(screen.getByText('down')).toBeInTheDocument()
    expect(screen.getByText('across')).toBeInTheDocument()
  })

  it('trace snaps each matched stroke, then write checks from memory and records a pass', async () => {
    renderMode()
    await screen.findByTestId('letters-strip')
    fireEvent.click(screen.getByTestId('step-trace'))
    const canvas = screen.getByTestId('ink-canvas')
    drawTemplate(canvas, BAR)
    expect(screen.queryByTestId('trace-complete')).not.toBeInTheDocument()
    drawTemplate(canvas, CROSS)
    expect(await screen.findByTestId('trace-complete')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('step-write'))
    const blank = screen.getByTestId('ink-canvas')
    drawTemplate(blank, BAR)
    drawTemplate(blank, CROSS)
    fireEvent.click(screen.getByTestId('letters-check'))
    expect(await screen.findByTestId('letters-verdict')).toHaveTextContent(/That’s it/)
    await waitFor(() => expect(mockRecord).toHaveBeenCalledWith(
      expect.objectContaining({ languageId: 'lang-ru', glyphId: 'g-t', passed: true }),
    ))
  })

  it('names the stroke and the reason on a miss', async () => {
    renderMode()
    await screen.findByTestId('letters-strip')
    fireEvent.click(screen.getByTestId('step-write'))
    const canvas = screen.getByTestId('ink-canvas')
    // The bar drawn bottom-to-top, the crossbar missing.
    drawTemplate(canvas, [BAR[1], BAR[0]])
    fireEvent.click(screen.getByTestId('letters-check'))
    const verdict = await screen.findByTestId('letters-verdict')
    expect(verdict).toHaveTextContent(/Stroke 1: drawn the other way round/)
    expect(verdict).toHaveTextContent(/Stroke 2: missing/)
    await waitFor(() => expect(mockRecord).toHaveBeenCalledWith(expect.objectContaining({ passed: false })))
  })

  it('teaches over the hand font while a letter has no strokes, and never grades it', async () => {
    mockGlyphs.mockResolvedValue({ script: 'cyrillic', glyphs: [], exemplars: [] })
    renderMode()
    expect(await screen.findByTestId('letters-learn-font')).toHaveTextContent('т')
    expect(screen.getByText(/speaker still has to trace/)).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('step-trace'))
    expect(screen.getByTestId('ink-canvas')).toBeInTheDocument()
    expect(screen.getByTestId('letters-no-check')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('step-write'))
    expect(screen.queryByTestId('letters-check')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('letters-reveal'))
    expect(screen.getByTestId('letters-reveal')).toHaveTextContent('Hide')
    expect(mockRecord).not.toHaveBeenCalled()
  })
})
