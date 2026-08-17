import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ReadingWait from '../features/reader/ReadingWait'
import ReadingReadyBanner from '../components/ReadingReadyBanner'
import { usePendingReadingStore } from '../stores/pendingReadingStore'

vi.mock('../api/review', () => ({
  getDueCards: vi.fn(() => Promise.resolve([])),
  getTrivia: vi.fn(() => Promise.resolve([])),
  markTriviaSeen: vi.fn(() => Promise.resolve()),
}))

import { getDueCards } from '../api/review'

const mockDue = getDueCards as ReturnType<typeof vi.fn>

function reset() {
  usePendingReadingStore.setState({ pending: null, ready: null, error: false })
}

function wrap(ui: React.ReactNode, route = '/read') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="*" element={<>{ui}</>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ---------------------------------------------------------------------------
// The store — the whole point is that it outlives the page
// ---------------------------------------------------------------------------

describe('pendingReadingStore', () => {
  beforeEach(reset)

  const job = {
    topic: 'cats',
    languageId: 'lang-es',
    languageCode: 'es',
    startedAt: 1,
  }
  const result = { id: 'r-1', reading: { title: 'Gatos' }, level: 'A1' }

  it('holds the job while it runs, then the finished reading', async () => {
    let settle: (v: typeof result) => void = () => {}
    const promise = new Promise<typeof result>((res) => (settle = res))
    usePendingReadingStore.getState().start(job, promise as never)

    expect(usePendingReadingStore.getState().pending).toEqual(job)
    settle(result)
    await waitFor(() =>
      expect(usePendingReadingStore.getState().ready).toMatchObject({
        id: 'r-1',
        topic: 'cats',
        level: 'A1',
      }),
    )
    expect(usePendingReadingStore.getState().pending).toBeNull()
  })

  it('a failure clears the job and raises the error flag', async () => {
    usePendingReadingStore
      .getState()
      .start(job, Promise.reject(new Error('boom')) as never)
    await waitFor(() =>
      expect(usePendingReadingStore.getState().error).toBe(true),
    )
    expect(usePendingReadingStore.getState().pending).toBeNull()
  })

  it('claim hands over the reading exactly once', async () => {
    usePendingReadingStore.getState().start(job, Promise.resolve(result) as never)
    await waitFor(() => expect(usePendingReadingStore.getState().ready).toBeTruthy())
    expect(usePendingReadingStore.getState().claim()?.id).toBe('r-1')
    expect(usePendingReadingStore.getState().claim()).toBeNull()
  })

  it('a stale result never lands after a newer job replaced it', async () => {
    const slow = new Promise<typeof result>((res) =>
      setTimeout(() => res({ ...result, id: 'stale' }), 5),
    )
    usePendingReadingStore.getState().start(job, slow as never)
    // The learner asked for something else before the first finished.
    const newer = { ...job, topic: 'dogs', startedAt: 2 }
    usePendingReadingStore.getState().start(newer, new Promise(() => {}) as never)

    await new Promise((r) => setTimeout(r, 20))
    expect(usePendingReadingStore.getState().ready).toBeNull()
    expect(usePendingReadingStore.getState().pending).toEqual(newer)
  })
})

// ---------------------------------------------------------------------------
// The wait panel
// ---------------------------------------------------------------------------

describe('ReadingWait', () => {
  beforeEach(() => {
    reset()
    vi.clearAllMocks()
    mockDue.mockResolvedValue([])
  })

  it('offers both a game and a review run while the text is written', () => {
    wrap(<ReadingWait languageId="lang-es" topic="cats" />)
    expect(screen.getByTestId('reading-wait')).toBeDefined()
    expect(screen.getByText(/writing about/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /play while you wait/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /review while you wait/i })).toBeDefined()
    // The promise that makes leaving safe.
    expect(screen.getByText(/tell you the moment it's ready/i)).toBeDefined()
  })

  it('plays the match game over the learner’s own due words', async () => {
    mockDue.mockResolvedValue([
      { correct_answer: 'gato', gloss: 'cat' },
      { correct_answer: 'perro', gloss: 'dog' },
      { correct_answer: 'casa', gloss: 'house' },
      { correct_answer: 'libro', gloss: 'book' },
      { correct_answer: 'agua', gloss: 'water' },
    ])
    wrap(<ReadingWait languageId="lang-es" topic="cats" />)
    // Nothing is fetched until they actually ask to play.
    expect(mockDue).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /play while you wait/i }))
    expect(await screen.findByTestId('match-game')).toBeDefined()
    // The board fills a tick later (the round is armed in a timeout so a
    // cleared board can breathe before the next one).
    expect(await screen.findByRole('button', { name: 'gato' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'cat' })).toBeDefined()
  })

  it('falls back to trivia when nothing is due to match', async () => {
    const { getTrivia } = await import('../api/review')
    ;(getTrivia as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: 'q1',
        question: 'Which language has the most speakers?',
        options: ['a', 'b', 'c'],
        answer_index: 0,
      },
    ])
    wrap(<ReadingWait languageId="lang-es" topic="cats" />)
    fireEvent.click(screen.getByRole('button', { name: /play while you wait/i }))
    expect(await screen.findByTestId('trivia-game')).toBeDefined()
  })

  it('asks for notification permission only when the learner leaves', () => {
    const requestPermission = vi.fn()
    vi.stubGlobal('Notification', {
      permission: 'default',
      requestPermission,
    })
    wrap(<ReadingWait languageId="lang-es" topic="cats" />)
    // Not on render — an unprompted permission dialog is the pattern this
    // deliberately avoids.
    expect(requestPermission).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /review while you wait/i }))
    expect(requestPermission).toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})

