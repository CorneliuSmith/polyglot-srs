import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { BarChart3, Dumbbell, Home, Menu } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

/**
 * The app's primary navigation on phones.
 *
 * Everything used to live on one dashboard scroll: the daily loop, the
 * reference pages, five separate statistics surfaces, and a dozen link
 * rows. Those have completely different visit frequencies — daily, once,
 * and occasionally — so sharing one page meant the thing a learner opens
 * the app to do sat seventh, below a language picker and two read-once
 * reference tiles.
 *
 * Four destinations, split by WHEN you need them:
 *   Study     — the daily loop. Learn, Review, decks.
 *   Practice  — the optional extras: Gym, Read, Tutor, your own cards.
 *   Progress  — how it's going. Every statistic, in one place.
 *   More      — reference, settings, everything occasional.
 *
 * Phones only: on desktop the header's inline nav already does this job
 * without spending vertical space. It also hides during a session — a
 * fixed bar would sit over the answer box and the on-screen keyboard, and
 * offering to leave mid-review is not a kindness.
 */

/** Routes that own the whole screen until the learner finishes or leaves. */
const IMMERSIVE = [
  '/learn',
  '/review',
  '/cram',
  '/gym',
  '/read',
  '/tutor',
  '/onboarding',
  '/welcome',
]

interface Tab {
  to: string
  label: string
  icon: LucideIcon
}

export default function BottomNav() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  if (IMMERSIVE.some((r) => pathname === r || pathname.startsWith(`${r}/`))) {
    return null
  }

  const tabs: Tab[] = [
    { to: '/', label: t('nav.study'), icon: Home },
    { to: '/practice', label: t('nav.practice'), icon: Dumbbell },
    { to: '/progress', label: t('nav.progress'), icon: BarChart3 },
    { to: '/more', label: t('nav.more'), icon: Menu },
  ]

  return (
    <nav
      data-testid="bottom-nav"
      aria-label={t('nav.primary')}
      className="md:hidden fixed bottom-0 inset-x-0 z-40 border-t border-gray-200 bg-white"
      // Clear of the home indicator on phones that have one.
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <ul className="flex">
        {tabs.map((tab) => {
          // '/' would prefix-match everything, so it's compared exactly.
          const active =
            tab.to === '/' ? pathname === '/' : pathname.startsWith(tab.to)
          const Icon = tab.icon
          return (
            <li key={tab.to} className="flex-1">
              <button
                type="button"
                onClick={() => navigate(tab.to)}
                aria-current={active ? 'page' : undefined}
                data-testid={`tab-${tab.to === '/' ? 'study' : tab.to.slice(1)}`}
                className={`w-full flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium transition-colors ${
                  active ? 'text-lang' : 'text-gray-500 hover:text-gray-700'
                }`}
                style={{ minHeight: '44px' }}
              >
                <Icon
                  aria-hidden
                  className="h-5 w-5"
                  strokeWidth={active ? 2.25 : 1.75}
                />
                {tab.label}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
