# Phase 4: Core Review Experience - Research

**Researched:** 2026-03-14
**Domain:** React + Vite + Tailwind frontend, RTL/BiDi layout, virtual keyboards, SRS review session UX, Supabase Auth integration, FastAPI API client
**Confidence:** HIGH (stack verified against official docs and existing backend code)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REV-01 | Review session presents due cards in queue, sorted by next_review | Backend `GET /api/review/due?language_id=` already implemented; frontend needs queue state machine |
| REV-02 | Fill-in-the-blank drill mode with `{{answer}}` markers in sentences | `drill_sentences.sentence` contains `{{answer}}`; frontend renders with input injected at marker. **Note:** Vocabulary cards do NOT have `{{answer}}` markers -- they use "type-the-word" mode where the definition is the prompt and the user types the word. |
| REV-03 | Quality rating buttons (Again/Hard/Good/Easy) map to SM-2 quality scores | Backend `POST /api/review/submit` takes `answer_result` string; quality map locked (CORRECT=4, CORRECT_SLOPPY=3, WRONG_FORM=2, WRONG=1) |
| REV-04 | WRONG_FORM feedback shows grammar explanation (aspect, case, verb form table) | NLP `check_answer` returns `(AnswerResult, feedback_str)`; new `POST /api/review/validate-answer` endpoint needed |
| REV-05 | CORRECT_SLOPPY shows warning with nudge toward correct form | Same feedback string from NLP -- rendered as styled warning banner |
| REV-06 | Session summary shows accuracy %, time spent, cards reviewed | Computed client-side from session state; no new API needed |
| REV-07 | Learn mode adds batch of new items from subscribed lists | Needs new `POST /api/review/learn` endpoint; batch_size from user profile |
| REV-08 | Review mode drills only previously learned items via SRS queue | `GET /api/review/due` already filters by `next_review <= now()` -- covers this |
| UX-01 | Per-language dashboard: due count, streak, CEFR progress | Needs new `GET /api/dashboard/{language_id}` endpoint; streak computed from review_log |
| UX-02 | RTL layout for Arabic (`dir="rtl"`, Noto Naskh Arabic, mirrored layouts, large font) | Tailwind v4 logical properties + React `dir` attribute toggling |
| UX-03 | On-screen keyboards for Cyrillic and Arabic input | `react-simple-keyboard` + `simple-keyboard-layouts` (both Russian and Arabic layouts included) |
| UX-08 | Mobile-responsive, 44px+ touch targets | Tailwind `min-h-[44px]` utilities, responsive breakpoints |
| PROF-01 | User profile stores batch_size (default 5) | `POST /api/auth/profile` already implemented; frontend reads/writes batch_size |
| PROF-02 | User selects active language; all sessions scoped to it | `active_language_id` on user_profiles; profile endpoint already supports update |
</phase_requirements>

---

## Summary

Phase 4 is the critical path milestone: it delivers the first user-visible product. The backend is largely complete -- JWT auth, `GET /api/review/due`, `POST /api/review/submit`, and profile endpoints exist and are tested. The work in this phase is primarily frontend scaffolding (React + Vite + Tailwind v4) plus three new backend endpoints: NLP answer validation (`POST /api/review/validate-answer`), Learn session (`POST /api/review/learn`), and dashboard aggregation (`GET /api/dashboard/{language_id}`).

The most technically complex pieces are the RTL layout system for Arabic and the on-screen keyboards. Both have well-established solutions: Tailwind v4 logical properties handle layout mirroring without dual CSS files, and `react-simple-keyboard` with `simple-keyboard-layouts` covers both Cyrillic (Russian layout) and Arabic out of the box.

State management is straightforward: Zustand for thin global state (auth session, active language), TanStack Query for server state (due cards, profile, dashboard). The review session queue itself is local component state -- a flat array drained one card at a time with timing tracked per card.

**Primary recommendation:** Scaffold React + Vite + Tailwind v4 frontend, wire to existing FastAPI backend via a typed API client that attaches the Supabase JWT as Bearer token, implement the review session as a queue state machine, add the three missing backend endpoints, and handle RTL with `dir` attribute toggling plus Tailwind logical properties.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.x | UI framework | Existing project decision; Vite template default |
| vite | 6.x | Build tool / dev server | Sub-second HMR, ES module native, project already uses it |
| @vitejs/plugin-react | 4.x | React fast-refresh in Vite | Official Vite-React integration |
| tailwindcss | 4.x | Utility CSS | Project decision; v4 ships @tailwindcss/vite eliminating PostCSS config |
| @tailwindcss/vite | 4.x | Vite plugin for Tailwind v4 | Required for v4 -- replaces postcss-based setup |
| typescript | 5.x | Type safety | Standard for new React projects |

