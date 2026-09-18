import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import StrokesPanel from '../features/contribute/StrokesPanel'
import { toGlyphBox, fromGlyphBox } from '../features/write/glyphBox'

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

// The bundled library would fill every form; these tests are about the
// server's rows, so the bundle is a pass-through here.
vi.mock('../features/write/strokes/provisional', () => ({
  withProvisional: (_s: string, _st: string, g: unknown[]) => g,
  isProvisionalId: (id: string) => id.startsWith('prov:'),
}))

vi.mock('../api/strokes', () => ({
  getAlphabet: vi.fn(),
  listStrokes: vi.fn(),
  saveGlyph: vi.fn(),
  reviewGlyph: vi.fn(),
  deleteGlyph: vi.fn(),
  saveExemplar: vi.fn(),
  reviewExemplar: vi.fn(),
  deleteExemplar: vi.fn(),
}))
import { getAlphabet, listStrokes, reviewGlyph, saveGlyph } from '../api/strokes'
const mockAlphabet = getAlphabet as ReturnType<typeof vi.fn>
const mockList = listStrokes as ReturnType<typeof vi.fn>
const mockSave = saveGlyph as ReturnType<typeof vi.fn>
const mockReview = reviewGlyph as ReturnType<typeof vi.fn>

function renderPanel(canReview = false) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <StrokesPanel languageId="lang-ar" languageCode="ar" canReview={canReview} />
    </QueryClientProvider>,
  )
}

function draw(canvas: HTMLElement, x: number) {
  fireEvent.pointerDown(canvas, { pointerId: 1, clientX: x, clientY: 40 })
  fireEvent.pointerMove(canvas, { pointerId: 1, clientX: x + 5, clientY: 120 })
  fireEvent.pointerUp(canvas, { pointerId: 1, clientX: x + 5, clientY: 120 })
}

describe('glyph box', () => {
  it('normalises ink into the 1000 box and back', () => {
    const boxed = toGlyphBox([[{ x: 10, y: 10 }, { x: 110, y: 60 }]])
    expect(boxed).toHaveLength(1)
    expect(boxed[0][0][0]).toBeLessThan(boxed[0][1][0])
    expect(Math.max(...boxed.flat().flat())).toBeLessThanOrEqual(1000)
    const back = fromGlyphBox(boxed, 200)
    expect(back[0][0].x).toBeGreaterThanOrEqual(0)
    expect(back[0][1].x).toBeLessThanOrEqual(200)
  })
})

