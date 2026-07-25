import { useQuery } from '@tanstack/react-query'
import { getSuggestionMetrics } from '../../api/contribute'

/** Admin: how often the extractor's doc-sourced AI vocab recommendations get
 * accepted. These re-seed proposals (a model suggesting values for a word a
 * human already curated, instead of overwriting it) cost real model spend, so
 * the acceptance rate is worth watching — a low rate means the spend isn't
 * paying off. Reads content_suggestions where source='extraction'. */
export default function SuggestionMetricsPanel() {
  const { data } = useQuery({
    queryKey: ['suggestion-metrics'],
    queryFn: () => getSuggestionMetrics(),
    retry: false,
  })
  if (!data || data.total === 0) return null

  const rate =
    data.acceptance_rate === null
      ? '—'
      : `${Math.round(data.acceptance_rate * 100)}%`

  const tile = (value: string | number, label: string, accent?: string) => (
    <div className="rounded-xl p-3 bg-gray-50">
      <div className={`text-xl font-bold tabular-nums ${accent ?? 'text-lang'}`}>
        {value}
      </div>
      <div className="text-xs text-gray-600">{label}</div>
    </div>
  )

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="suggestion-metrics"
    >
      <h2 className="text-sm font-semibold text-gray-800">
        Doc AI recommendations
      </h2>
      <p className="text-xs text-gray-500 mb-3">
        Values the extractor proposed for already-curated words (not
        overwritten). These cost model spend — this is how often reviewers keep
        them.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {tile(rate, 'accepted', 'text-green-700')}
        {tile(data.pending, 'pending', 'text-amber-600')}
        {tile(data.approved, 'approved', 'text-green-700')}
        {tile(data.rejected, 'declined', 'text-gray-500')}
        {tile(data.total, 'total')}
      </div>
    </div>
  )
}