### State & Data Fetching
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | 5.x | Server state (API calls, caching) | All API calls -- due cards, profile, dashboard |
| zustand | 5.x | Global client state | Auth session token, active language selection |
| @supabase/supabase-js | 2.x | Supabase Auth client | Session management, JWT access token retrieval |

### Routing
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-router-dom | 7.x | Client-side routing | Pages: login, dashboard, review, session-summary |

### Keyboards & Fonts
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-simple-keyboard | 3.x | On-screen virtual keyboard | Cyrillic and Arabic input (UX-03) |
| simple-keyboard-layouts | latest | Pre-built keyboard layouts | Russian + Arabic layouts, no hand-rolling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| axios | 1.x | HTTP client | API calls with auth interceptor; easier than raw fetch for interceptors |
| clsx | 2.x | Conditional className utility | RTL/LTR class toggling, state-based styles |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TanStack Query | SWR | TanStack Query has better DevTools, mutation support, and is dominant in 2025 |
| Zustand | React Context | Context causes full re-renders on change; Zustand is selective. For an app with active language switching affecting entire pages, Zustand avoids cascading re-renders |
| axios | fetch | axios interceptors make attaching the JWT Bearer token to every request trivial; fetch requires wrapping manually |
| react-simple-keyboard | custom keyboard | Extreme complexity of Arabic keyboard (contextual glyph shaping, RTL input) makes custom build unjustifiable |
| Tailwind v4 logical properties | tailwindcss-rtl plugin | v4 ships logical property support natively; plugin adds unnecessary dependency |

**Installation:**
```bash
# Frontend scaffold (run in project root or /frontend subfolder)
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install tailwindcss @tailwindcss/vite
npm install @tanstack/react-query zustand @supabase/supabase-js
npm install react-router-dom axios clsx
npm install react-simple-keyboard simple-keyboard-layouts
npm install -D @types/react @types/react-dom
```

---

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── src/
│   ├── api/              # Typed API client functions (axios-based)
│   │   ├── client.ts     # axios instance with auth interceptor
│   │   ├── review.ts     # getDueCards, submitReview, validateAnswer, startLearn
│   │   ├── dashboard.ts  # getDashboard
│   │   └── profile.ts    # getProfile, updateProfile
│   ├── features/
│   │   ├── auth/         # Login page, auth store, Supabase hooks
│   │   ├── dashboard/    # DashboardPage, DueCount, StreakBadge, CEFRProgress
│   │   ├── review/       # ReviewSession, DrillCard, FeedbackPanel, RatingButtons
│   │   │   ├── ReviewSessionPage.tsx
│   │   │   ├── DrillCard.tsx     # renders sentence with {{answer}} replaced by <input>
│   │   │   ├── FeedbackPanel.tsx # CORRECT_SLOPPY warning / WRONG_FORM explanation
│   │   │   ├── RatingButtons.tsx # Again / Hard / Good / Easy
│   │   │   ├── SessionSummary.tsx
│   │   │   └── useReviewSession.ts  # queue state machine hook
│   │   └── keyboards/    # OnScreenKeyboard component, layout configs
│   ├── components/       # Shared UI (Button, Card, ProgressBar, LanguagePicker)
│   ├── stores/           # Zustand stores
│   │   ├── authStore.ts  # session, accessToken, user
│   │   └── prefsStore.ts # activeLanguageId, persisted to localStorage
│   ├── hooks/            # useSupabaseSession, useActiveLanguage
│   ├── lib/              # clsx helpers, date utils
│   ├── main.tsx
│   └── index.css         # @import "tailwindcss";
├── vite.config.ts
└── index.html
```

### Pattern 1: Vite + Tailwind v4 Configuration
**What:** Single plugin in vite.config.ts, single CSS import -- no tailwind.config.js, no PostCSS config.
**When to use:** All new React + Vite projects targeting Tailwind v4.

```typescript
// Source: https://tailwindcss.com/docs/installation/framework-guides/react-router
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

