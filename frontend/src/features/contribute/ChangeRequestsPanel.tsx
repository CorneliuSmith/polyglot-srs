import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getChangeRequests,
  resolveChangeRequest,
  voteChangeRequest,
  type ChangeRequest,
} from '../../api/contribute'

const FIELD_LABEL: Record<string, string> = {
  sentence: 'Sentence',
  hint: 'Hint',
  translation: 'Translation',
  answer: 'Answer',
  explanation: 'Explanation',
  other: 'Other',
}

/**
 * The change-request review board (owner request): staff suggestions raised
 * inline from Learn/Review, ranked by vote. Reviewers, contributors, and
 * admins vote; only admins accept or reject.
 */
export default function ChangeRequestsPanel({ languageId }: { languageId: string }) {
  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ['change-requests', languageId],
    queryFn: () => getChangeRequests(languageId, 'open'),
    enabled: !!languageId,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['change-requests', languageId] })

  const voteMutation = useMutation({
    mutationFn: ({ id, vote }: { id: string; vote: number }) =>
      voteChangeRequest(id, vote),
    onSuccess: invalidate,
  })
  const resolveMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'accepted' | 'rejected' }) =>
      resolveChangeRequest(id, status),
    onSuccess: invalidate,
  })

  const requests = data?.requests ?? []
  const canResolve = data?.can_resolve ?? false

  return (
    <section className="space-y-3" data-testid="change-requests">
      <h2 className="font-semibold text-gray-800">
        Change requests
        <span className="ml-2 text-xs font-normal text-gray-400">
          suggestions from Learn &amp; Review — vote to prioritise
        </span>
      </h2>

      {requests.length === 0 && (
        <p className="text-sm text-gray-500">
          No open change requests. Raise one from any card while learning or
          reviewing.
        </p>
      )}

      {requests.map((r: ChangeRequest) => (
        <div
          key={r.id}
          className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 flex gap-3"
        >
          {/* Vote column */}
          <div className="flex flex-col items-center gap-0.5 pt-0.5">
            <button
              type="button"
              aria-label="Upvote"
              onClick={() =>
                voteMutation.mutate({ id: r.id, vote: r.my_vote === 1 ? 0 : 1 })
              }
              className={`text-lg leading-none ${
                r.my_vote === 1 ? 'text-lang' : 'text-gray-300 hover:text-gray-500'
              }`}
            >
              ▲
            </button>
            <span className="text-sm font-semibold tabular-nums text-gray-700">
              {r.score}
            </span>
            <button
              type="button"
              aria-label="Downvote"
              onClick={() =>
                voteMutation.mutate({ id: r.id, vote: r.my_vote === -1 ? 0 : -1 })
              }
              className={`text-lg leading-none ${
                r.my_vote === -1 ? 'text-red-500' : 'text-gray-300 hover:text-gray-500'
              }`}
            >
              ▼
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span className="rounded bg-gray-100 px-1.5 py-0.5 font-medium text-gray-600">
                {FIELD_LABEL[r.field] ?? r.field}
              </span>
              {r.author_email && <span>by {r.author_email}</span>}
            </div>
            {r.target_label && (
              <p className="text-sm text-gray-500 italic truncate">
                “{r.target_label}”
              </p>
            )}
            <p className="text-sm text-gray-800">{r.issue}</p>
            {r.suggestion && (
              <p className="text-sm text-green-700">
                <span className="text-gray-400">Suggested: </span>
                {r.suggestion}
              </p>
            )}
            {canResolve && (
              <div className="flex items-center gap-3 pt-1">
                <button
                  type="button"
                  onClick={() =>
                    resolveMutation.mutate({ id: r.id, status: 'accepted' })
                  }
                  disabled={resolveMutation.isPending}
                  className="text-xs font-semibold text-green-700 hover:underline"
                >
                  Accept
                </button>
                <button
                  type="button"
                  onClick={() =>
                    resolveMutation.mutate({ id: r.id, status: 'rejected' })
                  }
                  disabled={resolveMutation.isPending}
                  className="text-xs font-semibold text-red-600 hover:underline"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
    </section>
  )
}
