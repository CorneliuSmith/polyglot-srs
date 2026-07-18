import { useQuery } from '@tanstack/react-query'
import { getEngagement } from '../../api/contribute'

/** Admin engagement snapshot (beta request): who's using the app, doing
 * what, for how long — read from the activity tables normal use writes. */
export default function EngagementPanel() {
  const { data } = useQuery({
    queryKey: ['engagement'],
    queryFn: () => getEngagement(30),
    retry: false,
  })
  if (!data) return null

  const stat = (label: string, value: string | number, sub?: string) => (
    <div className="rounded-xl bg-gray-50 p-3">
      <div className="text-xl font-bold text-lang tabular-nums">{value}</div>
      <div className="text-xs text-gray-600">{label}</div>
      {sub && <div className="text-[10px] text-gray-400">{sub}</div>}
    </div>
  )

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="engagement"
    >
      <h2 className="text-sm font-semibold text-gray-800">
        Engagement · last {data.days} days
      </h2>
      <p className="text-xs text-gray-500 mb-3">
        All users, all languages — from review, tutor, reader, and learning
        activity. No extra tracking.
      </p>

      <div className="grid grid-cols-3 gap-2 mb-3">
        {stat('active today', data.active_users.d1)}
        {stat('active · 7 days', data.active_users.d7)}
        {stat('active · 30 days', data.active_users.d30, `of ${data.total_users} total`)}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        {stat('reviews', data.reviews.toLocaleString(), `${data.review_hours} h studying`)}
        {stat('tutor messages', data.tutor_messages.toLocaleString(), `${data.feature_users.tutor} users`)}
        {stat('reader sessions', data.readings.toLocaleString(), `${data.feature_users.reader} users`)}
        {stat('cards started', data.cards_started.toLocaleString(), `+${data.new_users} new users`)}
      </div>

      {data.top_languages.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wide text-gray-400 mb-1">
            Most-studied languages
          </h3>
          <table className="w-full text-xs">
            <tbody>
              {data.top_languages.map((l) => (
                <tr key={l.code} className="border-t border-gray-50 text-gray-700">
                  <td className="py-1">{l.name}</td>
                  <td className="py-1 text-right text-gray-500">
                    {l.learners} learner{l.learners === 1 ? '' : 's'}
                  </td>
                  <td className="py-1 text-right text-gray-400">
                    {l.cards.toLocaleString()} cards
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
