import { lazy, Suspense, useEffect, type ComponentType } from 'react'
import {
  createBrowserRouter,
  RouterProvider,
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { supabase } from './lib/supabase'
import { useAuthStore } from './stores/authStore'
import ErrorScreen from './components/ErrorScreen'
import ProtectedRoute from './components/ProtectedRoute'
import ThemeApplier from './components/ThemeApplier'
import LanguageThemeApplier from './components/LanguageThemeApplier'
import UiSkinApplier from './components/UiSkinApplier'

// Route code-splitting (mobile perf): each page becomes its own chunk that
// loads on demand, so landing on the Dashboard no longer downloads the
// Tutor, Reader, Gym, Contributor, and on-screen-keyboard code up front.
// This is the single biggest first-load win on a cellular connection —
// the eager bundle was ~940 kB, most of it never touched on the Dashboard.
//
// lazyWithRetry hardens that split for flaky mobile networks and mid-rollout
// deploys: a chunk that fails to load is retried a couple of times, and only
// a persistent failure (e.g. the hashed chunk no longer exists after a
// deploy) triggers a single hard reload to pick up the new asset manifest —
// far better than stranding the user on the route error screen. The reload
// is guarded in sessionStorage so it can never loop.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function lazyWithRetry<T extends ComponentType<any>>(
  factory: () => Promise<{ default: T }>,
) {
  return lazy(async () => {
    try {
      return await factory()
    } catch (err) {
      try {
        // One quick retry covers a transient network blip.
        return await factory()
      } catch {
        if (!sessionStorage.getItem('polyglot-chunk-reloaded')) {
          sessionStorage.setItem('polyglot-chunk-reloaded', '1')
          window.location.reload()
          // Return a never-resolving module so Suspense holds the fallback
          // through the reload instead of flashing the error boundary.
          return new Promise<{ default: T }>(() => {})
        }
        throw err
      }
    }
  })
}

const LoginPage = lazyWithRetry(() => import('./features/auth/LoginPage'))
const ResetPasswordPage = lazyWithRetry(() => import('./features/auth/ResetPasswordPage'))
const DashboardPage = lazyWithRetry(() => import('./features/dashboard/DashboardPage'))
const PracticePage = lazyWithRetry(() => import('./features/dashboard/PracticePage'))
const ProgressPage = lazyWithRetry(() => import('./features/dashboard/ProgressPage'))
const MorePage = lazyWithRetry(() => import('./features/dashboard/MorePage'))
const ReviewSessionPage = lazyWithRetry(() => import('./features/review/ReviewSessionPage'))
const LearnPage = lazyWithRetry(() => import('./features/review/LearnPage'))
const TutorPage = lazyWithRetry(() => import('./features/tutor/TutorPage'))
const ReaderPage = lazyWithRetry(() => import('./features/reader/ReaderPage'))
const SpeakPage = lazyWithRetry(() => import('./features/speak/SpeakPage'))
const LettersPage = lazyWithRetry(() => import('./features/letters/LettersPage'))
const RecommendationsPage = lazyWithRetry(() => import('./features/recommendations/RecommendationsPage'))
const LanguageAboutPage = lazyWithRetry(() => import('./features/about/LanguageAboutPage'))
const GymPage = lazyWithRetry(() => import('./features/gym/GymPage'))
const NotesPage = lazyWithRetry(() => import('./features/notes/NotesPage'))
const FeedbackPage = lazyWithRetry(() => import('./features/feedback/FeedbackPage'))
const OnboardingPage = lazyWithRetry(() => import('./features/onboarding/OnboardingPage'))
const WelcomePage = lazyWithRetry(() => import('./features/onboarding/WelcomePage'))
const SettingsPage = lazyWithRetry(() => import('./features/settings/SettingsPage'))
const GrammarPathPage = lazyWithRetry(() => import('./features/curriculum/GrammarPathPage'))
const ContributorPage = lazyWithRetry(() => import('./features/contribute/ContributorPage'))
const TermsPage = lazyWithRetry(() => import('./features/legal/TermsPage'))
const PrivacyPage = lazyWithRetry(() => import('./features/legal/PrivacyPage'))
const SearchPage = lazyWithRetry(() => import('./features/search/SearchPage'))
const DecksPage = lazyWithRetry(() => import('./features/decks/DecksPage'))
const DeckDetailPage = lazyWithRetry(() => import('./features/decks/DeckDetailPage'))

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
    // Public: app-store submissions require a dedicated privacy URL.
    path: '/privacy',
    element: <PrivacyPage />,
    errorElement: <ErrorScreen />,
  },
  {
    element: <ProtectedRoute />,
    errorElement: <ErrorScreen />,
    children: [
      { path: '/', element: <DashboardPage /> },
      // The dashboard's three siblings — see components/BottomNav.
      { path: '/practice', element: <PracticePage /> },
      { path: '/progress', element: <ProgressPage /> },
      { path: '/more', element: <MorePage /> },
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
      { path: '/speak', element: <SpeakPage /> },
      { path: '/letters', element: <LettersPage /> },
      { path: '/recommendations', element: <RecommendationsPage /> },
      // Staff triage. The panel already existed inside Settings → Admin;
      // this gives it an address the dashboard alert can link to.
      { path: '/feedback', element: <FeedbackPage /> },
      { path: '/about', element: <LanguageAboutPage /> },
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
      <UiSkinApplier />
      <Suspense fallback={<RouteFallback />}>
        <RouterProvider router={router} />
      </Suspense>
    </>
  )
}

/** Shown for the brief moment a lazily-loaded route chunk is fetching. */
function RouteFallback() {
  const { t } = useTranslation()
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div
        className="h-8 w-8 rounded-full border-2 border-gray-200 border-t-lang animate-spin"
        role="status"
        aria-label={t('shared.loading')}
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
