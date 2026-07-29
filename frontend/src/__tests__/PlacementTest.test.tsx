import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('../api/onboarding', () => ({
  placementNext: vi.fn(),
  setLearnerLevel: vi.fn(),
  getWritingAvailability: vi.fn(() => Promise.resolve({ available: true })),
  assessWritingSample: vi.fn(),
}))
vi.mock('../api/health', () => ({
  getSchemaHealth: vi.fn(() => Promise.resolve(null)),
  pendingMigrationNote: vi.fn(() => null),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ qwertyTranslit: {} }),
  ),
}))

import PlacementTest from '../features/onboarding/PlacementTest'
import {
  assessWritingSample,
  getWritingAvailability,
  placementNext,
  setLearnerLevel,
} from '../api/onboarding'

const mockNext = placementNext as ReturnType<typeof vi.fn>
const mockSetLevel = setLearnerLevel as ReturnType<typeof vi.fn>
const mockAssess = assessWritingSample as ReturnType<typeof vi.fn>
const mockWritingOffer = getWritingAvailability as ReturnType<typeof vi.fn>

const LANGUAGE = {
  id: 'lang-la', code: 'la', name: 'Latin', rtl: false, is_visible: true,
}

function renderTest(onClose = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <PlacementTest language={LANGUAGE} onClose={onClose} />
    </QueryClientProvider>,
  )
  return onClose
}

const item = (id: string, prompt: string) => ({
  id, kind: 'vocabulary' as const, level: 'A2', prompt, translation: null,
})

describe('PlacementTest', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSetLevel.mockResolvedValue({ level: 'B1', subscribed: 3, unsubscribed: 0 })
  })

  it('walks the adaptive staircase, replaying the answer history', async () => {
    mockNext
      .mockResolvedValueOnce({
        available: true, done: false, asked: 0, max_items: 12, item: item('i1', 'water'),
      })
      .mockResolvedValueOnce({
        available: true, done: false, asked: 1, max_items: 12, item: item('i2', 'bread'),
      })
    renderTest()
    expect(await screen.findByText('water')).toBeDefined()

    fireEvent.change(screen.getByLabelText('water'), { target: { value: 'aqua' } })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    expect(await screen.findByText('bread')).toBeDefined()
    expect(mockNext).toHaveBeenLastCalledWith('lang-la', [{ id: 'i1', input: 'aqua' }])
  })

  it('"I don\'t know" submits an empty answer rather than blocking', async () => {
    mockNext
      .mockResolvedValueOnce({
        available: true, done: false, asked: 0, item: item('i1', 'water'),
      })
      .mockResolvedValueOnce({
        available: true, done: true, asked: 1, estimated_level: 'A1', per_level: {},
      })
    renderTest()
    await screen.findByText('water')
    fireEvent.click(screen.getByRole('button', { name: /don.t know/i }))
    await waitFor(() =>
      expect(mockNext).toHaveBeenLastCalledWith('lang-la', [{ id: 'i1', input: '' }]),
    )
  })

  it('shows the estimate and only changes the level when asked to', async () => {
    mockNext.mockResolvedValue({
      available: true, done: true, asked: 6,
      estimated_level: 'B1', per_level: {}, attempt: 1, previous_level: null,
    })
    renderTest()
    const result = await screen.findByTestId('placement-result')
    expect(result.textContent).toMatch(/looks about\s*B1/)
    // Nothing re-seated until the learner presses the button.
    expect(mockSetLevel).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /set me to B1/i }))
    await waitFor(() => expect(mockSetLevel).toHaveBeenCalledWith('lang-la', 'B1'))
  })

  it('"Keep my level" closes without touching the decks', async () => {
    mockNext.mockResolvedValue({
      available: true, done: true, asked: 6, estimated_level: 'B1', per_level: {},
    })
    const onClose = renderTest()
    await screen.findByTestId('placement-result')
    fireEvent.click(screen.getByRole('button', { name: /keep my level/i }))
    expect(mockSetLevel).not.toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })

  it('a retake reports the movement against the previous estimate', async () => {
    mockNext.mockResolvedValue({
      available: true, done: true, asked: 7,
      estimated_level: 'B1', per_level: {}, attempt: 2, previous_level: 'A2',
    })
    renderTest()
    await screen.findByTestId('placement-result')
    expect(screen.getByText(/one level up from A2/i)).toBeDefined()
  })

  it('a language with too little content says so instead of hanging', async () => {
    mockNext.mockResolvedValue({
      available: false, done: true, estimated_level: null, per_level: {}, asked: 0,
    })
    renderTest()
    expect(await screen.findByText(/not enough latin content/i)).toBeDefined()
  })
})

