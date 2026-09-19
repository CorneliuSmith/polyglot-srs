import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import {
  getQualitySettings,
  updateQualitySettings,
  updateQualityTarget,
  type QualitySettings,
  type QualitySettingsResponse,
  type QualityTargets,
} from '../../api/contribute'

/**
 * The judge's spend controls (owner: a nightly judge only on condition that
 * the cap is theirs to set, in the app — "it can be a lot of money").
 *
 * Sits under Costs, not Content, because that is what it is: the switch
 * and the cap decide what the API key spends every night, and the quality
 * numbers it produces are read on the Content health panel. Nothing here is
 * a config.py constant; `quality_settings` (migration 20261107000000) is a
 * singleton row, and the loop reads it before every batch, so a change
 * lands on the next cycle without a redeploy.
 */

const MIGRATION_NOTE =
  'Quality settings need migration 20261107000000 applied — see Rollouts → Deployment.'

/** Same idiom as RolesPanel: surface the server's detail when there is one —
 * here that's the 503 naming the not-yet-applied migration. */
function extractDetail(err: unknown): string | undefined {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data
    ?.detail
}

/** An integer setting with its own Save, enabled only when the field holds a
 * valid number that differs from what is stored (TierRow's shape). */
function IntRow({
  label,
  ariaLabel,
  current,
  max,
  hint,
  disabled,
  saving,
  onSave,
}: {
  label: string
  ariaLabel: string
  current: number
  max: number
  hint?: string
  disabled: boolean
  saving: boolean
  onSave: (value: number) => void
}) {
  const [value, setValue] = useState(String(current))
  // Re-sync when the server's number changes under us (another admin, or our
  // own save landing) — without this the field keeps showing a stale edit.
  useEffect(() => setValue(String(current)), [current])

  const parsed = Number(value)
  const valid = Number.isInteger(parsed) && parsed >= 0 && parsed <= max
  const dirty = valid && parsed !== current

  return (
    <div className="flex flex-wrap items-center gap-3 border-t border-gray-100 py-2 first:border-t-0">
      <span className="min-w-0 flex-1 text-sm text-gray-800">{label}</span>
      <input
        type="number"
        min={0}
        max={max}
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        aria-label={ariaLabel}
        className="w-32 rounded border border-gray-300 px-2 py-1 text-sm tabular-nums disabled:opacity-40"
      />
      {hint && <span className="text-xs text-gray-500 tabular-nums">{hint}</span>}
      <button
        type="button"
        onClick={() => onSave(parsed)}
        disabled={disabled || !dirty || saving}
        className="rounded border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
      >
        Save
      </button>
    </div>
  )
}

/** The model override: blank means the checker tier for the course. */
function ModelRow({
  current,
  disabled,
  saving,
  onSave,
}: {
  current: string | null
  disabled: boolean
  saving: boolean
  onSave: (value: string | null) => void
}) {
  const [value, setValue] = useState(current ?? '')
  useEffect(() => setValue(current ?? ''), [current])
  const next = value.trim() === '' ? null : value.trim()
  const valid = next === null || next.length <= 100
  const dirty = valid && next !== current

  return (
    <div className="flex flex-wrap items-center gap-3 border-t border-gray-100 py-2">
      <span className="min-w-0 flex-1 text-sm text-gray-800">Model</span>
      <input
        type="text"
        value={value}
        disabled={disabled}
        maxLength={100}
        placeholder="checker tier"
        onChange={(e) => setValue(e.target.value)}
        aria-label="Judge model"
        className="w-56 rounded border border-gray-300 px-2 py-1 font-mono text-sm disabled:opacity-40"
      />
      <span className="text-xs text-gray-500">blank = the checker tier</span>
      <button
        type="button"
        onClick={() => onSave(next)}
        disabled={disabled || !dirty || saving}
        className="rounded border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
      >
        Save
      </button>
    </div>
  )
}

