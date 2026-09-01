# LEARN.md — technology choices and concepts

This is an onboarding document for the *owner*, not for an AI agent: it exists
so you can explain why the codebase looks the way it does, and change it
yourself without having to rediscover the reasoning first. It complements
[`ARCHITECTURE.md`](ARCHITECTURE.md) rather than repeating it — that file has
the diagrams and the "how a request flows through the system" walkthroughs;
this file is organized around "why this technology, and what does it buy
you." Where a topic already has a dedicated doc under `docs/`, this file
gives you the one-paragraph version and points at the real thing. See
[`DEBT.md`](DEBT.md) for the companion list of rough edges and choices worth
revisiting.

> **This file is maintained, not archived.** A change that adds or drops a
> dependency, introduces a pattern worth copying, or changes how a core
> concept works updates this file in the same PR. The rule is in
> `CLAUDE.md` → *Shipping* → *LEARN.md and DEBT.md are living documents*.
> If something here contradicts the code, the code is right and this file
> is a bug — fix it.

## How to navigate the docs

- **`ARCHITECTURE.md`** — the system diagrams, the request-flow walkthroughs,
  and a "decisions worth knowing about" section. Read this first.
- **`docs/*.md`** — one file per subsystem (`content-visibility.md`,
  `review-workflow.md`, `seeding.md`, `accounts-and-roles.md`, `database.md`,
  `native-apps.md`, `offline.md`, `content-generation-cli.md`,
  `curriculum-design.md`, `extraction-sources.md`, `ingestion-interchange.md`,
  `pricing-and-launch.md`, `DEPLOY.md`). Each is written the same way this
  file is — plain language, explains the *why*, not just the *what*.
