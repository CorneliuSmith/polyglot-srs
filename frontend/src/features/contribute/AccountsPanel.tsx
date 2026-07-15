import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createAccount,
  deleteAccount,
  grantRole,
  listAccounts,
  listAllRoles,
  overridePlan,
  revokeRole,
  setTutorAccess,
  type AdminAccount,
  type GrantableRole,
  type RoleGrantRow,
  type TutorAccess,
} from '../../api/contribute'
import type { Language } from '../../api/types'

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail
  return detail ?? 'Something went wrong.'
}

/** Per-account role chips + a compact grant control. Grants aren't
 * exclusive (reviewer for Russian AND contributor everywhere is legal),
 * so "changing" a role = add the new grant, revoke the old chip. */
function RolesCell({
  account,
  grants,
  languages,
  selfId,
}: {
  account: AdminAccount
  grants: RoleGrantRow[]
  languages: Language[]
  selfId: string | null
}) {
  const queryClient = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [role, setRole] = useState<GrantableRole>('reviewer')
  const [languageId, setLanguageId] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['all-roles'] })
    queryClient.invalidateQueries({ queryKey: ['admin-accounts'] })
  }

  const grantMutation = useMutation({
    mutationFn: () =>
      grantRole({
        email: account.email,
        role,
        language_id: languageId || null,
      }),
    onSuccess: () => {
      setAdding(false)
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorMessage(err)),
  })

  const revokeMutation = useMutation({
    mutationFn: (g: RoleGrantRow) =>
      revokeRole({ user_id: g.user_id, role: g.role, language_id: g.language_id }),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorMessage(err)),
  })

  const scopeName = (g: RoleGrantRow) => {
    if (!g.language_id) return 'all languages'
    return (
      languages.find((l) => l.id === g.language_id)?.name ??
      g.language_code ??
      g.language_id
    )
  }

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-1">
        {grants.length === 0 && !adding && (
          <span className="text-xs text-gray-400">learner</span>
        )}
        {grants.map((g) => {
          // Revoking your own admin grant locks you out of this panel —
          // same protection as the delete button.
          const isSelfAdmin =
            g.role === 'admin' && account.id === selfId
          return (
            <span
              key={`${g.role}-${g.language_id ?? 'all'}`}
              className="inline-flex items-center gap-1 text-xs rounded-full pl-2 pr-1 py-0.5 bg-lang-soft text-lang-dark"
            >
              <span className="capitalize">{g.role}</span>
              <span className="text-gray-400">· {scopeName(g)}</span>
              <button
                type="button"
                onClick={() => revokeMutation.mutate(g)}
                disabled={isSelfAdmin || revokeMutation.isPending}
                aria-label={`Revoke ${g.role} (${scopeName(g)}) for ${account.email}`}
                title={
                  isSelfAdmin
                    ? "You can't revoke your own admin role from here"
                    : 'Revoke this role'
                }
                className="rounded-full px-1 hover:bg-white/60 disabled:opacity-40"
              >
                ×
              </button>
            </span>
          )
        })}
        <button
          type="button"
          onClick={() => setAdding((v) => !v)}
          aria-label={`Add role for ${account.email}`}
          className="text-xs text-lang hover:underline"
        >
          {adding ? 'cancel' : '+ role'}
        </button>
      </div>
      {adding && (
        <div className="flex flex-wrap items-center gap-1">
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as GrantableRole)}
            aria-label={`New role for ${account.email}`}
            className="rounded border border-gray-300 bg-white px-1.5 py-1 text-xs"
          >
            <option value="contributor">Contributor</option>
            <option value="reviewer">Reviewer</option>
            <option value="admin">Admin</option>
          </select>
          <select
            value={languageId}
            onChange={(e) => setLanguageId(e.target.value)}
            aria-label={`Role scope for ${account.email}`}
            className="rounded border border-gray-300 bg-white px-1.5 py-1 text-xs"
          >
            <option value="">All languages</option>
            {languages.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => grantMutation.mutate()}
            disabled={grantMutation.isPending}
            className="rounded bg-lang hover:bg-lang-dark text-lang-on px-2 py-1 text-xs font-semibold disabled:opacity-50"
          >
            Grant
          </button>
        </div>
      )}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}

/** Per-account tutor override: Default (tiers decide) / Enabled with a
 * daily message cap (bounded API cost for trials) / Blocked. */
