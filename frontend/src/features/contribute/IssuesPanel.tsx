import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getReviewNotes, resolveReviewNote } from '../../api/contribute'

/**
 * Open reviewer notes for the language — the audit trail between "fixed it
 * myself" and "didn't approve". Reviewers/admins resolve a note once the
 * point has been corrected (or the concern dismissed with cause).
 */
export default function IssuesPanel({
  languageId,
  canResolve,
}: {
  languageId: string
  canResolve: boolean
}) {
  const queryClient = useQueryClient()
  const { data: notes = [] } = useQuery({
    queryKey: ['review-notes', languageId],
    queryFn: () => getReviewNotes(languageId),
  })

  const resolveMutation = useMutation({
    mutationFn: (noteId: string) => resolveReviewNote(noteId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['review-notes', languageId] }),
  })

  if (notes.length === 0) return null

  return (
    <div
      className="bg-amber-50 border border-amber-200 rounded-2xl p-4 space-y-2"
      data-testid="issues-panel"
    >
      <h2 className="text-sm font-semibold text-amber-900">
        Open issues ({notes.length})
      </h2>
      <ul className="space-y-2">
        {notes.map((n) => (
          <li key={n.id} className="text-sm">
            <div className="flex items-start gap-2">
              <div className="flex-1">
                <span className="font-medium text-gray-900">
                  {n.point_title}
                </span>
                {n.level && (
                  <span className="ml-1 text-xs text-gray-400">{n.level}</span>
                )}
                <p className="text-gray-700 whitespace-pre-wrap">{n.note}</p>
                <p className="text-xs text-gray-400">{n.author_email}</p>
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
