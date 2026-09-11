import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import WritePage from '../features/write/WritePage'

// jsdom has no 2D canvas either; the component guards for a null context,
// and the stub keeps jsdom's "not implemented" noise out of the output.
HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext

// jsdom has no PointerEvent, and testing-library's fallback Event carries
// no clientX/clientY — every point would be NaN and no ink would register.
// A MouseEvent with a pointerId is all the canvas reads.
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

vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (sel: (s: Record<string, unknown>) => unknown) =>
      sel({ activeLanguageId: 'lang-ru' }),
  ),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn().mockResolvedValue([
    { id: 'lang-ru', code: 'ru', name: 'Russian', rtl: false, is_visible: true },
  ]),
}))
vi.mock('../api/write', () => ({
  getWriteStatus: vi.fn(),
  getWritePrompts: vi.fn(),
  assessWriting: vi.fn(),
  confirmWriting: vi.fn(),
}))
// jsdom has no canvas; the export is the seam.
vi.mock('../features/write/inkExport', () => ({
  renderInkToPng: vi.fn().mockResolvedValue(new Blob(['png'], { type: 'image/png' })),
}))

import { assessWriting, confirmWriting, getWritePrompts, getWriteStatus } from '../api/write'
const mockStatus = getWriteStatus as ReturnType<typeof vi.fn>
const mockConfirm = confirmWriting as ReturnType<typeof vi.fn>
const mockPrompts = getWritePrompts as ReturnType<typeof vi.fn>
const mockAssess = assessWriting as ReturnType<typeof vi.fn>

