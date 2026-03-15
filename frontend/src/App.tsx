import { useEffect } from 'react'
import {
  createBrowserRouter,
  RouterProvider,
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { supabase } from './lib/supabase'
import { useAuthStore } from './stores/authStore'
import LoginPage from './features/auth/LoginPage'
import ProtectedRoute from './components/ProtectedRoute'

const queryClient = new QueryClient()

// Placeholder pages — will be replaced in 04-04 and 04-05
function DashboardPage() {
  return <div>Dashboard</div>
}

function ReviewSessionPage() {
  return <div>Review Session</div>
}

function LearnPage() {
  return <div>Learn</div>
}

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/review', element: <ReviewSessionPage /> },
      { path: '/learn', element: <LearnPage /> },
    ],
  },
])

function AppInner() {
  const setSession = useAuthStore((s) => s.setSession)
  const setLoading = useAuthStore((s) => s.setLoading)

  useEffect(() => {
    // Initialise session from storage then clear loading
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
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
  }, [setSession, setLoading])

  return <RouterProvider router={router} />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
