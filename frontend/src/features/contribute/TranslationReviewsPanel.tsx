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
import QueueHelp, { QUEUE_HELP } from './QueueHelp'
import ReviewedCardView from './ReviewedCardView'
import { useFocusList } from './useFocusList'

export default function TranslationReviewsPanel({
  languageId,
  awaiting,
  focus = false,
}: {
  languageId?: string
  /** What the Review Inbox counts for this queue, passed ONLY when the
   * viewer can open it (admins). Left undefined the panel keeps its old
   * self-hiding behaviour — reviewers whose GET 403s shouldn't be shown an
   * error about a queue that isn't theirs. */
  awaiting?: number
  /** One at a time with ‹ › instead of the whole list. */
  focus?: boolean
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

  const { shown, nav } = useFocusList(reviews ?? [], focus, 'translation', (r) => [
    ...(r.proposed
      ? [{ key: 'a', label: 'Approve', run: () => approve.mutate(r.id),
           disabled: approve.isPending || reject.isPending }]
      : []),
    { key: 'r', label: r.proposed ? 'Reject' : 'Dismiss', run: () => reject.mutate(r.id),
      disabled: approve.isPending || reject.isPending },
  ])

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
        <h2 className="text-sm font-semibold text-gray-800">
          AI translations
          <QueueHelp
            title="AI translations"
            help={QUEUE_HELP['translation-reviews']}
            testId="help-translation-reviews"
          />
        </h2>
        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
          AI generated · awaiting review
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        The maker–checker wasn’t confident enough to apply these. Approve
        puts the proposed text on the card. Reject or Dismiss clears the row
        — the card keeps what it shows now, nothing else changes. Rows where
        the checker saw a problem but had no fix offer only Dismiss; each
        one says so, and carries the card so you can correct it here.
      </p>
      {nav}
      <ul className="divide-y divide-gray-50">
        {shown.map((r) => (
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
                /* Why this row has one button and its neighbour has two.
                   The old copy said what had happened ("rejected it
                   outright") and left the consequence to be inferred from
                   the missing button — the owner read the result as a bug:
                   "on some i only get the option to dismiss and not
                   understand why". Say the consequence first, then the
                   cause, then the way out. */
                <div
                  className="text-xs text-gray-500 italic"
                  data-testid={`no-proposal-${r.id}`}
                >
                  Nothing to approve: the checker rejected this gloss without
                  offering a replacement, so Dismiss is the only action. If
                  the current text is wrong, edit the card below.
                </div>
              )}
              {r.reason && (
                <div className="text-[11px] text-amber-700">{r.reason}</div>
              )}
              {/* The word itself, and the way to correct it: a row with no
                  proposal is otherwise a dead end that hands the reviewer a
                  problem and no means to fix it. */}
              {r.card && (
                <div className="mt-1.5">
                  <ReviewedCardView
                    card={r.card}
                    targetType={r.target_type}
                    targetId={r.target_id}
                    canEdit
                    testId={`translation-card-${r.id}`}
                  />
                </div>
              )}
            </div>
            <div className="flex gap-1 shrink-0">
              {/* A row with no proposal used to show a DISABLED Approve
                  next to Reject — which read as "the only thing I can do
                  is reject", with no hint of what rejecting did (owner).
                  There is genuinely one action on such a row, so show one
                  button, named for what it does. */}
              {r.proposed ? (
                <>
                  <button
                    type="button"
                    onClick={() => approve.mutate(r.id)}
                    disabled={approve.isPending || reject.isPending}
                    title="Put the proposed text on the card"
                    className="rounded-lg bg-lang px-2.5 py-1 text-xs font-semibold text-lang-on disabled:opacity-40"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => reject.mutate(r.id)}
                    disabled={approve.isPending || reject.isPending}
                    title="Clear this row; the card keeps what it shows now"
                    className="rounded-lg border border-gray-200 px-2.5 py-1 text-xs text-gray-500 hover:text-red-600 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => reject.mutate(r.id)}
                  disabled={approve.isPending || reject.isPending}
                  title="Clear this row; the card keeps what it shows now"
                  data-testid={`dismiss-review-${r.id}`}
                  className="rounded-lg border border-gray-200 px-2.5 py-1 text-xs text-gray-500 hover:text-red-600 disabled:opacity-50"
                >
                  Dismiss
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