```css
/* src/index.css */
@import "tailwindcss";

/* Custom Arabic font -- loaded when language is Arabic */
@import url('https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap');
```

### Pattern 2: Supabase Auth -> JWT -> API Client
**What:** Supabase manages auth state; axios interceptor attaches the JWT to every backend call.
**When to use:** Any page that calls FastAPI endpoints.

```typescript
// src/api/client.ts
import axios from 'axios'
import { supabase } from '../lib/supabase'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
})

apiClient.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})
```

```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
)
```

### Pattern 3: Review Session Queue State Machine
**What:** Local hook manages the ordered queue of due cards, timing, and session results.
**When to use:** ReviewSessionPage -- keeps state local, avoids overcomplicating global store.

```typescript
// src/features/review/useReviewSession.ts
import { useState, useRef, useCallback } from 'react'

interface SessionCard {
  id: string
  sentence: string       // contains {{answer}} for grammar; definition for vocabulary
  correctAnswer: string
  languageCode: string
  cardContext?: Record<string, unknown>
}

interface ReviewResult {
  cardId: string
  answerResult: 'correct' | 'correct_sloppy' | 'wrong_form' | 'wrong'
  timeTakenMs: number
}

export function useReviewSession(cards: SessionCard[]) {
  const [queue, setQueue] = useState(cards)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [results, setResults] = useState<ReviewResult[]>([])
  const [phase, setPhase] = useState<'answering' | 'feedback' | 'summary'>('answering')
  const cardStartTime = useRef<number>(Date.now())

  const currentCard = queue[currentIndex] ?? null
  const isComplete = currentIndex >= queue.length

  const recordResult = useCallback((result: ReviewResult) => {
    setResults(prev => [...prev, result])
    setPhase('feedback')
  }, [])

  const advance = useCallback(() => {
    if (currentIndex + 1 >= queue.length) {
      setPhase('summary')
    } else {
      setCurrentIndex(i => i + 1)
      setPhase('answering')
      cardStartTime.current = Date.now()
    }
  }, [currentIndex, queue.length])

  const elapsedMs = () => Date.now() - cardStartTime.current

  return { currentCard, phase, results, isComplete, recordResult, advance, elapsedMs }
}
```

### Pattern 4: RTL Layout for Arabic
**What:** Toggle `dir` attribute on a wrapper element; use Tailwind logical properties everywhere.
**When to use:** Any component that renders content in the active language.

```tsx
// src/components/LanguageWrapper.tsx
import { usePrefsStore } from '../stores/prefsStore'
import clsx from 'clsx'

interface Props { children: React.ReactNode; languageCode: string }

export function LanguageWrapper({ children, languageCode }: Props) {
  const isRtl = languageCode === 'ar'
  return (
    <div
      dir={isRtl ? 'rtl' : 'ltr'}
      className={clsx(
        'w-full',
        isRtl && 'font-[\'Noto_Naskh_Arabic\'] text-xl leading-loose'
      )}
    >
      {children}
    </div>
  )
}
```

Tailwind logical property usage (works in both LTR and RTL automatically):
```html
<!-- Use ms-*/me-* instead of ml-*/mr-* -->
<!-- Use ps-*/pe-* instead of pl-*/pr-* -->
<div class="ms-4 pe-3 border-s-2">...</div>
```

### Pattern 5: On-Screen Keyboard
**What:** `react-simple-keyboard` with Russian/Arabic layouts from `simple-keyboard-layouts`.
**When to use:** DrillCard when activeLanguage is `ru` or `ar`.

```tsx
// src/features/keyboards/OnScreenKeyboard.tsx
import Keyboard from 'react-simple-keyboard'
import 'react-simple-keyboard/build/css/index.css'
import russianLayout from 'simple-keyboard-layouts/build/layouts/Russian'
import arabicLayout from 'simple-keyboard-layouts/build/layouts/Arabic'

interface Props {
  languageCode: 'ru' | 'ar'
  onChange: (value: string) => void
  inputValue: string
}

export function OnScreenKeyboard({ languageCode, onChange, inputValue }: Props) {
  const layout = languageCode === 'ru' ? russianLayout : arabicLayout

  return (
    <Keyboard
      layout={layout.layout}
      layoutName="default"
      onChange={onChange}
      input={inputValue}
      theme="hg-theme-default"
    />
  )
}
```

