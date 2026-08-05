import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { BarChart3, Dumbbell, Home, Menu } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

/**
 * The four sections, for screens with no bottom tab bar.
 *
 * BottomNav is `md:hidden` on the grounds that "the header's inline nav
 * already does this job" on desktop. It did not: that row lists Decks,
 * Tutor, Read, Gym, Search and Account — individual destinations, not the
 * sections. So when the daily loop was split into Study / Practice /
 * Progress / More, desktop got the split without the navigation: three of
 * the four sections became reachable only by typing the URL, and the
 * Study page was left looking abandoned because most of what used to be
 * on it had moved somewhere with no way in.
 *
 * The per-feature destinations live inside these sections, the same way
 * they do on a phone — one information architecture rather than two.
 */
interface Section {
  to: string
  labelKey: string
  Icon: LucideIcon
}

const SECTIONS: Section[] = [
  { to: '/', labelKey: 'nav.study', Icon: Home },
  { to: '/practice', labelKey: 'nav.practice', Icon: Dumbbell },
  { to: '/progress', labelKey: 'nav.progress', Icon: BarChart3 },
  { to: '/more', labelKey: 'nav.more', Icon: Menu },
]

export default function SectionNav() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <nav
      data-testid="section-nav"
      // Phones have the tab bar; this would be a second copy of it.
      className="hidden md:flex items-center gap-1"
      aria-label={t('nav.sections')}
    >
      {SECTIONS.map(({ to, labelKey, Icon }) => {
        // '/' is a prefix of every route, so it has to match exactly or
        // Study lights up everywhere.
        const active = to === '/' ? pathname === '/' : pathname.startsWith(to)
        return (
          <button
            key={to}
            type="button"
            data-testid={`section-${to === '/' ? 'study' : to.slice(1)}`}
            onClick={() => navigate(to)}
            aria-current={active ? 'page' : undefined}
            className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors ${
              active
                ? 'bg-lang-soft text-lang'
                : 'text-gray-500 hover:text-lang hover:bg-gray-100'
            }`}
          >
            <Icon aria-hidden className="h-4 w-4" />
            {t(labelKey)}
          </button>
        )
      })}
    </nav>
  )
}
