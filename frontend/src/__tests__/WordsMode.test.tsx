import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import WordsMode, { lines } from '../features/write/WordsMode'
import { compose, fitComposed } from '../features/write/composer'
import type { Glyph } from '../api/strokes'

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

vi.mock('../api/write', () => ({ getWritePrompts: vi.fn() }))
vi.mock('../api/strokes', () => ({ recordLetterAttempts: vi.fn() }))
import { getWritePrompts } from '../api/write'
import { recordLetterAttempts } from '../api/strokes'
const mockPrompts = getWritePrompts as ReturnType<typeof vi.fn>
const mockRecord = recordLetterAttempts as ReturnType<typeof vi.fn>

const L = [[[500, 100], [500, 900]]]
const O = [[[300, 300], [700, 300], [700, 700], [300, 700], [300, 300]]]
const glyphs: Glyph[] = [
  { id: 'g-l', script: 'latin', glyph: 'l', form: 'lower', style: 'print', strokes: L, joins: {}, hints: [], source: 'w', reviewed: true },
  { id: 'g-o', script: 'latin', glyph: 'o', form: 'lower', style: 'print', strokes: O, joins: {}, hints: [], source: 'w', reviewed: true },
]

function renderMode(g: Glyph[] = glyphs) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <WordsMode languageId="lang-es" code="es" style="print" glyphs={g} />
    </QueryClientProvider>,
  )
}

/** Draw a fitted stroke onto the canvas: jsdom has no width, so the
 * component and this helper both measure 600 × 220. */
function draw(canvas: HTMLElement, stroke: { x: number; y: number }[]) {
  fireEvent.pointerDown(canvas, { pointerId: 1, clientX: stroke[0].x, clientY: stroke[0].y })
  for (const p of stroke.slice(1)) fireEvent.pointerMove(canvas, { pointerId: 1, clientX: p.x, clientY: p.y })
  const last = stroke[stroke.length - 1]
  fireEvent.pointerUp(canvas, { pointerId: 1, clientX: last.x, clientY: last.y })
}

describe('lines', () => {
  it('breaks a sentence into whole-word lines by letter count', () => {
    expect(lines('lo lo lo lo', 5)).toEqual(['lo lo', 'lo lo'])
    expect(lines('longword lo', 3)).toEqual(['longword', 'lo'])
  })
})

describe('WordsMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPrompts.mockResolvedValue([
      { prompt: 'x', answer: 'lx', source: 'course' },   // x has no form: skipped
      { prompt: 'water', answer: 'lo', source: 'own' },
    ])
    mockRecord.mockResolvedValue([])
  })

  it('shows only what the library can compose, learns, traces letter by letter, then writes and records each form', async () => {
    renderMode()
    await waitFor(() => expect(screen.getByTestId('trace-text')).toHaveTextContent('lo'))
    expect(screen.getByTestId('trace-learn')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('trace-step-trace'))
    const canvas = document.querySelector('canvas[data-testid="ink-canvas"]') ?? document.querySelector('canvas')!
    const composed = compose('lo', 'es', 'print', glyphs)
    const frame = fitComposed(composed, 600, 220)
    draw(canvas as HTMLElement, frame.strokes[0])
    await waitFor(() => expect(screen.getByTestId('letter-0')).toHaveAttribute('data-state', 'ok'))
    expect(screen.getByTestId('letter-1')).toHaveAttribute('data-state', 'pending')
    draw(canvas as HTMLElement, frame.strokes[1])
    await waitFor(() => expect(screen.getByTestId('trace-complete')).toBeInTheDocument())

    fireEvent.click(screen.getByTestId('trace-next'))
    expect(screen.getByTestId('trace-step-write')).toHaveAttribute('aria-selected', 'true')
    const canvas2 = document.querySelector('canvas')!
    // From memory, smaller and elsewhere: the fit takes care of it.
    for (const s of frame.strokes) draw(canvas2 as HTMLElement, s.map((p) => ({ x: 30 + p.x * 0.6, y: 40 + p.y * 0.6 })))
    fireEvent.click(screen.getByTestId('trace-check'))
    await waitFor(() => expect(screen.getByTestId('trace-verdict')).toHaveTextContent('Every letter matches'))
    expect(mockRecord).toHaveBeenCalledWith({
      languageId: 'lang-es',
      attempts: expect.arrayContaining([
        expect.objectContaining({ glyphId: 'g-l', passed: true }),
        expect.objectContaining({ glyphId: 'g-o', passed: true }),
      ]),
    })
  })

  it('names the letter that failed, with its expected form', async () => {
    renderMode()
    await waitFor(() => expect(screen.getByTestId('trace-text')).toHaveTextContent('lo'))
    fireEvent.click(screen.getByTestId('trace-step-write'))
    const canvas = document.querySelector('canvas')!
    const frame = fitComposed(compose('lo', 'es', 'print', glyphs), 600, 220)
    draw(canvas as HTMLElement, frame.strokes[0])
    // The o as a zigzag instead of a loop.
    draw(canvas as HTMLElement, frame.strokes[1].map((p, i) => ({ x: p.x + (i % 2 ? 45 : -45), y: p.y + 35 })))
    fireEvent.click(screen.getByTestId('trace-check'))
    await waitFor(() => expect(screen.getByTestId('trace-verdict')).toHaveTextContent('Not every letter yet'))
    expect(screen.getByTestId('letter-0')).toHaveAttribute('data-state', 'ok')
    expect(screen.getByTestId('letter-1')).toHaveAttribute('data-state', 'miss')
    expect(mockRecord).toHaveBeenCalledWith(expect.objectContaining({
      attempts: expect.arrayContaining([expect.objectContaining({ glyphId: 'g-o', passed: false })]),
    }))
  })

  it('says which letters are missing when nothing can be traced', async () => {
    mockPrompts.mockResolvedValue([{ prompt: 'x', answer: 'lx', source: 'course' }])
    renderMode()
    await waitFor(() => expect(screen.getByTestId('trace-empty')).toHaveTextContent('x'))
  })
})