### Pattern 6: Fill-in-the-Blank Sentence Rendering
**What:** Replace `{{answer}}` in the sentence string with a controlled input element. If no `{{answer}}` marker exists (vocabulary cards), render as type-the-word mode.
**When to use:** DrillCard display.

```tsx
// src/features/review/DrillCard.tsx
interface Props {
  sentence: string    // e.g. "I {{answer}} to the store." (grammar) or "to go, to walk" (vocabulary)
  value: string
  onChange: (v: string) => void
  dir?: 'ltr' | 'rtl'
}

export function DrillCard({ sentence, value, onChange, dir = 'ltr' }: Props) {
  if (!sentence.includes('{{answer}}')) {
    // Vocabulary card: type-the-word mode
    return (
      <div dir={dir} className="text-center">
        <p className="text-xl leading-loose mb-4">{sentence}</p>
        <input type="text" value={value} onChange={e => onChange(e.target.value)}
          className="border-b-2 border-primary min-w-[120px] text-center focus:outline-none bg-transparent"
          dir={dir} autoFocus />
      </div>
    )
  }
  const [before, after] = sentence.split('{{answer}}')
  return (
    <p dir={dir} className="text-xl leading-loose text-center">
      {before}
      <input type="text" value={value} onChange={e => onChange(e.target.value)}
        className="inline-block border-b-2 border-primary min-w-[120px] text-center focus:outline-none bg-transparent mx-2"
        dir={dir} autoFocus />
      {after}
    </p>
  )
}
```

### Pattern 7: Quality Rating Buttons (44px+ targets)
**What:** Four buttons mapping to AnswerResult strings sent to `POST /api/review/submit`.
**When to use:** After NLP validation feedback is shown.

```tsx
// src/features/review/RatingButtons.tsx
const RATINGS = [
  { label: 'Again', result: 'wrong',         className: 'bg-red-500' },
  { label: 'Hard',  result: 'wrong_form',    className: 'bg-orange-400' },
  { label: 'Good',  result: 'correct_sloppy',className: 'bg-yellow-400' },
  { label: 'Easy',  result: 'correct',       className: 'bg-green-500' },
] as const

export function RatingButtons({ onRate }: { onRate: (r: string) => void }) {
  return (
    <div className="grid grid-cols-4 gap-2 w-full">
      {RATINGS.map(({ label, result, className }) => (
        <button
          key={result}
          onClick={() => onRate(result)}
          className={`${className} text-white font-semibold rounded-lg
                      min-h-[44px] py-3 px-4 touch-manipulation
                      hover:opacity-90 active:scale-95 transition`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
```

### Anti-Patterns to Avoid
- **Putting session queue in Zustand/global state:** The review queue is ephemeral per-session. Global state causes stale queue issues on navigation. Keep it in `useReviewSession` hook.
- **Calling NLP validate + SRS submit in one step:** Validate first (show feedback), then submit quality rating on user's explicit button press. Two separate user actions, two API calls.
- **Using `ml-*`/`mr-*`/`pl-*`/`pr-*` in shared components:** These physical properties do not flip in RTL. Use `ms-*`/`me-*`/`ps-*`/`pe-*` (logical) throughout.
- **Applying `dir="rtl"` at `<html>` level globally:** Only Arabic content needs RTL. Toggle it at the sentence/card wrapper level so UI chrome stays LTR.
- **Hard-coding the `answer_result` from the user's manual rating buttons directly:** The quality rating buttons show AFTER NLP validation. The frontend should use the NLP-returned `answer_result` as the default, allowing user override via the rating buttons. Do not conflate these two flows.

---

## New Backend Endpoints Required

These three endpoints do not yet exist and must be added in Phase 4:

### POST /api/review/validate-answer
**Purpose:** Run NLP `check_answer` and return result + feedback message before the user rates.
**Request body:**
```json
{
  "language_code": "string",
  "user_input": "string",
  "correct_answer": "string",
  "card_context": {}
}
```
**Response:**
```json
{
  "answer_result": "correct_sloppy",
  "feedback": "Correct meaning, but check the exact form. Expected: <correct form>"
}
```
**Implementation:** Calls `validate_answer_async(language_code, user_input, correct_answer, card_context)` from `backend.services.nlp`. Must catch `ValueError` from `get_nlp()` for unknown language codes and return HTTP 422.

