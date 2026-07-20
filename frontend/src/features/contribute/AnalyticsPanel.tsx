import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getAnalyticsCohorts,
  getAnalyticsTimeseries,
} from '../../api/contribute'
import type { AnalyticsDay } from '../../api/contribute'

/** Admin Analytics v2 (WP26 a+b): trends instead of snapshots — daily
 * active users / reviews / study minutes with a range picker, plus the
 * weekly signup-cohort retention grid. Everything derives from tables
 * normal use already writes. */

const RANGES = [7, 30, 90] as const

function Chart({ series, field, label, color }: {
  series: AnalyticsDay[]
  field: 'active_users' | 'reviews' | 'minutes'
  label: string
  color: string
}) {
  const values = series.map((d) => d[field])
  const max = Math.max(...values, 1)
  const w = 560
  const h = 96
  const step = series.length > 1 ? w / (series.length - 1) : w
  const points = values
    .map((v, i) => `${(i * step).toFixed(1)},${(h - (v / max) * h).toFixed(1)}`)
    .join(' ')
  const last = series[series.length - 1]
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-gray-500">{label}</span>
        <span className="text-xs tabular-nums text-gray-400">
          today {last ? last[field] : 0} · peak {max}
        </span>
      </div>
      <svg
        viewBox={`0 0 ${w} ${h + 4}`}
        className="mt-1 w-full"
        role="img"
        aria-label={`${label} over ${series.length} days`}
        preserveAspectRatio="none"
        style={{ height: 64 }}
      >
        <polyline
          points={`0,${h} ${points} ${w},${h}`}
          fill={color}
          fillOpacity="0.12"
          stroke="none"
        />
        <polyline points={points} fill="none" stroke={color} strokeWidth="2" />
      </svg>
    </div>
  )
}

export default function AnalyticsPanel() {
  const [days, setDays] = useState<(typeof RANGES)[number]>(30)
  const { data: series } = useQuery({
    queryKey: ['analytics-timeseries', days],
    queryFn: () => getAnalyticsTimeseries(days),
    retry: false,
  })
  const { data: cohorts } = useQuery({
    queryKey: ['analytics-cohorts'],
    queryFn: getAnalyticsCohorts,
    retry: false,
  })
  if (!series) return null

  const signups = series.reduce((sum, d) => sum + d.new_users, 0)

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="analytics"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800">
          Trends · last {days} days
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
        {signups} new signup{signups === 1 ? '' : 's'} in this window.
      </p>

      <div className="space-y-4">
        <Chart series={series} field="active_users" label="Active users / day"
               color="var(--color-lang, #4f46e5)" />
        <Chart series={series} field="reviews" label="Reviews / day"
               color="#059669" />
        <Chart series={series} field="minutes" label="Study minutes / day"
               color="#d97706" />
      </div>

      {cohorts && cohorts.length > 0 && (
        <div className="mt-5">
          <h3 className="text-xs uppercase tracking-wide text-gray-400 mb-1">
            Retention · signup cohorts × weeks since
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs whitespace-nowrap">
              <thead>
                <tr className="text-left text-gray-400 uppercase tracking-wide text-[10px]">
                  <th className="py-1 pr-2">Joined week of</th>
                  <th className="py-1 pr-2 text-right">Size</th>
                  {Array.from({ length: 8 }, (_, i) => (
                    <th key={i} className="py-1 px-1 text-center">w{i}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cohorts.map((c) => (
                  <tr key={c.cohort_week} className="border-t border-gray-50">
                    <td className="py-1 pr-2 text-gray-700">{c.cohort_week}</td>
                    <td className="py-1 pr-2 text-right tabular-nums text-gray-500">
                      {c.size}
                    </td>
                    {c.returned.map((n, i) => {
                      const pct = c.size > 0 ? Math.round((n / c.size) * 100) : 0
                      return (
                        <td
                          key={i}
                          className="py-1 px-1 text-center tabular-nums text-gray-700"
                          style={{
                            backgroundColor: `rgba(79, 70, 229, ${pct / 140})`,
                          }}
                          title={`${n} of ${c.size}`}
                        >
                          {pct}%
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-1 text-[10px] text-gray-400">
            w0 is the signup week itself; future weeks read 0% until they
            happen.
          </p>
        </div>
      )}
    </div>
  )
}
