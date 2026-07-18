import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { grantRole, listAllRoles, revokeRole } from '../../api/contribute'
import type { GrantableRole } from '../../api/contribute'
import type { Language } from '../../api/types'

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail
  return detail ?? 'Something went wrong.'
}

/**
 * Admin-only role management: who can contribute, who can approve, per
 * language or globally. Grants go by account email — the person signs up
 * first, then an admin elevates them here.
 */
export default function RolesPanel({ languages }: { languages: Language[] }) {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<GrantableRole>('contributor')
  const [languageId, setLanguageId] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const { data: grants = [] } = useQuery({
    queryKey: ['all-roles'],
    queryFn: listAllRoles,
  })

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['all-roles'] })

  const grantMutation = useMutation({
    mutationFn: grantRole,
    onSuccess: () => {
      setEmail('')
      setError(null)
      refresh()
    },
    onError: (err) => setError(errorMessage(err)),
  })

  const revokeMutation = useMutation({
    mutationFn: revokeRole,
    onSuccess: refresh,
  })

  const languageName = (id: string | null, code: string | null) => {
    if (!id) return 'all languages'
    return languages.find((l) => l.id === id)?.name ?? code ?? id
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-gray-800">Roles</h2>
        <p className="text-xs text-gray-500">
          Contributors draft; reviewers approve for their language; admins do
          everything. Learners need no role.
        </p>
      </div>

      {grants.length > 0 && (
        <ul className="divide-y divide-gray-50 text-sm">
          {grants.map((g) => (
            <li
              key={`${g.user_id}-${g.role}-${g.language_id ?? 'all'}`}
              className="py-1.5 flex items-center gap-2"
            >
              <span className="flex-1 truncate text-gray-800">{g.email}</span>
              <span className="text-xs rounded-full px-2 py-0.5 bg-lang-soft text-lang-dark capitalize">
                {g.role}
              </span>
              <span className="text-xs text-gray-400">
                {languageName(g.language_id, g.language_code)}
              </span>
              <button
                type="button"
                onClick={() =>
                  revokeMutation.mutate({
                    user_id: g.user_id,
                    role: g.role,
                    language_id: g.language_id,
                  })
                }
                className="text-xs text-red-500 hover:underline"
              >
                Revoke
              </button>
            </li>
          ))}
        </ul>
      )}

      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (!email.trim()) return
          grantMutation.mutate({
            email: email.trim(),
            role,
            language_id: languageId || null,
          })
        }}
      >
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="account email"
          aria-label="Account email"
          className="flex-1 min-w-[180px] rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as GrantableRole)}
          aria-label="Role"
          className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
        >
          <option value="contributor">Contributor</option>
          <option value="reviewer">Reviewer</option>
          <option value="admin">Admin</option>
        </select>
        <select
          value={languageId}
          onChange={(e) => setLanguageId(e.target.value)}
          aria-label="Role scope"
          title="Which languages this CONTENT role covers — not what the account can study"
          className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
        >
          <option value="">Role scope: all languages</option>
          {languages.map((l) => (
            <option key={l.id} value={l.id}>
              Role scope: {l.name}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={grantMutation.isPending || !email.trim()}
          className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-lg px-4 py-1.5 text-sm"
        >
          Grant
        </button>
      </form>
      {/* A tester got locked to one language because "All languages" here
          read like the STUDY plan. It is not — say so where the admin looks. */}
      <p className="text-xs text-gray-400">
        Roles control content permissions (editing, reviewing). To change which
        languages an account can <em>study</em>, use the Accounts panel’s plan
        switch (Single ↔ All languages).
      </p>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}
