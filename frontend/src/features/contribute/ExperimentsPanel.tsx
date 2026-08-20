import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FlaskConical, UserPlus, X } from 'lucide-react'
import {
  assignExperiment,
  getExperiments,
  updateExperiment,
  type Experiment,
} from '../../api/contribute'

/** Same idiom as LanguageVisibilityPanel: surface the server's own detail,
 * because the useful case is the 503 naming the migration that hasn't been
 * applied yet. */
function extractDetail(err: unknown): string | undefined {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data
    ?.detail
}

/**
 * Admin control (owner: "an option in admin to toggle between uis… Maybe
 * assign a ui to them? Broadly this would be for rollout changes? And get
 * feedback?").
 *
 * Three controls, in the order a rollout actually goes:
 *
 *   1. Put a few named people on it and ask them. That is the one that
 *      produces sentences rather than numbers, and it is first because at
 *      this stage there is nothing to measure yet.
 *   2. Turn it on and give it a percentage. Everyone without an explicit
 *      assignment is bucketed from their user id, so the same person keeps
 *      the same answer and raising the share never yanks anyone back out.
 *   3. Turn it off. Everyone returns to the default on their next page
 *      load, and every assignment stays on disk for when it comes back.
 *
 * Feedback sent from the app records which variant the sender was looking
 * at (server-side, see repositories/feedback.py), so the reports come back
 * already sorted by what people were actually seeing.
 */
export default function ExperimentsPanel() {
  const qc = useQueryClient()
  const { data: experiments = [], isError, error } = useQuery({
    queryKey: ['experiments'],
    queryFn: getExperiments,
    retry: false,
  })

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
      <div className="flex items-center gap-2 mb-1">
        <FlaskConical aria-hidden className="h-4 w-4 text-gray-500" />
        <h2 className="text-xs uppercase tracking-wide text-gray-500">
          Rollouts
        </h2>
      </div>
      <p className="text-sm text-gray-500 mb-3">
        Give a change to some accounts and not others, then read what they
        say about it. Feedback sent from the app records which version the
        sender was on.
      </p>
      {isError && (
        <p className="text-sm text-red-600" data-testid="experiments-error">
          {extractDetail(error) ?? 'Could not load rollouts.'}
        </p>
      )}
      {!isError && experiments.length === 0 && (
        <p className="text-sm text-gray-500">Nothing set up yet.</p>
      )}
      <div className="space-y-4">
        {experiments.map((experiment) => (
          <ExperimentRow
            key={experiment.key}
            experiment={experiment}
            onChanged={() => qc.invalidateQueries({ queryKey: ['experiments'] })}
          />
        ))}
      </div>
    </div>
  )
}

