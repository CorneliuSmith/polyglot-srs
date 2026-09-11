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

### What `command_timeout` bounds — and what it does not

asyncpg's `connect(..., command_timeout=N)` bounds one thing: how long a
single statement may wait for its reply. Every runbook content tool sets it
— the seven modules in `GUARDED` in `test_seeder_command_timeout.py`, via
`COMMAND_TIMEOUT` (300 s) in `backend/services/seeder/base.py` — because
the Supabase pooler can drop the server side of a session while the TCP
socket stays ESTABLISHED, and without a bound the client sleeps for ever —
that was the 7 Sep 2026 two-hour hang. (The API-key tools do not set it;
DEBT.md says why that is tolerated.)

What happens when it fires is worth understanding, because it is where the
first fix stopped short — twice. On timeout asyncpg does not just raise: it
sends a **cancel request**, which in the Postgres wire protocol is a
*second* connection to the server carrying the session's secret key, and it
parks a waiter that resolves when the server answers the cancelled
statement. Two things then wait on that waiter with no timeout of their
own. `Connection.close()` — the thing the seeder's `finally` calls — awaits
it *before* it looks at its own `timeout` argument. And so does **every
later statement on the same connection**, before it arms its own
`command_timeout`. On a healthy server the answer arrives in milliseconds
and nobody notices. On a dropped session it never arrives: the statement
raised `TimeoutError` after five minutes and the close hung for ever behind
it; or — if the timed-out statement was the audit INSERT, whose error
`log_change` used to swallow — the next statement hung with no timeout and
no error at all. The timeout had moved the hang, not removed it; both were
measured on 9–10 Sep 2026 with a proxy that swallows server→client bytes
(`test_dropped_session_integration.py`).

The pattern that returns is **bounded close, then tear down the socket by
hand** (`close_quietly`): `asyncio.wait_for(conn.close(), CLOSE_TIMEOUT)`
cancels the close from outside — asyncpg catches the cancellation and marks
the connection aborted — and then the transport captured *before* the close
is aborted explicitly. The explicit step matters: asyncpg's `close()` sets a
`closing` flag before it waits, its `abort()` is a no-op once that flag is
set, and `terminate()` goes through `abort()`, so without it the Python
object says closed while the TCP session stays open for the life of the
process. The general shape: a library's polite shutdown may itself wait on
the peer, so the operation's timeout and the cleanup's timeout are two
different guards, a `finally` that can block needs its own, and "closed"
is a claim to verify at the socket, not at the object. The seeder swallows
errors in that `finally` on purpose — the exception worth seeing is the one
that got us there, not "and the close failed too".

The corollary for `log_change`: "best-effort" is about the audit table,
not the session. It still swallows an audit-table error (the migration may
not have landed), and now re-raises the dead-session shapes
(`audit.DEAD_SESSION`), because a connection that cannot carry the audit
write cannot carry the content write after it either — it can only hang
on it.

The other half is retry. A pooler that drops one session usually refuses
new ones for a while (about a minute on 10 Sep 2026), so `seed_grammar`
retries a course's write after 10 s and again after 60 s — long enough,
together, to outlast that minute — re-using the data it already
transformed. That is safe for content because every content statement is
an upsert: the second attempt completes a half-written course rather than
doubling it. It is not quite safe for the audit log — a curated point whose
proposal is re-walked gets a second `suggested` entry — which is the same
duplicate a manual rerun has always written and is tolerated for that
reason. Retrying the *transform* would be wrong — a paradigm gap is a file
error and retrying it just delays the same failure.

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

The rules the generation prompts share live in `services/quality_rules.py`:
the set-variety charter, the CEFR bar (`level_bar`) that the makers write
to and the auditors judge by — one sentence, quoted by both, so the two
cannot drift — and `language_brief`, the per-language tutor brief
(`tutor_skills/<code>/SKILL.md`) appended to the drill and example makers
the way the semantic reviewer and the seeders already had it. The 42-rule
digest in `.claude/skills/quality-rules/` is deliberately NOT read at
runtime: it governs the sessions that clean data; rules move from it into
`quality_rules.py` one at a time, as short mechanical statements.

