import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getPendingDrills,
  reviewDrill,
  recommend,
  type RecoTally,
} from '../../api/contribute'

/** Small "N recommend approve / M reject" line from trial reviewers. */
export function RecoSummary({ tally }: { tally?: RecoTally | null }) {
  if (!tally || (tally.approve === 0 && tally.reject === 0)) return null
  return (
    <div className="mt-0.5 text-[11px] text-gray-500" title={tally.notes.join(' · ')}>
      {tally.approve > 0 && (
        <span className="text-green-700">▲ {tally.approve} recommend approve</span>
      )}
      {tally.approve > 0 && tally.reject > 0 && <span> · </span>}
      {tally.reject > 0 && (
        <span className="text-red-600">▼ {tally.reject} recommend reject</span>
      )}
    </div>
  )
}

/** Contributor › Review: generated grammar drills awaiting review. They're
 * tagged 'ai', hidden from learners, and become permanent corpus only once a
 * reviewer approves them here (reject deletes). Trial reviewers can't publish —
 * they leave an advisory recommendation instead. */
export default function GeneratedDrillsPanel({
  languageId,
}: {
  languageId: string
}) {
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['pending-drills', languageId],
    queryFn: () => getPendingDrills(languageId),
    enabled: !!languageId,
    retry: false,
  })
  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ['pending-drills', languageId] })

  const publishMutation = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      reviewDrill(id, approve),
    onSuccess: invalidate,
  })
  const recommendMutation = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      recommend('drill', id, approve ? 'approve' : 'reject'),
    onSuccess: invalidate,
  })

  const pending = data?.pending
  const canPublish = data?.can_publish ?? false
  // Nothing pending → don't clutter the Review tab.
  if (!pending || pending.length === 0) return null
  const busy = publishMutation.isPending || recommendMutation.isPending

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm space-y-2"
      data-testid="generated-drills"
    >
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-800">
          Generated drills · awaiting review
        </h2>
        <span className="text-xs text-amber-600">{pending.length} pending</span>
      </div>
      <p className="text-xs text-gray-500">
        {canPublish
          ? 'AI-generated grammar drills, hidden from learners until you approve them — approved drills become permanent corpus, rejected ones are deleted.'
          : 'AI-generated grammar drills. As a trial reviewer you can recommend approve or reject; a full reviewer makes the final call.'}
      </p>
      <ul className="space-y-1.5">
        {pending.map((d) => (
          <li
            key={d.id}
            className="flex items-start justify-between gap-2 rounded-lg border border-gray-100 px-2.5 py-1.5"
          >
            <div className="min-w-0">
              <div className="text-xs text-gray-400">
                {d.point_title}
                {d.cell && <span className="ml-1 text-lang">· {d.cell}</span>}
              </div>
              <div className="text-sm text-gray-800">
                {d.sentence.replace('{{answer}}', `【${d.answer}】`)}
                {d.flagged && (
                  <span className="ml-2 align-middle rounded bg-red-50 text-red-600 px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
                    flagged
                  </span>
                )}
              </div>
              {d.translation && (
                <div className="text-[11px] text-gray-400">{d.translation}</div>
              )}
              {d.hint && (
                <div className="text-[11px] text-gray-400">hint: {d.hint}</div>
              )}
              {d.flagged && d.flag_reason && (
                <div className="text-[11px] text-red-500">⚠ {d.flag_reason}</div>
              )}
              <RecoSummary tally={d.recommendations} />
            </div>
            <div className="flex shrink-0 gap-1">
              {canPublish ? (
                <>
                  <button
                    type="button"
                    onClick={() => publishMutation.mutate({ id: d.id, approve: true })}
                    disabled={busy}
                    className="rounded-md bg-green-600 text-white px-2 py-1 text-[11px] hover:bg-green-700 disabled:opacity-40"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => publishMutation.mutate({ id: d.id, approve: false })}
                    disabled={busy}
                    className="rounded-md border border-gray-200 text-gray-600 px-2 py-1 text-[11px] hover:bg-gray-50 disabled:opacity-40"
                  >
                    Reject
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => recommendMutation.mutate({ id: d.id, approve: true })}
                    disabled={busy}
                    className="rounded-md border border-green-300 text-green-700 px-2 py-1 text-[11px] hover:bg-green-50 disabled:opacity-40"
                  >
                    Recommend ✓
                  </button>
                  <button
                    type="button"
                    onClick={() => recommendMutation.mutate({ id: d.id, approve: false })}
                    disabled={busy}
                    className="rounded-md border border-gray-200 text-gray-600 px-2 py-1 text-[11px] hover:bg-gray-50 disabled:opacity-40"
                  >
                    Recommend ✗
                  </button>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
