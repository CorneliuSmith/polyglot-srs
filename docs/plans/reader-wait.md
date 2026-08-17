# The wait is not dead time: play or review while a text is written

Generating a reading got slower on purpose. The contract grader (#285)
adds a grading call, and a text that flunks its contract is regenerated —
so a bad text now costs two full generations before the learner sees
anything. That was the right trade for quality, but it left the Reader's
wait as a disabled button reading "Writing…" with nothing to do.

The owner: *"add an option to review or play the ling games while they
wait and they will be notified when done."*

The app already solved this shape once. The trailblazer wait screen
(`features/review/TrailblazerWait.tsx`) turns a content-fill wait into a
tap-to-match word game with a trivia fallback. That machinery is built,
tested, and localized — the Reader should use it rather than grow its own.

## What exists to reuse

| Piece | Where | Reuse |
| --- | --- | --- |
| Tap-to-match word game | `MatchGame`, nested inside `TrailblazerWait.tsx` | **Extract** to its own file; both waits import it |
| Linguistics trivia | `features/review/TriviaGame.tsx` | Import as-is (already standalone, empty-bank aware) |
| The learner's due words | `getDueCards(lang, n, 'vocabulary')` | Match-game pairs — reviewing, in game form |

## The hard part: surviving navigation

"Go review while you wait" means leaving `/read`. Today the request is a
`useMutation` owned by `ReaderPage`: unmount the page and the mutation
observer dies with it, so `onSuccess` never runs and the finished text is
dropped on the floor.

**The fix: the request outlives the page.** A small Zustand store
(`stores/pendingReadingStore.ts`) owns the promise and attaches its own
`.then/.catch`. Route changes don't touch it — an SPA navigation unmounts
components, not module state. `ReaderPage` becomes a subscriber, not the
owner.

Deliberately NOT a server-side job queue: that needs a jobs table, and
migrations here are applied by hand by the owner. The client-side job gets
the whole UX with no migration — and the failure mode is already covered,
because `/api/reader/generate` **saves the reading before it responds**.
Close the tab mid-generation and the text still lands in "My readings";
only the notification is lost.

## The four pieces

### 1. `stores/pendingReadingStore.ts`

```
{ pending: {topic, languageId, languageCode, startedAt} | null,
  ready:   {id, reading, topic, level} | null,
  error:   string | null }
start(job, promise) → tracks; on settle, moves pending → ready | error
claim() → hands the ready reading to whoever renders it, clears the slot
```

One job at a time: starting a second replaces the first (the Reader's
form is single-shot anyway, and two texts racing to a banner is worse
than the newest winning).

### 2. The wait panel in `ReaderPage`

Replaces the dead "Writing…" state. Shows what's being written, an honest
"this takes a minute — it gets graded and rewritten if it misses", and two
offers:

- **Play while you wait** — MatchGame over their due words, TriviaGame
  when nothing is due (same fallback ladder as the trailblazer).
- **Review while you wait** — a link to `/review`; the text keeps writing.

Plus the promise that makes leaving safe: *we'll tell you the moment it's
ready.*

### 3. `components/ReadingReadyBanner.tsx` — the notification

Mounted app-wide in `AppInner`, so it reaches the learner wherever they
went. Two channels:

- **Always**: an in-app banner — "Your text about *X* is ready · Read it"
  — which navigates to `/read` and opens the reading.
- **When the tab is hidden**: a Web `Notification`, if permission is
  granted. Permission is requested **only when the learner chooses to
  wander off** (the "review while you wait" tap), never on page load —
  an unprompted permission dialog is the single most-hated pattern on the
  web, and asking at the moment it means something is how it earns a yes.

The banner is suppressed on `/read` itself: the page shows the reading
directly, so a banner announcing it would be noise. It also never appears
inside a running review session (`/review`, `/learn`, `/cram`,
`/gym`) — interrupting an answer with a floating card is how a learner
loses their streak. It waits for them to come out.

### 4. `ReaderPage` claims on mount

Coming back to `/read` — by banner or by tab — claims the ready reading
and renders it exactly as if the learner had never left, listen-first
stage included.

## Testing

- Store: pending → ready, error path, claim clears, second start replaces.
- ReaderPage: wait panel appears while pending; game renders; the review
  link exists; a text that resolves after the page unmounted is still
  claimed on return (the whole point).
- Banner: shows off-reader, hidden on `/read` and in sessions, navigates
  on tap, fires the browser Notification only when hidden + granted.
- MatchGame extraction: trailblazer tests keep passing untouched.

## Non-goals

- No push notifications to a closed app (needs a service worker + VAPID
  keys + a backend subscription table — a project, not a step).
- No queue of multiple simultaneous texts.
- No change to the generation contract itself; this is purely about what
  the learner does with the sixty seconds it now costs.
