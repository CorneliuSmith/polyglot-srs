---
phase: 04-core-review-experience
plan: "02"
subsystem: ui
tags: [react, vite, tailwind, zustand, supabase, axios, typescript, react-router, react-query]

# Dependency graph
requires:
  - phase: 04-01
    provides: Backend API contracts for review, dashboard, profile, and language endpoints

provides:
  - Vite + React + Tailwind v4 frontend project scaffold at frontend/
  - Supabase client singleton (frontend/src/lib/supabase.ts)
  - Axios API client with Bearer JWT interceptor and 401 auto-refresh (frontend/src/api/client.ts)
  - TypeScript interfaces for all backend API contracts (frontend/src/api/types.ts)
  - Typed API function modules (review.ts, dashboard.ts, profile.ts)
  - Zustand auth store tracking Supabase session (frontend/src/stores/authStore.ts)
  - Zustand prefs store persisting activeLanguageId to localStorage (frontend/src/stores/prefsStore.ts)
  - App shell with react-router routes (/login, /, /review, /learn) and protected layout
  - Vitest test configuration with jsdom environment and @testing-library/jest-dom setup

affects:
  - 04-03-PLAN.md (dashboard and login page consume stores, API client, and router)
  - 04-04-PLAN.md (review session uses getDueCards, validateAnswer, submitReview, useAuthStore)
  - 04-05-PLAN.md (RTL and keyboard components mount inside existing route structure)

# Tech tracking
tech-stack:
  added:
    - react@19
    - react-dom@19
    - react-router-dom@7
    - "@tanstack/react-query@5"
    - zustand@5 (with persist middleware)
    - "@supabase/supabase-js@2"
    - axios@1
    - tailwindcss@4 via @tailwindcss/vite (no postcss config)
    - vite@6 with @vitejs/plugin-react
    - vitest@3 with jsdom + @testing-library/react
    - react-simple-keyboard + simple-keyboard-layouts
    - clsx
  patterns:
    - Supabase session sourced from store — never fetched inline in components
    - axios interceptor for auth: request adds Bearer, response retries on 401
    - Zustand persist middleware for cross-session state (active language)
    - createBrowserRouter + RouterProvider (data router API, not BrowserRouter)
    - ProtectedLayout as a layout route child redirecting unauthenticated users

key-files:
  created:
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/vitest.config.ts
    - frontend/tsconfig.json
    - frontend/tsconfig.app.json
    - frontend/tsconfig.node.json
    - frontend/index.html
    - frontend/src/index.css
    - frontend/src/vite-env.d.ts
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/test/setup.ts
    - frontend/src/lib/supabase.ts
    - frontend/src/api/types.ts
    - frontend/src/api/client.ts
    - frontend/src/api/review.ts
    - frontend/src/api/dashboard.ts
    - frontend/src/api/profile.ts
    - frontend/src/stores/authStore.ts
    - frontend/src/stores/prefsStore.ts
  modified: []

key-decisions:
  - "QueryClientProvider wraps AppInner inside App.tsx rather than main.tsx — App owns its own providers for encapsulation"
  - "onAuthStateChange listener and initial getSession() both live in App useEffect — single source of truth for session"
  - "axios retry uses error.config cast to unknown then Record — avoids TypeScript index signature mismatch on InternalAxiosRequestConfig"
  - "Zustand persist key is 'polyglot-prefs' — stable across app renames"
  - "npm install --ignore-scripts used due to esbuild spawn restriction in CI sandbox (ENOSYS -88); TypeScript type-check used as verification in place of vite build"

patterns-established:
  - "API functions are thin wrappers: one file per domain (review, dashboard, profile), typed with backend contract interfaces from types.ts"
  - "Stores are minimal: session + setter + derived getter (isAuthenticated). No business logic in stores."
  - "ProtectedLayout pattern: layout route element checks isAuthenticated(), renders Outlet or Navigate redirect"

requirements-completed: [PROF-02]

# Metrics
duration: 12min
completed: 2026-03-15
---

# Phase 4 Plan 02: Frontend Scaffold Summary

**Vite + React 19 + Tailwind v4 frontend with Supabase auth session tracking, axios API client with Bearer JWT interceptor and 401 auto-refresh, Zustand stores (auth + persisted language prefs), typed API contracts for all backend endpoints, and react-router data router with protected layout.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-15T05:09:18Z
- **Completed:** 2026-03-15T05:21:00Z
- **Tasks:** 2
- **Files modified:** 20

