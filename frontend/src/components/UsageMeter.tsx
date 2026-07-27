import type { TutorAllowance } from '../api/tutor'

/** Claude-style usage meter (owner, 2026-07-27): the intelligent features are
 * invisible machinery; the only thing a member ever sees about them is how
 * much of their monthly usage they've drawn — a percentage and a reset date,
 * never message counts, models, or plumbing. Renders nothing for unlimited
 * or blocked accounts (no meter is the "it just works" state). */
export default function UsageMeter({
  allowance,
  className = '',
}: {
  allowance: TutorAllowance | null | undefined
  className?: string
}) {
  if (!allowance || allowance.unlimited || !allowance.limit) return null
  if (allowance.tier === 'blocked') return null
  const pct = Math.min(
    100,
    Math.round(((allowance.used ?? 0) / allowance.limit) * 100),
  )
  const resets = allowance.resets_at
    ? new Date(allowance.resets_at).toLocaleDateString(undefined, {
        month: 'long',
        day: 'numeric',
      })
    : null
  const barColor =
    pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-lang'
  return (
    <div className={className} data-testid="usage-meter">
      <div className="flex items-baseline justify-between text-xs text-gray-500">
        <span>Monthly usage</span>
        <span data-testid="usage-pct">{pct}% used</span>
      </div>
      <div
        className="mt-1 h-1.5 w-full rounded-full bg-gray-200 overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Monthly usage"
      >
        <div
          className={`h-full rounded-full ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {resets && (
        <p className="mt-1 text-xs text-gray-400">Resets {resets}</p>
      )}
    </div>
  )
}
