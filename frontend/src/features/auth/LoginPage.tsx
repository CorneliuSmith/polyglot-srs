import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { supabase } from '../../lib/supabase'
import { useAuthStore } from '../../stores/authStore'

type Tab = 'signin' | 'signup'

export default function LoginPage() {
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
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-6 text-gray-900">
          Polyglot SRS
        </h1>

        {/* Tabs */}
        {!resetMode && (
        <div className="flex rounded-lg overflow-hidden border border-gray-200 mb-6">
          <button
            type="button"
            onClick={() => { setTab('signin'); setError(null); setMessage(null) }}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              tab === 'signin'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
            style={{ minHeight: '44px' }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setTab('signup'); setError(null); setMessage(null) }}
            className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
              tab === 'signup'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
            style={{ minHeight: '44px' }}
          >
            Sign Up
          </button>
        </div>
        )}

        {resetMode && (
          <p className="text-sm text-gray-600 mb-4">
            Enter your account email and we’ll send you a link to choose a new
            password.
          </p>
        )}

        {/* Email/Password form */}
        <form
          onSubmit={resetMode ? handleResetRequest : handleEmailAuth}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              style={{ minHeight: '44px' }}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>

          {!resetMode && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              style={{ minHeight: '44px' }}
              placeholder={tab === 'signup' ? 'At least 6 characters' : '••••••••'}
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
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium rounded-lg px-4 py-2.5 text-sm transition-colors"
            style={{ minHeight: '44px' }}
          >
            {loading
              ? 'Loading…'
              : resetMode
                ? 'Send reset link'
                : tab === 'signin'
                  ? 'Sign In'
                  : 'Create Account'}
          </button>
        </form>

        <div className="mt-3 text-center">
          {resetMode ? (
            <button
              type="button"
              onClick={() => { setResetMode(false); setError(null); setMessage(null) }}
              className="text-sm text-indigo-600 hover:underline"
            >
              ← Back to sign in
            </button>
          ) : (
            tab === 'signin' && (
              <button
                type="button"
                onClick={() => { setResetMode(true); setError(null); setMessage(null) }}
                className="text-sm text-indigo-600 hover:underline"
              >
                Forgot password?
              </button>
            )
          )}
        </div>

        {!resetMode && (
        <>
        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-xs text-gray-400">
            <span className="bg-white px-2">or continue with</span>
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
          Sign in with Google
        </button>
        </>
        )}
      </div>
    </div>
  )
}