describe('PlacementTest escape hatches', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSetLevel.mockResolvedValue({ level: 'B1', subscribed: 0, unsubscribed: 0 })
  })

  it('a failed start is closable — a modal with no way out is a trap', async () => {
    // Owner report: "the popup does not disappear". The error state rendered
    // a bare message with no button, behind a full-screen overlay.
    mockNext.mockRejectedValue(new Error('500'))
    const onClose = vi.fn()
    renderTest(onClose)
    expect(await screen.findByText(/couldn.t start the test/i)).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('a failed start offers a retry without reopening the dialog', async () => {
    mockNext.mockRejectedValue(new Error('500'))
    renderTest()
    await screen.findByText(/couldn.t start the test/i)
    mockNext.mockClear()
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    await waitFor(() => expect(mockNext).toHaveBeenCalledWith('lang-la', []))
  })

  it('is cancellable while still loading', async () => {
    // A hung request must not trap the learner either.
    mockNext.mockImplementation(() => new Promise(() => {}))
    const onClose = vi.fn()
    renderTest(onClose)
    fireEvent.click(await screen.findByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalled()
  })
})

describe('PlacementTest names a pending migration instead of shrugging', () => {
  it('shows which migration is missing when that is the cause', async () => {
    const { pendingMigrationNote } = await import('../api/health')
    ;(pendingMigrationNote as ReturnType<typeof vi.fn>).mockReturnValue(
      'The database is behind this build — 20260902000000_placement_attempts.sql hasn\u2019t been applied yet.',
    )
    mockNext.mockRejectedValue(new Error('500'))
    renderTest()
    expect(
      await screen.findByText(/20260902000000_placement_attempts\.sql/),
    ).toBeDefined()
    // Still escapable.
    expect(screen.getByRole('button', { name: /close/i })).toBeDefined()
    ;(pendingMigrationNote as ReturnType<typeof vi.fn>).mockReturnValue(null)
  })

  it('falls back to the generic message when the schema is fine', async () => {
    mockNext.mockRejectedValue(new Error('network'))
    renderTest()
    expect(
      await screen.findByText(/something went wrong reaching the server/i),
    ).toBeDefined()
  })
})

describe('PlacementTest input method', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNext.mockResolvedValue({
      available: true, done: false, asked: 0, max_items: 12,
      item: { id: 'i1', kind: 'vocabulary', level: 'A2', prompt: 'water', translation: null },
    })
  })

  it('every item is typed — there is no multiple choice', async () => {
    renderTest()
    expect(await screen.findByLabelText('water')).toBeDefined()
    // The only way past an item is typing it or declaring you don't know.
    expect(screen.getByRole('button', { name: /don.t know/i })).toBeDefined()
  })

  it('offers the on-screen keyboard for a non-Latin script', async () => {
    // Placement asks the learner to TYPE the target language. Without this a
    // Persian learner on a phone had no way to produce the script at all, so
    // the test measured keyboard availability rather than knowledge.
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <PlacementTest
          language={{ id: 'lang-fa', code: 'fa', name: 'Persian', rtl: true, is_visible: true }}
          onClose={vi.fn()}
        />
      </QueryClientProvider>,
    )
    await screen.findByLabelText('water')
    expect(screen.getByTestId('on-screen-keyboard')).toBeDefined()
    expect(screen.getByRole('button', { name: /hide keyboard/i })).toBeDefined()
  })

  it('does not offer one for a language that has no layout', async () => {
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <PlacementTest
          language={{ id: 'lang-en', code: 'en', name: 'English', rtl: false, is_visible: true }}
          onClose={vi.fn()}
        />
      </QueryClientProvider>,
    )
    await screen.findByLabelText('water')
    expect(screen.queryByTestId('on-screen-keyboard')).toBeNull()
  })

  it('keyboard presses reach the answer box', async () => {
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <PlacementTest
          language={{ id: 'lang-fa', code: 'fa', name: 'Persian', rtl: true, is_visible: true }}
          onClose={vi.fn()}
        />
      </QueryClientProvider>,
    )
    await screen.findByLabelText('water')
    const kb = screen.getByTestId('on-screen-keyboard')
    const key = kb.querySelector('[data-skbtn="\u0628"]') as HTMLElement
    expect(key, 'expected a Persian key').toBeTruthy()
    fireEvent.mouseDown(key)
    await waitFor(() =>
      expect((screen.getByLabelText('water') as HTMLInputElement).value).toContain('\u0628'),
    )
  })
})

