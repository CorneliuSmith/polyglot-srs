import { useEffect, useLayoutEffect, useRef, useState } from 'react'
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

/** Breathing room between the menu and the screen edge. */
const VIEWPORT_MARGIN = 8

export default function UiLanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  // How far the menu has been nudged to stay on screen (see the layout
  // effect). Mirrored in a ref so a re-measure can undo it and work from the
  // menu's natural, unshifted position.
  const shiftRef = useRef(0)
  const [shift, setShift] = useState(0)
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

  // Keep the open menu on screen. It hangs off the button's inline-end edge,
  // which is right for a globe in the top-RIGHT of a header but ran the menu
  // clean off the left of a phone screen on pages where the globe sits at
  // the LEFT (the About page: "← Panel ⊕"), clipping every language name to
  // "glish" / "pañol". Rather than hard-code a side per page, measure once
  // on open and translate the menu back inside the viewport if it spills.
  useLayoutEffect(() => {
    if (!open) return
    const fit = () => {
      const menu = menuRef.current
      if (!menu) return
      const rect = menu.getBoundingClientRect()
      // No measurable box (jsdom, hidden ancestor) — leave the authored
      // position alone rather than nudge it on made-up numbers.
      if (!rect.width) return
      // Work from where the menu WOULD sit unshifted, so re-measuring after
      // a rotation doesn't compound the previous correction.
      const left = rect.left - shiftRef.current
      const right = rect.right - shiftRef.current
      const limit = window.innerWidth - VIEWPORT_MARGIN
      let next = 0
      if (left < VIEWPORT_MARGIN) next = VIEWPORT_MARGIN - left
      else if (right > limit) next = limit - right
      if (next !== shiftRef.current) {
        shiftRef.current = next
        setShift(next)
      }
    }
    fit()
    window.addEventListener('resize', fit)
    return () => {
      window.removeEventListener('resize', fit)
      shiftRef.current = 0
      setShift(0)
    }
  }, [open])

  const choose = (code: string) => {
    setOpen(false)
    applyUiLanguage(code)
    if (authed) {
      // The chrome language always follows the globe. The CARD language
      // follows it only while nobody has said otherwise.
      //
      // This used to set both, unconditionally, on every use. So a learner
      // who had deliberately picked their translations language in Learn,
      // Review or Settings had it silently replaced by their interface
      // language the next time they touched the globe — which reads as the
      // app forgetting the choice and flipping back on its own.
      //
      // support_locale IS the record of that: it is NULL until something
      // sets it, so "nothing chosen" and "chosen" are already
      // distinguishable without a new column. Automatic fills the empty
      // case; an explicit choice outranks it and is left alone.
      //
      // (One honest seam: choosing English explicitly also stores NULL — 'en'
      // is the reset value — so that one choice can still be re-cascaded.
      // Separating them needs a column and this endpoint is on every page
      // load, so it is not worth taking the app down over.)
      // Read from the cache rather than a useQuery: this switcher is
      // rendered on the login page OUTSIDE any QueryClientProvider (see the
      // guarded useQueryClient above), so a hook here would throw. Signed in,
      // ProfileLanguageSync has already put the profile there.
      const cached = queryClient?.getQueryData<{ support_locale?: string | null }>(
        ['profile'],
      )
      const chosen = cached?.support_locale != null
      updateProfile(chosen ? { ui_language: code }
                           : { ui_language: code, support_locale: code })
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
        data-testid="ui-language-switcher"
        title={t('switcher.label')}
        className="w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:text-lang hover:border-lang/40 leading-none"
      >
        <Globe aria-hidden className="h-4 w-4 md:h-3.5 md:w-3.5" />
      </button>
      {open && (
        <div
          role="menu"
          aria-label={t('switcher.label')}
          ref={menuRef}
          style={shift ? { transform: `translateX(${shift}px)` } : undefined}
          className="absolute end-0 mt-2 z-50 min-w-36 max-w-[calc(100vw-1rem)] bg-white rounded-xl shadow-lg border border-gray-100 py-1"
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
