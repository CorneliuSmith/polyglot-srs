import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('../api/onboarding', () => ({
  placementNext: vi.fn(),
  setLearnerLevel: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ qwertyTranslit: {} }),
  ),
}))

import PlacementTest from '../features/onboarding/PlacementTest'
import { placementNext, setLearnerLevel } from '../api/onboarding'

const mockNext = placementNext as ReturnType<typeof vi.fn>
const mockSetLevel = setLearnerLevel as ReturnType<typeof vi.fn>

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