function TutorCell({ account }: { account: AdminAccount }) {
  const queryClient = useQueryClient()
  const [cap, setCap] = useState<string>(
    account.tutor_daily_cap == null ? '' : String(account.tutor_daily_cap),
  )
  const mutation = useMutation({
    mutationFn: (input: { access: TutorAccess; dailyCap: number | null }) =>
      setTutorAccess(account.id, input.access, input.dailyCap),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['admin-accounts'] }),
  })

  const parsedCap = () => {
    const n = parseInt(cap, 10)
    return Number.isFinite(n) && n >= 0 ? n : null
  }

  return (
    <div className="space-y-1">
      <select
        value={account.tutor_access}
        onChange={(e) =>
          mutation.mutate({
            access: e.target.value as TutorAccess,
            dailyCap: parsedCap(),
          })
        }
        disabled={mutation.isPending}
        aria-label={`Tutor access for ${account.email}`}
        className="rounded border border-gray-300 bg-white px-2 py-1 text-xs"
      >
        <option value="default">Default (tier)</option>
        <option value="enabled">Enabled</option>
        <option value="blocked">Blocked</option>
      </select>
      {account.tutor_access === 'enabled' && (
        <input
          value={cap}
          onChange={(e) => setCap(e.target.value.replace(/\D/g, ''))}
          onBlur={() =>
            mutation.mutate({ access: 'enabled', dailyCap: parsedCap() })
          }
          placeholder="cap/day"
          aria-label={`Tutor daily message cap for ${account.email}`}
          title="Max tutor messages per day (blank = the plus tier's daily number)"
          className="w-20 rounded border border-gray-300 bg-white px-2 py-1 text-xs"
          inputMode="numeric"
        />
      )}
      {mutation.isError && (
        <p className="text-xs text-red-500">Could not save.</p>
      )}
    </div>
  )
}

function AccountRow({
  account,
  grants,
  languages,
  selfId,
}: {
  account: AdminAccount
  grants: RoleGrantRow[]
  languages: Language[]
  selfId: string | null
}) {
  const queryClient = useQueryClient()
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['admin-accounts'] })

  const planMutation = useMutation({
    mutationFn: (input: { scope: 'single' | 'all'; languageId?: string }) =>
      overridePlan(account.id, input.scope, input.languageId),
    onSuccess: invalidate,
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteAccount(account.id),
    onSuccess: invalidate,
  })

  const handlePlanChange = (value: string) => {
    if (value === 'all') {
      planMutation.mutate({ scope: 'all' })
      return
    }
    // single: the value carries the licensed language id
    planMutation.mutate({ scope: 'single', languageId: value })
  }

  const handleDelete = () => {
    // Deleting a person's account and entire history deserves more than a
    // yes/no: the admin retypes the email.
    const typed = window.prompt(
      `PERMANENTLY delete this account and all its data (cards, history, notes)?\n\nType the account email to confirm:\n${account.email}`,
    )
    if (typed !== null && typed.trim().toLowerCase() === account.email.toLowerCase()) {
      deleteMutation.mutate()
    } else if (typed !== null) {
      window.alert('Email did not match — nothing was deleted.')
    }
  }

  const isSelf = account.id === selfId
  const planValue =
    account.plan_scope === 'single'
      ? languages.find((l) => l.code === account.plan_language)?.id ?? 'all'
      : 'all'

  return (
    <tr className="odd:bg-gray-50 align-top">
      <td className="px-3 py-2">
        <span className="block text-sm text-gray-800">{account.email}</span>
        <span className="block text-xs text-gray-400">
          joined {account.created_at?.slice(0, 10) ?? '—'}
          {isSelf && ' · you'}
        </span>
      </td>
      <td className="px-3 py-2 text-xs text-gray-500 tabular-nums">
        {account.cards} cards · {account.languages_studied} lang
      </td>
      <td className="px-3 py-2">
        <select
          value={planValue}
          onChange={(e) => handlePlanChange(e.target.value)}
          disabled={planMutation.isPending}
          aria-label={`Plan for ${account.email}`}
          className="rounded border border-gray-300 bg-white px-2 py-1 text-xs"
        >
          <option value="all">All languages</option>
          {languages.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name} only
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-2 min-w-44">
        <RolesCell
          account={account}
          grants={grants}
          languages={languages}
          selfId={selfId}
        />
      </td>
      <td className="px-3 py-2">
        <TutorCell account={account} />
      </td>
      <td className="px-3 py-2 text-right">
        <button
          type="button"
          onClick={handleDelete}
          disabled={isSelf || deleteMutation.isPending}
          title={
            isSelf
              ? "You can't delete your own account from here"
              : 'Permanently delete this account'
          }
          className="text-xs text-red-600 hover:underline disabled:opacity-40 disabled:no-underline"
        >
          Delete
        </button>
      </td>
    </tr>
  )
}