function ExperimentRow({
  experiment,
  onChanged,
}: {
  experiment: Experiment
  onChanged: () => void
}) {
  const [email, setEmail] = useState('')
  const [assignVariant, setAssignVariant] = useState(
    experiment.variants.find((v) => v.key !== experiment.default_variant)?.key ??
      experiment.default_variant,
  )

  const patch = useMutation({
    mutationFn: updateExperiment,
    onSuccess: onChanged,
  })
  const assign = useMutation({
    mutationFn: assignExperiment,
    onSuccess: () => {
      setEmail('')
      onChanged()
    },
  })

  // Explicit assignments only — bucketed accounts are computed from their id
  // and never stored, so there is no row to count. Showing a made-up total
  // would be worse than showing the percentage next to it.
  const pinned = (experiment.counts ?? []).reduce(
    (n, c) => n + c.count,
    0,
  )

  return (
    <div className="rounded-xl border border-gray-200 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-gray-900">{experiment.name}</p>
          {experiment.description && (
            <p className="text-sm text-gray-500 mt-0.5 max-w-prose">
              {experiment.description}
            </p>
          )}
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700 shrink-0">
          <input
            type="checkbox"
            checked={experiment.enabled}
            data-testid={`experiment-enabled-${experiment.key}`}
            onChange={(e) =>
              patch.mutate({ key: experiment.key, enabled: e.target.checked })
            }
            className="h-4 w-4"
          />
          {experiment.enabled ? 'Running' : 'Off'}
        </label>
      </div>

      {/* Off is a real state, not a paused one: it puts everybody back on the
          default immediately and keeps every assignment for later. Saying so
          here is cheaper than someone finding out by trying it. */}
      {!experiment.enabled && (
        <p className="mt-2 text-xs text-gray-500">
          Everyone is on {labelOf(experiment, experiment.default_variant)}.
          Assignments below are kept, and take effect again when you turn this
          back on.
        </p>
      )}

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">
            Everyone else gets
          </p>
          <select
            value={experiment.default_variant}
            data-testid={`experiment-default-${experiment.key}`}
            onChange={(e) =>
              patch.mutate({
                key: experiment.key,
                default_variant: e.target.value,
              })
            }
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
          >
            {experiment.variants.map((v) => (
              <option key={v.key} value={v.key}>
                {v.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">
            …unless they fall in this share
          </p>
          <div className="space-y-2">
            {experiment.variants
              .filter((v) => v.key !== experiment.default_variant)
              .map((v) => (
                <label key={v.key} className="flex items-center gap-2 text-sm">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    disabled={!experiment.enabled}
                    value={experiment.rollout[v.key] ?? 0}
                    data-testid={`experiment-rollout-${experiment.key}-${v.key}`}
                    onChange={(e) =>
                      patch.mutate({
                        key: experiment.key,
                        rollout: {
                          ...experiment.rollout,
                          [v.key]: Math.max(
                            0,
                            Math.min(100, Number(e.target.value) || 0),
                          ),
                        },
                      })
                    }
                    className="w-20 rounded-lg border border-gray-200 px-2 py-1 text-sm tabular-nums disabled:opacity-50"
                  />
                  <span className="text-gray-700">% on {v.label}</span>
                </label>
              ))}
          </div>
        </div>
      </div>

      <label className="mt-3 flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={experiment.learner_choice}
          data-testid={`experiment-choice-${experiment.key}`}
          onChange={(e) =>
            patch.mutate({
              key: experiment.key,
              learner_choice: e.target.checked,
            })
          }
          className="h-4 w-4"
        />
        Let people switch themselves in Settings
      </label>

      {patch.isError && (
        <p className="mt-2 text-sm text-red-600" data-testid="experiment-save-error">
          {extractDetail(patch.error) ?? 'Could not save that.'}
        </p>
      )}

      {/* Assign by email, because that is who the admin is thinking of —
          nobody remembers a UUID. */}
      <div className="mt-4 border-t border-gray-100 pt-3">
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">
          Put someone on a version {pinned > 0 && `(${pinned} pinned)`}
        </p>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (email.trim()) {
              assign.mutate({
                key: experiment.key,
                email: email.trim(),
                variant: assignVariant,
              })
            }
          }}
        >
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="their email"
            data-testid={`experiment-email-${experiment.key}`}
            className="flex-1 min-w-[12rem] rounded-lg border border-gray-200 px-3 py-2 text-sm"
          />
          <select
            value={assignVariant}
            onChange={(e) => setAssignVariant(e.target.value)}
            data-testid={`experiment-assign-variant-${experiment.key}`}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
          >
            {experiment.variants.map((v) => (
              <option key={v.key} value={v.key}>
                {v.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={assign.isPending || !email.trim()}
            data-testid={`experiment-assign-${experiment.key}`}
            className="flex items-center gap-1.5 rounded-lg bg-lang px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            <UserPlus aria-hidden className="h-4 w-4" />
            Assign
          </button>
        </form>
        {assign.isError && (
          <p className="mt-2 text-sm text-red-600" data-testid="experiment-assign-error">
            {extractDetail(assign.error) ?? 'Could not assign that.'}
          </p>
        )}

        {(experiment.assigned ?? []).length > 0 && (
          <ul className="mt-3 space-y-1">
            {experiment.assigned!.map((row) => (
              <li
                key={row.user_id}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <span className="min-w-0 truncate text-gray-700">
                  {row.email ?? row.user_id}
                  <span className="text-gray-500">
                    {' '}
                    — {labelOf(experiment, row.variant)}
                    {/* Worth showing: "42 on flat" means something different
                        when 40 of them chose it themselves. */}
                    {row.source === 'self' && ' (their choice)'}
                  </span>
                </span>
                <button
                  type="button"
                  aria-label={`Release ${row.email ?? row.user_id}`}
                  onClick={() =>
                    assign.mutate({
                      key: experiment.key,
                      email: row.email ?? '',
                      variant: null,
                    })
                  }
                  className="shrink-0 rounded-lg p-1 text-gray-400 hover:text-gray-700"
                >
                  <X aria-hidden className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function labelOf(experiment: Experiment, key: string): string {
  return experiment.variants.find((v) => v.key === key)?.label ?? key
}
