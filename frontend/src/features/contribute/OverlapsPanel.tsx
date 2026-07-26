import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getOverlaps, resolveOverlap } from '../../api/contribute'
import type { OverlapPair } from '../../api/contribute'

const VERDICT_LABEL: Record<OverlapPair['verdict'], string> = {
  duplicate: 'Duplicate',
  subsumes: 'One subsumes the other',
  partial: 'Partial overlap',
}

/**
 * Overlapping grammar points (owner request): the audit judge flags pairs
 * that teach substantially the same thing; a reviewer decides. "Merged" =
 * they've folded the content together (done by editing the points),
 * "Keep both" = real overlap but intentionally two points, "Dismiss" = the
 * judge was wrong. Hides itself when the queue is empty.
 */
export default function OverlapsPanel({
  languageId,
  canResolve,
}: {
  languageId: string
  canResolve: boolean
}) {
  const queryClient = useQueryClient()
  const { data: overlaps = [] } = useQuery({
    queryKey: ['overlaps', languageId],
    queryFn: () => getOverlaps(languageId),
    enabled: !!languageId,
    retry: false,
  })

  const resolveMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'merged' | 'distinct' | 'dismissed' }) =>
      resolveOverlap(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['overlaps', languageId] })
      queryClient.invalidateQueries({ queryKey: ['review-inbox', languageId] })
    },
  })

  if (overlaps.length === 0) return null

  return (
    <section
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
      data-testid="overlaps-panel"
    >
      <div>
        <h2 className="font-semibold text-gray-800">
          Overlapping grammar points ({overlaps.length})
        </h2>
        <p className="text-xs text-gray-500">
          The audit thinks each pair teaches substantially the same thing.
          Merge the content by editing the points, then record what you did —
          nothing is merged automatically.
        </p>
      </div>
      <ul className="space-y-3">
        {overlaps.map((o) => (
          <li
            key={o.id}
            className="rounded-xl border border-gray-100 bg-gray-50 p-3 space-y-2"
            data-testid="overlap-pair"
          >
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium text-gray-800">
                {o.point_a.title}
                {o.point_a.level && (
                  <span className="ml-1 text-[10px] text-gray-400">{o.point_a.level}</span>
                )}
              </span>
              <span className="text-gray-400">vs</span>
              <span className="font-medium text-gray-800">
                {o.point_b.title}
                {o.point_b.level && (
                  <span className="ml-1 text-[10px] text-gray-400">{o.point_b.level}</span>
                )}
              </span>
              <span className="rounded-full bg-amber-100 text-amber-800 px-2 py-0.5 text-[10px] font-semibold">
                {VERDICT_LABEL[o.verdict]}
              </span>
            </div>
            {o.reason && <p className="text-xs text-gray-500">{o.reason}</p>}
            {canResolve && (
              <div className="flex flex-wrap gap-2 pt-0.5">
                <button
                  type="button"
                  onClick={() => resolveMutation.mutate({ id: o.id, status: 'merged' })}
                  disabled={resolveMutation.isPending}
                  className="rounded-lg border border-green-200 bg-white px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-50 disabled:opacity-50"
                >
                  Merged the content
                </button>
                <button
                  type="button"
                  onClick={() => resolveMutation.mutate({ id: o.id, status: 'distinct' })}
                  disabled={resolveMutation.isPending}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Keep both
                </button>
                <button
                  type="button"
                  onClick={() => resolveMutation.mutate({ id: o.id, status: 'dismissed' })}
                  disabled={resolveMutation.isPending}
                  className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                >
                  Not an overlap
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
