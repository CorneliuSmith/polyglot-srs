import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { UserCheck } from 'lucide-react'
import {
  approveTrialRequest,
  listTrialRequests,
  rejectTrialRequest,
  type TrialRequestRow,
} from '../../api/contribute'

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail
  return detail ?? 'Something went wrong.'
}

/**
 * The trial-access queue (admin): visitors ask from the login page, the
 * request lands here (and in the admin's inbox when ADMIN_NOTIFY_EMAIL is
 * set). Approving mints the account with a TEMPORARY password — shown once
 * here, and emailed to the applicant when Resend is configured — which the
 * app forces them to replace on first sign-in.
 */
export default function TrialRequestsPanel() {
  const qc = useQueryClient()
  // Approval results keyed by request id: the temp password is shown ONCE
  // and survives the row flipping to "approved" on refetch.
  const [approved, setApproved] = useState<
    Record<string, { temp_password: string; emailed: boolean }>
  >({})
  const [error, setError] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['trial-requests'],
    queryFn: listTrialRequests,
  })

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ['trial-requests'] })

  const approveMutation = useMutation({
    mutationFn: (r: TrialRequestRow) => approveTrialRequest(r.id),
    onSuccess: (res, r) => {
      setApproved((prev) => ({
        ...prev,
        [r.id]: { temp_password: res.temp_password, emailed: res.emailed },
      }))
      setError(null)
      invalidate()
      qc.invalidateQueries({ queryKey: ['admin-accounts'] })
    },
    onError: (err) => setError(errorMessage(err)),
  })

  const rejectMutation = useMutation({
    mutationFn: (r: TrialRequestRow) => rejectTrialRequest(r.id),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: (err) => setError(errorMessage(err)),
  })

  const requests = data?.requests ?? []
  const pending = requests.filter((r) => r.status === 'pending')
  const decided = requests.filter((r) => r.status !== 'pending')

  return (
    <section
      data-testid="trial-requests-panel"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div className="flex items-start gap-2">
        <UserCheck aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-lang" />
        <div>
          <h2 className="font-semibold text-gray-800">
            Trial requests
            {pending.length > 0 && (
              <span className="ms-2 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                {pending.length} waiting
              </span>
            )}
          </h2>
          <p className="text-xs text-gray-500">
            People asking for access from the login page. Approving creates
            their account with a temporary password (they must change it on
            first sign-in) and emails it to them.
          </p>
        </div>
      </div>

      {isLoading && <p className="text-xs text-gray-500">Loading…</p>}
      {data && !data.available && (
        <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
          Trial signup needs migration 20260921 applied — run{' '}
          <code>supabase db push</code>.
        </p>
      )}
      {data?.available && requests.length === 0 && (
        <p className="text-xs text-gray-500">No requests yet.</p>
      )}

      {pending.length > 0 && (
        <ul className="divide-y divide-gray-100">
          {pending.map((r) => (
            <li key={r.id} className="py-2 space-y-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <span className="block truncate text-sm text-gray-800">
                    {r.name ? `${r.name} · ` : ''}
                    {r.email}
                  </span>
                  <span className="block text-xs text-gray-500">
                    asked {r.requested_at.slice(0, 10)}
                  </span>
                  {r.note && (
                    <span className="block text-xs text-gray-500">
                      “{r.note}”
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => approveMutation.mutate(r)}
                    disabled={approveMutation.isPending}
                    className="rounded bg-lang hover:bg-lang-dark text-lang-on px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => rejectMutation.mutate(r)}
                    disabled={rejectMutation.isPending}
                    className="text-xs text-red-600 hover:underline disabled:opacity-40"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {Object.entries(approved).map(([id, res]) => {
        const row = requests.find((r) => r.id === id)
        return (
          <div
            key={id}
            className="rounded-lg bg-green-50 px-3 py-2 text-xs text-green-800"
          >
            <strong>{row?.email ?? 'Account'}</strong> approved — temporary
            password{' '}
            <code className="rounded bg-white px-1 py-0.5 font-mono">
              {res.temp_password}
            </code>
            {res.emailed
              ? ' (emailed to them; they must change it on first sign-in).'
              : ' — email is not configured, so copy it to them yourself. They must change it on first sign-in.'}
          </div>
        )
      })}

      {decided.length > 0 && (
        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer">
            Decided ({decided.length})
          </summary>
          <ul className="mt-1 space-y-0.5">
            {decided.map((r) => (
              <li key={r.id}>
                {r.email} — {r.status}
                {r.decided_at ? ` on ${r.decided_at.slice(0, 10)}` : ''}
              </li>
            ))}
          </ul>
        </details>
      )}

      {error && <p className="text-xs text-red-500">{error}</p>}
    </section>
  )
}
