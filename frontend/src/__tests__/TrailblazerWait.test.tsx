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
    t: (k: string, o?: Record<string, unknown>) => {
      if (o && 'pct' in o) return `${k}:${o.pct}`
      if (o && 'have' in o) return `${k}:${o.have}/${o.needed}`
      return k
    },
  }),
}))

const mocked = vi.mocked(getSessionReadiness)
const mockTrivia = vi.mocked(getTrivia)

/** Five cards, three of them needed to start — the shape the gate sees. */
function lane(pct: number, ready_enough: boolean, cards_ready = 0) {
  return {
    total: 10,
    ready: Math.round(pct * 10),
    pct,
    cards: 5,
    cards_ready,
    start_cards: 3,
    ready_enough,
  }
}

function readiness(
  pct: number,
  ready_enough: boolean,
  pairs: string[] = [],
  cardsReady = 0,
) {
  return {
    locale: 'es',
    threshold: 0.6,
    learn: lane(pct, ready_enough, cardsReady),
    review: lane(pct, ready_enough, cardsReady),
    pairs: pairs.map((w) => ({ word: w, gloss: `${w}-gloss` })),
  }
}

const onExit = vi.fn()

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
        onExit={onExit}
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

  it('counts down to the gate, not through the whole batch', async () => {
    // The bar has to track what opens the door. The batch percentage is a
    // different, much slower number — example sentences are the bulk of it
    // and are translated last — so showing that left someone watching "5 %"
    // with no way to tell they were one card from being let in.
    mocked.mockResolvedValue(readiness(0.05, false, [], 2))
    renderWait()
    await screen.findByText('trailblazer.cardsReady:2/3')
    // Two of the three cards needed.
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '67')
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

  it('lets someone leave who wants neither the wait nor English', async () => {
    // The tab bar is hidden on session routes, so before this the only
    // affordance was "Start in English" — a dead end for anyone who wanted
    // neither option, and on the native shells not even Back would help.
    mocked.mockResolvedValue(readiness(0, false))
    renderWait()
    // Wait for the wait screen proper: the loading state carries its own
    // copy of this control, and clicking that one leaves a detached node.
    await screen.findByText('trailblazer.title')
    await userEvent.click(screen.getByTestId('trailblazer-exit'))
    expect(onExit).toHaveBeenCalled()
  })

  it('offers the way out while readiness is still being fetched', async () => {
    // The "preparing…" state is where a hanging request strands someone,
    // and it is the state they are most likely to describe as stuck.
    mocked.mockReturnValue(new Promise(() => {}))
    renderWait()
    await userEvent.click(await screen.findByTestId('trailblazer-exit'))
    expect(onExit).toHaveBeenCalled()
  })

  it('still reports a stall when the window outlasts the poll interval', async () => {
    // The production case, and the one the other stall tests miss: the
    // window is 45s and the lane is polled every 5s. While the timer was
    // armed inside the effect that watches the query, every poll tore it
    // down and started a fresh one, so it never reached its own deadline —
    // a fill that had stopped sat at the same percentage forever without
    // ever admitting it. Both the shorter tests pass with that bug present,
    // because their window is shorter than one poll.
    mocked.mockResolvedValue(readiness(0.5, false))
    renderWait(vi.fn(), 6000)
    await screen.findByTestId('trailblazer-stalled', undefined, { timeout: 9000 })
  }, 12000)

  it('does not cry stall before the window is actually up', async () => {
    // The check runs on a repeating tick now, so the thing to guard is the
    // opposite mistake: reporting a stall the moment a poll comes back
    // unchanged. Nothing may appear until the full window has passed.
    mocked.mockResolvedValue(readiness(0.3, false))
    renderWait(vi.fn(), 10_000)
    await screen.findByText('trailblazer.title')
    await new Promise((r) => setTimeout(r, 250))
    expect(screen.queryByTestId('trailblazer-stalled')).not.toBeInTheDocument()
  })

  it('takes the stall notice back down as soon as rows land again', async () => {
    // A stall is a guess, and a slow fill that resumes must be able to
    // withdraw it — otherwise the first quiet stretch marks the screen dead
    // for the rest of the wait.
    mocked.mockResolvedValue(readiness(0.3, false))
    renderWait(vi.fn(), 200)
    await screen.findByTestId('trailblazer-stalled')
    // A later poll reports more rows ready. That is movement, and it must
    // reset the clock rather than being ignored because a stall was
    // already showing.
    mocked.mockResolvedValue(readiness(0.5, false, [], 1))
    await waitFor(
      () => expect(screen.getByText('trailblazer.cardsReady:1/3')).toBeInTheDocument(),
      { timeout: 8000 },
    )
    expect(screen.queryByTestId('trailblazer-stalled')).not.toBeInTheDocument()
  }, 12000)
})
