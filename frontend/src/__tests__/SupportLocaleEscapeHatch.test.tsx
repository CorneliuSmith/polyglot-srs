/**
 * An English speaker studying Spanish was shown ARABIC translations, with no
 * way to turn them off.
 *
 * Two things had drifted apart. `support_locale` began life as "I'm learning
 * English FROM this language", so every control that sets it was gated on
 * `studyingEnglish` — the active course being English. Later the backend
 * generalised it: `cards.py _effective_locale` now applies support_locale to
 * EVERY course, and the globe in the header writes it for everyone on every
 * UI-language change.
 *
 * So the setting stayed live on a Spanish course while its only off-switch
 * was hidden, and the languages query behind the picker was `enabled:
 * studyingEnglish` — meaning even if the control had rendered, it would have
 * had no options in it. The learner could see the damage and not reach the
 * lever.
 *
 * These tests pinned the lever open INSIDE a running session.
 *
 * The owner has since removed it from Learn and Review — a language control
 * mid-session re-fetches the very cards the learner is part-way through,
 * which is its own kind of broken. So the rule is now narrower rather than
 * reversed: the lever must exist, it must not live inside a session.
 *
 * It lives in Settings, and the globe — a wordless icon, which is what
 * makes it usable by someone who cannot read the current UI — is on every
 * page that is not a running session. That is the escape hatch. This file
 * now guards the new shape: no picker in the session, and no reintroducing
 * one without reading the incident above.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

const getDueCards = vi.fn()
const getProfile = vi.fn()
const getLanguages = vi.fn()
const updateProfile = vi.fn()

vi.mock('../api/review', () => ({
  getDueCards: (...a: unknown[]) => getDueCards(...a),
  getCramCards: vi.fn(async () => []),
  getSessionReadiness: vi.fn(async () => ({
    locale: 'en',
    learn: { total: 0, ready: 0, pct: 1, ready_enough: true },
    review: { total: 0, ready: 0, pct: 1, ready_enough: true },
  })),
  submitReview: vi.fn(),
  validateAnswer: vi.fn(),
  markCardKnown: vi.fn(),
}))
vi.mock('../api/profile', () => ({
  getProfile: () => getProfile(),
  updateProfile: (...a: unknown[]) => updateProfile(...a),
  getLanguages: () => getLanguages(),
}))
vi.mock('../api/gym', () => ({
  recordGymAttempt: vi.fn(),
  generateGymDrills: vi.fn(),
}))
vi.mock('../api/audio', () => ({
  TTS_LANGUAGES: new Set<string>(),
  prefetchTTS: vi.fn(),
  prefetchTTSMany: vi.fn(),
}))

const { default: ReviewSessionPage } = await import(
  '../features/review/ReviewSessionPage'
)
const { usePrefsStore } = await import('../stores/prefsStore')

const LANGUAGES = [
  { id: 'lang-es', code: 'es', name: 'Spanish' },
  { id: 'lang-ar', code: 'ar', name: 'Arabic' },
  { id: 'lang-en', code: 'en', name: 'English' },
]

/** A SPANISH card — the course the cousin was actually studying — carrying
 * the Arabic translation he was served. */
function spanishCard(translation: string) {
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
  usePrefsStore.setState({ activeLanguageId: 'lang-es', hintLevel: 3 })
  getLanguages.mockResolvedValue(LANGUAGES)
  updateProfile.mockResolvedValue({})
  // The state the report describes: English UI, Arabic content locale.
  // These two diverge legitimately — three surfaces write support_locale
  // without touching ui_language.
  getProfile.mockResolvedValue({ support_locale: 'ar', ui_language: 'en' })
  getDueCards.mockResolvedValue([spanishCard('أقرأ كتابًا.')])
})

function renderSession() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ReviewSessionPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return qc
}

describe('the way out is reachable from a non-English course', () => {
  it('has no language picker inside a running session', async () => {
    renderSession()
    await screen.findByText('أقرأ كتابًا.')
    // Mid-session it re-fetched the deck under a learner who was part-way
    // through. The way out is the globe on every other page, and Settings.
    expect(
      screen.queryByRole('combobox', { name: /translations/i }),
    ).not.toBeInTheDocument()
  })

  it('does not write the profile from inside a session', async () => {
    // The lever being absent is only half of it: nothing in here should be
    // able to change the card language under the session either.
    renderSession()
    await screen.findByText('أقرأ كتابًا.')
    expect(updateProfile).not.toHaveBeenCalled()
  })
})
