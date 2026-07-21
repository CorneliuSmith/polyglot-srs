import { lazy, Suspense, useEffect } from 'react'
import {
  createBrowserRouter,
  RouterProvider,
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { supabase } from './lib/supabase'
import { useAuthStore } from './stores/authStore'
import ErrorScreen from './components/ErrorScreen'
import ProtectedRoute from './components/ProtectedRoute'
import ThemeApplier from './components/ThemeApplier'
import LanguageThemeApplier from './components/LanguageThemeApplier'

// Route code-splitting (mobile perf): each page becomes its own chunk that
// loads on demand, so landing on the Dashboard no longer downloads the
// Tutor, Reader, Gym, Contributor, and on-screen-keyboard code up front.
// This is the single biggest first-load win on a cellular connection —
// the eager bundle was ~940 kB, most of it never touched on the Dashboard.
const LoginPage = lazy(() => import('./features/auth/LoginPage'))
const ResetPasswordPage = lazy(() => import('./features/auth/ResetPasswordPage'))
const DashboardPage = lazy(() => import('./features/dashboard/DashboardPage'))
const ReviewSessionPage = lazy(() => import('./features/review/ReviewSessionPage'))
const LearnPage = lazy(() => import('./features/review/LearnPage'))
const TutorPage = lazy(() => import('./features/tutor/TutorPage'))
const ReaderPage = lazy(() => import('./features/reader/ReaderPage'))
const LettersPage = lazy(() => import('./features/letters/LettersPage'))
const GymPage = lazy(() => import('./features/gym/GymPage'))
const NotesPage = lazy(() => import('./features/notes/NotesPage'))
const OnboardingPage = lazy(() => import('./features/onboarding/OnboardingPage'))
const WelcomePage = lazy(() => import('./features/onboarding/WelcomePage'))
const SettingsPage = lazy(() => import('./features/settings/SettingsPage'))
const GrammarPathPage = lazy(() => import('./features/curriculum/GrammarPathPage'))
const ContributorPage = lazy(() => import('./features/contribute/ContributorPage'))
const TermsPage = lazy(() => import('./features/legal/TermsPage'))
const SearchPage = lazy(() => import('./features/search/SearchPage'))
const DecksPage = lazy(() => import('./features/decks/DecksPage'))
const DeckDetailPage = lazy(() => import('./features/decks/DeckDetailPage'))

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
      { path: '/welcome', element: <WelcomePage /> },
      { path: '/settings', element: <SettingsPage /> },
      { path: '/account', element: <SettingsPage /> },
      { path: '/grammar', element: <GrammarPathPage /> },
      { path: '/review', element: <ReviewSessionPage /> },
      { path: '/cram', element: <ReviewSessionPage cram /> },
      { path: '/search', element: <SearchPage /> },
      { path: '/decks', element: <DecksPage /> },
      { path: '/decks/:deckId', element: <DeckDetailPage /> },
      { path: '/learn', element: <LearnPage /> },
      { path: '/tutor', element: <TutorPage /> },
      { path: '/read', element: <ReaderPage /> },
      { path: '/letters', element: <LettersPage /> },
      { path: '/gym', element: <GymPage /> },
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
      <Suspense fallback={<RouteFallback />}>
        <RouterProvider router={router} />
      </Suspense>
    </>
  )
}

/** Shown for the brief moment a lazily-loaded route chunk is fetching. */
function RouteFallback() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div
        className="h-8 w-8 rounded-full border-2 border-gray-200 border-t-lang animate-spin"
        role="status"
        aria-label="Loading"
      />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
