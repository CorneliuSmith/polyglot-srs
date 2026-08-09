import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  BookOpen,
  Clapperboard,
  Dumbbell,
  Flame,
  MessagesSquare,
  SpellCheck,
  Sparkles,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { getGymManifest } from '../../api/gym'
import { usePrefsStore } from '../../stores/prefsStore'
import type { DashboardStats } from '../../api/types'

/**
 * The right-hand column of the Study page, on wide screens only.
 *
 * Splitting the dashboard into four sections was the right call for a
 * phone: the daily loop had been sitting seventh, under a language picker
 * and two read-once reference tiles. But a desktop screen is not short of
 * room, and the split left Study as two tiles floating above several
 * hundred pixels of grey — the same content, arranged for a constraint
 * that doesn't apply.
 *
 * So on `lg` and up the things a learner reaches for next come back
 * alongside the loop rather than behind a tab. Below `lg` this renders
 * nothing and the tab bar does its job.
 *
 * Shortcuts, not replacements: Practice and Progress still hold the full
 * versions, and this deliberately shows only what fits without scrolling.
 */
function RailTile({
  icon: Icon,
  label,
  onClick,
  disabled,
  testId,
}: {
  icon: LucideIcon
  label: string
  onClick: () => void
  disabled?: boolean
  testId: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="flex flex-col items-center gap-1.5 rounded-xl border border-gray-200 bg-white px-2 py-3 text-xs font-medium text-gray-700 transition-colors hover:border-lang/40 hover:text-lang disabled:opacity-40"
    >
      <Icon aria-hidden className="h-5 w-5 text-lang" />
      {label}
    </button>
  )
}

export default function DesktopRail({ stats }: { stats?: DashboardStats }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: gym } = useQuery({
    queryKey: ['gym-manifest', activeLanguageId],
    queryFn: () => getGymManifest(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
  const hasGym = (gym?.columns?.length ?? 0) > 0

  // Whatever the profile has actually recorded — an empty rail is worse
  // than no rail, so the progress card only appears once there is a number
  // worth showing.
  const learned = stats?.profile?.items_studied ?? 0
  const streak = stats?.streak_days ?? 0
  const dueTomorrow = stats?.forecast?.[0]?.count ?? 0

  return (
    <aside
      data-testid="desktop-rail"
      className="hidden lg:flex lg:flex-col lg:gap-4"
      aria-label={t('nav.practice')}
    >
      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
          {t('nav.practice')}
        </h2>
        <div className={`grid gap-2 ${hasGym ? 'grid-cols-2' : 'grid-cols-3'}`}>
          {hasGym && (
            <RailTile
              icon={Dumbbell}
              label={t('nav.gym')}
              testId="rail-gym"
              onClick={() => navigate('/gym')}
            />
          )}
          <RailTile
            icon={BookOpen}
            label={t('nav.read')}
            testId="rail-read"
            disabled={!activeLanguageId}
            onClick={() => navigate('/read')}
          />
          <RailTile
            icon={MessagesSquare}
            label={t('nav.tutor')}
            testId="rail-tutor"
            disabled={!activeLanguageId}
            onClick={() => navigate('/tutor')}
          />
          {/* The weekly picks page — the one destination this rail was
              missing, so the feature was invisible on desktop unless you
              knew the URL. */}
          <RailTile
            icon={Clapperboard}
            label={t('dashboard.recommendedTitle')}
            testId="rail-reco"
            disabled={!activeLanguageId}
            onClick={() => navigate('/recommendations')}
          />
        </div>
      </section>

      <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
          {t('nav.languageGuide')}
        </h2>
        <div className="grid grid-cols-2 gap-2">
          <RailTile
            icon={SpellCheck}
            label={t('dashboard.lettersTitle')}
            testId="rail-letters"
            onClick={() => navigate('/letters')}
          />
          <RailTile
            icon={Sparkles}
            label={t('dashboard.aboutTitle')}
            testId="rail-about"
            onClick={() => navigate('/about')}
          />
        </div>
      </section>

      {learned > 0 && (
        <button
          type="button"
          data-testid="rail-progress"
          onClick={() => navigate('/progress')}
          className="rounded-2xl border border-gray-100 bg-white p-4 text-start shadow-sm transition-colors hover:border-lang/40"
        >
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
            {t('nav.progress')}
          </h2>
          <p className="mb-2 flex items-center gap-1.5 text-sm text-gray-700">
            <Flame aria-hidden className="h-4 w-4 text-lang" />
            {t('dashboard.streak', { count: streak })}
          </p>
          <dl className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-gray-500">{t('dashboard.itemsStudied')}</dt>
              <dd className="font-semibold tabular-nums text-gray-900">{learned}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-500">{t('dashboard.forecastTitle')}</dt>
              <dd className="font-semibold tabular-nums text-gray-900">{dueTomorrow}</dd>
            </div>
          </dl>
        </button>
      )}
    </aside>
  )
}
