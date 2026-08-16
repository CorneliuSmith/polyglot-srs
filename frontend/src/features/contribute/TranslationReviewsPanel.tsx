import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  approveTranslationReview,
  getTranslationReviews,
  rejectTranslationReview,
} from '../../api/contribute'
import QueueStatus from './QueueStatus'

/** The AI maker-checker's "not sure" pile: glosses and hints it refused to
 * auto-apply. Lives in the REVIEW workspace with the other queues (owner:
 * "these should go into the review section, marked as AI generated"),
 * scoped to the working language, each row badged with the review type.
 * An admin approves (applies to the card) or rejects (dismisses).
 * 'en-hint' rows are flagged English definitions; other locales are
 * English-course L1 glosses. */
export default function TranslationReviewsPanel({
  languageId,
  awaiting,
}: {
  languageId?: string
  /** What the Review Inbox counts for this queue, passed ONLY when the
   * viewer can open it (admins). Left undefined the panel keeps its old
   * self-hiding behaviour — reviewers whose GET 403s shouldn't be shown an
   * error about a queue that isn't theirs. */
  awaiting?: number
}) {
  const queryClient = useQueryClient()
  const { data: reviews, isError } = useQuery({
    queryKey: ['translation-reviews', languageId ?? 'all'],
    queryFn: () => getTranslationReviews(languageId),
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

  if (!reviews || reviews.length === 0) {
    if (awaiting === undefined) return null
    return (
      <QueueStatus
        title="AI translations"
        isError={isError}
        awaiting={awaiting}
        testId="translation-reviews-status"
      />
    )
  }

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="translation-reviews"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold text-gray-800">AI translations</h2>
        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
          AI generated · awaiting review
        </span>
      </div>
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
              {/* The decision is current-vs-proposed, so both are shown as a
                  pair. Proposals used to be dropped on the way in (see
                  maker_check_batch) and every row rendered as a reason with
                  a Reject button — a bin, not a review. */}
              {r.current_definition && (
                <div className="text-xs text-gray-500">
                  <span className="text-gray-500">now:</span>{' '}
                  {r.current_definition}
                </div>
              )}
              {r.proposed ? (
                <div className="text-xs text-gray-700">
                  <span className="text-gray-500">proposed:</span>{' '}
                  <b className="text-gray-900">{r.proposed}</b>
                </div>
              ) : (
                <div className="text-xs text-gray-500 italic">
                  no replacement proposed — the checker rejected it outright
                </div>
              )}
              {r.reason && (
                <div className="text-[11px] text-amber-700">{r.reason}</div>
              )}
            </div>
            <div className="flex gap-1 shrink-0">
              <button
                type="button"
                onClick={() => approve.mutate(r.id)}
                disabled={!r.proposed || approve.isPending || reject.isPending}
                title={
                  r.proposed
                    ? 'Put the proposed text on the card'
                    : 'Nothing to apply — this row has no proposal'
                }
                className="rounded-lg bg-lang px-2.5 py-1 text-xs font-semibold text-lang-on disabled:opacity-40"
              >
                Approve
              </button>
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
