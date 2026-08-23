import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import UiLanguageSwitcher from '../components/UiLanguageSwitcher'
import i18n, {
  __resetUiLanguageSyncForTests,
  applyUiLanguage,
  detectUiLanguage,
  syncUiLanguageFromProfile,
} from '../i18n'

const { mockAuthed } = vi.hoisted(() => ({ mockAuthed: { value: false } }))

vi.mock('../api/profile', () => ({
  getProfile: vi.fn(() =>
    Promise.resolve({ ui_language: 'en', support_locale: null }),
  ),
  updateProfile: vi.fn(() => Promise.resolve({})),
}))
vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ isAuthenticated: () => mockAuthed.value }),
  ),
}))

import { getProfile, updateProfile } from '../api/profile'

const mockUpdateProfile = updateProfile as ReturnType<typeof vi.fn>
const mockGetProfile = getProfile as ReturnType<typeof vi.fn>

function renderSwitcher() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <UiLanguageSwitcher />
    </QueryClientProvider>,
  )
}

async function reset() {
  __resetUiLanguageSyncForTests()
  localStorage.clear()
  await i18n.changeLanguage('en')
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en'
}

describe('UiLanguageSwitcher', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    mockAuthed.value = false
    await reset()
  })
  afterEach(reset)

  it('opens a list of every language in its own name', async () => {
    renderSwitcher()
    fireEvent.click(screen.getByLabelText('Site language'))
    for (const name of [
      'English', 'العربية', 'Español', 'Русский', 'Français', 'Português',
    ]) {
      expect(screen.getByText(name)).toBeDefined()
    }
  })

  it('choosing a language switches the UI instantly and saves the device choice', async () => {
    renderSwitcher()
    fireEvent.click(screen.getByLabelText('Site language'))
    fireEvent.click(screen.getByText('Español'))
    await waitFor(() => expect(i18n.language).toBe('es'))
    expect(localStorage.getItem('polyglot-ui-language')).toBe('es')
    expect(document.documentElement.lang).toBe('es')
    // Signed out: the choice is device-only, never a profile write.
    expect(mockUpdateProfile).not.toHaveBeenCalled()
    // The switcher itself now reads in Spanish.
    expect(screen.getByLabelText('Idioma del sitio')).toBeDefined()
  })

  it('Arabic flips the whole document to RTL, and leaving it flips back', async () => {
    renderSwitcher()
    fireEvent.click(screen.getByLabelText('Site language'))
    fireEvent.click(screen.getByText('العربية'))
    await waitFor(() => expect(document.documentElement.dir).toBe('rtl'))

    fireEvent.click(screen.getByLabelText('لغة الموقع'))
    fireEvent.click(screen.getByText('English'))
    await waitFor(() => expect(document.documentElement.dir).toBe('ltr'))
  })

  // The menu hangs off the button's inline-end edge. On pages where the
  // globe sits at the LEFT of a phone-width header (About: "← Panel ⊕")
  // that ran it off-screen, clipping every name to "glish" / "pañol".
  function openWithMenuBox(box: { left: number; right: number }) {
    renderSwitcher()
    fireEvent.click(screen.getByLabelText('Site language'))
    const menu = screen.getByRole('menu')
    menu.getBoundingClientRect = () =>
      ({ ...box, width: box.right - box.left, top: 0, bottom: 40, height: 40,
         x: box.left, y: 0, toJSON: () => ({}) }) as DOMRect
    // Re-measure through the same path a rotation would take.
    fireEvent(window, new Event('resize'))
    return menu
  }

  it('a menu that would spill off the left edge is nudged back on screen', () => {
    const menu = openWithMenuBox({ left: -60, right: 120 })
    // 8px of breathing room from the edge: -60 → 8 is a 68px shift.
    expect(menu.style.transform).toBe('translateX(68px)')
  })

  it('a menu that would spill off the right edge is pulled back too', () => {
    // jsdom's viewport is 1024 wide.
    const menu = openWithMenuBox({ left: 920, right: 1100 })
    expect(menu.style.transform).toBe('translateX(-84px)')
  })

  it('a menu that already fits is left exactly where it was authored', () => {
    const menu = openWithMenuBox({ left: 400, right: 580 })
    expect(menu.style.transform).toBe('')
  })

  it('signed in, the choice also writes the profile so it follows the user', async () => {
    mockAuthed.value = true
    renderSwitcher()
    fireEvent.click(screen.getByLabelText('Site language'))
    fireEvent.click(screen.getByText('Français'))
    // The new interface language, plus the help-language reset — never a
    // language written into support_locale (the freeze bug the describe
    // block below documents).
    await waitFor(() =>
      expect(mockUpdateProfile).toHaveBeenCalledWith({
        ui_language: 'fr', support_locale: 'auto',
      }),
    )
  })
})

