import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getContentHistory,
  revertContentChange,
  type ContentChange,
} from '../../api/contribute'

/** Human labels + tone for each logged action. */
const ACTION_LABEL: Record<string, { text: string; cls: string }> = {
  created: { text: 'created', cls: 'text-gray-500' },
  edited: { text: 'edited', cls: 'text-blue-600' },
  approved: { text: 'approved', cls: 'text-green-700' },
  rejected: { text: 'rejected', cls: 'text-red-600' },
  flagged: { text: 'flagged', cls: 'text-amber-600' },
  level_confirmed: { text: 'confirmed level', cls: 'text-green-700' },
  level_set: { text: 'set AI level', cls: 'text-gray-500' },
  ai_checked: { text: 'AI-checked', cls: 'text-indigo-600' },
  reverted: { text: 'rolled back', cls: 'text-purple-600' },
}

function fmt(when: string | null): string {
  if (!when) return ''
  const d = new Date(when)
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function summarize(v: Record<string, unknown> | null): string {
  if (!v) return ''
  // Prefer the most human field; fall back to a compact key list.
  for (const k of ['sentence', 'explanation', 'level', 'translation']) {
    if (typeof v[k] === 'string' && v[k]) return v[k] as string
  }
  return Object.entries(v)
    .map(([k, val]) => `${k}: ${val ?? '∅'}`)
    .join(', ')
}

function ChangeRow({
  change,
  canRevert,
  onReverted,
}: {
  change: ContentChange
  canRevert: boolean
  onReverted: () => void
}) {
  const revert = useMutation({
    mutationFn: () => revertContentChange(change.id),
    onSuccess: onReverted,
  })
  const label = ACTION_LABEL[change.action] ?? { text: change.action, cls: 'text-gray-600' }
  return (
    <li className="py-2 text-xs">
      <div className="flex items-center justify-between gap-2">
        <span>
          <span className={`font-medium ${label.cls}`}>{label.text}</span>
          <span className="text-gray-400"> · {change.actor_email ?? 'system'}</span>
          <span className="text-gray-300"> · {fmt(change.created_at)}</span>
        </span>
        {canRevert && change.revertible && (
          <button
            type="button"
            onClick={() => {
              if (window.confirm('Roll this change back to its previous value?'))
                revert.mutate()
            }}
            disabled={revert.isPending}
            className="shrink-0 text-purple-600 hover:underline disabled:opacity-40"
          >
            Roll back
          </button>
        )}
      </div>
      {change.note && <div className="mt-0.5 text-gray-500">{change.note}</div>}
      {(change.before || change.after) && change.action === 'edited' && (
        <div className="mt-0.5 space-y-0.5">
          {change.before && (
            <div className="text-gray-400 line-through truncate">
              {summarize(change.before)}
            </div>
          )}
          {change.after && (
            <div className="text-gray-600 truncate">{summarize(change.after)}</div>
          )}
        </div>
      )}
    </li>
  )
}

/**
 * The change timeline for one card: who did what, when, before→after, with a
 * roll-back button on revertible edits (full reviewers/admins). Collapsed by
 * default — a "History" toggle keeps the review panels uncluttered.
 */
export default function CardHistory({
  entityType,
  entityId,
}: {
  entityType: string
  entityId: string
}) {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['content-history', entityType, entityId],
    queryFn: () => getContentHistory(entityType, entityId),
    enabled: open,
    retry: false,
  })
  const onReverted = () => {
    qc.invalidateQueries({ queryKey: ['content-history', entityType, entityId] })
    // The underlying content changed; let the host list refetch too.
    qc.invalidateQueries({ queryKey: ['vocab-examples'] })
  }

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] text-gray-400 hover:text-gray-600"
      >
        {open ? 'Hide history' : 'History'}
      </button>
      {open && (
        <div data-testid="card-history" className="mt-1 rounded-lg bg-gray-50 border border-gray-100 px-2.5 py-1">
          {isLoading && <p className="text-xs text-gray-400 py-1">Loading…</p>}
          {data && data.changes.length === 0 && (
            <p className="text-xs text-gray-400 py-1">No changes recorded yet.</p>
          )}
          {data && data.changes.length > 0 && (
            <ul className="divide-y divide-gray-100">
              {data.changes.map((c) => (
                <ChangeRow
                  key={c.id}
                  change={c}
                  canRevert={data.can_revert}
                  onReverted={onReverted}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
