# DEBT.md — strange choices and technical debt

A triage list, not an to-do list: some of these are deliberate and correct
(and are here so you remember *why* the next time they look wrong), some are
genuinely worth fixing, and a couple are just doc drift. Each entry says
which. Companion to [`LEARN.md`](LEARN.md) — read that first if a term here
is unfamiliar.

> **This file is maintained, not archived.** Anything left deliberately off,
> any workaround for a platform limitation, any bug whose cause was
> non-obvious, and any doc found drifting gets an entry here in the same PR
> that discovers it — and an entry that stops being true gets **deleted**,
> not left to send the next reader hunting for a problem that's already
> fixed. The rule is in `CLAUDE.md` → *Shipping* → *LEARN.md and DEBT.md are
> living documents*.

---

## Deliberate, correct, and easy to mistake for a bug

### Monetization is fully built and switched off

`stripe` is integrated, "Monetization v2" (single-language `$7` plan with no
AI included, a `$5/mo` AI add-on that *adds to* rather than replaces the
plan's base pool, a `$5` one-time top-up) is implemented — and none of it is
live. Everything routes through `app_flags.monetization`
(`backend/services/flags.py`), which defaults `False` even if its own
migration hasn't landed. This is an owner decision (an employer
conflict-of-interest hold), not an abandoned feature — don't "finish" it by
flipping the flag; that's your call to make when the hold lifts. If you ever
audit the codebase and find payment code that looks unreachable, this is
why.

### The production push is gated on two things, and has been for a while

Per `docs/decisions/2026-08-26-owner-decisions.md`: no `supabase db push` /
reconcile sequence runs until (1) the Gym level is finished and (2) the
grammar concepts have had a *comprehensive* review, not just a
defect-free one. Worth re-reading before assuming "the code is ready, why
isn't it deployed" — the repository has been ahead of the deployed app for a
while on purpose.

### `trial_reviewer` in the database, "Tester" on screen

The stored role value is `trial_reviewer`; the UI calls it "Tester"
everywhere. It wasn't renamed because the value sits in a CHECK constraint
that existing role grants depend on — renaming it is a migration, and
migrations are owner-applied. If you're grepping for the tester role and
finding nothing, search for `trial_reviewer` instead.

### `'strict'` is a legacy spelling of `human_only`

Content-visibility policies store `'strict'` for what the UI and newer code
call `human_only`. `normalize_policy` maps both to the same behavior and the
stored spelling is never rewritten — a global rename would cost a table
rewrite for zero behavior change. Not a bug; just a name that only exists in
one direction.

### `camel-tools` stays out of the default install

Arabic's full morphological grader (`camel-tools`) is an optional extra, not
a base dependency — it pulls in `torch` + `transformers` (~4GB) and has
already blown a DigitalOcean build machine's disk during a real deploy
attempt. Arabic answer grading runs a diacritic-folding heuristic instead.
This is orthogonal to Arabic *romanization*, which is already solved without
`camel-tools` via `backend/services/nlp/semitic_reading.py`'s dictionary
lookup — don't reach for `camel-tools` if what you actually need is a
reading, not a grader.

### Two "AI review" features that sound like one

`services/semantic_check.py` (a reviewer-triggered, advisory "run AI check"
button that never publishes anything) and the maker-checker generation
checker (`services/generate.py` / `translate.py` / `define.py`, which runs
automatically at creation time and *can* auto-publish under an `ai_ok`
policy) are genuinely different systems that happen to both be called "AI
review" in conversation. If a bug report says "the AI check didn't catch
X," find out which one they mean before debugging — see
`docs/review-workflow.md`.

---

## Real gotchas — already hit once, will bite again if forgotten

### RateLimiter's cached Redis client can point at a dead event loop

Each `TestClient` (and each uvicorn worker) runs its own asyncio event loop.
If the rate limiter's async Redis client gets built against one loop and is
later read from another, it fails — and it fails in a way that looks
environmental (passes alone, passes without `REDIS_URL`, passes in CI, and
the *set* of failing tests shifts with test order). This already cost 8
backend test failures in one debugging session before the actual cause was
found. If you see order-dependent test failures anywhere near rate limiting,
suspect this before suspecting the test infrastructure.

### A mock that agrees with the bug

One real production 500 (the assign-by-email endpoint) existed because a
unit test's mock returned a dict shape that didn't match what the real
repository function actually returned (a bare string) — the mock quietly
"agreed" with the wrong assumption instead of catching it. Since fixed, but
the general risk is structural: any mock of a repository function is only as
good as its fidelity to that function's real return type. Prefer an
integration test against real Postgres for anything where the return shape
matters.

### A partial mock, caught this time

The same class as above, from the other direction: a `test_contributor.py`
unit test mocks `list_requests` to return request dicts *without*
`target_type`, because nothing read that field when the test was written.
Adding `load_cards` — which does read it — turned that into a `KeyError`
that only appeared in the full suite. The fix was to make `load_cards`
total (every field read with `.get()`, an unrecognised row simply gets no
card), which is the right shape anyway for a function whose whole job is
attaching optional context: it must never be the reason a board fails to
render. Worth remembering that a partial mock is a *latent* failure — it
passes until someone reads a field the fixture never had.

### A "graceful degradation" that degraded nothing (fixed)

