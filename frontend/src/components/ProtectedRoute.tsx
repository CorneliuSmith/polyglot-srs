import { useEffect } from 'react'
import { Navigate, Outlet, useNavigate } from 'react-router-dom'
import BottomNav from './BottomNav'
import { initNative } from '../lib/native'
import { useAuthStore } from '../stores/authStore'
import StaffBar from './StaffBar'

export default function ProtectedRoute() {
  // Native shell wiring (status bar, Android Back, deep links, splash).
  // A no-op in a browser, so the same bundle serves web, PWA and both
  // native builds. Lives here because this is the app's only shared
  // authenticated shell — the same reason StaffBar and BottomNav do.
  const navigate = useNavigate()
  useEffect(() => {
    void initNative((to) => navigate(to))
  }, [navigate])

  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)()
  const loading = useAuthStore((s) => s.loading)
  // Trial accounts are minted with a TEMPORARY password and this metadata
  // flag; nothing in the app is reachable until they choose their own.
  // Cleared by ResetPasswordPage in the same updateUser call that sets the
  // new password.
  const mustChangePassword = useAuthStore(
    (s) => s.session?.user?.user_metadata?.must_change_password === true,
  )

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-lang border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading…</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (mustChangePassword) {
    return <Navigate to="/reset-password" replace />
  }

  // Staff chrome (Review Mode + the admin "view as" switcher) above every
  // authenticated page — this is the app's only shared authenticated shell,
  // so it's the single place a global bar can live. It renders nothing at
  // all for a plain learner.
  // BottomNav rides here for the same reason: the only shared shell. It
  // hides itself on desktop, where the header's inline nav already covers
  // the same destinations without spending vertical space.
  return (
    <>
      <StaffBar />
      <Outlet />
      <BottomNav />
    </>
  )
}