describe('detection order', () => {
  beforeEach(reset)
  afterEach(reset)

  it('an explicit device choice beats the browser language', () => {
    localStorage.setItem('polyglot-ui-language', 'ru')
    expect(detectUiLanguage()).toBe('ru')
  })

  it('falls back to the browser language, base-matched, then English', () => {
    // jsdom reports en-US; with no stored choice that resolves to en.
    expect(detectUiLanguage()).toBe('en')
    Object.defineProperty(navigator, 'languages', {
      value: ['pt-BR', 'en-US'],
      configurable: true,
    })
    expect(detectUiLanguage()).toBe('pt')
    Object.defineProperty(navigator, 'languages', {
      value: ['de-DE'],
      configurable: true,
    })
    expect(detectUiLanguage()).toBe('en')
  })

  it('the account language wins, even over an old device choice', async () => {
    // This used to be the other way round — a stored device choice beat
    // the account forever, which is how a phone ran in Russian while the
    // computer ran in English AND the server (which follows the account)
    // translated review cards for the language the screen wasn't showing.
    // One authority: the account, last change anywhere wins.
    syncUiLanguageFromProfile('ar')
    expect(i18n.language).toBe('ar')
    // The cache follows, so the next first paint here is already right.
    expect(localStorage.getItem('polyglot-ui-language')).toBe('ar')

    await reset()
    localStorage.setItem('polyglot-ui-language', 'es')
    await i18n.changeLanguage('es')
    syncUiLanguageFromProfile('ar')
    expect(i18n.language).toBe('ar')
    expect(localStorage.getItem('polyglot-ui-language')).toBe('ar')
  })

  it('a globe tap made seconds ago is not bounced by a stale profile read', async () => {
    // The tap saves to the profile asynchronously; a profile response from
    // BEFORE the tap can land after it. For a short grace window the
    // device's fresh decision holds — then the tap's own save makes the
    // account and the device agree everywhere.
    applyUiLanguage('es')
    expect(i18n.language).toBe('es')
    syncUiLanguageFromProfile('ru')
    expect(i18n.language).toBe('es')
  })
})

describe('the globe and an explicitly chosen translations language', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await reset()
    mockAuthed.value = true
  })
  afterEach(() => {
    mockAuthed.value = false
  })

  async function pickSpanishFromTheGlobe() {
    renderSwitcher()
    fireEvent.click(await screen.findByTestId('ui-language-switcher'))
    fireEvent.click(await screen.findByText('Español'))
    await waitFor(() => expect(mockUpdateProfile).toHaveBeenCalled())
    return mockUpdateProfile.mock.calls[0][0]
  }

  // The globe is the user DECIDING their language, and the last decision
  // wins everywhere — the owner's rule, verbatim: "the page is supposed
  // to refresh based on what the user says on the globe". So one payload,
  // from every starting state: the new interface language plus a reset of
  // the help language to automatic ('auto' → stored NULL; the server then
  // derives help from ui_language at read time).
  //
  // The unconditional reset is the point, and it is third-time-lucky:
  //  - v1 wrote support_locale = code, which froze "automatic" into a
  //    fake choice (an all-English page whose Speak coach wrote French,
  //    months after one tap);
  //  - v2 preserved divergent stored choices through globe taps, which
  //    meant the page did NOT follow the globe for exactly the accounts
  //    v1 had frozen — the shapes are indistinguishable in the data.
  // A deliberate split still exists: Settings, until the next globe tap.

  it('never writes a language into support_locale when nothing is chosen', async () => {
    mockGetProfile.mockResolvedValue({ ui_language: 'en', support_locale: null })
    expect(await pickSpanishFromTheGlobe()).toEqual({
      ui_language: 'es', support_locale: 'auto',
    })
  })

  it('re-decides over a divergent stored choice', async () => {
    // Interface English, help Russian — whether that split was deliberate
    // (Settings) or a leftover freeze, the globe tap is a NEWER decision
    // and everything follows it.
    mockGetProfile.mockResolvedValue({ ui_language: 'en', support_locale: 'ru' })
    expect(await pickSpanishFromTheGlobe()).toEqual({
      ui_language: 'es', support_locale: 'auto',
    })
  })

  it('heals a lockstep freeze back to automatic', async () => {
    // support == ui is exactly the state the old write produced.
    mockGetProfile.mockResolvedValue({ ui_language: 'fr', support_locale: 'fr' })
    expect(await pickSpanishFromTheGlobe()).toEqual({
      ui_language: 'es', support_locale: 'auto',
    })
  })

  it('still changes the interface either way', async () => {
    mockGetProfile.mockResolvedValue({ ui_language: 'en', support_locale: 'ru' })
    const sent = await pickSpanishFromTheGlobe()
    expect(sent.ui_language).toBe('es')
  })
})


describe('two open devices converging', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await reset()
    mockAuthed.value = true
  })
  afterEach(async () => {
    vi.useRealTimers()
    mockAuthed.value = false
    await reset()
  })

  it('an open tab re-reads the profile on a heartbeat, not only on reload', async () => {
    // The owner's report after the account-wins fix shipped: "They are
    // still both different." Both devices were long-lived tabs, and the
    // app-wide refetchOnWindowFocus:false meant the profile — and with it
    // the account's language — was read exactly once per hard reload.
    // The sync query opts back in: an open tab converges within a minute
    // of the other device's globe tap.
    vi.useFakeTimers()
    mockGetProfile.mockResolvedValue({ ui_language: 'en', support_locale: null })
    renderSwitcher()
    await vi.waitFor(() => expect(mockGetProfile).toHaveBeenCalledTimes(1))

    // The other device switches the account to Russian…
    mockGetProfile.mockResolvedValue({ ui_language: 'ru', support_locale: null })
    await vi.advanceTimersByTimeAsync(61_000)
    await vi.waitFor(() =>
      expect(mockGetProfile.mock.calls.length).toBeGreaterThanOrEqual(2),
    )
    // …and this tab follows without anyone touching it.
    await vi.waitFor(() => expect(i18n.language).toBe('ru'))
  })
})
