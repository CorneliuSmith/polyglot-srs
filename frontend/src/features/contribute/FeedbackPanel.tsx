import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getFeedback, resolveFeedback } from '../../api/contribute'

/**
 * Open learner feedback for the active language, for contributors to triage.
 * Resolving an item removes it from the queue.
 */
export default function FeedbackPanel({ languageId }: { languageId: string }) {
  const queryClient = useQueryClient()

  const { data: items = [] } = useQuery({
    queryKey: ['feedback', languageId],
    queryFn: () => getFeedback(languageId),
    retry: false,
  })

  const resolveMutation = useMutation({
    mutationFn: (id: string) => resolveFeedback(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['feedback', languageId] }),
  })

  if (items.length === 0) return null

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-amber-200 p-4 space-y-2">
      <h2 className="text-sm font-semibold text-amber-800">
        Learner feedback ({items.length})
      </h2>
      {items.map((f) => (
        <div key={f.id} className="flex items-start justify-between gap-3 text-sm border-t border-gray-100 pt-2">
          <div>
            <span className="font-medium text-gray-700">{f.card_title ?? f.content_id}</span>
            <span className="text-xs text-gray-400"> · {f.card_type}</span>
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
      ))}
    </div>
  )
}
