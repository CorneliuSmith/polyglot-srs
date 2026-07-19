import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  approveTranslationReview,
  getTranslationReviews,
  rejectTranslationReview,
} from '../../api/contribute'

/** The AI maker-checker's "not sure" pile: glosses and hints it refused to
 * auto-apply. An admin approves (applies to the card) or rejects (dismisses).
 * 'en-hint' rows are flagged English definitions; other locales are
 * English-course L1 glosses. */
export default function TranslationReviewsPanel() {
  const queryClient = useQueryClient()
  const { data: reviews } = useQuery({
    queryKey: ['translation-reviews'],
    queryFn: getTranslationReviews,
    retry: false,
  })
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ['translation-reviews'] })
  const approve = useMutation({
    mutationFn: approveTranslationReview,
    onSuccess: refresh,
  })
  const reject = useMutation({
    mutationFn: rejectTranslationReview,
    onSuccess: refresh,
  })

  if (!reviews || reviews.length === 0) return null

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="translation-reviews"
    >
      <h2 className="text-sm font-semibold text-gray-800">
        AI translations awaiting review
      </h2>
      <p className="text-xs text-gray-500 mb-3">
        The maker–checker wasn’t confident enough to apply these. Approve to
        put the proposed text on the card; reject to dismiss.
      </p>
      <ul className="divide-y divide-gray-50">
        {reviews.map((r) => (
          <li key={r.id} className="py-2 flex items-start gap-3">
            <span className="text-[10px] font-mono uppercase rounded bg-gray-100 text-gray-500 px-1.5 py-0.5 mt-0.5">
              {r.locale}
            </span>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-gray-800">{r.word}</div>
              {r.current_definition && (
                <div className="text-xs text-gray-400 truncate">
                  now: {r.current_definition}
                </div>
              )}
              {r.proposed && (
                <div className="text-xs text-gray-700">
                  proposed: <b>{r.proposed}</b>
                </div>
              )}
              {r.reason && (
                <div className="text-[11px] text-amber-700">{r.reason}</div>
              )}
            </div>
            <div className="flex gap-1 shrink-0">
              {r.proposed && (
                <button
                  type="button"
                  onClick={() => approve.mutate(r.id)}
                  disabled={approve.isPending || reject.isPending}
                  className="rounded-lg bg-lang px-2.5 py-1 text-xs font-semibold text-lang-on disabled:opacity-50"
                >
                  Approve
                </button>
              )}
              <button
                type="button"
                onClick={() => reject.mutate(r.id)}
                disabled={approve.isPending || reject.isPending}
                className="rounded-lg border border-gray-200 px-2.5 py-1 text-xs text-gray-500 hover:text-red-600 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
