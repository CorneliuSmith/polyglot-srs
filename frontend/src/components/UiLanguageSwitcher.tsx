import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { getProfile, updateProfile } from '../api/profile'
import {
  UI_LANGUAGES,
  applyUiLanguage,
  syncUiLanguageFromProfile,
} from '../i18n'
import { useAuthStore } from '../stores/authStore'

/** The "flag at the top" — deliberately a globe, not a flag: which flag is
 * Spanish (Spain or Mexico?), which is Arabic (25 countries)? Each option
 * shows the language's own name for itself, so a user lost in the wrong
 * language can always find theirs.
 *
 * Choosing applies instantly, saves to this device, and — when signed in —
 * writes the profile's ui_language so the choice follows them across
 * devices. Signed out (login page) it still works, device-only. */
/** Signed-in only: apply the account's saved language when this device has
 * no explicit choice. A separate child so the signed-out switcher (login
 * page) never touches react-query — that page renders outside any
 * QueryClientProvider in tests, and needs no profile anyway. */
function ProfileLanguageSync() {
  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  })
  useEffect(() => {
    if (profile) syncUiLanguageFromProfile(profile.ui_language)
  }, [profile])
  return null
}

export default function UiLanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  // The login page renders this switcher OUTSIDE any QueryClientProvider
  // (nothing there needs react-query), and useQueryClient throws without
  // one. The hook call stays unconditional — only the failure is absorbed;
  // signed-out there is never a cache to invalidate anyway.
  let queryClient: ReturnType<typeof useQueryClient> | null = null
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    queryClient = useQueryClient()
  } catch {
    queryClient = null
  }
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const authed = isAuthenticated()

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  const choose = (code: string) => {
    setOpen(false)
    applyUiLanguage(code)
    if (authed) {
      // One switch changes BOTH the chrome and the cards: support_locale is
      // what card queries COALESCE glosses on, so without it a Spanish UI
      // still served English cards. Glosses fall back to English per word
      // until the translation overlay for this pair fills in.
      // Best-effort account sync; the local switch already happened and a
      // failed write must not undo it.
      updateProfile({ ui_language: code, support_locale: code })
        .then(() => queryClient?.invalidateQueries())
        .catch(() => {})
    }
  }

  return (
    <div className="relative" ref={ref}>
      {authed && <ProfileLanguageSync />}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t('switcher.label')}
        aria-expanded={open}
        title={t('switcher.label')}
        className="w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-400 hover:text-lang hover:border-lang/40 leading-none"
      >
        <Globe aria-hidden className="h-4 w-4 md:h-3.5 md:w-3.5" />
      </button>
      {open && (
        <div
          role="menu"
          aria-label={t('switcher.label')}
          className="absolute end-0 mt-2 z-50 min-w-36 bg-white rounded-xl shadow-lg border border-gray-100 py-1"
        >
          {UI_LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              role="menuitemradio"
              aria-checked={i18n.language === lang.code}
              onClick={() => choose(lang.code)}
              // Each name renders in its own script/direction regardless of
              // the surrounding page direction.
              dir="auto"
              className={`w-full text-start px-3 py-2 text-sm hover:bg-gray-50 ${
                i18n.language === lang.code
                  ? 'text-lang font-medium'
                  : 'text-gray-700'
              }`}
            >
              {lang.native}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
