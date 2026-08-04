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

export default function TranslationStatusPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['translation-status'],
    queryFn: getTranslationStatus,
    refetchInterval: 60_000,
  })

  if (isLoading) return <p className="text-xs text-gray-400">Checking…</p>
  if (isError || !data) {
    return <p className="text-xs text-red-500">Could not read status.</p>
  }

  const migrationsOk = Object.values(data.migrations).every(Boolean)
  const missing = Object.entries(data.migrations)
    .filter(([, ok]) => !ok)
    .map(([t]) => t)

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
        <span className="text-xs text-gray-400">
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
        return (
          <div
            key={`${p.code}-${p.locale}`}
            className="rounded-lg border border-gray-100 p-2"
          >
            <p className="text-xs font-semibold text-gray-800">
              {p.language} → {p.locale}{' '}
              <span className="font-normal text-gray-400">
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
                  .join(' · ') + ' left'
              )}
            </p>
            <p className="text-[11px] text-gray-400">
              done: {p.filled.words} words · {p.filled.drills} drills ·{' '}
              {p.filled.explanations} explanations
            </p>
          </div>
        )
      })}

      {data.switched_off.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-amber-700">
            Learners waiting on a switched-off course
          </p>
          <ul className="mt-0.5 space-y-0.5">
            {data.switched_off.map((o) => (
              <li key={`${o.code}-${o.locale}`} className="text-[11px] text-gray-500">
                {o.language} → {o.locale} · {o.learners} learner
                {o.learners === 1 ? '' : 's'} — turn Auto-translate on above
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
