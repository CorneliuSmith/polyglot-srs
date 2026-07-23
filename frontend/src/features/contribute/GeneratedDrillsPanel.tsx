import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getPendingDrills, reviewDrill } from '../../api/contribute'

/** Contributor › Review: generated grammar drills awaiting review. They're
 * tagged 'ai', hidden from learners, and become permanent corpus only once a
 * reviewer approves them here (reject deletes). Parallel to the vocab example
 * gate; this is where background-generated drills surface. */
export default function GeneratedDrillsPanel({
  languageId,
}: {
  languageId: string
}) {
  const qc = useQueryClient()
  const { data: pending } = useQuery({
    queryKey: ['pending-drills', languageId],
    queryFn: () => getPendingDrills(languageId),
    enabled: !!languageId,
    retry: false,
  })

  const mutation = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      reviewDrill(id, approve),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['pending-drills', languageId] }),
  })

  // Nothing pending → don't clutter the Review tab.
  if (!pending || pending.length === 0) return null

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
        AI-generated grammar drills. They&apos;re hidden from learners until you
        approve them — approved drills become permanent corpus, rejected ones are
        deleted.
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
              </div>
              {d.translation && (
                <div className="text-[11px] text-gray-400">{d.translation}</div>
              )}
              {d.hint && (
                <div className="text-[11px] text-gray-400">hint: {d.hint}</div>
              )}
            </div>
            <div className="flex shrink-0 gap-1">
              <button
                type="button"
                onClick={() => mutation.mutate({ id: d.id, approve: true })}
                disabled={mutation.isPending}
                className="rounded-md bg-green-600 text-white px-2 py-1 text-[11px] hover:bg-green-700 disabled:opacity-40"
              >
                Approve
              </button>
              <button
                type="button"
                onClick={() => mutation.mutate({ id: d.id, approve: false })}
                disabled={mutation.isPending}
                className="rounded-md border border-gray-200 text-gray-600 px-2 py-1 text-[11px] hover:bg-gray-50 disabled:opacity-40"
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
