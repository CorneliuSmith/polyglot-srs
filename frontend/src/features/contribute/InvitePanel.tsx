import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { UserPlus } from 'lucide-react'
import { createAccount } from '../../api/contribute'

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: string } } })
    ?.response?.data?.detail
  return detail ?? 'Could not create that account.'
}

/**
 * The ambassador's whole surface: make an account, hand over the login.
 *
 * Deliberately NOT the admin AccountsPanel with buttons hidden. That panel
 * opens by listing every account on the system — email, plan, study volume —
 * and an ambassador has no business reading the roster to add one person to
 * it. Different component, different query, nothing to accidentally reveal.
 *
 * The created password is shown ONCE, here, because there is no invite email
 * yet and an ambassador who can't read it back has nothing to give the
 * person they just signed up.
 */
export default function InvitePanel() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [created, setCreated] = useState<{ email: string; password: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => createAccount(email.trim(), password),
    onSuccess: (res) => {
      setCreated({ email: res.email ?? email.trim().toLowerCase(), password })
      setEmail('')
      setPassword('')
      setError(null)
    },
    onError: (err) => setError(errorMessage(err)),
  })

  return (
    <section
      data-testid="invite-panel"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div className="flex items-start gap-2">
        <UserPlus aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-lang" />
        <div>
          <h2 className="font-semibold text-gray-800">Add an account</h2>
          <p className="text-xs text-gray-500">
            Signup is invite-only, so accounts are made here. Pick a password,
            give it to the person, and tell them to change it once they’re in.
          </p>
        </div>
      </div>

      <form
        className="space-y-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (!email.trim() || password.length < 10) return
          mutation.mutate()
        }}
      >
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="their email"
          aria-label="Email"
          autoComplete="off"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="a starting password (10+ characters)"
          aria-label="Starting password"
          autoComplete="off"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={
            mutation.isPending || !email.trim() || password.length < 10
          }
          className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-lg px-4 py-2 text-sm"
          style={{ minHeight: '44px' }}
        >
          {mutation.isPending ? 'Creating…' : 'Create account'}
        </button>
      </form>

      {created && (
        <div
          role="status"
          data-testid="invite-created"
          className="rounded-xl border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
        >
          <p className="font-semibold">Account created</p>
          <p className="text-xs break-all">
            {created.email} — password{' '}
            <span className="font-mono">{created.password}</span>
          </p>
          <p className="text-xs text-green-700/80">
            This is the only time the password is shown. Send it now.
          </p>
        </div>
      )}
      {error && (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      )}

      <p className="text-xs text-gray-500 border-t border-gray-100 pt-2">
        Adding accounts is all this role does — you can’t see the account list,
        change anyone’s plan, or grant roles. Ask an admin for those.
      </p>
    </section>
  )
}