/** Mint a beta account (invite-only signup is disabled — the admin
 * creates email+password logins and hands them to friends). */
function InviteForm() {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const mutation = useMutation({
    mutationFn: () => createAccount(email.trim(), password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-accounts'] })
      setEmail('')
    },
  })
  const generate = () => {
    const words = ['kea', 'tui', 'moa', 'ruru', 'kiwi', 'weka', 'huia', 'kaka']
    const pick = () => words[Math.floor(Math.random() * words.length)]
    setPassword(`${pick()}-${pick()}-${Math.floor(1000 + Math.random() * 9000)}`)
  }
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
      <p className="text-xs text-gray-500">
        Create a beta account and share the password with your friend — they
        can change it later via “Forgot password?”.
      </p>
      <div className="flex flex-wrap gap-2">
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="friend@email.com"
          aria-label="New account email"
          className="flex-1 min-w-40 rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password (min 10 chars)"
          aria-label="New account password"
          className="flex-1 min-w-40 rounded border border-gray-300 bg-white px-2 py-1.5 text-sm font-mono"
        />
        <button
          type="button"
          onClick={generate}
          className="text-xs text-lang hover:underline"
        >
          Generate
        </button>
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={
            !email.includes('@') || password.length < 10 || mutation.isPending
          }
          className="rounded bg-lang hover:bg-lang-dark text-lang-on px-3 py-1.5 text-sm font-semibold disabled:opacity-50"
        >
          {mutation.isPending ? 'Creating…' : 'Create account'}
        </button>
      </div>
      {mutation.isSuccess && (
        <p className="text-xs text-green-700">
          Account created — password stays visible above until you clear it.
        </p>
      )}
      {mutation.isError && (
        <p className="text-xs text-red-600">
          {(mutation.error as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail ?? 'Could not create the account.'}
        </p>
      )}
    </div>
  )
}

/**
 * Admin account management: every user with plan, roles, and study volume;
 * plan override; inline role grants/revokes; permanent deletion
 * (typed-email confirm, never yourself).
 */
export default function AccountsPanel({
  languages,
  selfId,
}: {
  languages: Language[]
  selfId: string | null
}) {
  const [open, setOpen] = useState(false)
  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['admin-accounts'],
    queryFn: listAccounts,
    enabled: open,
  })
  // Same cache key as the Roles panel below, so edits here update both.
  const { data: allGrants = [] } = useQuery({
    queryKey: ['all-roles'],
    queryFn: listAllRoles,
    enabled: open,
  })
  const grantsByUser = new Map<string, RoleGrantRow[]>()
  for (const g of allGrants) {
    const bucket = grantsByUser.get(g.user_id) ?? []
    bucket.push(g)
    grantsByUser.set(g.user_id, bucket)
  }

  return (
    <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">Accounts</h2>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-xs text-lang hover:underline"
        >
          {open ? 'Hide' : 'Manage accounts'}
        </button>
      </div>
      {open && <InviteForm />}
      {open && (
        <div className="overflow-x-auto">
          {isLoading && <p className="text-xs text-gray-400">Loading…</p>}
          {!isLoading && (
            <table className="w-full text-sm" data-testid="accounts-table">
              <thead>
                <tr className="text-left text-xs text-gray-400">
                  <th className="px-3 py-1 font-normal">Account</th>
                  <th className="px-3 py-1 font-normal">Activity</th>
                  <th className="px-3 py-1 font-normal">Plan</th>
                  <th className="px-3 py-1 font-normal">Roles</th>
                  <th className="px-3 py-1 font-normal">Tutor</th>
                  <th className="px-3 py-1" />
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <AccountRow
                    key={a.id}
                    account={a}
                    grants={grantsByUser.get(a.id) ?? []}
                    languages={languages}
                    selfId={selfId}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  )
}