### POST /api/review/learn
**Purpose:** Add a batch of `batch_size` new items (from subscribed lists) to `user_cards`.
**Request body:**
```json
{ "language_id": "uuid" }
```
**Response:** `{ "added": 5, "items": [...] }`
**Implementation:** Query `content_lists` joined with `user_content_subscriptions` for the user's subscribed lists in the given language, then select `batch_size` items from `vocabulary`/`grammar_points` NOT already in `user_cards`, INSERT them into `user_cards` with `next_review = now()`.

### GET /api/dashboard/{language_id}
**Purpose:** Single endpoint for dashboard page aggregation.
**Response:**
```json
{
  "due_count": 12,
  "streak_days": 5,
  "cefr_progress": { "A1": 0.75, "A2": 0.3, "B1": 0.0 }
}
```
**Implementation:** Three queries -- (1) COUNT from `user_cards` WHERE `next_review <= now()`, (2) streak from consecutive days in `review_log`, (3) CEFR progress from `user_cards` joined to `vocabulary`/`grammar_points`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| On-screen Cyrillic keyboard | Custom key grid component | `react-simple-keyboard` + `simple-keyboard-layouts` Russian layout | Arabic keyboard requires contextual glyph shaping, bidirectional cursor -- weeks of work |
| On-screen Arabic keyboard | Custom Arabic key grid | Same library, Arabic layout | Same as above; RTL input + Arabic glyph joining is solved problem |
| RTL layout flipping | Dual CSS stylesheets | Tailwind v4 logical properties (`ms-*`, `me-*`, `ps-*`, `pe-*`) | Physical properties (ml/mr/pl/pr) don't flip; logical properties are CSS standard |
| Arabic text rendering | Custom font stack | Noto Naskh Arabic via Google Fonts | Ensures correct glyph shaping; system fonts on non-Arabic systems are inadequate |
| JWT attachment | Custom fetch wrapper | axios interceptor on shared `apiClient` | One place to update; handles token refresh coordination |
| Session persistence | LocalStorage code | `@supabase/supabase-js` (auto stores in localStorage) | Supabase client handles storage, expiry, and refresh token rotation |
| API response caching | Manual state + useEffect | TanStack Query | Handles loading/error states, background refetch, deduplication |

**Key insight:** The virtual keyboard domain is especially dangerous to underestimate. Arabic contextual letter forms (isolated, initial, medial, final), RTL cursor movement, and proper Unicode bidirectional algorithm handling are all non-trivial. `react-simple-keyboard` has solved these across 3.8M+ weekly downloads.

---

## Common Pitfalls

### Pitfall 1: RTL Breaking LTR Chrome
**What goes wrong:** Applying `dir="rtl"` to the `<html>` or a top-level wrapper causes all UI buttons, navigation, and form labels to mirror.
**Why it happens:** Arabic content is only in the drill card / sentence area, not in UI chrome.
**How to avoid:** Apply `dir` only to the `<LanguageWrapper>` containing the sentence text and vocabulary display. Keep nav, buttons, and modals in their own LTR container.
**Warning signs:** Sidebar navigation jumps to right side; form submit buttons appear on left.

### Pitfall 2: Physical vs Logical Tailwind Properties
**What goes wrong:** `ml-4` works in LTR but doesn't flip to right margin in RTL, creating asymmetric layouts.
**Why it happens:** CSS `margin-left` is physical; `margin-inline-start` (Tailwind `ms-*`) is logical.
**How to avoid:** Establish a rule: any component that might render inside a `dir="rtl"` container must use logical properties. Lint with a custom rule or code review checklist.
**Warning signs:** Card padding looks correct in LTR view but is wrong-sided in Arabic mode.

### Pitfall 3: Supabase Token Expiry During Long Sessions
**What goes wrong:** User starts a 30-card review; 60 minutes in, the JWT expires and API calls return 401.
**Why it happens:** Supabase JWTs default to 1 hour expiry. Long review sessions can span this.
**How to avoid:** The axios interceptor calls `supabase.auth.getSession()` before each request -- the Supabase client automatically refreshes if within refresh window. Confirm this behavior with `onAuthStateChange` listener. For belt-and-suspenders: add a 401 response interceptor that calls `supabase.auth.refreshSession()` and retries once.
**Warning signs:** 401 errors appearing after 60+ minutes of inactivity.