- **`docs/decisions/`** — an ADR log. Short, dated records of specific calls
  that constrain future work (e.g. "offline belongs in the web layer, not a
  new native app"). Check here before re-opening a settled question.
- **`docs/plans/`** — design docs for features, some shipped, some not.
  Useful as "why does this feature have this shape" once it exists, or as
  "here's a fully-thought-through spec" for something that doesn't yet
  (`offline.md`'s companion, `docs/plans/*`, are the un-built ones).
- **This file (`LEARN.md`)** — the technology layer underneath all of the
  above: why FastAPI and not Django, why raw SQL and not an ORM, why FSRS,
  why Capacitor, and so on.

---

## Backend

### FastAPI + asyncpg, no ORM — by design

The backend is FastAPI (`backend/main.py`) talking to Postgres directly
through `asyncpg`. There is no ORM (no SQLAlchemy, no Tortoise) anywhere in
the codebase. This is a deliberate choice, not an oversight: the database is
Supabase Postgres with Row-Level Security as the actual security boundary
(see below), and RLS policies are easiest to reason about when the SQL that
runs is SQL you wrote, not SQL an ORM generated on your behalf. The cost is
that every query is hand-written; the benefit is that "what does this
endpoint actually ask the database for" is always answerable by reading one
function.

### The three-layer rule

Enforced by convention (there's no linter for it, so it lives in
`ARCHITECTURE.md` and in how PRs get reviewed):

```
routers/**       auth + request validation + HTTP status codes. No SQL.
services/**      pure logic. No DB access. Unit-testable with zero network.
repositories/**  SQL, and only SQL. Connection-agnostic (takes a connection,
                 doesn't open one).
```

If you're adding a feature and find yourself writing SQL inside a router, or
opening a database connection inside a service, that's the signal you're
fighting the grain of the codebase — move it to a repository.

### Two kinds of database connection

`backend/repositories/pool.py` (or wherever the connection helpers live)
exposes two entry points, and which one a piece of code uses is a real
security decision, not a style choice:

- **`rls_connection(user_id)`** — sets the Postgres session so RLS policies
  see that user as `auth.uid()`. Use this for anything acting *as* a
  specific learner. The database itself refuses to leak another user's rows,
  even if the query above it has a bug.
- **`privileged_connection()`** — bypasses RLS. Only used after the *router*
  has already checked the caller's role (admin, reviewer, etc.) — the
  privilege check happens in application code before this connection is ever
  opened. Grep for `privileged_connection(` before trusting a new endpoint;
  if it's called without a preceding role check, that's a bug worth finding
  immediately.

### Auth: Supabase JWTs, verified locally

The frontend gets a JWT from Supabase Auth (GoTrue) on sign-in. The backend
never calls out to Supabase to verify it — it verifies the signature itself
with `PyJWT` + `cryptography` (ES256/RS256) against Supabase's public keys.
This means auth verification has no per-request network dependency on
Supabase; it's a pure crypto check.

### Migrations are the owner's, not the agent's

**No agent — including Claude Code sessions — runs `supabase db push`.**
Migrations are applied by you. This means any code that reads a table or
column added in a migration that hasn't landed yet must degrade rather than
crash: probe first (`to_regclass`, `information_schema.columns`, or catch
`asyncpg.exceptions.UndefinedTableError` / `UndefinedColumnError`) and fall
back to "feature not available yet" rather than a 500. This matters most on
hot paths — the profile endpoint loads on every page view, so an unguarded
new column there takes down the *whole app*, not just one setting (this
already happened once — the `is_visible` outage, see
`docs/decisions/0001-probe-tables-instead-of-catching-errors.md`).

The corollary: seeded/default values always use `ON CONFLICT DO NOTHING`,
never `DO UPDATE` — a migration that gets re-applied (or a seed script that
gets re-run) must never stomp a value you've since changed by hand.

### Optional profile columns: ask, never catch

`user_profiles` grows a column every time a per-account setting is added,
and migrations are owner-applied, so the code routinely runs against a
database that is one migration behind. `backend/routers/auth.py` handles
that by **asking `information_schema.columns` which optional columns
exist** and building the SELECT and the upsert to match
(`_present_profile_columns`, `_profile_column_plan`,
`_OPTIONAL_PROFILE_FIELDS`).

It is worth knowing *why* it is a probe and not a try/except. The obvious
shape — try the wide query, catch `UndefinedColumnError`, retry a narrower
one — **does not work here**: `rls_connection` runs everything inside one
explicit transaction (the RLS claims are transaction-scoped, so it has to),
and a statement that errors aborts that transaction. The retry then raises
`InFailedSQLTransactionError`, which nothing catches, on the endpoint that
renders every page. That is `docs/decisions/0001-probe-tables-instead-of-
catching-errors.md` in one paragraph, and the profile endpoint carried the
broken version of it until the gloss setting was added and it was measured.

If you add a per-account setting: add the column to
`_OPTIONAL_PROFILE_FIELDS` with its SQL default and to the matching
defaults dict, and both the read and the write handle a database without it.

### When you must catch instead: `savepoint(conn)`

The probe is the right shape for the profile endpoint, but the codebase
had thirty-six other places with the try/catch-and-retry shape — readiness,
the dashboard, the tutor, the seeders — and one of them is what 500ed
`/api/review/readiness` on the deployed app. Rewriting every one as a probe
was not worth it; what they needed was for the retry to run on a live
transaction. `backend/repositories/pool.py` now has `savepoint(conn)`:

```python
try:
    async with savepoint(conn):
        rows = await conn.fetch(<wide SELECT>)
except UndefinedColumnError:
    rows = await conn.fetch(<narrow SELECT>)   # the transaction is still alive
```

asyncpg's nested `transaction()` emits `SAVEPOINT` / `RELEASE`, and on an
exception `ROLLBACK TO SAVEPOINT`, which returns the outer transaction to
the state it was in before the failed statement — RLS claims included.
Outside a transaction it is just a transaction, so the same code is safe on
a bare pooled connection. `backend/tests/integration/test_savepoint_integration.py`
pins all three facts: the privileged path commits, the RLS path still sees
`auth.uid()` after the rollback, and the retry *without* the savepoint
raises `InFailedSQLTransactionError` (so nobody can quietly remove it).

Two rules that go with it. Ask first when you can (`to_regclass`,
`information_schema`) — a probe costs one cheap statement and reads as what
it is. And in unit tests, a mocked connection needs `transaction()` to
return an async context manager: use `mock_conn()` / `FakeTransaction` from
`backend/tests/fakes.py` rather than `AsyncMock()`, whose `transaction()`
returns a coroutine and fails at `async with`.

### Endpoints on the page-load path never 500

Two endpoints are called on every app load: `/api/review/readiness` and
`/api/contribute/notifications` (the staff bell). Both now degrade instead
of erroring. Readiness returns `_readiness_open()` — every lane open,
`degraded: true` — if anything in the gate calculation raises, because the
worst case of a wrong "open" is an English card, while the worst case of a
500 is a learner who cannot start. The bell catches `_BELL_DEGRADES`, which
includes builtin `TimeoutError`: the pool's `command_timeout` (30 s)
surfaces as `asyncio.TimeoutError`, not as a `PostgresError`, so a catch
written for Postgres errors alone let the roll-up timeout straight through.

### AI integration: maker-checker, everywhere

Every place the app uses Claude to produce learner-facing content follows
the same pattern: **AI output lands as provisional, never auto-published.**
A `source` (or `level_source`, `topic_source`, `explanation_source`) column
records that a row came from `'ai'`; it's either surfaced immediately under
a language's publish policy (`ai_ok` / `all`) or held for a human to approve
(`strict`, the default). See `docs/review-workflow.md` for the full
maker→checker→publish flow, and `docs/content-visibility.md` for exactly
which two independent signals (`reviewed`, `ai_check_status`) gate what a
learner sees.

`resolve_model(task, language_code, override=...)` is the one place model
selection happens — it picks the right Claude model per task and per
language (some languages are pinned to a specific model because it performs
measurably better on them), with an admin-settable per-language override.
If you're ever tempted to hardcode a model string in a new feature, this
function is why you shouldn't.

### SRS: FSRS, not SM-2

The scheduler is **FSRS** (Free Spaced Repetition Scheduler) —
`backend/services/fsrs.py`, `fsrs_weights.py`, `fsrs_optimizer.py`,
`srs_stages.py` — with per-user, per-language weight fitting via an
`scipy`/`numpy` L-BFGS-B optimizer against each learner's own review
history. This is worth knowing explicitly because `README.md` still says
"SM-2 scheduling" (a much simpler, non-personalized algorithm) — that's
stale, not a second scheduler; see `DEBT.md`.

### NLP: one backend per language family, chosen on measured accuracy

Answer grading is per-language and morphology-aware — it coaches on a
missing diacritic rather than failing the answer outright, which is the
single most distinctive thing about the product (see
`ARCHITECTURE.md`'s "decisions worth knowing about"). The backends:
`pymorphy3` (Russian), `spacy` + `lemminflect` (English — `spacy` needs a
separate `en_core_web_sm` model download, not just a pip install),
`nltk`/WordNet (English seeder only, not grading), `cyrtranslit`
(Cyrillic↔Latin transliteration).

Two language families get **lookup-based romanization** instead of a
computed one, because a computed romanizer drops information a learner
needs: `backend/services/nlp/thai_reading.py` (RTGS + a Paiboon-derived tone
line, since Thai is tonal and RTGS alone doesn't carry tone) and
`backend/services/nlp/semitic_reading.py` (Hebrew/Persian/Arabic, since
their scripts drop vowels a reading needs — see
`docs/decisions/2026-08-26-owner-decisions.md` items 3–4 for why this
replaced an earlier "can't be computed, so skip it" stance). Both were
reached the same way: a computed approach was tried, measured, and rejected
in favor of a dictionary lookup.

`camel-tools` (full Arabic morphological analysis, for grading) stays an
**optional** extra, not installed by default — it pulls in `torch` +
`transformers` (~4GB), which has previously blown a DigitalOcean build
machine's disk during a real deploy. Arabic grading falls back to a
diacritic-folding heuristic (`ArabicNLP`) behind a guarded import. This is
independent of Arabic *romanization*, which works today via
`semitic_reading.py`'s lookup and needs none of that weight.

### Billing: built, wired, deliberately inert

The `stripe` SDK integration is complete but sits behind a single master
flag, `app_flags.monetization`, which **ships OFF by default**. This isn't a
half-finished feature — it's a fully-built one the owner has chosen not to
switch on yet (see `DEBT.md` for the reason). `services/flags.py`'s
`monetization_enabled()` is the one function every payment-adjacent surface
checks, and it fails safe (`default=False`) even if the flag row's own
migration hasn't landed.

### Rate limiting

In-process by default; becomes cross-instance via `redis` when `REDIS_URL`
is set. One gotcha worth remembering if you ever see intermittent,
order-dependent test failures touching rate limits: an async Redis client
cached against one event loop silently breaks when read from a different
one, and each test client / uvicorn worker gets its own loop. This has
already caused real (and initially confusing) test failures — see
`DEBT.md`.

### Content visibility: one function, not twenty-one copies

`backend/services/visibility.py` is the single source of truth for "can this
learner see this content." It used to be hand-copied into 21 different SQL
queries; now every one of them calls the same helper. `normalize_policy`
maps any value it doesn't recognize (a typo, a legacy spelling) to the
*strictest* policy — fail closed, not open. Full detail:
`docs/content-visibility.md`.

---

### Review queues: one taxonomy table, many surfaces

`frontend/src/lib/reviewTaxonomy.ts` is the single table describing every
review queue — where its items come from (`origin`), who may act on them
(`audience`), and which Review-tab panel acts on them (`panel`). The Review
Inbox, the staff notification bell, the focused-queue view, and
`docs/review-workflow.md`'s tables all render from it, so a queue can never
be described one way in the bell and another in the inbox. Add a queue by
adding a row here first.

Two conventions built on top of it:

- **Focus mode** — a tile scopes the whole Review tab to one queue
  (`?queue=<panel>` in the URL, so it is linkable and bookmarkable), and
  inside it `useFocusList` steps through items one at a time with ‹ › and
  the arrow keys. The hook returns *a slice plus a nav element* rather than
  wrapping the panel, so each panel keeps rendering its own card, actions
  and all — focus mode is the same card one at a time, never a second
  rendering that can drift from the list one.
- **Card context on a review item** — a change request stores only
  `target_type` + a nullable `target_id`, so `load_cards` in
  `repositories/change_requests.py` resolves those into the live row
  (sentence, answer, hint, translation, plus what situates it) and the board
  renders the whole card, not a label. It groups by target type, so a board
  of 200 rows over four kinds costs four queries. Three target kinds
  (`tutor_message`, `reading`, `other`) have no stored row by design — a
  tutor reply is generated per learner and never saved, so the quote
  captured at flag time IS the record — and they degrade to that quote
  rather than erroring. A card deleted since the request was raised also
  resolves to nothing, which the board says out loud.
- **`QueueHelp` / `QUEUE_HELP`** — the "what does this button actually do"
  hover for each queue, written to three beats (what these items are, who
  can act, and what each action *does*). It exists because "Resolve" reads
  as "mark it done" while in several panels the underlying action deletes
  the row, and nothing on screen said which.

### The first-session gate ("trailblazer" wait), and the live swap

A learner whose support locale isn't English may arrive before the course's
cards have been translated into it (the `auto_translate_loop` fills them
progressively). `session_readiness` in `backend/repositories/cards.py` is
what decides whether to show the waiting room (`TrailblazerWait.tsx`, with
its match game and trivia) or start the session. The rule, after the owner
found the original version stalling people:

- **Only a learner who is new to the course waits.** `new_here` is "no
  `user_cards` row for this language that is unsuspended or has ever been
  reviewed" (learn cards are inserted suspended until the batch is
  confirmed, so a half-finished first lesson still counts as new). A
  returning learner's lanes are always `ready_enough`, whatever the
  translation percentage.
- **The gate opens on the first ready card** (`START_CARDS = 1`), not on a
  percentage of the batch. Example sentences are the bulk of the text and
  are translated last, so a batch percentage kept people waiting long after
  something playable existed.
- **The rest arrives while they study, in reading order.** The readiness
  call (`GET /api/review/readiness`) runs `fill_start_batch` in
  `backend/services/auto_translate.py` as a background task. It walks the
  *whole* session — grammar and vocab cards interleaved exactly as the
  session serves them (`_interleave_typed`, the same order `add_learn_batch`
  uses) — and for each chunk translates, in this order, the words, the
  grammar titles (`pending_grammar_meta`), the explanations, the example
  sentences and the drills, before moving to the next chunk. The first
  chunk is two cards (`INLINE_FILL_FIRST`) so the gate opens fast; then
  six at a time (`INLINE_FILL_CHUNK`) up to 30 cards or 300 s
  (`INLINE_FILL_MAX_CARDS`, `INLINE_FILL_SECONDS`). Before this the inline
  fill translated only the first ≤ 8 words / ≤ 3 explanations / ≤ 8
  sentences and *no titles*; everything else waited for the 15-minute
  `auto_translate_loop`, which is why card two was English until the
  learner came back later. Each pass queries the *still-pending* rows of
  every card walked so far, so a row the provider rejected once rides
  again with the next pass instead of waiting for the sweep.
- **One fill per (user, language) at a time.** `_INLINE_FILLS` holds a
  status dict per pair (`running` / `done` / `error` / `no_provider`, with
  `landed` rows and `cards_done`). A running fill is never started twice,
  and a finished one is not re-run for 90 s. Readiness reports it as
  `fill`, so the wait screen can say *why* nothing is moving instead of
  guessing: `no_provider` (no `ANTHROPIC_API_KEY` on the web service) shows
  at once, `error` names itself once the stall window passes.
- **The frontend keeps re-arming the fill and swaps on a tick.** While a
  lane's `pct` is below 1, `LearnPage` and `ReviewSessionPage` re-fetch
  readiness every 15 s (`READINESS_POLL_MS`) — each poll re-arms the server
  fill if it has stopped — and every 10 s (`SWAP_POLL_MS`) *as well as on
  every advance* re-fetch the upcoming cards — `POST
  /api/review/lessons/refresh` for learn, `POST /api/review/due/refresh`
  (ids of the cards after the current one, ≤ 50) for review — and swap in
  whichever have gained a translation. The current card is never replaced
  under someone's fingers. Both are best-effort: a failed refresh leaves
  the English card.
- **The readiness call also queues the slow path.** Whenever either lane is
  below 1 it queues `pretranslate_upcoming` and `kick()`s the loop, so
  whatever the inline fill did not reach still lands eventually.

English (or no) support locale short-circuits all of this: `new_here` is
false and both lanes are open. The waiting room shows the count of cards
needed when the gate needs more than one; with a one-card gate it falls
back to the batch percentage so the bar visibly moves.

## Frontend

React 19 + Vite 6 + TypeScript (~5.7, project-graph mode via `tsc -b`) +
TanStack Query 5 + Zustand 5 + react-router-dom 7 + Tailwind CSS 4.

**`npm run build`, not `npx tsc --noEmit`, is the only trustworthy
type-check.** The build runs `tsc -b`, which type-checks the whole project
graph; `--noEmit` alone has already let four real type errors through into a
red CI once (a prefetch reading a field that doesn't exist on the type it
was given). This is codified in `CLAUDE.md` and matches what CI actually
runs (`.github/workflows/ci.yml`); it's worth knowing precisely because
`ARCHITECTURE.md` used to recommend the weaker command — now fixed, see
`DEBT.md` for the general pattern of doc drift to watch for.

Zustand stores worth knowing: `prefsStore` (study-language, UI preferences —
synced across devices, not just local), `authStore`, `viewAsStore` (an
admin's "view the app as this learner" mode).

Three locale concepts, kept deliberately separate — conflating any two of
them is the most common source of "why is this in the wrong language" bugs:

1. **The course being studied** (e.g. learning Russian).
2. **The "support locale"** the course is explained *in* — an overlay system
   where English is the eagerly-authored spine and other locales fill in by
   demand (`auto_translate.py`'s maker-checker sweep), never a pre-seeded
   full matrix. A field with no translation yet falls back to English.
3. **The UI/chrome language** (`user_profiles.ui_language`) — six locales
   (en, es, fr, pt, ru, ar; `ar` is RTL and flips the whole document
   direction). Detection order: explicit device choice → account's saved
   choice → browser's preferred languages → English. Deliberately never IP
   geolocation.

### Hint layers, and the gloss setting

`frontend/src/features/review/hintLayers.ts` owns the order in which a card
gives help away: reading → pronunciation → word-by-word gloss → translation →
the authored hint, with the reading step skipped for Latin-script courses.
Each press of Hint reveals one layer:

**The gloss is an opt-in account setting.** A gloss is a Leipzig
morphological decomposition (`bark.3SG`, `have.NEG`) — it answers *how is
this sentence built*, a structural question, not *what does it mean*.
Learners reported it as confusing and as not enough to guess a word from,
and meeting it unasked was the complaint, so `user_profiles.show_glosses`
(**OFF** by default) decides whether the layer is offered at all. The
`hintLayersFor` option defaults to off for the same reason: a caller that
forgets to pass it withholds unfamiliar notation rather than showing it. The filter is inside `hintLayersFor`, not at each call
site, so the setting holds on every surface that reveals a layer —
including whichever one is written next — and the hint dots shorten by one
rather than leaving a rung that reveals nothing.

The gloss carries an `InfoDot` explaining the notation — on the card and,
more importantly, on the Settings toggle, since that is where someone
decides whether they want it. It exists because `bark.3SG` means nothing
to someone who hasn't seen it, and the English
labels read as a bug rather than the deliberate choice they are (see
`docs/decisions/2026-08-26-owner-decisions.md` §5 — glosses are structural
on all 27 courses and their metalanguage is English *by design*, since the
value is the decomposition). The explanation itself is translated into all
six UI locales: a learner who cannot read the explanation is precisely the
learner it exists for.

`react-simple-keyboard` powers the on-screen keyboard for non-Latin/diacritic
input; `react-markdown` + `remark-gfm` render the tutor's chat; `@sentry/react`
is crash telemetry.

---

## Mobile

Capacitor 8.5, not React Native — the product was already mobile-first (a
bottom tab bar, safe-area insets, six UI locales, an on-screen keyboard), so
a React Native port would just re-implement the same screens a second time.
`frontend/` builds once; both `android/` and `ios/` are committed Capacitor
shells around the same bundle (`webDir: 'dist'`, no remote `server.url` — the
bundle ships inside the binary, which is also what App Store review
requires). The trade: **shipping a web change to the apps means shipping a
new build** — the web app updates on deploy, the apps update on store
review. Full detail, including what's still missing before a store
submission, is in `docs/native-apps.md`.

Offline support is a fully worked-out **design**, not yet built —
`docs/offline.md` is worth reading even though nothing in it exists yet,
because it explains precisely which two things (answer grading, FSRS
scheduling) are pure client-side computation and therefore genuinely
portable to a service worker + IndexedDB pack, versus what's permanently
online-only (anything that costs a model call).

---

## Testing

- **Backend**: `pytest` (`asyncio_mode = "auto"`) + `ruff`. Integration
  tests are gated behind `INTEGRATION_DATABASE_URL` and **skip silently**
  without it — a green "1400 passed, 95 skipped" run may have exercised zero
  SQL. Always set it before trusting a result that touches the database; see
  `CLAUDE.md` for the exact local commands (Postgres + Redis on non-default
  ports, so they don't collide with anything else running).
- **Frontend**: `vitest` for unit/component tests, `npm run build` as the
  real type-check (see above).
- **A standing risk class worth knowing about**: a unit test's mock can
  "agree with a bug" if its return shape doesn't match what the real
  repository function actually returns. This caused one real production
  500 (the assign-by-email bug, since fixed) where a mock returned a dict
  and the real function returned a bare string. Mocks are only as good as
  their fidelity to the real shape — when in doubt, prefer the integration
  test that hits real Postgres over a mocked unit test for anything
  touching a repository's return type.

---

## Deployment

DigitalOcean App Platform, `Dockerfile` at the repo root. One quirk worth
remembering if a feature ever seems to hang under load: DO's egress can't
always reach Supabase's HTTP/Storage APIs directly (connections hang until
timeout on some paths) — worked around with tight timeouts and a cooldown
circuit-breaker (see `backend/routers/audio.py`'s TTS storage upload path
for the pattern; anything uploading to Supabase Storage from the backend
should probably use the same shape).

Background loops run in-process from `backend/main.py`'s app lifespan (all
never-raise, all cancelled cleanly on shutdown): `reminder_loop` (15 min,
review reminders), `digest_loop` (1 hour, weekly digest + admin ops digest),
`auto_translate_loop` (15 min, fills missing support-locale text),
`_check_schema` (once at boot — logs loudly if the code is ahead of the
applied migrations, which is your early warning that a `supabase db push` is
overdue).

### Knowing what the server is running

`/api/health` returns `{"status": "ok", "build": {...}}` — `sha`,
`built_at`, `latest_migration` — from `backend/services/build_info.py`.
`built_at` is written by the image build (`/app/BUILD_TIME`), not at boot,
so a restart of an old image cannot look like a deploy. `sha` is the
`BUILD_SHA` env (Dockerfile `ARG GIT_SHA`) or `.git` when running from a
checkout; DigitalOcean passes no commit by default, so on production it is
usually null and `built_at` is the identifying fact. `latest_migration` is
the newest file in the image's `supabase/migrations` — the migration files
now ship in the image precisely so `/api/health/schema` has something to
diff against the live database (it used to report `ok: true`
unconditionally because `.dockerignore` excluded them; it now returns an
error when it has no expectations, rather than a hollow ok).

The same three facts plus the schema diff are in the app: **Settings →
Admin → Deployment** (`DeploymentPanel.tsx`). When "I don't see the
setting" comes up, read that panel first — it distinguishes "not deployed
yet" from "deployed, migration not applied" from "a real bug" without a
terminal.

See `docs/database.md` for exactly how portable this all is if you ever
wanted to leave Supabase — short version: the schema and RLS are portable
today (plain SQL, no Supabase-only schemas, verified in CI against a
throwaway Postgres); the one real lock-in is sign-in (GoTrue).
