import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import ViewAsBar from './ViewAsBar'

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)()
  const loading = useAuthStore((s) => s.loading)

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

  // The admin "view as" switcher is the one piece of chrome above every
  // authenticated page — this is the app's only shared authenticated shell,
  // so it's the single place a global bar can live. It renders nothing at
  // all for non-admins.
  return (
    <>
      <ViewAsBar />
      <Outlet />
    </>
  )
}
