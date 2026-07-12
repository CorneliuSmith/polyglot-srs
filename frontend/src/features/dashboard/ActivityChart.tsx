import type { ActivityDay } from '../../api/types'

/** Reviews per day for the last two weeks, vocab vs grammar stacked. */
export default function ActivityChart({ activity }: { activity: ActivityDay[] }) {
  const max = Math.max(1, ...activity.map((d) => d.vocab + d.grammar))
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs uppercase tracking-wide text-gray-400">Activity</h2>
        <div className="flex items-center gap-3 text-[10px] text-gray-500">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-sm bg-lang" /> Vocab
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-sm bg-emerald-400" /> Grammar
          </span>
        </div>
      </div>
      <div className="flex items-end justify-between gap-1" style={{ height: 88 }}>
        {activity.map((d) => {
          const total = d.vocab + d.grammar
          return (
            <div
              key={d.date}
              className="flex-1 flex flex-col items-center justify-end"
              title={`${d.date}: ${d.vocab} vocab, ${d.grammar} grammar`}
            >
              <div className="w-full flex flex-col justify-end rounded-t overflow-hidden"
                   style={{ height: `${Math.max(total > 0 ? 6 : 2, (total / max) * 72)}px` }}>
                <div
                  className="w-full bg-emerald-400"
                  style={{ height: total ? `${(d.grammar / total) * 100}%` : 0 }}
                />
                <div
                  className={`w-full flex-1 ${total > 0 ? 'bg-lang' : 'bg-gray-100'}`}
                />
              </div>
            </div>
          )
        })}
      </div>
      <div className="flex justify-between mt-1 text-[10px] text-gray-400">
        <span>2 weeks ago</span>
        <span>today</span>
      </div>
    </div>
  )
}
