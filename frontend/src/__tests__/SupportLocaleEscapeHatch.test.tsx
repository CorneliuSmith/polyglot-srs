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
 * These tests pin the lever open. Every one of them fails on the old code.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  it('shows the translations-language picker on a Spanish course', async () => {
    renderSession()
    await screen.findByText('أقرأ كتابًا.')
    // Gated on studyingEnglish before, so on any non-English course this
    // was simply absent and the learner was stuck.
    expect(
      await screen.findByRole('combobox', { name: /translations/i }),
    ).toBeInTheDocument()
  })

  it('loads the options — the picker is useless empty', async () => {
    renderSession()
    // `enabled: studyingEnglish` meant this call never went out on a
    // Spanish course, so even a rendered picker would offer nothing but
    // the hardcoded English entry.
    await waitFor(() => expect(getLanguages).toHaveBeenCalled())
    const select = await screen.findByRole('combobox', { name: /translations/i })
    const values = Array.from(
      select.querySelectorAll('option'),
    ).map((o) => (o as HTMLOptionElement).value)
    expect(values).toContain('en')
    expect(values).toContain('ar')
  })

  it('shows the locale actually in force, not a default of English', async () => {
    // Rendering 'en' while serving Arabic would tell the learner the
    // setting is already correct and hide the real cause from them.
    renderSession()
    const select = (await screen.findByRole('combobox', {
      name: /translations/i,
    })) as HTMLSelectElement
    expect(select.value).toBe('ar')
  })

  it('choosing English writes it, which is what resets the profile', async () => {
    renderSession()
    const select = await screen.findByRole('combobox', { name: /translations/i })
    await userEvent.selectOptions(select, 'en')
    // The backend maps 'en' -> NULL (NULLIF($5,'en')), so this is the
    // documented reset, not merely another locale.
    await waitFor(() =>
      expect(updateProfile).toHaveBeenCalledWith({ support_locale: 'en' }),
    )
  })

  it('still works on an English course — the old case is not broken', async () => {
    usePrefsStore.setState({ activeLanguageId: 'lang-en' })
    getDueCards.mockResolvedValue([
      { ...spanishCard('I read a book.'), language_code: 'en' },
    ])
    renderSession()
    await screen.findByText('I read a book.')
    expect(
      await screen.findByRole('combobox', { name: /translations/i }),
    ).toBeInTheDocument()
  })
})
