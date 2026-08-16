import { Flame } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { DashboardProfile } from '../../api/types'

// Ordered Sun..Sat to match Date#getUTCDay(). The one-letter column labels
// are derived from the translated day abbreviations' first character.
const DAY_KEYS = [
  'days.sun',
  'days.mon',
  'days.tue',
  'days.wed',
  'days.thu',
  'days.fri',
  'days.sat',
]

/** Streak flame week + study totals, Bunpro profile-card style. */
export default function ProfileCard({
  profile,
  streakDays,
}: {
  profile: DashboardProfile
  streakDays: number
}) {
  const { t } = useTranslation()
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 space-y-4">
      <div>
        <h2 className="text-xs uppercase tracking-wide text-gray-500 mb-2">
          {t('dashboard.streak', { count: streakDays })}
        </h2>
        <div className="flex items-center justify-between">
          {profile.week.map((d) => {
            const day = new Date(`${d.date}T00:00:00Z`)
            return (
              <div key={d.date} className="flex flex-col items-center gap-1">
                <span
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                    d.studied ? 'bg-orange-100' : 'bg-gray-100'
                  }`}
                  aria-label={d.studied ? t('dashboard.dayStudied') : t('dashboard.dayNotStudied')}
                >
                  {d.studied ? (
                    <Flame aria-hidden className="h-4 w-4 text-orange-500" fill="currentColor" />
                  ) : (
                    '·'
                  )}
                </span>
                <span className="text-[10px] text-gray-500">
                  {Array.from(t(DAY_KEYS[day.getUTCDay()]))[0]}
                </span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-xl bg-lang-soft p-3">
          <span className="block text-xl font-bold text-lang-dark tabular-nums">
            {profile.days_studied}
          </span>
          <span className="block text-[10px] uppercase tracking-wide text-lang/70">
            {t('dashboard.daysStudied')}
          </span>
        </div>
        <div className="rounded-xl bg-lang-soft p-3">
          <span className="block text-xl font-bold text-lang-dark tabular-nums">
            {profile.last_session_accuracy != null
              ? `${Math.round(profile.last_session_accuracy * 100)}%`
              : '—'}
          </span>
          <span className="block text-[10px] uppercase tracking-wide text-lang/70">
            {t('dashboard.lastSession')}
          </span>
        </div>
        <div className="rounded-xl bg-lang-soft p-3">
          <span className="block text-xl font-bold text-lang-dark tabular-nums">
            {profile.items_studied}
          </span>
          <span className="block text-[10px] uppercase tracking-wide text-lang/70">
            {t('dashboard.itemsStudied')}
          </span>
        </div>
      </div>
    </div>
  )
}
