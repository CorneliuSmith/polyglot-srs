import type { RelatedPoint } from '../api/types'
import StageBadge from './StageBadge'

/**
 * Bunpro-style Related grid on grammar points: authored neighbours with a
 * contrastive one-liner and the learner's stage on each — "you know this
 * cousin, here's how it differs."
 */
export default function RelatedGrid({
  related,
  onOpen,
}: {
  related: RelatedPoint[]
  /** when provided, tiles are clickable (e.g. opens the point in the path) */
  onOpen?: (id: string) => void
}) {
  if (related.length === 0) return null
  return (
    <div>
      <h3 className="font-semibold text-gray-700 mb-1">Related</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {related.map((r) => {
          const body = (
            <>
              <span className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-gray-900">{r.title}</span>
                <StageBadge stage={r.stage} />
              </span>
              {(r.contrast || r.function_note) && (
                <span className="block text-xs text-gray-500 mt-0.5">
                  {r.contrast ?? r.function_note}
                </span>
              )}
            </>
          )
          return onOpen ? (
            <button
              key={r.id}
              type="button"
              onClick={() => onOpen(r.id)}
              className="text-left rounded-xl border border-gray-200 bg-white px-3 py-2 hover:border-lang/40 transition"
            >
              {body}
            </button>
          ) : (
            <div key={r.id} className="rounded-xl border border-gray-200 bg-white px-3 py-2">
              {body}
            </div>
          )
        })}
      </div>
    </div>
  )
}
