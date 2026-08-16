import { useEffect } from 'react'
import {
  BookOpen,
  FolderOpen,
  Inbox,
  Languages,
  MessagesSquare,
  Route,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { usePrefsStore } from '../../stores/prefsStore'

/** Post-placement walkthrough (beta request: "nothing popped up showing
 * the tools available"). One card per area of the app, each tappable.
 * New accounts land here right after onboarding; anyone can reopen it
 * from Settings → "Show me around". */

const TOOLS: {
  route: string
  icon: LucideIcon
  nameKey: string
  blurbKey: string
}[] = [
  {
    route: '/',
    icon: Inbox,
    nameKey: 'welcome.reviewsName',
    blurbKey: 'welcome.reviewsBlurb',
  },
  {
    route: '/grammar',
    icon: Route,
    nameKey: 'welcome.grammarPathName',
    blurbKey: 'welcome.grammarPathBlurb',
  },
  {
    route: '/tutor',
    icon: MessagesSquare,
    nameKey: 'welcome.tutorName',
    blurbKey: 'welcome.tutorBlurb',
  },
  {
    route: '/read',
    icon: BookOpen,
    nameKey: 'welcome.readerName',
    blurbKey: 'welcome.readerBlurb',
  },
  {
    route: '/letters',
    icon: Languages,
    nameKey: 'welcome.lettersName',
    blurbKey: 'welcome.lettersBlurb',
  },
  {
    route: '/decks',
    icon: FolderOpen,
    nameKey: 'welcome.decksName',
    blurbKey: 'welcome.decksBlurb',
  },
]

export default function WelcomePage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const setWalkthroughDone = usePrefsStore((s) => s.setWalkthroughDone)

  // This page IS the tour — don't also auto-open the slide modal the
  // dashboard shows to first-time accounts, or new users get two tours
  // back to back.
  useEffect(() => {
    setWalkthroughDone(true)
  }, [setWalkthroughDone])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-xl mx-auto px-4 py-10 space-y-6">
        <header>
          <h1 className="text-2xl font-bold text-gray-900">{t('welcome.title')}</h1>
          <p className="text-sm text-gray-500">
            {t('welcome.subtitle')}
          </p>
        </header>

        <div className="space-y-3">
          {TOOLS.map((tool) => (
            <button
              key={tool.route + tool.nameKey}
              type="button"
              onClick={() => navigate(tool.route)}
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-start hover:border-lang/50 hover:bg-lang-soft"
              style={{ minHeight: '44px' }}
            >
              <span className="flex items-start gap-3">
                <tool.icon aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-lang" strokeWidth={1.75} />
                <span>
                  <span className="block text-sm font-semibold text-gray-800">
                    {t(tool.nameKey)}
                  </span>
                  <span className="block text-xs text-gray-500">{t(tool.blurbKey)}</span>
                </span>
              </span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => navigate('/', { replace: true })}
          className="w-full bg-lang hover:bg-lang-dark text-lang-on font-semibold rounded-xl px-6 py-3 text-sm"
          style={{ minHeight: '44px' }}
        >
          {t('welcome.goDashboard')}
        </button>

        <p className="text-xs text-gray-500 text-center">
          {t('welcome.reopenNote')}
        </p>
      </div>
    </div>
  )
}
