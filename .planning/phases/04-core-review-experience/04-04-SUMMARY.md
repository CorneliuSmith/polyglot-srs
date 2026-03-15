---
phase: 04-core-review-experience
plan: "04"
subsystem: ui
tags: [react, tanstack-query, vitest, zustand, tailwind, review-session, sm2]

requires:
  - phase: 04-01
    provides: Backend validate-answer, submit, learn, due-cards endpoints
  - phase: 04-02
    provides: API client (axios), types (DueCard, ValidateAnswerResponse), prefsStore
  - phase: 04-03
    provides: DashboardPage, LoginPage, ProtectedRoute, App routing shell

provides:
  - useReviewSession hook — queue state machine with phase transitions and accuracy tracking
  - DrillCard component — fill-in-the-blank (grammar) and type-the-word (vocabulary) modes
  - FeedbackPanel component — color-coded NLP result display
  - RatingButtons component — Again/Hard/Good/Easy touch-friendly buttons
  - ReviewSessionPage — complete review session flow wiring all components
  - SessionSummary — end-of-session stats with accuracy%, time, cards reviewed
  - LearnPage — adds new cards from subscriptions and routes to review
  - App.tsx updated with real ReviewSessionPage and LearnPage imports

affects: [05-list-browsing-and-subscriptions, 06-deployment]

tech-stack:
  added: []
  patterns:
    - useMutation from TanStack Query for validate-answer and submit-review (prevents double-submit)
    - useReviewSession state machine separates UI state from API calls
    - mock.calls[0][0] pattern for asserting first arg when TanStack passes context as second arg

key-files:
  created:
    - frontend/src/features/review/useReviewSession.ts
    - frontend/src/features/review/DrillCard.tsx
    - frontend/src/features/review/FeedbackPanel.tsx
    - frontend/src/features/review/RatingButtons.tsx
    - frontend/src/features/review/ReviewSessionPage.tsx
    - frontend/src/features/review/SessionSummary.tsx
    - frontend/src/features/review/LearnPage.tsx
    - frontend/src/__tests__/useReviewSession.test.ts
    - frontend/src/__tests__/DrillCard.test.tsx
    - frontend/src/__tests__/FeedbackPanel.test.tsx
    - frontend/src/__tests__/RatingButtons.test.tsx
    - frontend/src/__tests__/ReviewSessionPage.test.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/vitest.config.ts

key-decisions:
  - "vitest globals:true added to config — jest-dom setup.ts expects global expect which was undefined without it"
  - "mock.calls[0][0].toMatchObject() used instead of toHaveBeenCalledWith() — TanStack Query passes a second context arg to mutationFn that breaks strict equality"
  - "useReviewSession.rate() both records result AND advances index atomically — avoids race between session state and API call"
  - "DrillCard detects vocabulary mode by absence of {{answer}} marker — matches 04-01 decision that vocabulary sentence IS the definition"
  - "lastInput state in ReviewSessionPage captures user input before clearing — FeedbackPanel shows what user typed after input is reset"

requirements-completed: [REV-01, REV-02, REV-03, REV-04, REV-05, REV-06, REV-08]

duration: 20min
completed: 2026-03-15
---

# Phase 4 Plan 04: Core Review Session Summary

**Complete SRS review loop built in React: fill-in-the-blank drill cards with NLP validation feedback, four-button SM-2 rating, and session summary — wired from card queue to accuracy stats**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-15T02:00:00Z
- **Completed:** 2026-03-15T02:20:00Z
- **Tasks:** 2
- **Files modified:** 14 (12 created, 2 modified)

## Accomplishments