### Pitfall 4: NLP Validate + SRS Submit Conflation
**What goes wrong:** Frontend submits quality rating the same moment NLP returns, before user sees feedback or chooses their own rating.
**Why it happens:** Misunderstanding the two-step UX flow: (1) validate answer -> show feedback, (2) user rates difficulty -> submit to SRS.
**How to avoid:** Keep validation (POST /validate-answer) and submission (POST /submit) as two separate user-triggered events. The `phase` state machine in `useReviewSession` enforces this -- `answering` -> `feedback` -> next card.
**Warning signs:** Users report not seeing feedback before cards advance.

### Pitfall 5: Arabic Font Loading Jank
**What goes wrong:** Arabic text renders in system fallback font briefly, then reflows when web font loads.
**Why it happens:** Google Fonts loaded via `<link>` in `<head>` but not preloaded; React renders before font is available.
**How to avoid:** Add `<link rel="preload">` for Noto Naskh Arabic. Use `font-display: swap` in the @font-face rule. Consider CSS `font-display: optional` if reflow is unacceptable.
**Warning signs:** Visible flash of different font, layout shift on Arabic pages.

### Pitfall 6: Missing `card_context` in Validate-Answer Payload
**What goes wrong:** Arabic verb form detection and Russian aspect detection return `WRONG` instead of `WRONG_FORM` because the `card_context` with morphology data was not sent.
**Why it happens:** `check_answer` uses `card_context["morphology"]` for aspect partner and verb form lookups. If omitted, these tiers are skipped silently.
**How to avoid:** When the frontend fetches due cards (`GET /api/review/due`), the backend should return `card_context` (including the `morphology` JSONB and `alternatives` array). The validate-answer endpoint forwards this context verbatim.
**Warning signs:** WRONG_FORM feedback never appears in testing even for obvious form errors.

---

## Code Examples

### Supabase Auth State Listener in App Root
```tsx
// src/App.tsx
import { useEffect } from 'react'
import { supabase } from './lib/supabase'
import { useAuthStore } from './stores/authStore'

export function App() {
  const setSession = useAuthStore(s => s.setSession)

  useEffect(() => {
    // Restore session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => setSession(session)
    )
    return () => subscription.unsubscribe()
  }, [setSession])

  return <RouterProvider router={router} />
}
```

### Zustand Auth Store
```typescript
// src/stores/authStore.ts
import { create } from 'zustand'
import type { Session } from '@supabase/supabase-js'

interface AuthState {
  session: Session | null
  setSession: (s: Session | null) => void
  accessToken: () => string | null
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  setSession: (session) => set({ session }),
  accessToken: () => get().session?.access_token ?? null,
}))
```

### TanStack Query: Due Cards
```typescript
// src/api/review.ts
import { apiClient } from './client'

export async function getDueCards(languageId: string) {
  const { data } = await apiClient.get('/api/review/due', {
    params: { language_id: languageId }
  })
  return data as DueCard[]
}

// src/features/review/ReviewSessionPage.tsx
import { useQuery } from '@tanstack/react-query'
import { getDueCards } from '../../api/review'

const { data: cards, isLoading } = useQuery({
  queryKey: ['due-cards', activeLanguageId],
  queryFn: () => getDueCards(activeLanguageId),
  staleTime: 1000 * 60 * 5,  // 5 minutes
})
```

### CEFR Progress Bar Component
```tsx
// src/features/dashboard/CEFRProgress.tsx
const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] as const

export function CEFRProgress({ progress }: { progress: Record<string, number> }) {
  return (
    <div className="space-y-2">
      {LEVELS.map(level => (
        <div key={level} className="flex items-center gap-3">
          <span className="text-sm font-mono w-8 text-muted">{level}</span>
          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${(progress[level] ?? 0) * 100}%` }}
            />
          </div>
          <span className="text-xs text-muted w-10 text-end">
            {Math.round((progress[level] ?? 0) * 100)}%
          </span>
        </div>
      ))}
    </div>
  )
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PostCSS + tailwind.config.js | `@tailwindcss/vite` plugin, no config file | Tailwind v4 (Jan 2025) | Simpler setup, automatic content detection |
| `@tailwindcss/postcss` | `@tailwindcss/vite` for Vite projects | Tailwind v4 (Jan 2025) | Plugin-first, PostCSS no longer required |
| `ml-*`/`mr-*` for RTL | Logical `ms-*`/`me-*` | Tailwind v3.3+ (2023) | RTL support without dual CSS |
| `getSession().user` (trusted) | `getUser()` or `getClaims()` for security-critical | Supabase 2024 | getSession user object not verified server-side |
| Redux for all state | Zustand (client) + TanStack Query (server) | 2023-2024 | Separation of concerns, less boilerplate |

