import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getReviewNotes, resolveReviewNote } from '../../api/contribute'
import QueueStatus from './QueueStatus'

/**
 * Open reviewer notes for the language — the audit trail between "fixed it
 * myself" and "didn't approve". Reviewers/admins resolve a note once the
 * point has been corrected (or the concern dismissed with cause).
 */
import QueueHelp, { QUEUE_HELP } from './QueueHelp'
import { useFocusList } from './useFocusList'

export default function IssuesPanel({
  languageId,
  canResolve,
  awaiting,
  focus = false,
}: {
  languageId: string
  canResolve: boolean
  /** What the Review Inbox counts for this queue (see QueueStatus). */
  awaiting?: number
  /** One at a time with ‹ › instead of the whole list. */
  focus?: boolean
}) {
  const queryClient = useQueryClient()
  const { data: notes = [], isError } = useQuery({
    queryKey: ['review-notes', languageId],
    queryFn: () => getReviewNotes(languageId),
    retry: false,
  })

  const { shown, nav } = useFocusList(notes, focus, 'note')

  const resolveMutation = useMutation({
    mutationFn: (noteId: string) => resolveReviewNote(noteId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['review-notes', languageId] }),
  })

  if (notes.length === 0)
    return (
      <QueueStatus
        title="Open issues"
        isError={isError}
        awaiting={awaiting}
        testId="issues-panel-status"
      />
    )

  return (
    <div
      className="bg-amber-50 border border-amber-200 rounded-2xl p-4 space-y-2"
      data-testid="issues-panel"
    >
      <h2 className="text-sm font-semibold text-amber-900">
        Open issues ({notes.length})
        <QueueHelp
          title="Review notes"
          help={QUEUE_HELP['issues']}
          testId="help-issues"
        />
      </h2>
      {nav}
      <ul className="space-y-2">
        {shown.map((n) => (
          <li key={n.id} className="text-sm">
            <div className="flex items-start gap-2">
              <div className="flex-1">
                <span className="font-medium text-gray-900">
                  {n.entity_label ?? n.point_title}
                </span>
                <span className="ms-1 rounded bg-amber-100 text-amber-700 px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
                  {n.entity_type === 'vocab' ? 'word' : 'grammar'}
                </span>
                {n.level && (
                  <span className="ms-1 text-xs text-gray-500">{n.level}</span>
                )}
                <p className="text-gray-700 whitespace-pre-wrap">{n.note}</p>
                <p className="text-xs text-gray-500">{n.author_email}</p>
              </div>
              {canResolve && (
                <button
                  type="button"
                  onClick={() => resolveMutation.mutate(n.id)}
                  disabled={resolveMutation.isPending}
                  className="shrink-0 text-xs text-green-700 hover:underline disabled:opacity-50"
                >
                  Resolve
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
