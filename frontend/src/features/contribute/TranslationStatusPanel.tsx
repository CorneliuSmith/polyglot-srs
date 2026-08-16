import { useQuery } from '@tanstack/react-query'
import { getTranslationStatus } from '../../api/contribute'

/**
 * Why automatic translation is (or isn't) running — admin only.
 *
 * Every way this feature can silently do nothing looks the same from the
 * app: cards still read English. That could be a missing provider key, an
 * unapplied migration, the course left switched off, or simply a backlog
 * the per-cycle budget hasn't reached yet. Rather than guess from the
 * outside, this names the cause and shows the real remaining counts.
 * Staff-facing, so deliberately English like the rest of the admin tools.
 */
function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-xs">
      <span
        aria-hidden
        className={`inline-block h-2 w-2 rounded-full ${
          ok ? 'bg-green-500' : 'bg-red-500'
        }`}
      />
      <span className={ok ? 'text-gray-600' : 'text-red-600 font-medium'}>
        {label}
      </span>
    </span>
  )
}

/** "4 min ago" — a timestamp alone doesn't answer "is it alive right now",
 * which is the only reason anyone reads this line. */
function ago(iso: string | null): string {
  if (!iso) return 'never'
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (!Number.isFinite(secs)) return 'never'
  if (secs < 90) return 'just now'
  const mins = Math.round(secs / 60)
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 48) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

export default function TranslationStatusPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['translation-status'],
    queryFn: getTranslationStatus,
    refetchInterval: 60_000,
  })

  if (isLoading) return <p className="text-xs text-gray-500">Checking…</p>
  if (isError || !data) {
    return <p className="text-xs text-red-500">Could not read status.</p>
  }

  const migrationsOk = Object.values(data.migrations).every(Boolean)
  const missing = Object.entries(data.migrations)
    .filter(([, ok]) => !ok)
    .map(([t]) => t)

  // The sweep is the one thing every other number here depends on, and it
  // was the one thing this panel didn't show — so a dead loop and a drained
  // queue looked identical. `loop` is optional at runtime because a server
  // deployed before it existed simply won't send it; treat that as unknown
  // rather than as broken.
  const beat = data.loop
  const loopRunning = Boolean(data.loop_enabled && beat?.started && !beat?.last_error)
  const loopLabel = !data.loop_enabled
    ? 'Sweep switched off — set auto_translate_loop_enabled'
    : !beat
      ? 'Sweep status unknown — server predates this readout'
      : !beat.started
        ? 'Sweep enabled but never started in this process'
        : beat.last_error
          ? `Last sweep failed: ${beat.last_error}`
          : `Sweep running · last cycle ${ago(beat.last_cycle_at)} · ${beat.cycles} cycles`

  return (
    <div className="space-y-3" data-testid="translation-status">
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <Check
          ok={data.provider_ready}
          label={
            data.provider_ready
              ? 'Provider key present'
              : 'No ANTHROPIC_API_KEY — nothing can translate'
          }
        />
        <Check
          ok={migrationsOk}
          label={
            migrationsOk
              ? 'Migrations applied'
              : `Run supabase db push — missing: ${missing.join(', ')}`
          }
        />
        <Check ok={loopRunning} label={loopLabel} />
        <span className="text-xs text-gray-500">
          {data.budget_per_cycle} items per {Math.round(data.sweep_seconds / 60)} min
        </span>
      </div>

      {data.pairs.length === 0 && (
        <p className="text-xs text-gray-500">
          No live pairs. A pair exists only when an account is studying a
          switched-on course with a non-English support language.
        </p>
      )}

      {data.pairs.map((p) => {
        const left = Object.values(p.pending).reduce((a, b) => a + b, 0)
        // A raw backlog invites the wrong conclusion. 14,830 words looks
        // like a fault; "≈3d at this rate" reads as arithmetic, which is
        // what it is. Whole-backlog only — a learner's own cards are drawn
        // from demand first and don't wait behind this.
        const hours =
          data.budget_per_cycle > 0
            ? (left / data.budget_per_cycle) * (data.sweep_seconds / 3600)
            : 0
        const eta =
          hours < 1 ? '< 1h' : hours < 48 ? `${Math.round(hours)}h` : `${Math.round(hours / 24)}d`
        return (
          <div
            key={`${p.code}-${p.locale}`}
            className="rounded-lg border border-gray-100 p-2"
          >
            <p className="text-xs font-semibold text-gray-800">
              {p.language} → {p.locale}{' '}
              <span className="font-normal text-gray-500">
                · {p.learners} learner{p.learners === 1 ? '' : 's'}
              </span>
            </p>
            <p className="mt-0.5 text-[11px] text-gray-500">
              {left === 0 ? (
                <span className="text-green-600">Fully translated.</span>
              ) : (
                Object.entries(p.pending)
                  .filter(([, n]) => n > 0)
                  .map(([kind, n]) => `${n} ${kind}`)
                  .join(' · ') + ` left · ≈${eta} at this rate`
              )}
            </p>
            <p className="text-[11px] text-gray-500">
              done: {p.filled.words} words · {p.filled.drills} drills ·{' '}
              {p.filled.explanations} explanations
            </p>
          </div>
        )
      })}

      {data.switched_off.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-amber-700">
            Courses off the full backlog fill
          </p>
          <ul className="mt-0.5 space-y-0.5">
            {data.switched_off.map((o) => (
              <li key={`${o.code}-${o.locale}`} className="text-[11px] text-gray-500">
                {o.language} → {o.locale} · {o.learners} learner
                {o.learners === 1 ? '' : 's'} — demand and a starter corpus
                still fill; turn Auto-translate on to drain the whole backlog
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
