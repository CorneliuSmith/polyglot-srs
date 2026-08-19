import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '../../api/dashboard'
import { usePrefsStore } from '../../stores/prefsStore'
import SectionHeader from '../../components/SectionHeader'
import { CARD_COLUMNS, PAGE_WIDE } from '../../lib/layout'
import ActivityChart from './ActivityChart'
import CEFRProgress from './CEFRProgress'
import ForecastStrip from './ForecastStrip'
import ProfileCard from './ProfileCard'
import StageTiles from './StageTiles'

/**
 * Every statistic, in one place.
 *
 * Five surfaces used to be stacked down the dashboard — forecast, activity,
 * stage buckets, streak, CEFR — below the daily loop and above a dozen link
 * rows. Three of them (the activity bars, the streak dots, "days studied")
 * are different renderings of the same fact, and on a young account they
 * are a column of zeros. Statistics are a weekly curiosity, not a daily
 * need, so they get their own tab and stop taxing the trip a learner makes
 * every day.
 */
export default function ProgressPage() {
  const { t } = useTranslation()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard', activeLanguageId],
    queryFn: () => getDashboardStats(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  // Each card earns its place: a surface with nothing in it is hidden
  // rather than rendered as a row of zeros.
  const hasForecast = (stats?.forecast ?? []).some((d) => d.count > 0)
  const hasActivity = (stats?.activity ?? []).some(
    (d) => d.vocab > 0 || d.grammar > 0,
  )
  const hasStages = Object.values(stats?.stages ?? {}).some((byStage) =>
    Object.values(byStage).some((n) => n > 0),
  )
  const hasCefr = Object.values(stats?.cefr_progress ?? {}).some(
    (lvl) => (lvl?.learned ?? 0) > 0,
  )
  const studied = (stats?.profile?.items_studied ?? 0) > 0
  const nothingYet =
    !hasForecast && !hasActivity && !hasStages && !hasCefr && !studied

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className={`${PAGE_WIDE} mx-auto px-4 py-6 space-y-4 pb-24 md:pb-6`}>
        <SectionHeader title={t('nav.progress')} />

        {isLoading || !stats ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 animate-pulse">
            <div className="h-4 w-28 bg-gray-200 rounded mb-4" />
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 mb-3">
                <div className="w-7 h-3 bg-gray-100 rounded" />
                <div className="flex-1 h-2 bg-gray-100 rounded-full" />
                <div className="w-9 h-3 bg-gray-100 rounded" />
              </div>
            ))}
          </div>
        ) : nothingYet ? (
          // A card reading 0 in five buckets teaches nothing, and five of
          // them stacked reads as failure rather than as "not started".
          // Say what will appear here instead — the cards come back on
          // their own as soon as there's anything real in them.
          <div
            data-testid="progress-empty"
            className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-1"
          >
            <h2 className="font-semibold text-gray-800">
              {t('dashboard.progressEmptyTitle')}
            </h2>
            <p className="text-sm text-gray-600">
              {t('dashboard.progressEmptyBody')}
            </p>
          </div>
        ) : (
          <div className={CARD_COLUMNS}>
            {stats.profile && (
              <ProfileCard profile={stats.profile} streakDays={stats.streak_days} />
            )}
            {hasForecast && <ForecastStrip forecast={stats.forecast} />}
            {/* The two time-series cards keep the full width: a fortnight of
                bars squeezed into half a column is the one chart here that
                gets HARDER to read as the page gets wider. */}
            {hasActivity && (
              <div className="lg:col-span-2">
                <ActivityChart activity={stats.activity} />
              </div>
            )}
            {hasStages && <StageTiles stages={stats.stages} />}
            {hasCefr && <CEFRProgress progress={stats.cefr_progress} />}
          </div>
        )}
      </div>
    </div>
  )
}