describe('StrokesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAlphabet.mockResolvedValue({
      code: 'ar', script: 'arabic', styles: ['naskh', 'ruqah'],
      letters: [
        { glyph: 'ب', romanization: 'b', sound: '', forms: ['isolated', 'final', 'initial', 'medial'] },
        { glyph: 'ا', romanization: 'a', sound: '', forms: ['isolated', 'final'] },
      ],
    })
    mockList.mockResolvedValue({
      script: 'arabic',
      glyphs: [{
        id: 'g1', script: 'arabic', glyph: 'ب', form: 'isolated', style: 'naskh',
        strokes: [[[100, 500], [900, 500]], [[500, 700], [500, 720]]], joins: {}, hints: ['bowl'],
        source: 'workshop', reviewed: false,
      }],
      exemplars: [],
    })
    mockSave.mockResolvedValue({ id: 'g2', reviewed: false })
    mockReview.mockResolvedValue(undefined)
  })

  it('draws the grid with every form and its status', async () => {
    renderPanel()
    expect(await screen.findByTestId('form-ب-medial')).toBeInTheDocument()
    expect(screen.queryByTestId('form-ا-medial')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('form-ب-isolated')).toHaveTextContent('·'))
    expect(screen.getByText(/0 of 6 forms reviewed \(1 authored\)/)).toBeInTheDocument()
  })

  it('traces a new form and saves it as a draft in the 1000 box', async () => {
    renderPanel()
    fireEvent.click(await screen.findByTestId('form-ب-medial'))
    expect(screen.getByTestId('strokes-editor')).toBeInTheDocument()
    expect(screen.getByTestId('strokes-save')).toBeDisabled()
    const canvas = screen.getAllByTestId('ink-canvas')[0]
    draw(canvas, 30)
    draw(canvas, 90)
    expect(screen.getByTestId('stroke-list').children).toHaveLength(2)
    fireEvent.click(screen.getByTestId('strokes-save'))
    await waitFor(() => expect(mockSave).toHaveBeenCalled())
    const args = mockSave.mock.calls[0][0]
    expect(args).toMatchObject({ languageId: 'lang-ar', glyph: 'ب', form: 'medial', style: 'naskh' })
    expect(args.strokes).toHaveLength(2)
    expect(Math.max(...args.strokes.flat().flat())).toBeLessThanOrEqual(1000)
    expect(await screen.findByTestId('strokes-message')).toHaveTextContent(/draft/)
  })

  it('opens an existing form with its strokes and lets a reviewer sign it off', async () => {
    renderPanel(true)
    fireEvent.click(await screen.findByTestId('form-ب-isolated'))
    await waitFor(() => expect(screen.getByTestId('stroke-list').children).toHaveLength(2))
    expect(screen.getByDisplayValue('bowl')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('strokes-review'))
    await waitFor(() => expect(mockReview).toHaveBeenCalledWith('g1', 'lang-ar', true))
  })

  it('a font-derived form is retraced in its own em frame and keeps joins', async () => {
    mockList.mockResolvedValue({
      script: 'arabic',
      glyphs: [{
        id: 'g9', script: 'arabic', glyph: 'ب', form: 'initial', style: 'naskh',
        strokes: [[[120, 600], [60, 560], [0, 602]], [[55, 700], [65, 700]]],
        joins: { advance: 120, joins_next: true, exit: [0, 602], marks: 1 }, hints: ['body', 'dot'],
        source: 'provisional', reviewed: true,
      }],
      exemplars: [],
    })
    renderPanel(true)
    fireEvent.click(await screen.findByTestId('form-ب-initial'))
    await waitFor(() => expect(screen.getByTestId('stroke-list').children).toHaveLength(2))
    // Draw a fresh body across the canvas and a short dot, then save.
    fireEvent.click(screen.getAllByText('Clear')[0])
    const canvas = screen.getAllByTestId('ink-canvas')[0]
    fireEvent.pointerDown(canvas, { pointerId: 1, clientX: 200, clientY: 120 })
    fireEvent.pointerMove(canvas, { pointerId: 1, clientX: 100, clientY: 100 })
    fireEvent.pointerMove(canvas, { pointerId: 1, clientX: 30, clientY: 125 })
    fireEvent.pointerUp(canvas, { pointerId: 1, clientX: 30, clientY: 125 })
    fireEvent.pointerDown(canvas, { pointerId: 1, clientX: 110, clientY: 160 })
    fireEvent.pointerMove(canvas, { pointerId: 1, clientX: 114, clientY: 160 })
    fireEvent.pointerUp(canvas, { pointerId: 1, clientX: 114, clientY: 160 })
    fireEvent.click(screen.getByTestId('strokes-save'))
    await waitFor(() => expect(mockSave).toHaveBeenCalled())
    const args = mockSave.mock.calls[0][0]
    // Not re-fitted to the 1000 box: the ink stays around the template's
    // baseline (y ≈ 560–700), x from 0, with joins the composer can use.
    const ys = args.strokes.flat().map((p: number[]) => p[1])
    expect(Math.min(...ys)).toBeGreaterThan(450)
    expect(Math.max(...ys)).toBeLessThan(800)
    expect(Math.min(...args.strokes[0].map((p: number[]) => p[0]))).toBe(0)
    expect(args.joins.advance).toBeGreaterThan(0)
    expect(args.joins.marks).toBe(1)
    expect(args.joins.joins_next).toBe(true)
    expect(args.joins.exit).toEqual(expect.any(Array))
  })

  it('a bundled provisional form can be saved over but not reviewed or deleted', async () => {
    mockList.mockResolvedValue({
      script: 'arabic',
      glyphs: [{
        id: 'prov:arabic|ب|final|naskh', script: 'arabic', glyph: 'ب', form: 'final', style: 'naskh',
        strokes: [[[200, 600], [0, 602]]], joins: { advance: 200, joins_next: false, entry: [200, 600], marks: 0 },
        hints: ['body'], source: 'provisional', reviewed: true,
      }],
      exemplars: [],
    })
    renderPanel(true)
    expect(await screen.findByTestId('form-ب-final')).toHaveTextContent('≈')
    fireEvent.click(screen.getByTestId('form-ب-final'))
    await waitFor(() => expect(screen.getByTestId('stroke-list')).toBeInTheDocument())
    expect(screen.queryByTestId('strokes-review')).not.toBeInTheDocument()
    expect(screen.queryByText('Delete')).not.toBeInTheDocument()
    expect(screen.getByTestId('strokes-save')).toHaveTextContent('Save over it')
    expect(screen.getByText(/0 of 6 forms reviewed \(0 authored\)/)).toBeInTheDocument()
  })

  it('hides the review button from a plain contributor', async () => {
    renderPanel(false)
    fireEvent.click(await screen.findByTestId('form-ب-isolated'))
    await waitFor(() => expect(screen.getByTestId('stroke-list')).toBeInTheDocument())
    expect(screen.queryByTestId('strokes-review')).not.toBeInTheDocument()
  })
})