**Deprecated/outdated:**
- `tailwind.config.js` content array: No longer required in v4; auto-detected.
- `@apply` directives: Still work but discouraged in v4; use components/utilities directly.
- PostCSS setup for Tailwind with Vite: Replaced by `@tailwindcss/vite` plugin.

---

## Open Questions

1. **`card_context` in GET /api/review/due response**
   - What we know: `get_due_cards()` currently returns only `user_cards` columns (SRS state); it does NOT join vocabulary/grammar_points to get the sentence, correct_answer, morphology, or alternatives.
   - What's unclear: The backend returns `card_id` and `card_type` but not the card content. The frontend needs the drill sentence and `card_context` for NLP validation.
   - Recommendation: Extend `get_due_cards()` to JOIN against `drill_sentences`/`vocabulary` based on `card_type`, returning the sentence, correct_answer, morphology JSONB, and alternatives array. This is a required backend change for Phase 4.

2. **Streak calculation algorithm**
   - What we know: `review_log` has `created_at` timestamps; `user_profiles` has no streak column.
   - What's unclear: Whether to compute streak dynamically in the dashboard query or store it on `user_profiles` (updated on each review submission).
   - Recommendation: Compute dynamically in `GET /api/dashboard/{language_id}` using a SQL window function over `review_log`. Avoids stale state. Precompute if performance is an issue (unlikely at Phase 4 scale).

3. **Learn mode item selection order**
   - What we know: `PROG-01` (CEFR-ordered grammar curriculum) is Phase 5, not Phase 4. In Phase 4, grammar points may not yet be CEFR-ordered.
   - What's unclear: How to order new items for Learn sessions before the Phase 5 curriculum is in place.
   - Recommendation: For Phase 4, order new vocabulary by `frequency_rank ASC` (lower rank = more common). Fall back to `created_at ASC` for grammar points. Accept this as a temporary ordering; Phase 5 replaces it with CEFR progression.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (backend); Vitest (frontend) |
