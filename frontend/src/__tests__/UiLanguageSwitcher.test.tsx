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
  getProfile: vi.fn(() => Promise.resolve({ ui_language: 'en' })),
  updateProfile: vi.fn(() => Promise.resolve({})),
}))
vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ isAuthenticated: () => mockAuthed.value }),
  ),
}))

import { updateProfile } from '../api/profile'

const mockUpdateProfile = updateProfile as ReturnType<typeof vi.fn>

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

  it('signed in, the choice also writes the profile so it follows the user', async () => {
    mockAuthed.value = true
    renderSwitcher()
    fireEvent.click(screen.getByLabelText('Site language'))
    fireEvent.click(screen.getByText('Français'))
    await waitFor(() =>
      expect(mockUpdateProfile).toHaveBeenCalledWith({ ui_language: 'fr' }),
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
