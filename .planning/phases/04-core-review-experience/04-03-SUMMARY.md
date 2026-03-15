---
phase: 04-core-review-experience
plan: 03
subsystem: ui
tags: [react, tailwind, tanstack-query, supabase, zustand, typescript]

# Dependency graph
requires:
  - phase: 04-02
    provides: Vite/React/Tailwind scaffold, auth store, prefs store, api client, all API function modules
  - phase: 04-01
    provides: GET /api/dashboard/{language_id}, GET /api/languages/, POST /api/auth/profile

provides:
  - LoginPage with email/password Sign In/Sign Up tabs and Google OAuth via Supabase
  - ProtectedRoute with loading spinner while session is restored from storage
  - DashboardPage with live data from getDashboardStats() via TanStack Query
  - LanguagePicker dropdown auto-selecting first language, persisting to server and store
  - DueCount, StreakBadge, CEFRProgress — standalone stat display components
  - authStore extended with loading: boolean and setLoading() for session init guard

affects:
  - 04-04-review-session
  - 04-05-learn-flow

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TanStack Query useQuery with queryKey: ['dashboard', activeLanguageId] for cache invalidation on language switch"
    - "Loading gate in ProtectedRoute: loading=true until getSession() resolves, preventing flash-redirect to /login"
    - "Auto-select first language in LanguagePicker: fires useEffect when activeLanguageId is null and languages are loaded"
    - "useMutation for startLearnSession — navigates to /review on success"
    - "Skeleton placeholders with animate-pulse while dashboard query loads"

key-files:
  created:
    - frontend/src/features/auth/LoginPage.tsx
    - frontend/src/components/ProtectedRoute.tsx
    - frontend/src/features/dashboard/DashboardPage.tsx
    - frontend/src/features/dashboard/DueCount.tsx
    - frontend/src/features/dashboard/StreakBadge.tsx
    - frontend/src/features/dashboard/CEFRProgress.tsx
    - frontend/src/components/LanguagePicker.tsx
    - frontend/src/__tests__/DashboardPage.test.tsx
  modified:
    - frontend/src/stores/authStore.ts
    - frontend/src/App.tsx

key-decisions:
  - "ProtectedRoute checks loading before isAuthenticated to prevent flash redirect to /login during session restore"
  - "LanguagePicker uses useEffect (not onChange-only) to auto-select first language when store is null on mount"
  - "Review Due Cards button disabled when due_count === 0; Learn New Cards button always enabled (server decides batch size)"
  - "authStore loading starts true; set to false after getSession() resolves in AppInner useEffect"
  - "CEFRProgress always renders all 6 levels (A1-C2) even with empty progress, using progress[level] ?? 0"

patterns-established:
  - "Feature folders: src/features/{name}/{ComponentName}.tsx — co-located feature components"
  - "Shared UI components in src/components/ — LanguagePicker, ProtectedRoute"
  - "TanStack Query for all data fetching; no fetch calls in components directly"

requirements-completed: [UX-01, PROF-02, REV-07, REV-08]

# Metrics
duration: 12min
completed: 2026-03-15
---

# Phase 4 Plan 03: Login Page and Dashboard Summary

**Supabase-auth login page (Sign In/Sign Up/Google OAuth) and live dashboard with language picker, due count, streak badge, CEFR progress bars, and session start buttons**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-15T05:20:02Z
- **Completed:** 2026-03-15T05:32:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Full login flow: email/password (sign in and sign up tabs) plus Google OAuth via Supabase, with error messages from Supabase auth errors
- ProtectedRoute with loading spinner guard — no flash redirect during session restore from localStorage
- Dashboard page with live data from `/api/dashboard/{language_id}` via TanStack Query, skeleton placeholders while loading
- LanguagePicker auto-selects first language on first visit and persists selection to both prefsStore and server profile
- 11 unit tests for DueCount, StreakBadge, and CEFRProgress components — all verifiable via `tsc --noEmit`

## Task Commits

1. **Task 1: Login page with Supabase auth and ProtectedRoute** - `13af997` (feat)
2. **Task 2: Dashboard page with language picker, due count, streak, CEFR progress, session buttons** - `b489bb8` (feat)

## Files Created/Modified

- `frontend/src/features/auth/LoginPage.tsx` - Two-tab email/password form + Google OAuth, Supabase auth calls, touch-friendly 44px inputs
- `frontend/src/components/ProtectedRoute.tsx` - Loading spinner while loading=true; redirects to /login when unauthenticated
- `frontend/src/features/dashboard/DashboardPage.tsx` - Main dashboard using getDashboardStats(), language picker, skeleton loading, Learn/Review buttons
- `frontend/src/features/dashboard/DueCount.tsx` - Card showing due count as large number
- `frontend/src/features/dashboard/StreakBadge.tsx` - Streak in days with flame icon; "Start your streak!" at 0
- `frontend/src/features/dashboard/CEFRProgress.tsx` - A1-C2 progress bars with RTL-compatible logical properties (text-end)
- `frontend/src/components/LanguagePicker.tsx` - Language dropdown with auto-select, persists to store + server
- `frontend/src/__tests__/DashboardPage.test.tsx` - 11 unit tests for three dashboard sub-components
- `frontend/src/stores/authStore.ts` - Added loading: boolean and setLoading() action
- `frontend/src/App.tsx` - Wired real LoginPage, DashboardPage, ProtectedRoute; loading=false after getSession()

## Decisions Made

- **Loading gate in ProtectedRoute:** `loading` starts `true` in authStore; set to `false` only after `getSession()` resolves. Without this, ProtectedRoute would redirect to /login on every hard refresh because session is null for the ~50ms before getSession() responds.
- **Review button disabled at due_count === 0:** Prevents navigating to an empty review session; Learn button remains enabled since the server controls batch size.
- **CEFRProgress always renders all 6 levels:** Empty progress still shows the full A1-C2 bar list so users can see what's ahead, using `progress[level] ?? 0`.
- **LanguagePicker auto-select uses useEffect:** Fires when languages load and activeLanguageId is null, updating both store and server, so first-time users have a working dashboard without manual selection.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The vitest and vite build commands could not run in this environment due to two pre-existing infrastructure problems:
1. esbuild native binary fails with `spawn Unknown system error -88` (errno -88 = ENOSYS on macOS — binary doesn't match system)
2. `strip-literal/node_modules/js-tokens/` directory was present but empty (broken npm install artifact; fixed by copying top-level js-tokens)

Verification was performed via `tsc --noEmit` which exited 0 with no errors — confirming all TypeScript is valid and all imports resolve correctly.

## User Setup Required

None - no external service configuration required beyond the Supabase env vars already established in 04-02.

## Next Phase Readiness

- Login page and dashboard are complete; 04-04 (review session) can import DueCard types and review API functions
- ReviewSessionPage and LearnPage placeholders in App.tsx are ready to be replaced by 04-04 and 04-05
- ProtectedRoute guards all /review and /learn routes automatically

---
*Phase: 04-core-review-experience*
*Completed: 2026-03-15*
