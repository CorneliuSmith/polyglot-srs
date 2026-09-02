import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getFeedback, resolveFeedback } from '../../api/contribute'
import QueueStatus from './QueueStatus'
import ReviewedCardView from './ReviewedCardView'

/**
 * Open learner feedback for the active language, for contributors to triage.
 * Resolving an item removes it from the queue.
 */
import QueueHelp, { QUEUE_HELP } from './QueueHelp'
import { useFocusList } from './useFocusList'

export default function FeedbackPanel({
  languageId,
  awaiting,
  focus = false,
}: {
  languageId: string
  /** What the Review Inbox counts for this queue — lets an empty list that
   * should not be empty announce itself instead of rendering nothing. */
  awaiting?: number
  /** One at a time with ‹ › instead of the whole list. */
  focus?: boolean
}) {
  const queryClient = useQueryClient()

  const { data: items = [], isError } = useQuery({
    queryKey: ['feedback', languageId],
    queryFn: () => getFeedback(languageId),
    retry: false,
  })

  const { shown, nav } = useFocusList(items, focus, 'report')

  const resolveMutation = useMutation({
    mutationFn: (id: string) => resolveFeedback(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['feedback', languageId] }),
  })

  if (items.length === 0)
    return (
      <QueueStatus
        title="Learner feedback"
        isError={isError}
        awaiting={awaiting}
        testId="feedback-panel-status"
      />
    )

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-amber-200 p-4 space-y-2">
      <h2 className="text-sm font-semibold text-amber-800">
        Learner feedback ({items.length})
        <QueueHelp
          title="Card feedback"
          help={QUEUE_HELP['feedback']}
          testId="help-feedback"
        />
      </h2>
      {nav}
      {shown.map((f) => (
        <div key={f.id} className="space-y-1.5 border-t border-gray-100 pt-2 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <span className="font-medium text-gray-700">{f.card_title ?? f.content_id}</span>
              <span className="text-xs text-gray-500"> · {f.card_type}</span>
              <p className="text-gray-600">{f.message}</p>
            </div>
            <button
              type="button"
              onClick={() => resolveMutation.mutate(f.id)}
              disabled={resolveMutation.isPending}
              className="text-xs text-lang hover:underline shrink-0"
            >
              Resolve
            </button>
          </div>
          {/* "Too much info" and "definition doesn't match the sentence" are
              judgements about text that used to be nowhere on this screen —
              the reviewer had the complaint and the word, and had to go
              looking for the card in another workspace to weigh either one.
              Anyone who can open this queue holds a contributor role for the
              language, which is exactly the bar the server sets on the edit. */}
          {f.card ? (
            <ReviewedCardView
              card={f.card}
              targetType={f.target_type}
              targetId={f.target_id}
              canEdit
              testId={`feedback-card-${f.id}`}
            />
          ) : (
            <p className="text-[11px] text-gray-400" data-testid="feedback-card-gone">
              This card no longer exists — it may have been deleted since the
              report was sent.
            </p>
          )}
        </div>
      ))}
    </div>
  )
}