const ALLOWANCE = {
  tier: 'unlimited', unlimited: true, entitled: true,
  limit: null, used: 0, remaining: null, resets_at: null,
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <WritePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/** Draw a few letters' worth of strokes on the canvas. */
function scribble(canvas: HTMLElement, n = 4) {
  for (let i = 0; i < n; i++) {
    const x = 30 + i * 40
    fireEvent.pointerDown(canvas, { pointerId: 1, clientX: x, clientY: 60 })
    fireEvent.pointerMove(canvas, { pointerId: 1, clientX: x + 2, clientY: 100 })
    fireEvent.pointerMove(canvas, { pointerId: 1, clientX: x + 4, clientY: 140 })
    fireEvent.pointerUp(canvas, { pointerId: 1, clientX: x + 4, clientY: 140 })
  }
}

describe('WritePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStatus.mockResolvedValue({ available: true, allowance: ALLOWANCE })
    mockPrompts.mockResolvedValue([
      { prompt: 'I am going home.', answer: 'Я иду домой', source: 'own' },
    ])
  })

  it('shows a sentence to write and will not check an empty canvas', async () => {
    renderPage()
    expect(await screen.findByTestId('write-prompt')).toHaveTextContent('I am going home.')
    expect(screen.getByTestId('write-check')).toBeDisabled()
    expect(screen.queryByTestId('neatness')).not.toBeInTheDocument()
  })

  it('defaults Russian to cursive, because that is what Russians write', async () => {
    renderPage()
    await screen.findByTestId('write-prompt')
    await waitFor(() =>
      expect(screen.getByTestId('style-cursive')).toHaveAttribute('aria-pressed', 'true'),
    )
  })

  it('measures neatness on the device as soon as there is ink', async () => {
    renderPage()
    await screen.findByTestId('write-prompt')
    scribble(screen.getByTestId('ink-canvas'))
    expect(screen.getByTestId('neatness')).toBeInTheDocument()
    expect(screen.getByTestId('neat-baseline')).toHaveTextContent('steady')
    expect(screen.getByTestId('write-check')).toBeEnabled()
    // Nothing has been sent anywhere.
    expect(mockAssess).not.toHaveBeenCalled()
  })

  it('sends the ink with the expected text and shows what was read', async () => {
    mockAssess.mockResolvedValue({
      transcription: 'Я иду домой', matches_target: true, word_diffs: [],
      legibility: 4, letterform_notes: [{ letter: 'д', note: 'Close the loop.' }],
      confidence: 'high', expected: 'Я иду домой', adapt: true, allowance: ALLOWANCE,
    })
    renderPage()
    await screen.findByTestId('write-prompt')
    scribble(screen.getByTestId('ink-canvas'))
    fireEvent.click(screen.getByTestId('write-check'))
    expect(await screen.findByTestId('write-read-as')).toHaveTextContent('Я иду домой')
    expect(screen.getByTestId('write-verdict')).toHaveTextContent('Correct')
    expect(screen.getByText('Close the loop.')).toBeInTheDocument()
    // The compare line shows the expected text in the written hand.
    expect(screen.getByTestId('write-compare')).toHaveTextContent('Я иду домой')
    const args = mockAssess.mock.calls[0][0]
    expect(args).toMatchObject({
      languageId: 'lang-ru', expected: 'Я иду домой', kind: 'sentence', style: 'cursive',
    })
    expect(args.image).toBeInstanceOf(Blob)
  })

  it('shows a misread as a misread, never as a fail', async () => {
    mockAssess.mockResolvedValue({
      transcription: 'Я иду домои', matches_target: false,
      word_diffs: [{ expected: 'домой', written: 'домои', note: 'й has a breve.' }],
      legibility: 2, letterform_notes: [], confidence: 'low',
      expected: 'Я иду домой', adapt: true, allowance: ALLOWANCE,
    })
    renderPage()
    await screen.findByTestId('write-prompt')
    scribble(screen.getByTestId('ink-canvas'))
    fireEvent.click(screen.getByTestId('write-check'))
    expect(await screen.findByTestId('write-verdict')).toHaveTextContent(/not sure/i)
    expect(screen.getByText('домой')).toBeInTheDocument()
  })

  it('lets the learner write their own text, and nothing at all', async () => {
    mockAssess.mockResolvedValue({
      transcription: 'привет', matches_target: true, word_diffs: [],
      legibility: 5, letterform_notes: [], confidence: 'high',
      expected: 'привет', adapt: true, allowance: ALLOWANCE,
    })
    renderPage()
    await screen.findByTestId('write-prompt')
    fireEvent.click(screen.getByTestId('kind-own'))
    fireEvent.change(screen.getByTestId('write-own'), { target: { value: ' привет ' } })
    scribble(screen.getByTestId('ink-canvas'))
    fireEvent.click(screen.getByTestId('write-check'))
    await screen.findByTestId('write-result')
    expect(mockAssess.mock.calls[0][0]).toMatchObject({ expected: 'привет', kind: 'sentence' })

    fireEvent.click(screen.getByTestId('kind-free'))
    scribble(screen.getByTestId('ink-canvas'))
    fireEvent.click(screen.getByTestId('write-check'))
    await waitFor(() => expect(mockAssess).toHaveBeenCalledTimes(2))
    expect(mockAssess.mock.calls[1][0]).toMatchObject({ expected: null, kind: 'free' })
  })

  it('says so when checking is off, and keeps the canvas', async () => {
    mockStatus.mockResolvedValue({ available: false, allowance: null })
    renderPage()
    expect(await screen.findByTestId('write-unavailable')).toBeInTheDocument()
    scribble(screen.getByTestId('ink-canvas'))
    expect(screen.getByTestId('neatness')).toBeInTheDocument()
    expect(screen.getByTestId('write-check')).toBeDisabled()
  })

  it('says when there is nothing to write yet', async () => {
    mockPrompts.mockResolvedValue([])
    renderPage()
    expect(await screen.findByTestId('write-no-prompts')).toBeInTheDocument()
  })

  it('lets the writer overrule a misread, and sends how the ink was made', async () => {
    mockAssess.mockResolvedValue({
      transcription: 'ين', matches_target: false,
      word_diffs: [{ expected: 'أن', written: 'ين', note: 'hamza' }],
      legibility: 2, letterform_notes: [{ letter: 'أ', note: 'floating hamza' }],
      confidence: 'low', expected: 'أن', adapt: true, allowance: ALLOWANCE,
    })
    mockConfirm.mockResolvedValue({ kept: true, samples: 3 })
    renderPage()
    await screen.findByTestId('write-prompt')
    scribble(screen.getByTestId('ink-canvas'))
    fireEvent.click(screen.getByTestId('write-check'))
    const confirm = await screen.findByTestId('write-confirm')
    // Strokes ride along with the Check, compacted.
    expect(mockAssess.mock.calls[0][0].strokes.length).toBe(4)
    fireEvent.click(confirm)
    expect(await screen.findByTestId('write-learned')).toHaveTextContent(/3 samples/)
    const args = mockConfirm.mock.calls[0][0]
    expect(args).toMatchObject({ languageId: 'lang-ru', text: 'أن', letters: ['أ'] })
    expect(args.strokes.length).toBe(4)
    expect(args.image).toBeInstanceOf(Blob)
  })

  it('offers no confirm button when the reader is not learning the hand', async () => {
    mockAssess.mockResolvedValue({
      transcription: 'x', matches_target: false, word_diffs: [], legibility: 2,
      letterform_notes: [], confidence: 'low', expected: 'y', adapt: false, allowance: ALLOWANCE,
    })
    renderPage()
    await screen.findByTestId('write-prompt')
    scribble(screen.getByTestId('ink-canvas'))
    fireEvent.click(screen.getByTestId('write-check'))
    await screen.findByTestId('write-result')
    expect(screen.queryByTestId('write-confirm')).not.toBeInTheDocument()
  })

  it('free writing confirms an editable reading', async () => {
    mockAssess.mockResolvedValue({
      transcription: 'привет', matches_target: true, word_diffs: [], legibility: 4,
      letterform_notes: [], confidence: 'medium', expected: null, adapt: true, allowance: ALLOWANCE,
    })
    mockConfirm.mockResolvedValue({ kept: true, samples: 1 })
    renderPage()
    await screen.findByTestId('write-prompt')
    fireEvent.click(screen.getByTestId('kind-free'))
    scribble(screen.getByTestId('ink-canvas'))
    fireEvent.click(screen.getByTestId('write-check'))
    // No "Correct" badge for free writing — the reader cannot know; the
    // writer is asked instead.
    expect(await screen.findByTestId('write-verdict')).not.toHaveTextContent(/^Correct$/)
    expect(screen.getByText(/Is this what you wrote/)).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('write-not-it'))
    const box = await screen.findByTestId('write-confirm-text')
    expect(box).toHaveValue('привет')
    fireEvent.change(box, { target: { value: 'привет!' } })
    fireEvent.click(screen.getByTestId('write-confirm'))
    await waitFor(() => expect(mockConfirm).toHaveBeenCalled())
    expect(mockConfirm.mock.calls[0][0].text).toBe('привет!')
  })

  it('free writing: "yes" confirms the reading as read', async () => {
    mockAssess.mockResolvedValue({
      transcription: 'أنا', matches_target: true, word_diffs: [], legibility: 3,
      letterform_notes: [], confidence: 'high', expected: null, adapt: true, allowance: ALLOWANCE,
    })
    mockConfirm.mockResolvedValue({ kept: true, samples: 2 })
    renderPage()
    await screen.findByTestId('write-prompt')
    fireEvent.click(screen.getByTestId('kind-free'))
    scribble(screen.getByTestId('ink-canvas'))
    fireEvent.click(screen.getByTestId('write-check'))
    fireEvent.click(await screen.findByTestId('write-confirm'))
    await waitFor(() => expect(mockConfirm).toHaveBeenCalled())
    expect(mockConfirm.mock.calls[0][0].text).toBe('أنا')
  })
})