function Switch({
  checked,
  disabled,
  ariaLabel,
  onChange,
}: {
  checked: boolean
  disabled: boolean
  ariaLabel: string
  onChange: (next: boolean) => void
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={
        'rounded-full px-3 py-1 text-xs font-semibold border disabled:opacity-40 ' +
        (checked
          ? 'bg-emerald-600 border-emerald-600 text-white'
          : 'bg-gray-100 border-gray-300 text-gray-700')
      }
    >
      {checked ? 'On' : 'Off'}
    </button>
  )
}

/** One course's opt-in and thresholds. The toggle saves at once; the two
 * percentages share a Save that sends only what changed. */
function TargetRow({
  code,
  name,
  targets,
  disabled,
  saving,
  onSave,
}: {
  code: string
  name: string
  targets: QualityTargets
  disabled: boolean
  saving: boolean
  onSave: (partial: Partial<QualityTargets>) => void
}) {
  const [bad, setBad] = useState(String(targets.max_bad_card_pct))
  const [flag, setFlag] = useState(String(targets.max_judge_flag_pct))
  useEffect(() => setBad(String(targets.max_bad_card_pct)), [targets.max_bad_card_pct])
  useEffect(() => setFlag(String(targets.max_judge_flag_pct)), [targets.max_judge_flag_pct])

  const inRange = (v: number) => Number.isFinite(v) && v >= 0 && v <= 100
  const badN = Number(bad)
  const flagN = Number(flag)
  const valid = bad.trim() !== '' && flag.trim() !== '' && inRange(badN) && inRange(flagN)
  const partial: Partial<QualityTargets> = {}
  if (valid && badN !== targets.max_bad_card_pct) partial.max_bad_card_pct = badN
  if (valid && flagN !== targets.max_judge_flag_pct) partial.max_judge_flag_pct = flagN
  const dirty = Object.keys(partial).length > 0

  return (
    <tr className="border-t border-gray-50 text-gray-700" data-testid={`quality-target-${code}`}>
      <td className="py-1 pe-2 font-mono text-xs">{code}</td>
      <td className="py-1 pe-2">{name}</td>
      <td className="py-1 pe-2">
        <Switch
          checked={targets.judge_enabled}
          disabled={disabled || saving}
          ariaLabel={`Judge ${name}`}
          onChange={(next) => onSave({ judge_enabled: next })}
        />
      </td>
      <td className="py-1 pe-2">
        <input
          type="number"
          min={0}
          max={100}
          step="0.1"
          value={bad}
          disabled={disabled}
          onChange={(e) => setBad(e.target.value)}
          aria-label={`${name} max bad-card %`}
          className="w-20 rounded border border-gray-300 px-2 py-0.5 text-xs tabular-nums disabled:opacity-40"
        />
      </td>
      <td className="py-1 pe-2">
        <input
          type="number"
          min={0}
          max={100}
          step="0.1"
          value={flag}
          disabled={disabled}
          onChange={(e) => setFlag(e.target.value)}
          aria-label={`${name} max judge-flag %`}
          className="w-20 rounded border border-gray-300 px-2 py-0.5 text-xs tabular-nums disabled:opacity-40"
        />
      </td>
      <td className="py-1 text-end">
        <button
          type="button"
          onClick={() => onSave(partial)}
          disabled={disabled || !dirty || saving}
          className="rounded border border-gray-300 px-2 py-0.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
        >
          Save
        </button>
      </td>
    </tr>
  )
}

