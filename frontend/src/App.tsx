import { useEffect } from 'react'
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
  Outlet,
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { supabase } from './lib/supabase'
import { useAuthStore } from './stores/authStore'

const queryClient = new QueryClient()

// Placeholder pages
function LoginPage() {
  return <div>Login</div>
}

function DashboardPage() {
  return <div>Dashboard</div>
}

function ReviewSessionPage() {
  return <div>Review Session</div>
}

function LearnPage() {
  return <div>Learn</div>
}

// Protected route wrapper
function ProtectedLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <ProtectedLayout />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/review', element: <ReviewSessionPage /> },
      { path: '/learn', element: <LearnPage /> },
    ],
  },
])

function AppInner() {
  const setSession = useAuthStore((s) => s.setSession)

  useEffect(() => {
    // Initialise session from storage
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
    })

    // Track auth state changes (login, logout, token refresh)
    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session)
      },
    )

    return () => {
      listener.subscription.unsubscribe()
    }
  }, [setSession])

  return <RouterProvider router={router} />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