The profile endpoint's fallback for a not-yet-applied migration was a
ladder: try the widest SELECT, catch `UndefinedColumnError`, retry a
narrower one. It could never have worked. `rls_connection` runs inside one
explicit transaction, so the first failure aborted it and the retry raised
`InFailedSQLTransactionError` — uncaught — on the endpoint that renders
every page. It read as defensive for four migrations and was decorative;
nobody noticed because each migration was applied before the code that
needed it shipped. Replaced with a probe of `information_schema.columns`
(`docs/decisions/0001`). Kept here as a *pattern* warning: `try/except` a
SQL error and continue on the same connection is a no-op wherever the
connection is inside a transaction, which is everywhere `rls_connection` is
used.

The same ladder also only dropped column groups from the right, so
"newest migration applied, an older one not" — a real state when migrations
are owner-applied and independent — had no attempt that fitted it. The
replacement plans per column.

### Integration tests skip silently, and it has hidden ~79 tests before

Without `INTEGRATION_DATABASE_URL` set, DB-backed tests report as `skipped`,
not `failed` — and once made a "1244 passing" run meaningless because a
whole slice of the suite (RLS, portability, publish-policy integration
tests) never ran. `CLAUDE.md` has the exact commands to start a throwaway
Postgres + Redis and run the full suite; use them before trusting a
"tests pass" claim that touches the database.

---

## Documentation drift — accurate now, but watch for recurrence

### `README.md` undercounts languages and misnames the scheduler

As of this writing, `README.md`'s headline says "Languages (14)" and "SM-2
scheduling." The codebase actually teaches 27 languages (see
`docs/decisions/2026-08-26-owner-decisions.md`'s "on all 27 courses" and the
seeder's language list) and schedules with **FSRS**, not SM-2 (see
`backend/services/fsrs.py`). This is the repo's most-read file and it's
stale — worth a pass the next time you touch it, and worth treating as a
reminder that headline numbers in prose docs rot fast in a codebase that
ships this often.

### `docs/pricing-and-launch.md` predates Monetization v2

That memo (17 August 2026) proposes a $8/$14/$24 tiered-plan structure with
weighted-unit metering. What actually shipped, three weeks later, is
Monetization v2: a `$7` single-language plan with *no* AI included, a
separate `$5/mo` AI add-on, and a `$5` top-up — a different shape, not a
refinement of the memo's numbers. The memo is still useful for its cost
arithmetic (per-action Claude costs, the Reader-text-is-30x-a-tutor-message
problem) but its top-line prices are superseded. Worth a "superseded by"
note at the top of the file, or a fold into a single current pricing
doc, the next time pricing changes again.

### `ARCHITECTURE.md`'s testing command was wrong (fixed in this pass)

It recommended `npx tsc --noEmit && npx vitest run`, which contradicts
`CLAUDE.md`'s explicit, stronger instruction (`npm run build`, never
`--noEmit` alone) — and contradicts what CI itself runs
(`.github/workflows/ci.yml`: `npx vitest run` then `npm run build`). Already
corrected as part of writing this document. Flagging the *pattern* here
because it's a good example of how a "how to test this" line in a docs file
can silently drift out of sync with the actual CI config — worth spot-checking
docs against `.github/workflows/ci.yml` periodically rather than trusting
prose.

---

## Designed but not built

### Offline support

`docs/offline.md` is a complete design — pack format, the outbox pattern for
queued writes, a client-side FSRS port with shared test fixtures, per-language
fold tables for degraded offline grading, the iOS storage-durability trap —
and none of it exists in code yet. `frontend/public/sw.js` only caches the
app shell and static assets; there's no IndexedDB anywhere in
`frontend/src`. If "offline" comes up as a feature request, the design work
is already done; what's missing is implementation, staged exactly as the doc
lays out (Gym offline first — it's append-only and ungraded, so it proves the
sync loop with nothing at stake).

### Native app store submission

Both Capacitor shells (`frontend/android`, `frontend/ios`) build cleanly and
share the one web bundle, but neither has been compiled with its real
toolchain (no Xcode/Android SDK in CI), and several submission blockers are
still open: no app icons/splash generated from the PWA source assets, no
signing (distribution cert, provisioning profile, Play keystore), missing
usage-string entries (`NSMicrophoneUsageDescription` for the tutor's audio
recording, `RECORD_AUDIO` in the Android manifest), and deep-link domain
association files not yet served from the API host. Full list:
`docs/native-apps.md`. None of this is surprising or hidden — it's just work
that genuinely needs a macOS machine and developer accounts, not something
an agent session can close out.

---

## Small, real, and already known

### The `overlaps` tile pointed at a panel that isn't on that tab

`OverlapsPanel` is mounted by `ReviewQueue`, which renders in **Settings** —
not on the Workspace Review tab, where the Review Inbox tile said to look
("Overlaps panel · Review tab"). The hint is corrected and the tile is
deliberately not clickable in focus mode, since focusing it could only
scope the page to nothing. The panel itself is fine; only the signpost was
wrong. Worth deciding whether that queue should move onto the Review tab
with the others rather than staying the one exception.

---

## Naming / cosmetic

### Product name

`README.md` and the codebase call it PolyglotSRS throughout, including the
committed bundle identifier `com.polyglotsrs.app` in both native projects.
`docs/pricing-and-launch.md` argues for a rename before any app-store
listing goes out (its case: "SRS" doesn't mean anything to the audience,
"Polyglot" is the most crowded term in the category with no defensible
trademark). Not urgent, but worth deciding before the native app work in the
section above, since the bundle identifier is annoying to change after a
store submission.
