import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  PLAN_TIER_LABELS,
  getMonetization,
  getPlanLimits,
  setMonetization,
  setPlanLimit,
  type PlanTier,
} from '../../api/contribute'

/**
 * Monthly message allotment per account type (owner request: "admins should
 * be able to set token allocations for each type of account").
 *
 * These four numbers were Settings constants read from the environment — to
 * raise the free tier's cap, or trial a different number for a launch, an
 * admin had to ask an engineer to edit config and redeploy. Now they're rows
 * an admin edits here, and they take effect on every account's next
 * allowance check: nobody is logged out, nothing restarts.
 */

const TIERS: PlanTier[] = ['free', 'single', 'all', 'plus']

function TierRow({
  tier,
  current,
  onSave,
  saving,
}: {
  tier: PlanTier
  current: number
  onSave: (value: number) => void
  saving: boolean
}) {
  const [value, setValue] = useState(String(current))
  // Re-sync when the server's number changes under us (another admin, or our
  // own save landing) — without this the field keeps showing a stale edit.
  useEffect(() => setValue(String(current)), [current])

  const parsed = Number(value)
  const valid = Number.isInteger(parsed) && parsed >= 0
  const dirty = valid && parsed !== current

  return (
    <div className="flex flex-wrap items-center gap-3 border-t border-gray-100 py-2 first:border-t-0">
      <span className="min-w-0 flex-1 text-sm text-gray-800">
        {PLAN_TIER_LABELS[tier]}
      </span>
      <input
        type="number"
        min={0}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        aria-label={`${PLAN_TIER_LABELS[tier]} monthly messages`}
        className="w-28 rounded border border-gray-300 px-2 py-1 text-sm tabular-nums"
      />
      <span className="text-xs text-gray-500">msgs/month</span>
      <button
        type="button"
        onClick={() => onSave(parsed)}
        disabled={!dirty || saving}
        className="rounded border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
      >
        Save
      </button>
    </div>
  )
}

/**
 * The monetization master switch (owner: money features stay off until the
 * employer conflict-of-interest clearance lands, then one toggle turns
 * them on). While OFF, nothing payment-shaped exists anywhere in the app:
 * no prices, upgrade buttons, AI top-ups, billing links, or the tip jar —
 * and the checkout endpoints refuse. Learners just see neutral copy.
 */
function MonetizationSwitch() {
  const queryClient = useQueryClient()
  const { data: enabled, isLoading } = useQuery({
    queryKey: ['monetization'],
    queryFn: getMonetization,
    retry: false,
  })
  const mutation = useMutation({
    mutationFn: (next: boolean) => setMonetization(next),
    onSuccess: (next) => {
      queryClient.setQueryData(['monetization'], next)
      // The learner-facing flag rides on plan-prices — refetch so the
      // admin's own session reflects the flip without a reload.
      queryClient.invalidateQueries({ queryKey: ['plan-prices'] })
    },
  })

  return (
    <section
      data-testid="monetization-switch"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-gray-800">Money features</h2>
          <p className="text-xs text-gray-500">
            The master switch. Off: no prices, upgrade buttons, AI top-ups,
            billing links, or the tip jar appear anywhere, and checkout is
            closed. Turn on only once you're cleared to charge.
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled === true}
          disabled={isLoading || mutation.isPending}
          onClick={() => mutation.mutate(!enabled)}
          className={
            'rounded-full px-4 py-1.5 text-xs font-semibold border disabled:opacity-40 ' +
            (enabled
              ? 'bg-emerald-600 border-emerald-600 text-white'
              : 'bg-gray-100 border-gray-300 text-gray-700')
          }
        >
          {isLoading ? '…' : enabled ? 'On' : 'Off'}
        </button>
      </div>
      {mutation.isError && (
        <p className="text-sm text-red-600">
          That didn't save — if this deploy predates migration 20261006, the
          switch has nowhere to live yet (it reads as Off either way).
        </p>
      )}
    </section>
  )
}

export default function PlanLimitsPanel() {
  const queryClient = useQueryClient()
  const [savingTier, setSavingTier] = useState<PlanTier | null>(null)

  const { data: limits, isLoading, isError } = useQuery({
    queryKey: ['plan-limits'],
    queryFn: getPlanLimits,
    retry: false,
  })

  const mutation = useMutation({
    mutationFn: ({ tier, value }: { tier: PlanTier; value: number }) =>
      setPlanLimit(tier, value),
    onSuccess: (next) => {
      queryClient.setQueryData(['plan-limits'], next)
      setSavingTier(null)
    },
    onError: () => setSavingTier(null),
  })

  return (
    <div className="space-y-4">
    <MonetizationSwitch />
    <section
      data-testid="plan-limits"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div>
        <h2 className="font-semibold text-gray-800">Monthly allotments</h2>
        <p className="text-xs text-gray-500">
          How many AI messages each account type gets per calendar month —
          tutor chat, Gym generation, and the Reader all draw from this. Takes
          effect immediately; no redeploy.
        </p>
      </div>

      {isLoading && <p className="text-xs text-gray-500">Loading…</p>}
      {isError && (
        <p className="text-sm text-red-600">Couldn’t load the allotments.</p>
      )}

      {limits && (
        <div>
          {TIERS.map((tier) => (
            <TierRow
              key={tier}
              tier={tier}
              current={limits[tier]}
              saving={savingTier === tier}
              onSave={(value) => {
                setSavingTier(tier)
                mutation.mutate({ tier, value })
              }}
            />
          ))}
        </div>
      )}

      {mutation.isError && (
        <p className="text-sm text-red-600">
          That didn’t save. The number on screen is what you typed, not what’s
          stored — try again.
        </p>
      )}
      <p className="text-[11px] text-gray-500">
        A per-account override (Accounts → tutor access) still wins over the
        tier default for that one person. The AI add-on's pool is added ON
        TOP of the plan's base — single (0) + add-on = the "with AI"
        account; one-time top-ups stack the same way for one month.
      </p>
    </section>
    </div>
  )
}