// ---------------------------------------------------------------------------
// The banner — how a finished text finds a learner who wandered off
// ---------------------------------------------------------------------------

describe('ReadingReadyBanner', () => {
  beforeEach(reset)
  afterEach(() => vi.unstubAllGlobals())

  const ready = {
    id: 'r-1',
    reading: { title: 'Gatos' } as never,
    topic: 'cats',
    level: 'A1',
  }

  it('shows nothing while no text is waiting to be read', () => {
    wrap(<ReadingReadyBanner />, '/')
    expect(screen.queryByTestId('reading-ready-banner')).toBeNull()
  })

  it('announces a finished text wherever the learner went', () => {
    usePendingReadingStore.setState({ ready })
    wrap(<ReadingReadyBanner />, '/')
    expect(screen.getByTestId('reading-ready-banner')).toBeDefined()
    expect(screen.getByText(/your text is ready/i)).toBeDefined()
    expect(screen.getByText(/cats/)).toBeDefined()
  })

  it('stays quiet on the Reader itself — the page shows the text', () => {
    usePendingReadingStore.setState({ ready })
    wrap(<ReadingReadyBanner />, '/read')
    expect(screen.queryByTestId('reading-ready-banner')).toBeNull()
  })

  it('never lands on top of someone mid-session', () => {
    usePendingReadingStore.setState({ ready })
    wrap(<ReadingReadyBanner />, '/review')
    expect(screen.queryByTestId('reading-ready-banner')).toBeNull()
  })

  it('dismissing drops the text without opening it', () => {
    usePendingReadingStore.setState({ ready })
    wrap(<ReadingReadyBanner />, '/')
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(usePendingReadingStore.getState().ready).toBeNull()
  })

  it('fires a browser notification only when the tab is hidden', () => {
    const ctor = vi.fn()
    vi.stubGlobal(
      'Notification',
      Object.assign(ctor, { permission: 'granted' }),
    )
    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)

    usePendingReadingStore.setState({ ready })
    const first = wrap(<ReadingReadyBanner />, '/')
    expect(ctor).not.toHaveBeenCalled() // they're looking right at it
    first.unmount()

    hidden.mockReturnValue(true)
    usePendingReadingStore.setState({ ready: { ...ready, id: 'r-2' } })
    wrap(<ReadingReadyBanner />, '/')
    expect(ctor).toHaveBeenCalled()
    hidden.mockRestore()
  })
})