The tutor's per-language knowledge is a skill bundle,
`tutor_skills/<code>/`: `SKILL.md` rides in every prompt (kept under 2,500
chars by test), `REFERENCE.md` and `ERRORS.md` load on demand through the
`consult_reference` tool. Two of the three are now maintained by code.
`REFERENCE.md` is **generated** from `data/grammar/<code>_grammar.json` by
`services/tutor_reference.py` (`python -m backend.services.tutor_reference`;
`--check` in CI via `tests/test_tutor_reference.py`), so the tutor's map of
the course cannot drift from the deck — it had, for 22 of 27 languages.
`ERRORS.md` stays a human's document, but `scripts/tutor_skill_digest.py
<code>` digests the language's quality standard (`docs/quality/<code>.md`)
and open review notes into `ERRORS.extracted.md` for folding in, and stamps
it with the standard's content hash; `tests/test_tutor_skill_digest.py`
fails when a standard changes after its tutor's last digest, or lists the
language in `NEVER_DIGESTED` until its first one. That test is the answer
to "are the personas being updated with the language insights", made
mechanical.

Card text (grammar explanations, culture and function notes) is plain text
typeset by `components/ExplanationView.tsx` — term/gloss tables, arrow
derivations, label:forms chips — and, since 4 Sep 2026, **markdown when a
block carries markdown syntax**: `hasMarkdown` routes a blank-line block
with bold (`**`), a list, a table, inline code or a link to
`components/CardMarkdown.tsx`, which is react-markdown + remark-gfm +
rehype-sanitize on a small allow-list (no raw HTML, no images, no
headings). Plain blocks are untouched, so nothing in the existing corpus
moved; `backend/tests/test_content_markdown_guard.py` pins the seed at
zero markers so a marker in data/ is a deliberate entry in its `ALLOWED`
set. The server cleans the same column on the way in
(`services/markdown.py`: raw tags out, unsafe link schemes out) at the
editor and the AI generator — **not** in `seed_grammar.py`, which trusts
the committed file; a script that writes markdown into `data/grammar/`
must call `clean_markdown` itself (the markdown-explanations plan does) —
because the renderer is the last line, not the only one. And only
`explanation` renders markdown: culture and function notes are plain
text on every surface. Underscores are never a signal: "___" is how the
cards write a blank.

The append-only AI tables are pruned daily by `services/retention.py`
(`tutor_sessions` after 180 days, `tutor_usage` after 13 months — above
every window a reader uses), a lifespan task like the reminder and digest
loops, switched by `retention_sweep_enabled`.

The tier rule is in `services/models.py`'s `TASK_MODELS`: a `*_maker` drafts
on the configured chat model, its `*_checker` verifies one tier up
(`tutor_model_low_resource`), and `resolve_model` refuses per-language
overrides on checker fields so no admin dial can lower the floor. The
locale-translation lane has its own `translate_checker` task for the same
reason — until 3 Sep 2026 it shared `translate` with the maker and checked
Sonnet with Sonnet.

Every rejected rendering has a review row, whatever layer it belongs to.
Word glosses go to `translation_reviews`; drill lines and hints, grammar
explanations, grammar titles and notes, and example-sentence meanings go
to `translation_review_items` (keyed by kind, target, locale and field),
written by the same functions in `services/auto_translate.py` that would
have stored a pass. Both carry the maker's proposal even when the checker
refused it — a queue with nothing to approve is a bin, not a review — and
both surface in one admin panel ("AI translations", grouped by kind) and
one inbox count: the item count is folded into the `ai_translations` key
on the way out (`fold_counts` in `repositories/contributor.py`), so the
client sees one number for one panel. Approving writes the row's own layer
with `reviewed = true`; rejecting clears the row and the layer keeps its
English fallback until a later sweep tries again. The writers probe for
the table and skip the queue without it, so a deploy ahead of the owner's
migration behaves exactly as it did before.

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

### Plans: four options, one subscription

A plan is two decisions — **which languages** (`plan_scope`: single / all)
and **whether AI is included** (`plan_ai`) — and the four combinations are
the four options the app sells (owner: "Make the 4 options … Single
language with AI should be the default but provide options to upgrade").
`PlanPicker.tsx` renders them, Single + AI preselected, in onboarding and
under Settings → Plan ("Change plan").

- **One Stripe subscription per option.** `create_plan_checkout_session`
  builds a Checkout with the scope's Price and, for an AI option, the
  add-on's Price as a second line item; Stripe makes them one subscription
  with one charge. Both Prices must bill monthly. The session and the
  subscription carry `metadata.ai = "1" | "0"`, so the webhook records both
  halves: `set_plan_subscription(..., ai=…)` writes `plan_scope` and
  `plan_ai` (+ `plan_ai_subscription_id`) on the profile.
- **Prices and pools are never hardcoded.** `/api/billing/plan/prices`
  returns the three Stripe prices (`single`, `all`, `ai_addon`) and the
  admin-set message pools; the picker adds the two halves up
  (`optionPrice`) and says what each option includes.
- **Upgrades are new subscriptions.** Checkout only creates, so a change of
  option is a fresh subscription, and the webhook — after the new plan has
  landed — cancels the one it replaced (`cancel_subscription`, prorated).
  "Add AI" on a plan bought without it is the stand-alone add-on
  (`/api/billing/checkout`, `metadata.kind='ai'`), its own subscription,
  which sets `plan_ai` and is the only thing that can clear it.
- **Once money is on, a plan tier must be backed.** `user_profiles.plan_scope`
  defaults to `'all'`, so `get_tutor_access` also reports `plan_backed`
  (an active `plan_subscriptions` row — paid, dev-mock, admin-free, or the
  admin's plan override), and `get_allowance` ignores an unbacked scope
  while `monetization` is on. While it is off, the column is honoured as it
  always was: beta accounts chose a scope with no way to pay and keep it.
  Onboarding stops writing the scope once plans are priced — the choice
  goes through Checkout and only the webhook records what was bought.
- **Legacy per-language AI** (`tutor_entitlements`, one row per language)
  is still honoured by the allowance so nothing bought earlier loses its
  pool; nothing new writes it.

### The tutor's memory, and its bounds

Between sessions the tutor keeps a global profile and a per-language
profile (JSONB, every fact tagged `stated` or `inferred` in `_sources`), a
rolling `session_summary` the post-session summarizer *rewrites*, and an
append-only `tutor_sessions` log; it re-queries the 12 weakest SRS items
every turn. In-session history is the last 40 messages, truncated.

Since 3 Sep 2026 the profile is bounded (`services/tutor.py`): a
list-valued fact keeps its newest five (`MAX_FACT_VALUES`); a scope holds
at most 40 facts (`MAX_PROFILE_FACTS`), the oldest *inferred* one evicted
first by the `_touched` clock — a fact the learner stated, or an identity
key, is never evicted; the summary is capped on write
(`truncate_summary`, at a sentence boundary); and `build_system_blocks`
runs `bound_memory` over block 1 with a character budget
(`MEMORY_CHAR_BUDGET`), trimming the summary's tail, then old inferred
facts, then list tails, and logging how much it cut — that log is how the
constants get tuned. Settings → "What your tutor remembers" now shows the
summary and the focus list and offers *Forget this language* / *Forget
everything* (`DELETE /api/tutor/memory/all`); past session records are
history and stay.

### The AI allowance, and what "entitled" means

`services/allowance.py`'s `get_allowance(user, language)` is the one place
the tutor's monthly pool is computed: an admin override first (`blocked`
zeroes everything, `enabled` grants a capped pool), then operator free
access (`TUTOR_FREE_ACCESS`, unlimited), then the plan's base (free 20,
single 0, all 300 — editable at runtime in Settings → Admin → Plan
limits), plus the Tutor+ add-on and any one-time top-ups, all in one
calendar-month window. The tutor itself only asks "is there anything
left" (`reject_if_unavailable`).

`entitled` is a separate answer for the perks that spend from the pool
without being the tutor — recommendations and the weekly digest. It means
*the month's pool holds paid-for AI*: any tier but free, with a limit above
zero. It used to mean "tier is plus or granted", which refused the
all-languages plan — the plan whose 300 messages are exactly what those
perks draw on — and a reviewer on that plan read the amber "needs a Plus
subscription" note as being blocked. The free tier's twenty is a taster,
not a pool; single's base is 0 until a top-up or the add-on is bought,
which is why the rule reads the limit and not the tier name.

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
- **Focus mode has verbs as well as arrows.** `useFocusList` takes an
  optional `actions(item)` list — `a` accept/approve, `r` reject/resolve
  /dismiss, `u`/`d` vote — rendered as keycaps in the nav and bound on
  the same listener as the arrows (ignored while typing). Acting removes
  the item and the next slides in, so a queue is cleared from the
  keyboard. `ReviewedCardView` carries a History toggle (`CardHistory`,
  roll-back included) for every kind the history endpoint serves.
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

  Every queue that names a card carries it now, under the same
  `target_type` / `target_id` names: learner feedback, AI translations,
  review notes, suggestions and tester recommendations each map their own
  kind to the loader's (`grammar` → `grammar_point`, `example` →
  `example_sentence`) and get the same best-effort `load_cards` pass. One
  component renders all of them.
- **Editing the card from the queue** — `ReviewedCardView.tsx` shows the
  card and, for anyone with a contributor role, edits it in place:
  `PUT /api/contribute/review/card/{target_type}/{target_id}`, dispatched by
  `edit_reviewed_card` in `repositories/contributor.py`. The verdict on a
  learner report is usually "yes, and here is the correction", and that used
  to mean leaving the queue for the content editor and finding the same card
  again by search.

  The write side mirrors `_CARD_SQL`'s read side and routes each kind into
  the editor that already owns its semantics — a drill edit de-certifies its
  point, an example edit stamps provenance, an explanation edit re-enters
  the review pool — so an edit made from a queue is indistinguishable from
  one made in the content editor, audit row included. Two deliberate holes:
  a word's own text is never rewritten in place (every `user_cards` row,
  clip and example points at that row, so a rename would silently re-target
  all of them), and only the fields the editor actually offered are sent
  (`exclude_unset`), so a two-box editor cannot blank the other two. What a
  vocabulary edit writes is the **English** definition — the source every
  support locale is translated from, so a correction there propagates
  instead of fixing one locale and leaving the next to inherit the fault.
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
- **One fill per (user, language) at a time — and it absorbs what
  arrives while it runs.** `_INLINE_FILLS` holds a status dict per pair
  (`running` / `done` / `error` / `no_provider`, with `landed` rows,
  `cards_done`, the cards `walked` and any `extra` handed over). A running
  fill is never started twice: a call that lands while one runs appends
  its cards to `extra`, and the running fill walks them after its own,
  inside the same time budget. That is the learn-page poll starting the
  learn batch and the learner opening a review session seconds later — the
  review batch used to bounce off the in-flight guard, then off the
  cooldown, and stayed English until a sweep. The 90 s cooldown after a
  finished fill skips only cards that fill already walked (a refresh of
  the same batch); a batch it never saw runs at once. An `error` fill stays
  down for the whole cooldown whatever is asked, so a failing provider is
  not hit on every poll. Readiness reports the entry as `fill`, so the wait
  screen can say *why* nothing is moving: `no_provider` (no
  `ANTHROPIC_API_KEY` on the web service) shows at once, `error` names
  itself once the stall window passes.
- **What is pending is exactly what is served.** Every fill predicate —
  the demand detectors, the `pending_*` queries, `_still_pending`, the
  readiness score and the status counts — must ask the same question the
  card read asks, or a row can be on a learner's screen in English and, to
  every lane, not work. Two shapes of that bug have shipped: example
  sentences were filled only when `reviewed`, while the review page also
  serves generated sentences on an `ai_ok` / `all` course (now one clause,
  `services/visibility.served_example_sql`, and the locale sibling inherits
  its source's review state instead of being promoted to reviewed); and
  the drill demand detector asked "is there an overlay row?" while
  `pending_drills` asks field by field, so a drill whose hint rendered but
  whose translation the checker refused was never demanded again. When a
  serve-side predicate changes, grep for the fill side in the same PR.
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

### Write: reading handwriting with a model, measuring it on the device

Write (`/write`, `docs/plans/handwriting.md`) is the production feature
beside Speak: the learner writes by hand on a canvas and asks whether it
is correct and legible. Phase 1 — *Free write* — ships for every course
because it needs no authored content. Three parts, deliberately separate:

- **The canvas** (`features/write/InkCanvas.tsx`) records strokes as point
  lists in CSS pixels through pointer events — one API for finger, mouse
  and pen — with `touch-action: none` so a phone draws instead of
  scrolling. The ink model (`ink.ts`) is shared by everything below; a
  tap or an empty canvas fails `hasInk` and nothing is ever sent.
- **Neatness** (`neatness.ts`) is measured from the strokes on the device:
  strokes are clustered into letters or joined runs by horizontal
  proximity (a gap under 15 % of the median letter height is the same
  letter), then four ratios of the learner's own writing size — baseline
  drift and wobble, height consistency, slant consistency (principal axis
  of the tall strokes), gap regularity — each graded steady / uneven /
  wandering. Exact, free, offline, and the same verdict on a phone and a
  monitor. It needs three clusters to say anything.
- **The reader** (`services/write_assess.py`, `POST /api/write/assess`)
  renders the ink to a clean PNG (`inkExport.ts`: white ground, black
  ink, tight crop, upscaled) and asks a vision-capable model — task
  `write_assess`, the chat tier, per-language override honoured — for a
  tool-shaped answer: transcription first, then match, word diffs,
  legibility 1–5, at most two letterform notes, and its own confidence.
  The transcription is always shown: a misread must look like a misread,
  not a fail, and *low* confidence is rendered as "not sure I read that
  right" rather than as wrong. One assessment is one message on the AI
  allowance, logged `tutor_usage.kind='write'`, behind the tutor chat
  rate limiter; the verdict is logged to `writing_attempts` (migration
  20261018, probed) and **the ink never is** — the same rule as Speak's
  audio.

**The reader learns the writer's hand** (§11 of the plan; migration
20261019, probed). Three things, all the learner's own and all deleted by
the Account toggle *Adapt to my handwriting* or its Reset:

- **Samples** (`writing_samples`) — up to twelve per language of the
  writer's own canvases: the PNG, the text it reads, and *how it was
  made*: the strokes, compacted to ≤ 64 integer `[x, y, t]` points each,
  and a method summary (`services/ink_method.py`: stroke count, lifts,
  joined runs, dominant direction, right-to-left, duration, speed). A
  sample is kept when the writer **confirms** a reading (`POST
  /api/write/confirm`, free — no model call), or when the reader was sure
  and right; never from a low-confidence read, which would teach the
  wrong hand. Up to three ride along with every Check as reference images
  ("this writer's own hand, confirmed; it reads X; written in 3 strokes
  with the pen lifted…"), confirmed first.
- **Habits** (`writing_profiles.habits`) — per letter: the reader's last
  note, how often it recurred, and whether the writer confirmed the form
  legible. Confirmed forms are passed to the reader as *known — do not
  flag*; the rest are the material for the recurring-note count and the
  Progress trend (Phase B).
- **The method told to the reader** — the current canvas's own method
  line goes into the request as fact ("written in 4 strokes, pen lifted
  between strokes, mostly running down, over 2.1 s"), because a hamza
  drawn as its own stroke or an alif drawn bottom-to-top is something the
  picture can only guess at.

The confirm button appears only when the reader could be wrong — a miss,
a low-confidence read, or free writing with no expected text (where the
reading is editable). With the toggle off, or before the migration, every
call is exactly the Phase 1 call and nothing is kept.

**The writer's verdict is the ground truth** (§12.1). A confirmation
carries what the reader had said (`read`); the server aligns it with
what the writer says they wrote (`services/write_diff.py`: letters with
their combining marks as one unit, `difflib` alignment, so "й read as и"
is one misread and a hamza-less alif is one, not a missing mark) and
records *right* or *wrong* with every misread letter counted against the
letter actually written. A sure, matching Check counts as right on its
own. From those counts come the **readout** — "the reader gets your hand
right N of M times" and the five letters it trips on — shown on the Write
page after a confirmation, in Account under the toggle, and on the
Progress page with a legibility strip of the last checks
(`writing_profiles.stats.history`). Habits are counted back too: a
letter the reader has noted before is marked "again — 3×" in the notes,
so a habit reads as a habit and not as a fresh discovery. Staff see the
same per course — writers, right, wrong, accuracy, mean legibility,
letters to watch — in Workspace → Insights (`GET
/api/contribute/analytics/handwriting`), which is the signal for which
scripts the reader is weak on before anyone complains.

**The baseline session** (§12.2; `services/write_coverage.py`,
`GET /api/write/baseline`, `POST /api/write/baseline/done`). "Set up my
hand" — offered on Write and from Account — asks for eight short lines,
each written in the writer's usual hand and confirmed as such; the eight
land as confirmed samples marked `source = 'baseline'`, preferred as
references and replaced by a redo. The lines are a greedy set cover over
the course's served A1/A2 sentences against the script's *coverage
units*: a letter (case-folded for Cyrillic and Greek, so Ф covers ф);
for Arabic and Persian a letter **and its positional form**, decided by
whether the neighbours join (the six right-joining-only letters and the
hamza forms take no initial or medial); for Hangul the jamo of each
block, keyed by letter name so a final ㄴ and an initial ㄴ are one
unit; for a Latin-script course, whatever letters its own pool uses. A
speaker-reviewed exemplar set (§5) will replace the greedy pick per
script when it exists. One baseline per language per day, so it cannot
become unlimited spend; the end stamps `stats.baseline_at` and the
coverage reached, the zero point for the Progress trend and for the
personal neatness of Phase D.

Prompts come from content the app already holds (`repositories/write.py`):
a sentence is an example line with its meaning in the learner's support
locale (own cards first, then the course's A1/A2 lines), a word is one of
their own cards, or they type their own text, or write nothing in
particular. The compare view renders the expected text in a
handwriting-style Google face per script (`handFont.ts`, loaded on
demand) — a comparison, never a stroke source. The per-letter stroke
verdict, the traced letters, words and sentences, and the Workshop
authoring panel are the later phases in the plan; nothing in Phase 1
depends on them.

### The content pipeline is add-only; deleting and gating are separate tools

Every seeder UPSERTs and none deletes. `seeder.run` upserts vocabulary on
`(language_id, word)`; `seed_grammar` UPDATEs a drill's hint, translation and
gloss in place; `seed_sentences` inserts `ON CONFLICT DO NOTHING`. That is
what makes `scripts/setup_db.sh` safe to re-run and what keeps a learner's
`user_cards` from orphaning — and it means **a row removed from a file is
still in production** until a tool that deletes is run on purpose:

- `prune_sentences -l <code>` — file-authoritative: a sentence production
  holds that no committed bank endorses goes. Dry run by default; `--apply`
  writes `out/prune-<stamp>.sql` first and runs in one transaction; never
  strands a word; `curated`/`ai` rows are exempt unless they are only the
  headword. A bulk DELETE, so the owner runs it (CHECKS §18).
- `reconcile -l <code>` — corrections (glosses, parts of speech, sentence
  layers) with the same rollback-first shape. Never deletes a vocabulary
  row.
- `data/vocab_exclusions.tsv` — durable deletions at the FILE layer
  (`source_data.apply_vocab_exclusions`), because a TSV-only deletion is
  undone by the next regeneration. It has no production counterpart yet
  (DEBT.md).

Content produced by an in-session maker–checker pass never goes straight
into a file either. Three gates sit between a run's output and the data
directory, each a script with tests: `scripts/apply_drill_glosses.py`
(cells == tokens, one `___` on the answer, folded no-leak),
`scripts/apply_authored_sentences.py` (7–14 words, the word present, rank =
the word's frequency rank, duplicates and frames rejected) and
`scripts/enforce_sentence_floor.py` (a sub-five-token row goes only when its
word has a longer one). Each reads a run's `journal.jsonl` as well as its
task output, because the journal has held the full result every time the
task file came back empty. The order of operations, per course, is
`docs/quality/refeed.md`.

### One word, several spellings: the sentence fixes the shape

Turkish writes its yes/no particle `mi`, `mı`, `mu` or `mü` to agree with
the vowel before it — one word, four shapes. Making each shape its own
vocabulary card gives the learner four cards that share a definition and
cannot say which spelling to type; making the definition say "after a or ı"
hands over the one computation the language asks for. The pattern that
works (CHECKS §30): one headword; the other shapes in the frequency file's
`alt` column, which the seeder writes to `vocabulary.alternatives`;
`extract.find_cloze` blanks whichever shape the sentence carries and makes
THAT the expected answer; and the grader's layer 6 asks the language what an
alternative means — another right answer by default, "right word, wrong
shape" in Turkish. The rule for anything that asks "is this word in this
sentence" — the card, the audit, the authored-sentence gate, the prune — is
that it asks about every shape, through `backend/services/linked_forms.py`.

A second thing this taught: **case-insensitive is language-specific.**
Python's `re.IGNORECASE` folds dotless `ı` onto `i` (and `İ`, `ſ`, the
Kelvin sign), so a Turkish sentence matched the wrong letter for months.
Languages that find a word by something other than the regex — Thai
(segmentation), Turkish (Turkish casing) — register a span finder in ONE
module, `backend/services/span_finders.py`, and every consumer of
`make_cloze` reads it there rather than keeping its own dict.

### A definition has three homes, and one overlay

`data/<code>_frequency.tsv` carries the source gloss; `gloss_overrides.tsv`
carries the hand-authored correction; production carries whatever last
wrote it. Since 7 Sep 2026 both writers — every seeder
(`BaseSeeder.prepare_records`) and the reconcile (`expected_rows`) — lay the
override file over the frequency file before comparing or writing, so the
override is authoritative everywhere and a re-seed cannot revert it. Before
that, the overlay happened only when `source_data` rebuilt a file, and a
week of definitions sat in the override file reaching nothing (CHECKS §31).

## Frontend

React 19 + Vite 6 + TypeScript (~5.7, project-graph mode via `tsc -b`) +
TanStack Query 5 + Zustand 5 + react-router-dom 7 + Tailwind CSS 4.

**UI languages are catalogs, not code.** `frontend/src/i18n/` holds one
JSON per language and a `UI_LANGUAGES` list; adding one is a new catalog,
two lines in `index.ts`, and nothing else. Nothing on the server has an
allow-list to update — `user_profiles.ui_language` is free text, and the
API stores whatever the client sends — so a language ships or does not
ship entirely on the frontend. Seven now: English, Arabic, Spanish,
Russian, French, Portuguese and Turkish (5 Sep 2026).

Two things make that easy to get wrong. i18next falls back to English for
a **missing key, silently**, so a half-translated catalog does not break
— it leaks English into an otherwise-Turkish page and nobody finds out.
And **plural forms are not English's to decide**: Arabic needs six
categories, Russian three, Turkish and English two, so a locale carrying
`streak_few` where English has only `_one`/`_other` is correct. Worse,
Arabic's `_one` reads "يوم واحد" — the numeral spelled as a word, with no
`{{count}}` to interpolate at all. `__tests__/localeParity.test.ts`
encodes exactly that: every English key must exist everywhere and be
non-blank, extra keys are allowed only as plural variants, an invented
placeholder is always an error, and a *dropped* placeholder is an error
only outside plural forms. It found two keys missing from all five
existing catalogs on its first run.

**The fallback chain is the learner's locale, else English, never a third
language** (owner, 6 Sep 2026). Every card query already implements the
first two halves — `translation_locale IN ($locale, 'en')`, and a
per-field `COALESCE` onto the authored English — so a third language can
only reach a learner through a MISLABELLED row: Spanish text filed as
`translation_locale='en'`, or written into `drill_sentences.translation`,
which has no locale column because it is English by definition.

`services/locale_guard.py` is what catches that at serve time, and it now
answers two different questions. The original one is script-based: is
this text written in the script the locale uses? That proves "not Arabic"
and is blind between two Latin alphabets — which is exactly where the
reported bug hid. So it gained a second, function-word test that answers
only "is this provably NOT English", using closed-class words (articles,
prepositions, copulas) that appear in any sentence of their language and
are not borrowed into English prose.

Both tests are deliberately one-sided: what they flag IS wrong, what they
pass is merely not provably wrong. That asymmetry decides the outcome —
a mismatched field that might be English is KEPT and labelled (it is the
fallback, and on a cloze it is the learner's only semantic cue), while a
provable third language is REMOVED and reported in `locale_withheld`.
Undecidable text keeps its old behaviour, which matters because the
English course's own drill translations are terse notes like "Introducing
yourself." with no function words in them at all.

A UI language is **not** a support locale, and shipping one translates no
card content. `docs/seeding.md` has the table: a language code plays up to
three independent roles (course, UI language, support locale), each with
its own requirements, and only the UI one fails loudly.

**One staff console.** Everything a contributor, reviewer, tester or
admin does lives on the Workspace (`features/contribute/ContributorPage.tsx`,
route `/contribute`): a per-language scope picker, the Review Inbox and
its queues, the Workshop editors, and the admin sections. The Account
page (`features/settings/SettingsPage.tsx`) is the person's page — Learner
settings, the ambassador's Invite — plus a Workspace tab that is a door.
It used to carry a second copy of the review queues and admin panels,
built earlier and never removed; the two drifted (width, panel sets,
scoping, translation) until the owner asked why they looked so different.
Deep links into staff work take the Workspace's `?tab=`, `?section=`,
`?queue=` and `?point=` parameters; the Account page never read a tab
from the URL. Decision record: `docs/decisions/2026-09-04-one-staff-console.md`.

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