| Config file | Backend: `pyproject.toml` `[tool.pytest.ini_options]`; Frontend: `vitest.config.ts` (Wave 0) |
| Quick run command (backend) | `pytest backend/tests/ -x -q` |
| Quick run command (frontend) | `cd frontend && npm run test -- --run` |
| Full suite command | `pytest backend/tests/ && cd frontend && npm run test -- --run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REV-01 | Due cards returned sorted by next_review | integration | `pytest backend/tests/test_review_api.py::test_due_cards_sorted -x` | No (Wave 0) |
| REV-02 | `{{answer}}` marker renders as input in frontend | unit (component) | `cd frontend && npm run test -- DrillCard` | No (Wave 0) |
| REV-03 | Rating buttons call submit with correct answer_result | unit (component) | `cd frontend && npm run test -- RatingButtons` | No (Wave 0) |
| REV-04 | WRONG_FORM feedback shown after NLP validate | unit (component) | `cd frontend && npm run test -- FeedbackPanel` | No (Wave 0) |
| REV-05 | CORRECT_SLOPPY warning shown | unit (component) | `cd frontend && npm run test -- FeedbackPanel` | No (Wave 0) |
| REV-06 | Session summary shows correct accuracy % | unit (hook) | `cd frontend && npm run test -- useReviewSession` | No (Wave 0) |
| REV-07 | Learn endpoint adds batch_size new cards | integration | `pytest backend/tests/test_review_api.py::test_learn_session -x` | No (Wave 0) |
| REV-08 | Review mode only returns next_review <= now() cards | integration | `pytest backend/tests/test_review_api.py::test_due_only_learned -x` | No (Wave 0) |
| UX-01 | Dashboard returns due_count, streak, cefr_progress | integration | `pytest backend/tests/test_dashboard_api.py -x` | No (Wave 0) |
| UX-02 | Arabic content gets dir="rtl" and Noto Naskh Arabic | unit (component) | `cd frontend && npm run test -- LanguageWrapper` | No (Wave 0) |
| UX-03 | Keyboard renders for ru/ar, not for en | unit (component) | `cd frontend && npm run test -- OnScreenKeyboard` | No (Wave 0) |
| UX-08 | Rating buttons min height >= 44px | unit (component) | `cd frontend && npm run test -- RatingButtons` | No (Wave 0) |
| PROF-01 | Profile returns/updates batch_size | integration | `pytest backend/tests/test_auth.py::test_profile_batch_size -x` | No (Wave 0, partial -- test_auth.py exists) |
| PROF-02 | Active language scopes due cards | integration | `pytest backend/tests/test_review_api.py::test_due_scoped_to_language -x` | No (Wave 0) |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/ -x -q` (backend tasks) or `cd frontend && npm run test -- --run` (frontend tasks)
- **Per wave merge:** `pytest backend/tests/ && cd frontend && npm run test -- --run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_review_endpoints.py` -- covers REV-01, REV-07, REV-08, PROF-02
- [ ] `backend/tests/test_dashboard_endpoint.py` -- covers UX-01
- [ ] `frontend/src/__tests__/DrillCard.test.tsx` -- covers REV-02
- [ ] `frontend/src/__tests__/RatingButtons.test.tsx` -- covers REV-03, UX-08
- [ ] `frontend/src/__tests__/FeedbackPanel.test.tsx` -- covers REV-04, REV-05
- [ ] `frontend/src/__tests__/useReviewSession.test.ts` -- covers REV-06
- [ ] `frontend/src/__tests__/OnScreenKeyboard.test.tsx` -- covers UX-03
- [ ] `frontend/src/__tests__/LanguageWrapper.test.tsx` -- covers UX-02
- [ ] `frontend/src/__tests__/ReviewSessionPage.test.tsx` -- covers REV-03 (submitReview integration)
- [ ] `frontend/vitest.config.ts` -- frontend test framework config
- [ ] Framework install: `cd frontend && npm install -D vitest @testing-library/react @testing-library/user-event jsdom @vitejs/plugin-react`

---

## Sources

### Primary (HIGH confidence)
- Tailwind CSS v4 official docs (tailwindcss.com/docs) -- v4 Vite plugin setup, logical properties
- Supabase Auth docs (supabase.com/docs/reference/javascript/auth-getsession) -- getSession, access_token
- Supabase Auth React quickstart (supabase.com/docs/guides/auth/quickstarts/react) -- onAuthStateChange pattern
- Existing backend codebase (read directly) -- all endpoint signatures, DB schema, NLP interface confirmed

### Secondary (MEDIUM confidence)
- react-simple-keyboard npm package page + GitHub (hodgef.com/simple-keyboard) -- Russian + Arabic layout availability confirmed
- simple-keyboard-layouts GitHub -- 50+ layouts confirmed, Russian and Arabic explicitly listed
- Tailwind v4 RTL logical properties blog post (tailwindcss.com/blog/tailwindcss-v4) -- ms-*, me-*, ps-*, pe-* confirmed native v4 support
- Zustand GitHub (github.com/pmndrs/zustand) + community analysis -- auth + active language store pattern

### Tertiary (LOW confidence)
- Medium/DEV posts on SRS UI patterns -- general flashcard queue patterns, not SRS-specific verified implementations
- WebSearch results on 44px touch targets -- WCAG standard well-established, Tailwind implementation patterns are common knowledge

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified against official docs and npm; Tailwind v4 setup confirmed via official guide
- Architecture patterns: HIGH -- derived directly from existing backend API signatures (read backend code), not assumed
- New endpoints required: HIGH -- gap analysis based on reading existing router/repository code
- RTL approach: HIGH -- Tailwind v4 logical properties verified in official docs; `dir` attribute is HTML standard
- Virtual keyboards: MEDIUM -- library availability confirmed, Arabic layout confirmed; specific API props inferred from official docs + npm page (not tested)
- Pitfalls: MEDIUM -- RTL and token expiry pitfalls are well-documented; `card_context` omission is specific to this codebase

**Research date:** 2026-03-14
**Valid until:** 2026-06-14 (Tailwind v4 and react-simple-keyboard stable; Supabase auth API stable)
