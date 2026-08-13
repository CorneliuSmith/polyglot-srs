/**
 * Switching language mid-session has to change the CARDS, not just the chrome.
 *
 * The report, with a screenshot: the page furniture switched to Spanish
 * ("Tarjeta 1 de 5", "Pista") while the card still read English, and only
 * leaving the page and coming back fixed it.
 *
 * The cause was two doors to the same setting. The in-page picker called
 * onLocaleChanged and remounted the session; the globe in the header wrote
 * the profile and invalidated the queries — correct as far as it goes, but a
 * running session holds its card list in component state, so a refetch
 * behind it never reaches the screen. Watching the profile value itself
 * closes both doors, and any third one.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

const getDueCards = vi.fn()
const getProfile = vi.fn()

vi.mock('../api/review', () => ({
  getDueCards: (...a: unknown[]) => getDueCards(...a),
  getCramCards: vi.fn(async () => []),
  getSessionReadiness: vi.fn(async () => ({
    locale: 'es',
    learn: { total: 0, ready: 0, pct: 1, ready_enough: true },
    review: { total: 0, ready: 0, pct: 1, ready_enough: true },
  })),
  submitReview: vi.fn(),
  validateAnswer: vi.fn(),
  markCardKnown: vi.fn(),
}))
vi.mock('../api/profile', () => ({
  getProfile: () => getProfile(),
  updateProfile: vi.fn(async () => ({})),
  getLanguages: vi.fn(async () => []),
}))
vi.mock('../api/gym', () => ({
  recordGymAttempt: vi.fn(),
  generateGymDrills: vi.fn(),
}))
// TTS_LANGUAGES is a Set the component calls .has() on — an array here
// crashes the render before any assertion runs.
vi.mock('../api/audio', () => ({
  TTS_LANGUAGES: new Set<string>(),
  prefetchTTS: vi.fn(),
  prefetchTTSMany: vi.fn(),
}))

const { default: ReviewSessionPage } = await import(
  '../features/review/ReviewSessionPage'
)
const { usePrefsStore } = await import('../stores/prefsStore')

function card(translation: string) {
  return {
    id: 'c1', card_type: 'vocabulary', card_id: 'v1',
    sentence: 'Yo {{answer}} un libro.', correct_answer: 'leo',
    hint: null, translation, gloss: null, transliteration: null,
    morphology: null, alternatives: [], language_code: 'es',
    ease_factor: 2.5, interval: 0, repetitions: 0, streak: 0, lapses: 0,
    next_review: new Date().toISOString(),
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  // Hint layers are hidden at level 0, and the translation IS a hint
  // layer — the thing this test is about.
  usePrefsStore.setState({ activeLanguageId: 'lang-1', hintLevel: 3 })
})

function renderSession(qc: QueryClient) {
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ReviewSessionPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('changing the language mid-session re-serves the cards', () => {
  it('restarts the session when support_locale changes underneath it', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    getProfile.mockResolvedValue({ support_locale: 'en', ui_language: 'en' })
    getDueCards.mockResolvedValue([card('I read a book.')])

    renderSession(qc)
    expect(await screen.findByText('I read a book.')).toBeInTheDocument()

    // What the globe in the header does: write the profile, invalidate.
    // It never touched this page's own onLocaleChanged.
    getProfile.mockResolvedValue({ support_locale: 'es', ui_language: 'es' })
    getDueCards.mockResolvedValue([card('Leo un libro.')])
    await qc.invalidateQueries({ queryKey: ['profile'] })

    // Without the fix this stayed English until the page was left and
    // re-entered.
    expect(await screen.findByText('Leo un libro.')).toBeInTheDocument()
  })

  it('does not restart on first load, which would refetch the whole session', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    getProfile.mockResolvedValue({ support_locale: 'es', ui_language: 'es' })
    getDueCards.mockResolvedValue([card('Leo un libro.')])
    // Primed, as it is in production: the switcher and every page read the
    // same cached profile. With a COLD cache the due-cards key legitimately
    // changes once (en → es) and refetches — pre-existing behaviour, not
    // something this guard controls. Priming isolates the question actually
    // being asked: does the locale ARRIVING count as a change?
    qc.setQueryData(['profile'], { support_locale: 'es', ui_language: 'es' })

    renderSession(qc)
    await screen.findByText('Leo un libro.')
    await waitFor(() => expect(getDueCards).toHaveBeenCalledTimes(1))
  })

  it('does not restart when the profile refetches with the same locale', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    getProfile.mockResolvedValue({ support_locale: 'es', ui_language: 'es' })
    getDueCards.mockResolvedValue([card('Leo un libro.')])

    renderSession(qc)
    await screen.findByText('Leo un libro.')
    const before = getDueCards.mock.calls.length

    // Any unrelated profile write (there are many) must not blow away a
    // session in progress.
    await qc.invalidateQueries({ queryKey: ['profile'] })
    await waitFor(() => expect(getProfile).toHaveBeenCalledTimes(2))
    expect(getDueCards.mock.calls.length).toBe(before)
  })
})