export default function QualitySettingsPanel() {
  const qc = useQueryClient()
  const [savingField, setSavingField] = useState<string | null>(null)
  const [savingCode, setSavingCode] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['quality-settings'],
    queryFn: getQualitySettings,
    retry: false,
  })
  // Names come from the catalog the whole app already caches; the settings
  // response is keyed by code alone.
  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const nameByCode = new Map(languages.map((l) => [l.code, l.name]))

  const settingsMutation = useMutation({
    mutationFn: (partial: Partial<QualitySettings>) => updateQualitySettings(partial),
    onSuccess: (next) => {
      qc.setQueryData<QualitySettingsResponse>(['quality-settings'], next)
      // The content health header shows the switch and the cap.
      qc.invalidateQueries({ queryKey: ['content-health'] })
      setSavingField(null)
    },
    onError: () => setSavingField(null),
  })

  const targetMutation = useMutation({
    mutationFn: ({ code, partial }: { code: string; partial: Partial<QualityTargets> }) =>
      updateQualityTarget(code, partial),
    onSuccess: (res) => {
      qc.setQueryData<QualitySettingsResponse>(['quality-settings'], (old) =>
        old ? { ...old, targets: { ...old.targets, [res.code]: res.targets } } : old,
      )
      qc.invalidateQueries({ queryKey: ['content-health'] })
      setSavingCode(null)
    },
    onError: () => setSavingCode(null),
  })

  const available = data?.available === true
  const disabled = !available || isLoading
  const save = (field: keyof QualitySettings, value: QualitySettings[typeof field]) => {
    setSavingField(field)
    settingsMutation.mutate({ [field]: value })
  }

  const targetCodes = data ? Object.keys(data.targets).sort() : []

  return (
    <section
      data-testid="quality-settings"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-gray-800">Content judge</h2>
          <p className="text-xs text-gray-500">
            This spends the API key every night it is on. The daily cap is
            the most it can spend in a UTC day; rows per cycle is how much it
            tries each night.
          </p>
        </div>
        {data ? (
          <Switch
            checked={data.settings.judge_enabled}
            disabled={disabled || settingsMutation.isPending}
            ariaLabel="Judge master switch"
            onChange={(next) => save('judge_enabled', next)}
          />
        ) : (
          <span className="text-xs text-gray-400">…</span>
        )}
      </div>

      {isLoading && <p className="text-xs text-gray-500">Loading…</p>}
      {isError && <p className="text-sm text-red-600">Couldn’t load the judge settings.</p>}
      {data && !available && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800" role="status">
          {MIGRATION_NOTE}
        </p>
      )}

      {data && (
        <div>
          <IntRow
            label="Rows per cycle"
            ariaLabel="Judge rows per cycle"
            current={data.settings.judge_rows_per_cycle}
            max={10_000}
            hint="rows/night"
            disabled={disabled}
            saving={savingField === 'judge_rows_per_cycle'}
            onSave={(v) => save('judge_rows_per_cycle', v)}
          />
          <IntRow
            label="Daily token cap"
            ariaLabel="Judge daily token cap"
            current={data.settings.judge_daily_token_cap}
            max={1_000_000_000}
            hint={`${data.settings.judge_daily_token_cap.toLocaleString()} · spent today ${data.spent_today.toLocaleString()} of cap`}
            disabled={disabled}
            saving={savingField === 'judge_daily_token_cap'}
            onSave={(v) => save('judge_daily_token_cap', v)}
          />
          <ModelRow
            current={data.settings.judge_model}
            disabled={disabled}
            saving={savingField === 'judge_model'}
            onSave={(v) => save('judge_model', v)}
          />
        </div>
      )}

      {settingsMutation.isError && (
        <p className="text-sm text-red-600" role="alert">
          {extractDetail(settingsMutation.error) ??
            'That didn’t save. The number on screen is what you typed, not what’s stored — try again.'}
        </p>
      )}

      {/* Per course: which are judged, and what makes each one red on the
          Content health panel. A course with no row reads as the defaults
          (off, 15%, 5%). */}
      {data && targetCodes.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-start text-gray-500">
                <th className="py-1 font-medium">Code</th>
                <th className="py-1 font-medium">Course</th>
                <th className="py-1 font-medium">Judge</th>
                <th className="py-1 font-medium">Max bad cards %</th>
                <th className="py-1 font-medium">Max judge flags %</th>
                <th className="py-1" />
              </tr>
            </thead>
            <tbody>
              {targetCodes.map((code) => (
                <TargetRow
                  key={code}
                  code={code}
                  name={nameByCode.get(code) ?? code}
                  targets={data.targets[code]}
                  disabled={disabled}
                  saving={savingCode === code}
                  onSave={(partial) => {
                    setSavingCode(code)
                    targetMutation.mutate({ code, partial })
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {targetMutation.isError && (
        <p className="text-sm text-red-600" role="alert">
          {extractDetail(targetMutation.error) ?? 'That course’s targets didn’t save — try again.'}
        </p>
      )}
    </section>
  )
}
