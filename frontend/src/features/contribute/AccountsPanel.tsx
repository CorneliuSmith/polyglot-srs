import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteAccount,
  listAccounts,
  overridePlan,
  type AdminAccount,
} from '../../api/contribute'
import type { Language } from '../../api/types'

function AccountRow({
  account,
  languages,
  selfId,
}: {
  account: AdminAccount
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
    <tr className="odd:bg-gray-50">
      <td className="px-3 py-2">
        <span className="block text-sm text-gray-800">{account.email}</span>
        <span className="block text-xs text-gray-400">
          joined {account.created_at?.slice(0, 10) ?? '—'}
          {account.roles.length > 0 && ` · ${account.roles.join(', ')}`}
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

/**
 * Admin account management: every user with plan, roles, and study volume;
 * plan override; permanent deletion (typed-email confirm, never yourself).
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
                  <th className="px-3 py-1" />
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <AccountRow
                    key={a.id}
                    account={a}
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
