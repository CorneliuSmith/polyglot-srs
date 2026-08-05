import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '../../api/dashboard'
import { usePrefsStore } from '../../stores/prefsStore'
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

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-4 pb-24 md:pb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('nav.progress')}</h1>

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
        ) : (
          <>
            {stats.profile && (
              <ProfileCard profile={stats.profile} streakDays={stats.streak_days} />
            )}
            {stats.forecast && <ForecastStrip forecast={stats.forecast} />}
            {stats.activity && <ActivityChart activity={stats.activity} />}
            {stats.stages && <StageTiles stages={stats.stages} />}
            <CEFRProgress progress={stats.cefr_progress} />
          </>
        )}
      </div>
    </div>
  )
}