describe('PlacementTest written route', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockWritingOffer.mockResolvedValue({ available: true })
    mockSetLevel.mockResolvedValue({ level: 'C1', subscribed: 0, unsubscribed: 0 })
    mockNext.mockResolvedValue({
      available: true, done: false, asked: 0, max_items: 12,
      item: { id: 'i1', kind: 'vocabulary', level: 'A2', prompt: 'water', translation: null },
    })
  })

  it('offers writing a paragraph as an alternative to the questions', async () => {
    renderTest()
    expect(await screen.findByText(/rather write a paragraph/i)).toBeDefined()
  })

  it('assesses the paragraph and offers the level it demonstrates', async () => {
    // A paragraph shows complexity a per-item staircase cannot: the point is
    // that a real C1 can reach C1 here.
    mockAssess.mockResolvedValue({
      level: 'C1',
      notes: 'You sustain subordination across several clauses.',
      focus: ['aspect contrast', 'discourse connectives'],
    })
    renderTest()
    fireEvent.click(await screen.findByText(/rather write a paragraph/i))
    const box = await screen.findByLabelText(/your latin writing/i)
    fireEvent.change(box, { target: { value: 'Cum in urbem venissem, omnia mutata erant.' } })
    fireEvent.click(screen.getByRole('button', { name: /assess my writing/i }))

    expect(await screen.findByText(/looks about/i)).toBeDefined()
    expect(screen.getByText(/subordination/i)).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: /set me to C1/i }))
    await waitFor(() => expect(mockSetLevel).toHaveBeenCalledWith('lang-la', 'C1'))
  })

  it('counts words, so the learner can see they have written enough', async () => {
    renderTest()
    fireEvent.click(await screen.findByText(/rather write a paragraph/i))
    fireEvent.change(await screen.findByLabelText(/your latin writing/i), {
      target: { value: 'una duo tria' },
    })
    expect(await screen.findByText('3 words')).toBeDefined()
  })

  it('can go back to the questions', async () => {
    renderTest()
    fireEvent.click(await screen.findByText(/rather write a paragraph/i))
    fireEvent.click(await screen.findByRole('button', { name: /back to the questions/i }))
    expect(await screen.findByLabelText('water')).toBeDefined()
  })

  it('stays hidden when the account is not offered the assessment', async () => {
    // Token guard: the call costs a model request, so it is entitlement-gated.
    mockWritingOffer.mockResolvedValue({ available: false })
    renderTest()
    await screen.findByLabelText('water')
    expect(screen.queryByText(/rather write a paragraph/i)).toBeNull()
  })
})
