import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CircleUserRound, Globe2, Languages, Layers, Search } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { getLanguages } from '../../api/profile'
import { getMyRoles } from '../../api/contribute'
import { useViewAsKey } from '../../stores/viewAsStore'
import { useMonetization } from '../billing/useMonetization'
import { usePrefsStore } from '../../stores/prefsStore'
import DirArrow from '../../components/DirArrow'
import SectionHeader from '../../components/SectionHeader'
import { PAGE_WIDE } from '../../lib/layout'
import FeedbackButton from '../feedback/FeedbackButton'
import { lettersFor } from '../letters/lettersData'
import { factsFor } from '../about/languageFacts'

function Row({
  icon: Icon,
  title,
  sub,
  onClick,
  disabled = false,
  testId,
}: {
  icon?: LucideIcon
  title: string
  sub?: string
  onClick: () => void
  disabled?: boolean
  testId?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 rounded-xl px-4 py-3 border border-gray-200 transition-colors text-start flex items-center gap-3"
      style={{ minHeight: '44px' }}
    >
      {Icon && (
        <span className="shrink-0 rounded-xl bg-lang/10 p-2">
          <Icon aria-hidden className="h-5 w-5 text-lang" strokeWidth={1.75} />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-gray-800">{title}</span>
        {sub && (
          <span className="block text-xs font-normal text-gray-500 leading-tight">
            {sub}
          </span>
        )}
      </span>
      <DirArrow className="shrink-0 text-lang" />
    </button>
  )
}

/**
 * Everything occasional: the language guide, the other pages, feedback.
 *
 * Letters & Sounds and Things to Know used to sit ABOVE the daily loop on
 * the dashboard — read-once material above the thing you do every day,
 * which is the wrong way round however good it looks. They're grouped here
 * as a language guide instead, one tap from the tab bar.
 */
export default function MorePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: allLanguages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const code = allLanguages.find((l) => l.id === activeLanguageId)?.code
  const hasLetters = !!lettersFor(code)
  const hasFacts = !!factsFor(code)

  const { data: roleInfo } = useQuery({
    queryKey: ['my-roles', useViewAsKey()],
    queryFn: getMyRoles,
    retry: false,
  })
  const canContribute = (roleInfo?.roles?.length ?? 0) > 0
  const { monetization } = useMonetization()

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className={`${PAGE_WIDE} mx-auto px-4 py-6 space-y-4 pb-24 md:pb-6`}>
        <SectionHeader title={t('nav.more')} />

        {/* Two independent lists — the guide for this language, and the
            places to go. Side by side once there is room; the rows inside
            keep their own column's width rather than stretching. */}
        <div className="grid gap-4 lg:grid-cols-2 items-start">
          {(hasLetters || hasFacts) && (
            <section className="space-y-2" data-testid="language-guide">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                {t('nav.languageGuide')}
              </h2>
              {hasLetters && (
                <Row
                  icon={Languages}
                  title={t('dashboard.lettersTitle')}
                  sub={t('dashboard.lettersSub')}
                  onClick={() => navigate('/letters')}
                  testId="tile-letters"
                />
              )}
              {hasFacts && (
                <Row
                  icon={Globe2}
                  title={t('dashboard.aboutTitle')}
                  sub={t('dashboard.aboutSub')}
                  onClick={() => navigate('/about')}
                  testId="tile-about"
                />
              )}
            </section>
          )}

          <section className="space-y-2">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              {t('nav.more')}
            </h2>
            {/* Icons for the destination rows too — Account especially was
                the last text-only entry while every feature row had one. */}
            <Row
              icon={Layers}
              title={t('nav.decks')}
              onClick={() => navigate('/decks')}
              testId="row-decks"
            />
            <Row
              icon={Search}
              title={t('nav.search')}
              onClick={() => navigate('/search')}
              testId="row-search"
            />
            <Row
              icon={CircleUserRound}
              title={t('nav.account')}
              onClick={() => navigate('/account')}
              testId="row-account"
            />
          </section>
        </div>

        {/* The general feedback channel. Everything else in the app can only
            report a problem WITH A CARD, so anyone whose complaint was about
            the app itself had nowhere to put it. */}
        <FeedbackButton page="dashboard" />

        {canContribute && (
          <button
            type="button"
            onClick={() => navigate('/contribute')}
            className="w-full text-sm text-gray-500 hover:text-lang hover:underline text-start"
          >
            {t('dashboard.contribute')}
          </button>
        )}

        {/* Tip jar (owner: "donate a tea - I don't drink coffee"). Behind
            BOTH the env var and the monetization master switch — while the
            owner's employer clearance is pending, even a donation link is
            a money feature and must not render. Opens the payment page in
            a new tab — never navigates the app away. */}
        {monetization && import.meta.env.VITE_DONATE_URL && (
          <a
            href={import.meta.env.VITE_DONATE_URL}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="donate-tea"
            className="block w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-center text-sm font-medium text-gray-700 hover:border-lang/40 hover:text-lang"
          >
            {t('more.donateTea')}
          </a>
        )}

        {/* The honest small print, on the one page everyone can reach —
            with the full documents one tap away. */}
        <p className="text-[11px] leading-snug text-gray-400">
          {t('more.legalNote')}{' '}
          <button
            type="button"
            onClick={() => navigate('/terms')}
            className="underline hover:text-lang"
          >
            {t('more.terms')}
          </button>
          {' · '}
          <button
            type="button"
            onClick={() => navigate('/privacy')}
            className="underline hover:text-lang"
          >
            {t('more.privacy')}
          </button>
        </p>
      </div>
    </div>
  )
}
