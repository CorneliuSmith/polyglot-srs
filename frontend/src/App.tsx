import { useEffect } from 'react'
import {
  createBrowserRouter,
  RouterProvider,
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { supabase } from './lib/supabase'
import { useAuthStore } from './stores/authStore'
import LoginPage from './features/auth/LoginPage'
import ResetPasswordPage from './features/auth/ResetPasswordPage'
import DashboardPage from './features/dashboard/DashboardPage'
import ReviewSessionPage from './features/review/ReviewSessionPage'
import LearnPage from './features/review/LearnPage'
import TutorPage from './features/tutor/TutorPage'
import NotesPage from './features/notes/NotesPage'
import OnboardingPage from './features/onboarding/OnboardingPage'
import SettingsPage from './features/settings/SettingsPage'
import GrammarPathPage from './features/curriculum/GrammarPathPage'
import ContributorPage from './features/contribute/ContributorPage'
import TermsPage from './features/legal/TermsPage'
import ErrorScreen from './components/ErrorScreen'
import SearchPage from './features/search/SearchPage'
import DecksPage from './features/decks/DecksPage'
import DeckDetailPage from './features/decks/DeckDetailPage'
import ProtectedRoute from './components/ProtectedRoute'
import ThemeApplier from './components/ThemeApplier'
import LanguageThemeApplier from './components/LanguageThemeApplier'

// Cached data renders INSTANTLY on navigation; anything stale refreshes in
// the background instead of blanking the page behind a spinner. Writes
// (finishing a review, learning a batch, deck changes, resets) invalidate
// their queries explicitly, so nothing user-visible waits on the staleTime.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 30 * 60_000,
      refetchOnWindowFocus: false,
    },
  },
})

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
    errorElement: <ErrorScreen />,
  },
  {
    // Public: the recovery email link lands here with a fresh session.
    path: '/reset-password',
    element: <ResetPasswordPage />,
    errorElement: <ErrorScreen />,
  },
  {
    // Public: readable before signing up.
    path: '/terms',
    element: <TermsPage />,
    errorElement: <ErrorScreen />,
  },
  {
    element: <ProtectedRoute />,
    errorElement: <ErrorScreen />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/onboarding', element: <OnboardingPage /> },
      { path: '/settings', element: <SettingsPage /> },
      { path: '/grammar', element: <GrammarPathPage /> },
      { path: '/review', element: <ReviewSessionPage /> },
      { path: '/cram', element: <ReviewSessionPage cram /> },
      { path: '/search', element: <SearchPage /> },
      { path: '/decks', element: <DecksPage /> },
      { path: '/decks/:deckId', element: <DeckDetailPage /> },
      { path: '/learn', element: <LearnPage /> },
      { path: '/tutor', element: <TutorPage /> },
      { path: '/notes', element: <NotesPage /> },
      { path: '/contribute', element: <ContributorPage /> },
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

  return (
    <>
      <ThemeApplier />
      <LanguageThemeApplier />
      <RouterProvider router={router} />
    </>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
