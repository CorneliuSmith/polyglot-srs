import { useQuery } from '@tanstack/react-query'
import { getSuggestions, getReviewNotes, getFeedback } from '../../api/contribute'
import SuggestionsPanel from './SuggestionsPanel'
import IssuesPanel from './IssuesPanel'
import FeedbackPanel from './FeedbackPanel'

/**
 * The reviewer's queue: suggested edits, reported card issues, and card
 * feedback for one language. Each panel hides itself when it has nothing, so
 * with an empty queue the tab used to render as a confusing blank. This wraps
 * them and shows an explicit "nothing to review" state instead. The queries
 * reuse the panels' own query keys, so React Query shares the cache — no extra
 * requests.
 */
export default function ReviewQueue({
  languageId,
  canReview,
}: {
  languageId: string
  canReview: boolean
}) {
  const suggestions = useQuery({
    queryKey: ['suggestions', languageId],
    queryFn: () => getSuggestions(languageId),
    enabled: canReview,
  })
  const notes = useQuery({
    queryKey: ['review-notes', languageId],
    queryFn: () => getReviewNotes(languageId),
  })
  const feedback = useQuery({
    queryKey: ['feedback', languageId],
    queryFn: () => getFeedback(languageId),
  })

  const loading =
    (canReview && suggestions.isLoading) || notes.isLoading || feedback.isLoading
  const total =
    (canReview ? suggestions.data?.length ?? 0 : 0) +
    (notes.data?.length ?? 0) +
    (feedback.data?.length ?? 0)

  return (
    <>
      {canReview && <SuggestionsPanel languageId={languageId} />}
      <IssuesPanel languageId={languageId} canResolve={canReview} />
      <FeedbackPanel languageId={languageId} />

      {!loading && total === 0 && (
        <div
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center"
          data-testid="review-queue-empty"
        >
          <p className="text-sm text-gray-500">No reviews in the queue right now.</p>
          <p className="mt-1 text-xs text-gray-400">
            Edits others suggest, card issues they report, and feedback they leave
            will show up here for you to approve or resolve.
          </p>
        </div>
      )}
    </>
  )
}
