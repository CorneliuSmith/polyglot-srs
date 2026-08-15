import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { requestTrial } from '../../api/trial'
import { supabase } from '../../lib/supabase'
import { useAuthStore } from '../../stores/authStore'
import UiLanguageSwitcher from '../../components/UiLanguageSwitcher'

type Tab = 'signin' | 'signup'

// Invite-only beta: VITE_INVITE_ONLY=true hides self-serve signup and the
// Google button. Enforcement lives in Supabase (Auth → disable signups +
// Google provider) — this flag only keeps the UI honest about it.
const INVITE_ONLY = import.meta.env.VITE_INVITE_ONLY === 'true'

export default function LoginPage() {
  const { t } = useTranslation()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)()
  const authLoading = useAuthStore((s) => s.loading)
  const [tab, setTab] = useState<Tab>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  // Forgot-password mode: same email field, no password — sends the
  // recovery link that lands on /reset-password.
  const [resetMode, setResetMode] = useState(false)
  // Trial-request mode: the invite-only beta's front door. Same email
  // field, an optional note, no password — the admin approves from the
  // panel and the applicant gets a temporary password by email.
  const [trialMode, setTrialMode] = useState(false)
  const [trialName, setTrialName] = useState('')
  const [trialNote, setTrialNote] = useState('')

  async function handleTrialRequest(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setLoading(true)
    try {
      await requestTrial(email, trialName, trialNote)
      setMessage(
        'Request received! If it’s approved you’ll get an email with a ' +
          'temporary password.',
      )
      setTrialName('')
      setTrialNote('')
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setError(detail ?? 'Could not send the request — try again in a moment.')
    } finally {
      setLoading(false)
    }
  }

  async function handleResetRequest(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setLoading(true)
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      })
      if (error) setError(error.message)
      else {
        setMessage(
          'If an account exists for that email, a password-reset link is on its way.',
        )
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleEmailAuth(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setLoading(true)

    try {
      if (tab === 'signin') {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) setError(error.message)
      } else {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) {
          setError(error.message)
        } else {
          setMessage('Check your email for a confirmation link.')
        }
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleGoogleAuth() {
    setError(null)
    const { error } = await supabase.auth.signInWithOAuth({ provider: 'google' })
    if (error) {
      // The most common failure is server-side configuration, not user error.
      setError(
        /not enabled/i.test(error.message)
          ? 'Google sign-in isn’t configured on this server yet — an admin ' +
            'needs to enable the Google provider in Supabase (Authentication ' +
            '→ Providers). Use email + password in the meantime.'
          : error.message,
      )
    }
  }

  // Successful sign-in updates the auth store (onAuthStateChange) — leave
  // the login page the moment a session exists. Without this, signing in
  // "worked" but the user stayed here until a manual refresh.
  if (!authLoading && isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-gray-50 px-4">
      {/* Signed-out users can still pick the site language (device-only;
          it syncs to the account after sign-in). */}
      <div className="absolute top-4 end-4">
        <UiLanguageSwitcher />
      </div>
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-900">
          Polyglot SRS
        </h1>
        {INVITE_ONLY && !resetMode && !trialMode && (
          <p className="text-sm text-gray-500 mb-4">{t('login.privateBeta')}</p>
        )}

        {/* Tabs — hidden entirely in invite-only beta (accounts are
            created by the admin; Supabase-side signup is disabled too) */}
        {!resetMode && !trialMode && !INVITE_ONLY && (
        <div className="flex rounded-lg overflow-hidden border border-gray-200 mb-6">
          <button
            type="button"
            onClick={() => { setTab('signin'); setError(null); setMessage(null) }}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              tab === 'signin'
                ? 'bg-lang text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
            style={{ minHeight: '44px' }}
          >
            {t('login.signIn')}
          </button>
          <button
            type="button"
            onClick={() => { setTab('signup'); setError(null); setMessage(null) }}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              tab === 'signup'
                ? 'bg-lang text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
            style={{ minHeight: '44px' }}
          >
            {t('login.signUp')}
          </button>
        </div>
        )}

        {resetMode && (
          <p className="text-sm text-gray-600 mb-4">{t('login.resetIntro')}</p>
        )}

        {trialMode && (
          <p className="text-sm text-gray-600 mb-4">
            Ask for trial access — if it’s approved you’ll get an email with
            a temporary password to sign in with.
          </p>
        )}

        {/* Email/Password form */}
        <form
          onSubmit={
            resetMode
              ? handleResetRequest
              : trialMode
                ? handleTrialRequest
                : handleEmailAuth
          }
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="email">
              {t('login.email')}
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-lang focus:border-transparent"
              style={{ minHeight: '44px' }}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>

          {trialMode && (
            <>
              <div>
                <label
                  className="block text-sm font-medium text-gray-700 mb-1"
                  htmlFor="trial-name"
                >
                  Name (optional)
                </label>
                <input
                  id="trial-name"
                  type="text"
                  value={trialName}
                  onChange={(e) => setTrialName(e.target.value)}
                  maxLength={100}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-lang focus:border-transparent"
                  style={{ minHeight: '44px' }}
                  autoComplete="name"
                />
              </div>
              <div>
                <label
                  className="block text-sm font-medium text-gray-700 mb-1"
                  htmlFor="trial-note"
                >
                  What would you like to learn? (optional)
                </label>
                <textarea
                  id="trial-note"
                  value={trialNote}
                  onChange={(e) => setTrialNote(e.target.value)}
                  maxLength={500}
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-lang focus:border-transparent"
                />
              </div>
            </>
          )}

          {!resetMode && !trialMode && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
              {t('login.password')}
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-lang focus:border-transparent"
              style={{ minHeight: '44px' }}
              placeholder={tab === 'signup' ? t('login.passwordPlaceholderNew') : '••••••••'}
              autoComplete={tab === 'signin' ? 'current-password' : 'new-password'}
            />
          </div>
          )}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          {message && (
            <p className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2">{message}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-lang hover:bg-lang-dark disabled:opacity-60 text-lang-on font-medium rounded-lg px-4 py-2.5 text-sm transition-colors"
            style={{ minHeight: '44px' }}
          >
            {loading
              ? t('login.loading')
              : resetMode
                ? t('login.sendResetLink')
                : trialMode
                  ? 'Request trial access'
                  : tab === 'signin'
                    ? t('login.signIn')
                    : t('login.createAccount')}
          </button>
        </form>

        <div className="mt-3 text-center space-y-1">
          {resetMode || trialMode ? (
            <button
              type="button"
              onClick={() => {
                setResetMode(false)
                setTrialMode(false)
                setError(null)
                setMessage(null)
              }}
              className="text-sm text-lang hover:underline"
            >
              {t('login.backToSignIn')}
            </button>
          ) : (
            tab === 'signin' && (
              <>
                <button
                  type="button"
                  onClick={() => { setResetMode(true); setError(null); setMessage(null) }}
                  className="block w-full text-sm text-lang hover:underline"
                >
                  {t('login.forgotPassword')}
                </button>
                <button
                  type="button"
                  onClick={() => { setTrialMode(true); setError(null); setMessage(null) }}
                  className="block w-full text-sm text-lang hover:underline"
                >
                  No account? Request trial access
                </button>
              </>
            )
          )}
        </div>

        {!resetMode && !trialMode && !INVITE_ONLY && (
        <>
        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-xs text-gray-500">
            <span className="bg-white px-2">{t('login.orContinueWith')}</span>
          </div>
        </div>

        {/* Google OAuth */}
        <button
          type="button"
          onClick={handleGoogleAuth}
          className="w-full flex items-center justify-center gap-2 border border-gray-300 rounded-lg px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          style={{ minHeight: '44px' }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
            <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
          </svg>
          {t('login.googleSignIn')}
        </button>
        </>
        )}

        <p className="mt-6 text-center text-xs text-gray-500">
          {t('login.agreePrefix')}{' '}
          <a href="/terms" className="text-lang hover:underline">
            {t('login.terms')}
          </a>
          .
        </p>
      </div>
    </div>
  )
}
