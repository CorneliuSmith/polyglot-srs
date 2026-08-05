import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TrailblazerWait from '../features/review/TrailblazerWait'
import { getSessionReadiness, getTrivia } from '../api/review'

vi.mock('../api/review', () => ({
  getSessionReadiness: vi.fn(),
  getTrivia: vi.fn(() => Promise.resolve([])),
  markTriviaSeen: vi.fn(() => Promise.resolve()),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) =>
      o && 'pct' in o ? `${k}:${o.pct}` : k,
  }),
}))

const mocked = vi.mocked(getSessionReadiness)
const mockTrivia = vi.mocked(getTrivia)

function lane(pct: number, ready_enough: boolean) {
  return { total: 10, ready: Math.round(pct * 10), pct, ready_enough }
}

function readiness(pct: number, ready_enough: boolean, pairs: string[] = []) {
  return {
    locale: 'es',
    threshold: 0.6,
    learn: lane(pct, ready_enough),
    review: lane(pct, ready_enough),
    pairs: pairs.map((w) => ({ word: w, gloss: `${w}-gloss` })),
  }
}

function renderWait(onStart = vi.fn(), stallAfterMs?: number) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  render(
    <QueryClientProvider client={client}>
      <TrailblazerWait
        languageId="lang-1"
        kind="learn"
        onStart={onStart}
        stallAfterMs={stallAfterMs}
      />
    </QueryClientProvider>,
  )
  return onStart
}

describe('TrailblazerWait', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // No trivia by default, so the older assertions still describe the
    // progress-only state they were written for.
    mockTrivia.mockResolvedValue([])
  })

  it('offers the wait without forcing it, and starting is always one tap away', async () => {
    mocked.mockResolvedValue(readiness(0.2, false))
    const onStart = renderWait()

    await screen.findByText('trailblazer.title')
    expect(onStart).not.toHaveBeenCalled()

    await userEvent.click(screen.getByText('trailblazer.startInEnglish'))
    expect(onStart).toHaveBeenCalled()
  })

  it('starts the session itself once the lane crosses the threshold', async () => {
    mocked.mockResolvedValue(readiness(0.8, true))
    const onStart = renderWait()
    await waitFor(() => expect(onStart).toHaveBeenCalled())
  })

  it('never blocks a session when the readiness check itself fails', async () => {
    mocked.mockRejectedValue(new Error('offline'))
    const onStart = renderWait()
    // One retry first — a flaky network shouldn't cost the wait screen.
    await waitFor(() => expect(onStart).toHaveBeenCalled(), { timeout: 4000 })
  })

  it('holds the game back until enough words have actually landed', async () => {
    // Two pairs is below the floor: anything else shown would be English,
    // which is exactly what the learner chose to wait out.
    mocked.mockResolvedValue(readiness(0.2, false, ['uno', 'dos']))
    renderWait()

    await userEvent.click(await screen.findByText('trailblazer.waitAndPlay'))
    expect(screen.getByText('trailblazer.firstWords')).toBeInTheDocument()
    expect(screen.queryByTestId('match-game')).not.toBeInTheDocument()
  })

  it('plays the words of the session being waited for', async () => {
    const pool = ['uno', 'dos', 'tres', 'cuatro', 'cinco']
    mocked.mockResolvedValue(readiness(0.4, false, pool))
    renderWait()

    await userEvent.click(await screen.findByText('trailblazer.waitAndPlay'))
    const game = await screen.findByTestId('match-game')
    // Every word appears with its gloss — the pool IS the upcoming batch,
    // so a learner with no cards at all still has something to play.
    for (const w of pool) {
      expect(screen.getByText(w)).toBeInTheDocument()
      expect(screen.getByText(`${w}-gloss`)).toBeInTheDocument()
    }
    expect(game).toBeInTheDocument()
  })

  it('scores a correct match and leaves a wrong one unmatched', async () => {
    mocked.mockResolvedValue(
      readiness(0.4, false, ['uno', 'dos', 'tres', 'cuatro']),
    )
    renderWait()
    await userEvent.click(await screen.findByText('trailblazer.waitAndPlay'))
    await screen.findByTestId('match-game')

    await userEvent.click(screen.getByText('uno'))
    await userEvent.click(screen.getByText('dos-gloss'))
    expect(screen.queryByText('trailblazer.matched')).not.toBeInTheDocument()

    await userEvent.click(screen.getByText('uno'))
    await userEvent.click(screen.getByText('uno-gloss'))
    await waitFor(() =>
      expect(screen.getByText('trailblazer.matched')).toBeInTheDocument(),
    )
  })

  it('reports how far along the fill is', async () => {
    mocked.mockResolvedValue(readiness(0.35, false))
    renderWait()
    await screen.findByText('trailblazer.progress:35')
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '35')
  })

  it('plays trivia when this session has nothing to play with yet', async () => {
    // 0% is exactly when someone sits here, and the match game needs some
    // of the session to exist. The trivia bank is shared per locale, so it
    // was stocked long before this learner arrived.
    mocked.mockResolvedValue(readiness(0, false))
    mockTrivia.mockResolvedValue([
      {
        id: 't1',
        question: '¿Cuántas lenguas se hablan hoy?',
        options: ['Unas 700', 'Unas 7.000', 'Unas 70.000'],
        answer_index: 1,
        fact: 'Cerca de la mitad tiene menos de 10.000 hablantes.',
      },
    ])
    renderWait()

    await userEvent.click(await screen.findByText('trailblazer.waitAndPlay'))
    await screen.findByTestId('trivia-game')
    await userEvent.click(screen.getByText('Unas 7.000'))
    // The payoff fact is the part worth remembering.
    expect(await screen.findByTestId('trivia-fact')).toHaveTextContent(
      /menos de 10.000 hablantes/,
    )
  })

  it('falls back to plain progress when the trivia bank is empty too', async () => {
    mocked.mockResolvedValue(readiness(0, false))
    mockTrivia.mockResolvedValue([])
    renderWait()

    await userEvent.click(await screen.findByText('trailblazer.waitAndPlay'))
    expect(await screen.findByText('trailblazer.firstWords')).toBeInTheDocument()
    expect(screen.queryByTestId('trivia-game')).not.toBeInTheDocument()
  })

  it('says so when the fill has stopped moving, instead of sitting at 0%', async () => {
    // A bar that never moves is indistinguishable from a hang, and every
    // cause of it (no provider key, course switched off, empty budget) is
    // invisible from this screen. Short window so the real path runs.
    mocked.mockResolvedValue(readiness(0, false))
    renderWait(vi.fn(), 50)
    expect(await screen.findByTestId('trailblazer-stalled')).toBeInTheDocument()
  })

  it('does not cry stall while rows are still landing', async () => {
    mocked.mockResolvedValue(readiness(0.3, false))
    renderWait(vi.fn(), 50)
    await screen.findByText('trailblazer.title')
    expect(screen.queryByTestId('trailblazer-stalled')).not.toBeInTheDocument()
  })
})
