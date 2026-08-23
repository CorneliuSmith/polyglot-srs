import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getFeaturePopularity } from '../../api/contribute'

/** Admin: which features people actually use (owner: "analysis on what
 * features are popular amongst users"). One horizontal bar per feature —
 * bar length is DISTINCT USERS in the window, because "three people sent
 * a thousand tutor messages" and "a thousand people sent three" need to
 * look different: the count of events rides each row as text, in the
 * feature's own unit, so heavy use by few is visible next to light use
 * by many.
 *
 * A single measure on a single scale, so one hue carries every bar and
 * identity lives in the row labels, not in color. */

const RANGES = [7, 30, 90] as const

export default function FeaturePopularityPanel() {
  const [days, setDays] = useState<(typeof RANGES)[number]>(30)
  const { data: features } = useQuery({
    queryKey: ['feature-popularity', days],
    queryFn: () => getFeaturePopularity(days),
    retry: false,
  })
  if (!features || features.length === 0) return null

  const maxUsers = Math.max(...features.map((f) => f.users), 1)

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="feature-popularity"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800">
          Feature popularity · last {days} days
        </h2>
        <div className="flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setDays(r)}
              aria-pressed={days === r}
              className={
                'rounded-lg px-2.5 py-1 text-xs font-medium ' +
                (days === r
                  ? 'bg-lang text-lang-on'
                  : 'bg-gray-50 text-gray-500 hover:bg-gray-100')
              }
            >
              {r}d
            </button>
          ))}
        </div>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        Bar = how many different people used it; the count after each bar is
        how much it was used. From the tables each feature already writes.
      </p>

      <div className="space-y-2">
        {features.map((f) => (
          <div key={f.key} data-testid={`feature-${f.key}`}>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-xs font-medium text-gray-700">
                {f.label}
              </span>
              <span className="text-xs tabular-nums text-gray-500">
                {f.users} user{f.users === 1 ? '' : 's'} ·{' '}
                {f.events.toLocaleString()} {f.unit}
              </span>
            </div>
            <div
              className="mt-0.5 h-2 rounded-full bg-gray-100"
              role="img"
              aria-label={`${f.label}: ${f.users} users, ${f.events} ${f.unit}`}
            >
              <div
                className="h-2 rounded-full bg-lang"
                style={{ width: `${Math.max((f.users / maxUsers) * 100, f.users > 0 ? 2 : 0)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
