import type { DashboardProfile } from '../../api/types'

const DAY_LETTERS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']

/** Streak flame week + study totals, Bunpro profile-card style. */
export default function ProfileCard({
  profile,
  streakDays,
}: {
  profile: DashboardProfile
  streakDays: number
}) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 space-y-4">
      <div>
        <h2 className="text-xs uppercase tracking-wide text-gray-400 mb-2">
          Current streak — {streakDays} {streakDays === 1 ? 'day' : 'days'}
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
                  aria-label={d.studied ? 'studied' : 'not studied'}
                >
                  {d.studied ? '🔥' : '·'}
                </span>
                <span className="text-[10px] text-gray-400">
                  {DAY_LETTERS[day.getUTCDay()]}
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
            Days studied
          </span>
        </div>
        <div className="rounded-xl bg-lang-soft p-3">
          <span className="block text-xl font-bold text-lang-dark tabular-nums">
            {profile.last_session_accuracy != null
              ? `${Math.round(profile.last_session_accuracy * 100)}%`
              : '—'}
          </span>
          <span className="block text-[10px] uppercase tracking-wide text-lang/70">
            Last session
          </span>
        </div>
        <div className="rounded-xl bg-lang-soft p-3">
          <span className="block text-xl font-bold text-lang-dark tabular-nums">
            {profile.items_studied}
          </span>
          <span className="block text-[10px] uppercase tracking-wide text-lang/70">
            Items studied
          </span>
        </div>
      </div>
    </div>
  )
}
