import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import UiLanguageSwitcher from '../components/UiLanguageSwitcher'
import i18n, {
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
    await waitFor(() =>
      expect(mockUpdateProfile).toHaveBeenCalledWith({
        ui_language: 'fr',
        support_locale: 'fr',
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

  it('the account language applies only when this device has no choice', async () => {
    syncUiLanguageFromProfile('ar')
    expect(i18n.language).toBe('ar')
    // But it is not a device-level override…
    expect(localStorage.getItem('polyglot-ui-language')).toBeNull()

    // …and an existing device choice always wins over the account.
    await reset()
    localStorage.setItem('polyglot-ui-language', 'es')
    await i18n.changeLanguage('es')
    syncUiLanguageFromProfile('ar')
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

  it('fills the card language when nothing has been chosen', async () => {
    // The automatic case: a Spanish interface should bring Spanish cards
    // with it rather than leaving the learner on English.
    mockGetProfile.mockResolvedValue({ ui_language: 'en', support_locale: null })
    expect(await pickSpanishFromTheGlobe()).toEqual({
      ui_language: 'es', support_locale: 'es',
    })
  })

  it('leaves a chosen card language alone', async () => {
    // The bug: this used to send support_locale unconditionally, so a
    // learner who had picked Russian in Learn or Settings had it replaced
    // by their interface language the next time they touched the globe —
    // which reads as the app forgetting the choice and flipping back.
    mockGetProfile.mockResolvedValue({ ui_language: 'en', support_locale: 'ru' })
    const sent = await pickSpanishFromTheGlobe()
    expect(sent).toEqual({ ui_language: 'es' })
    expect(sent).not.toHaveProperty('support_locale')
  })

  it('still changes the interface either way', async () => {
    mockGetProfile.mockResolvedValue({ ui_language: 'en', support_locale: 'ru' })
    const sent = await pickSpanishFromTheGlobe()
    expect(sent.ui_language).toBe('es')
  })
})
