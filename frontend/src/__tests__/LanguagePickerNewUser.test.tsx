/**
 * A new account must never be silently put on a course it did not choose.
 *
 * The picker used to auto-select `languages[0]` whenever nothing was stored
 * on the device, and GET /api/languages is `ORDER BY name` — so of 27
 * courses the alphabetical winner was ARABIC. Any account with an empty
 * `polyglot-prefs` (a brand-new signup, or an existing learner in a fresh
 * browser, a private window, a second device, after clearing site data) was
 * switched to Arabic, and the guess was WRITTEN BACK to the profile,
 * overwriting the course they picked at onboarding.
 *
 * That is how an English speaker who signed up for Spanish ends up reading
 * Arabic. The profile is the authority; the local store is a cache of it.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

const getLanguages = vi.fn()
const getProfile = vi.fn()
const updateProfile = vi.fn()

vi.mock('../api/profile', () => ({
  getLanguages: () => getLanguages(),
  getProfile: () => getProfile(),
  updateProfile: (...a: unknown[]) => updateProfile(...a),
}))

const { default: LanguagePicker } = await import('../components/LanguagePicker')
const { usePrefsStore } = await import('../stores/prefsStore')

// Exactly what the API returns: ORDER BY name. Arabic first — that ordering
// is the whole hazard, so the fixture must not quietly "fix" it.
const LANGUAGES = [
  { id: 'lang-ar', code: 'ar', name: 'Arabic', rtl: true, is_visible: true },
  { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false, is_visible: true },
  { id: 'lang-ru', code: 'ru', name: 'Russian', rtl: false, is_visible: true },
]

beforeEach(() => {
  vi.clearAllMocks()
  // The state of a device that has never stored anything.
  usePrefsStore.setState({ activeLanguageId: null })
  getLanguages.mockResolvedValue(LANGUAGES)
  updateProfile.mockResolvedValue({})
})

function renderPicker() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <LanguagePicker />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return qc
}

describe('a device with nothing stored asks the account, never guesses', () => {
  it('adopts the course the account actually chose', async () => {
    getProfile.mockResolvedValue({ active_language_id: 'lang-es' })
    renderPicker()
    await waitFor(() =>
      expect(usePrefsStore.getState().activeLanguageId).toBe('lang-es'),
    )
  })

  it('never auto-selects the alphabetically first course', async () => {
    // The old code set lang-ar here, because Arabic sorts first.
    getProfile.mockResolvedValue({ active_language_id: 'lang-es' })
    renderPicker()
    await waitFor(() =>
      expect(usePrefsStore.getState().activeLanguageId).toBe('lang-es'),
    )
    expect(usePrefsStore.getState().activeLanguageId).not.toBe('lang-ar')
  })

  it('never overwrites the account with a guess', async () => {
    // The old code PATCHed active_language_id=lang-ar, destroying the
    // onboarding choice server-side — so the wrong course followed the
    // learner to every other device too.
    getProfile.mockResolvedValue({ active_language_id: 'lang-es' })
    renderPicker()
    await waitFor(() => expect(getLanguages).toHaveBeenCalled())
    await waitFor(() =>
      expect(usePrefsStore.getState().activeLanguageId).toBe('lang-es'),
    )
    expect(updateProfile).not.toHaveBeenCalled()
  })

  it('picks nothing when the account has no course either', async () => {
    // Pre-onboarding. Onboarding assigns the course; guessing here is what
    // stamped Arabic onto the profile before the learner ever saw the list.
    getProfile.mockResolvedValue({ active_language_id: null })
    renderPicker()
    await waitFor(() => expect(getLanguages).toHaveBeenCalled())
    await new Promise((r) => setTimeout(r, 20))
    expect(usePrefsStore.getState().activeLanguageId).toBeNull()
    expect(updateProfile).not.toHaveBeenCalled()
  })

  it('ignores a profile course that is not selectable', async () => {
    // Admin-hidden or deleted since: adopting it blind would strand the
    // learner on a course the picker cannot even show.
    getProfile.mockResolvedValue({ active_language_id: 'lang-gone' })
    renderPicker()
    await waitFor(() => expect(getLanguages).toHaveBeenCalled())
    await new Promise((r) => setTimeout(r, 20))
    expect(usePrefsStore.getState().activeLanguageId).toBeNull()
  })

  it('leaves an established device alone', async () => {
    usePrefsStore.setState({ activeLanguageId: 'lang-ru' })
    getProfile.mockResolvedValue({ active_language_id: 'lang-es' })
    renderPicker()
    await waitFor(() => expect(getLanguages).toHaveBeenCalled())
    await new Promise((r) => setTimeout(r, 20))
    // The device's own choice wins while it is set; switching is a
    // deliberate act through the picker.
    expect(usePrefsStore.getState().activeLanguageId).toBe('lang-ru')
    expect(updateProfile).not.toHaveBeenCalled()
  })

  it('still shows the picker so the learner can choose', async () => {
    getProfile.mockResolvedValue({ active_language_id: null })
    renderPicker()
    expect(await screen.findByTestId('language-picker')).toBeInTheDocument()
  })
})