- useReviewSession hook implements the answering->feedback->rating->next/summary state machine with correct accuracy accumulation across cards
- DrillCard handles both grammar (fill-in-the-blank with {{answer}} marker) and vocabulary (type-the-word, definition as prompt) modes matching the 04-01 backend design
- ReviewSessionPage wires the full cycle: getDueCards -> DrillCard -> validateAnswer -> FeedbackPanel -> RatingButtons -> submitReview -> advance
- SessionSummary displays accuracy (color-coded green/yellow/red), time formatted as "X min Y sec", and cards reviewed count
- 56 new tests across 5 test files — 66 total passing (including critical REV-03 coverage confirming submitReview is called on rating button click)

## Task Commits

1. **Task 1: useReviewSession, DrillCard, FeedbackPanel, RatingButtons with tests** - `708d088` (feat)
2. **Task 2: ReviewSessionPage, SessionSummary, LearnPage wiring and integration tests** - `94f6aee` (feat)

## Files Created/Modified

- `frontend/src/features/review/useReviewSession.ts` - Queue state machine hook: phase transitions, results array, accuracy, totalTimeMs, elapsedMs
- `frontend/src/features/review/DrillCard.tsx` - Fill-in-the-blank (grammar) and type-the-word (vocabulary) input modes
- `frontend/src/features/review/FeedbackPanel.tsx` - Color-coded panel: green=correct, amber=correct_sloppy, orange=wrong_form, red=wrong
- `frontend/src/features/review/RatingButtons.tsx` - Again/Hard/Good/Easy mapped to wrong/wrong_form/correct_sloppy/correct, NLP-suggested button highlighted with ring
- `frontend/src/features/review/ReviewSessionPage.tsx` - Full review page with progress indicator, two-step API flow, loading/empty states
- `frontend/src/features/review/SessionSummary.tsx` - End-of-session stats: accuracy%, time, count with color-coded accuracy
- `frontend/src/features/review/LearnPage.tsx` - Calls startLearnSession on mount, handles added/0/error states
- `frontend/src/App.tsx` - Replaced placeholder pages with real ReviewSessionPage and LearnPage imports
- `frontend/vitest.config.ts` - Added globals:true to resolve jest-dom setup error

## Decisions Made

- `vitest globals:true` added to config: jest-dom's `setup.ts` calls `expect.extend()` which requires `expect` to be globally available in jsdom environment.
- `mock.calls[0][0]` assertion pattern: TanStack Query's `useMutation` passes a second context argument to the mutation function, causing `toHaveBeenCalledWith()` strict equality to fail. Accessing `mock.calls[0][0]` and using `toMatchObject()` correctly targets only the request object.
- `lastInput` state captured before clearing: after user submits answer, the input is cleared for next card, but FeedbackPanel needs to show what the user typed. `lastInput` is set from `userInput` before reset.
- Vocabulary mode detection: absence of `{{answer}}` in sentence indicates vocabulary card (definition as prompt, user types the target word). This matches the 04-01 backend decision where `sentence=definition` for vocabulary cards.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added vitest globals:true to fix jest-dom setup failure**
- **Found during:** Pre-task baseline verification
- **Issue:** Existing tests failing — `expect is not defined` error in setup.ts because jest-dom calls `expect.extend()` but vitest globals weren't enabled
- **Fix:** Added `globals: true` to vitest.config.ts test options
- **Files modified:** frontend/vitest.config.ts
- **Verification:** All 10 pre-existing tests passed after fix
- **Committed in:** 708d088 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — pre-existing config issue)
**Impact on plan:** Required to run any tests at all. No scope creep.

## Issues Encountered

- TanStack Query `useMutation` passes context as second arg to `mutationFn` mock, breaking `toHaveBeenCalledWith()` strict matching. Fixed by asserting on `mock.calls[0][0]` with `toMatchObject()`.

## Next Phase Readiness

- Full review session flow complete — users can drill cards, see NLP feedback, rate difficulty
- Phase 5 (list browsing and subscriptions) can proceed — LearnPage already handles the 0-cards case with message about subscribing to lists
- DashboardPage already shows "Learn New Cards" and "Review Due Cards" buttons routing correctly

---
*Phase: 04-core-review-experience*
*Completed: 2026-03-15*
