import type { ForecastDay } from '../../api/types'

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/** Seven-day review forecast: when the queue refills, at a glance. */
export default function ForecastStrip({ forecast }: { forecast: ForecastDay[] }) {
  const max = Math.max(1, ...forecast.map((d) => d.count))
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
      <h2 className="text-xs uppercase tracking-wide text-gray-400 mb-3">
        Review forecast
      </h2>
      <div className="flex items-end justify-between gap-2" style={{ height: 72 }}>
        {forecast.map((d, i) => {
          const day = new Date(`${d.date}T00:00:00Z`)
          const label = i === 0 ? 'Today' : DAY_LABELS[day.getUTCDay()]
          return (
            <div key={d.date} className="flex-1 flex flex-col items-center justify-end gap-1">
              <span className="text-[10px] tabular-nums text-gray-500">
                {d.count > 0 ? d.count : ''}
              </span>
              <div
                className={`w-full rounded-t ${d.count > 0 ? 'bg-lang/70' : 'bg-gray-100'}`}
                style={{ height: `${Math.max(4, (d.count / max) * 44)}px` }}
              />
              <span className="text-[10px] text-gray-400">{label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