## Accomplishments

- Vite 6 + React 19 + Tailwind v4 project scaffold with correct tsconfig references structure and jsdom Vitest config
- Supabase auth fully integrated: session initialised on mount, tracked via onAuthStateChange, stored in Zustand without token duplication
- Axios API client automatically attaches Bearer JWT from Supabase session and retries once on 401 after refreshing the session
- Zustand prefs store persists active language selection to localStorage across page reloads
- TypeScript passes with zero errors across all 20 files (verified via `tsc --noEmit`)

## Task Commits

1. **Task 1: Scaffold Vite + React + Tailwind v4 project** - `8f326e3` (feat)
2. **Task 2: Supabase client, API client, types, stores, App shell** - `9db3de7` (feat)

## Files Created/Modified

- `frontend/package.json` — All production and dev dependencies, npm scripts
- `frontend/vite.config.ts` — @tailwindcss/vite plugin, /api proxy to localhost:8000
- `frontend/vitest.config.ts` — jsdom environment, ./src/test/setup.ts
- `frontend/tsconfig.{json,app.json,node.json}` — Vite React-TS tsconfig reference structure
- `frontend/index.html` — Noto Naskh Arabic font preload for Arabic card support
- `frontend/src/index.css` — `@import "tailwindcss"` + Google Fonts import
- `frontend/src/lib/supabase.ts` — Supabase createClient using env vars
- `frontend/src/api/types.ts` — Language, DueCard, Validate/Submit/Learn/Dashboard/Profile interfaces
- `frontend/src/api/client.ts` — Axios instance with auth interceptor and 401 retry
- `frontend/src/api/review.ts` — getDueCards, validateAnswer, submitReview, startLearnSession
- `frontend/src/api/dashboard.ts` — getDashboardStats
- `frontend/src/api/profile.ts` — getProfile, updateProfile, getLanguages
- `frontend/src/stores/authStore.ts` — Zustand store: session, setSession, isAuthenticated()
- `frontend/src/stores/prefsStore.ts` — Zustand persist store: activeLanguageId in 'polyglot-prefs'
- `frontend/src/App.tsx` — Auth init useEffect, onAuthStateChange, createBrowserRouter, ProtectedLayout
- `frontend/src/main.tsx` — StrictMode + App render

## Decisions Made

- **QueryClientProvider inside App.tsx**: App.tsx owns its providers for encapsulation — main.tsx is minimal.
- **axios cast strategy**: Used `error.config as unknown as Record<string, unknown>` to set `_retry` flag, avoiding TypeScript's index signature restriction on `InternalAxiosRequestConfig`.
- **npm --ignore-scripts**: esbuild's post-install script fails with ENOSYS -88 in sandboxed execution. TypeScript type-check (`tsc --noEmit`) used as build verification instead — all types resolve correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript type cast for axios retry flag**
- **Found during:** Task 2 (API client implementation)
- **Issue:** Casting `error.config` directly to `Record<string, unknown>` caused TS2352 — InternalAxiosRequestConfig lacks string index signature
- **Fix:** Used double cast `as unknown as Record<string, unknown>` to set `_retry` flag safely
- **Files modified:** `frontend/src/api/client.ts`
- **Verification:** `tsc --noEmit` exits 0
- **Committed in:** 9db3de7 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 type bug)
**Impact on plan:** Minimal — cast approach is idiomatic TypeScript for this axios retry pattern.

## Issues Encountered

- esbuild post-install script fails with `ENOSYS -88` (spawn not supported in sandbox). Used `npm install --ignore-scripts` and substituted `tsc --noEmit` for `vite build` as verification. This is a CI sandbox constraint — running `npm install` and `npm run build` in a real dev environment will work normally.

## User Setup Required

Users will need `.env` (or `.env.local`) in `frontend/` with:

```
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
```

`VITE_API_BASE_URL` is optional — omitting it uses the Vite dev proxy (`/api` -> `localhost:8000`).

## Next Phase Readiness

- Frontend scaffold is complete and type-safe — 04-03 can immediately import stores and API functions
- `useAuthStore` and `usePrefsStore` are ready for the login page and dashboard language picker
- Route structure exists at `/login`, `/`, `/review`, `/learn` — placeholder divs only
- Vitest configured — 04-03 and 04-04 can add component tests without further setup

---
*Phase: 04-core-review-experience*
*Completed: 2026-03-15*
