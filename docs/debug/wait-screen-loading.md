# The wait screen that never loads — working log

**Symptom (production, recurring):** switch study language → "You're first
here" → **0 de 3 tarjetas listas**, bar never moves, stall banner appears.
The game plays; the fill never lands. Reported repeatedly across languages
and UI locales (fr, pt, es screenshots on file).

**The acceptance test, in the owner's words:** *new language for that study
language → tell the user what is occurring → give the users the game if
they want to play or go on in English → load a reasonable number of
translations so that the users do not need to wait when they start
studying.* Deployed shape — real server, real DB, browser — not unit tests.

This file is the running record: what was tried, what each attempt proved,
what it deliberately did NOT prove, and what is still open. Update it with
every round; the point is that the next attempt starts from evidence, not
from memory.

---

## Fix attempts so far

| # | date | change | proved | did NOT prove |
|---|------|--------|--------|---------------|
| 1 | earlier | Example demand cleared per-word but worked per-sentence — fixed | that one stall cause | that the fill completes in prod |
| 2 | earlier | Wait-screen stall timer could never fire — fixed | banner shows on stall | anything about the fill |
| 3 | earlier | Start gate measured whole batch incl. examples — added `cards_ready`/`START_CARDS=3` | a session can open on 3 glossed cards | that 3 cards ever become ready in prod |
| 4 | earlier | Grammar meta/drills/examples recorded failure as permanent success — emptiness now means pending + attempt ledger | failures retry | that first-fill succeeds |
| 5 | earlier | Trivia generation competed with the fill on the same key — baseline corpus + LOW_WATER + yield-to-demand | the game stops stealing budget | that the fill lands |
| 6 | 2026-08-09 | **Demand lane filtered by the auto-translate toggle** — one line, `_demand_batches`. Toggle now governs backlog only; usage-scaled baseline lane added | in a repro w/ mock provider + hand-seeded rows: switched-off course READY in ≤10s, full browser journey twice | **anything about real seeded content or the real provider** |

## Why attempt 6's proof did not transfer to production

The repro that validated attempt 6 hand-inserted its content:

```sql
INSERT INTO vocabulary (language_id, word, level, part_of_speech) ...
INSERT INTO translations (vocabulary_id, locale, definition) VALUES (..., 'en', ...)
INSERT INTO example_sentences (..., translation_locale='en', reviewed=true, ...)
```

That bakes in assumptions the real pipeline may not satisfy:

- `pending_words` refuses to translate a word of a non-English course
  unless it has an **English pivot row** (`translations.locale='en'`). The
  repro guaranteed one per word by hand.
- readiness's `cards_ready` counts a card ready when its **support-locale
  gloss row** exists; the whole journey assumes glosses are producible.
- the learner was fresh, subscribed by hand to one A1 deck; production is
  the owner's long-lived account with history, levels and subscriptions.
- the provider was `TUTOR_DEV_MOCK`; production is the real API, where a
  failing call = backoff = minutes, not instant mock success.

Any of these could be the production difference. **The next repro must use
the real seeders and the real learner flow** (onboarding subscription
path), and only then the browser journey.

## Hypotheses, ranked (2026-08-09)

- **H1 — missing English pivot in seeded content.** If seeded vocab for
  some/most courses has no `translations(locale='en')` rows, `pending_words`
  returns nothing, demand settles as "done", readiness never moves —
  exactly the symptom, on every such course, with a perfectly healthy loop.
  Status: seeder `base.py` DOES write `translations` from
  `rec["translations"]` and per-language seeders emit `{"en": ...}` —
  BUT whether every language's data files actually carry definitions, and
  whether prod was seeded by this pipeline or an older one, is unverified.
  → test with the real seeders, then check for pivotless words as a class.
- **H2 — loop unhealthy in the deployed process.** A per-cycle exception
  (schema drift vs the new `baseline_pairs`/`review_log` join, provider
  auth, model id) fails every sweep; heartbeat would show
  `Last sweep failed: …` in the admin panel. Status: unverifiable from this
  sandbox — needs the panel's sweep line from the owner, or staging DB
  access (docs/claude-db-access.md; neither DATABASE_URL nor
  ANTHROPIC_API_KEY is set in this environment).
- **H3 — real-provider failure + backoff pacing.** First batch fails
  (rate limit, model), attempt ledger backs off 2 min+, learner stares at
  a stall banner that reads as "never". Repro's mock cannot exhibit this.
- **H4 — deploy lag.** The screenshots postdate the trivia corpus of #225
  (the Romanian question is on screen), so the deployed backend includes
  attempt 6. H4 is excluded for the fill fix itself.

## What this sandbox can and cannot verify

- CAN: run the real seeders into a local Postgres, real uvicorn, real
  browser, mock provider → proves the data-shape half (H1) end to end.
- CAN: force provider failures (a mock that 429s/refuses) → proves the
  pacing/honesty half (H3) and what the learner sees.
- CANNOT: observe the production loop (H2) or the production data. Needs
  either the admin panel's "Automatic translation status" sweep line after
  a stuck attempt, or a staging `DATABASE_URL` per docs/claude-db-access.md.

## Decisive evidence (owner, 2026-08-09)

> "I know the problem is not the api key because when I leave and come back
> eventually the stuff has loaded."

The fill COMPLETES in production — eventually. That kills H1 (no pivot →
would never load) and H4, and demotes H3. The broken thing is the FAST
path: demand + `kick()` are supposed to make the fill happen within
seconds while the learner watches; instead nothing lands until a later
sweep. Corroboration: the admin panel showed **18 cycles in ~4.5 h** —
exactly the 15-minute timer cadence, zero extra cycles from kicks, even
though wait screens were being watched in that window. The kick is not
waking the loop that does the work in the deployed topology (multiple
workers/replicas: `kick()` sets an in-process asyncio.Event; the process
that receives the readiness request need not be the process whose sweep
timer fires next; my single-process repro could never show this).

**Consequence for the fix:** the wait screen must not depend on any
background loop being co-resident. The request path itself must fill the
learner's start batch — bounded, guarded, inline — the same pattern the
trivia top-up already uses. The loop stays as the bulk engine; the wait
screen stops betting on reaching it.

## Round 2 plan (this round)

1. Fresh DB → migrations → **run the real seeders** for several courses
   (Latin-script + RTL + one with sparse data files).
2. Fresh learner via the **real onboarding path** (not hand INSERTs),
   support locale es, then the full browser journey per the acceptance
   test. If it sticks: the gap is reproduced; diagnose from inside.
3. Class-check H1 across ALL seeded courses: count words lacking the en
   pivot; if any exist, make the loop **produce the pivot** (the
   `-k definitions` generator already exists) instead of skipping the word,
   and make `diagnose_pair` name the condition.
4. H3: harden the learner-facing story under real-provider failure —
   readiness should expose *why* nothing is landing (blockers from
   `diagnose_pair`) so the wait screen can say it honestly instead of
   promising.
5. Whatever is found: fix, add the regression test that would have caught
   it, re-walk the browser journey per language, record results here.

## Round 2 results (2026-08-09)

- [x] **Seeder-shaped repro built** — fresh DB, all migrations, then the
  REAL seeders (`backend.services.seeder.run -l tr`, `-l ar`): 10,000
  Turkish + 8,787 Arabic words. Every seeded word carries the English
  pivot (`translations.locale='en'`) → **H1 dead** on evidence, not
  argument.
- [x] **Root cause confirmed = the kick topology (H2-adjacent).** The fix:
  `fill_start_batch` — the readiness request now translates the learner's
  start batch ITSELF (≤8 words + ≤3 grammar explanations, one
  maker–checker round trip), on the worker serving the request, with a
  90 s per-(user, language) cooldown and a process-wide concurrency cap
  of 2. `kick()` stays, demoted to best-effort bulk signalling; its
  docstring now records why it cannot be load-bearing.
- [x] **Journey walked with the loop DISABLED** (the deployed condition —
  no sweep can ever answer a kick):
  - Turkish, real onboarding (`POST /onboarding/complete`), API-level
    wait-screen poll: `0/3` at t=0 → **`7/3 ready_enough=true` at t=5 s**.
  - Arabic, full browser walk (vite + Chromium, Spanish UI): session open
    with Spanish glosses **at t=0** — the inline fill triggered by the
    page's own first readiness call had finished before the screen could
    even be photographed.
- [x] **Regression tests** — router wiring: a not-ready readiness
  schedules the inline fill with the batch the gate is scoring; a ready
  one spends nothing; the cooldown blocks refresh stampedes; the task
  never raises. Integration: `test_the_wait_converges_with_no_loop_at_all`
  — session opens with `run_translation_cycle` never called, the inline
  fill as the only engine.
- [x] Full suites at baseline (16 documented environment failures), ruff
  clean, frontend untouched.

**Still open, deliberately:** the "3" in "0 de 3" is `START_CARDS` — a
constant target, not a stuck count; it reads as suspicious when the left
number doesn't move, which after this fix it should within seconds. If
production sticks AGAIN after this deploys, the next probe is the admin
panel's sweep line at the moment of the stall (distinguishes a dead loop
from a failing provider) — and that observation costs the owner one
screenshot, not another iteration of guesswork.

## Round 3 (2026-08-09) — the fill worked, the sentences didn't ride along

Owner's report after the Round 2 deploy, with a screenshot: *"It seems the
loading worked better but it did not trigger the sentence translations as
well?"* — a Thai grammar card, Spanish interface, where CÓMO FUNCIONA (the
explanation) IS Spanish but the EN CONTEXTO lines under it are English.

That is Round 2's fix behaving exactly as written, and written too
narrowly: `fill_start_batch` translated precisely what the readiness gate
counts — word glosses and grammar explanations — and left the sentence
layer (example sentences, drill translations/hints) to the background
loop. Which is the same loop the whole round established cannot be
reached from the request path in the deployed topology. So the card's
body loaded inline and its sentences waited for the quarter-hour sweep:
the original bug, one layer down.

Fix: the inline fill now carries the sentence layer too, same bounds and
guards —

- example sentences for the batch's vocab ids (`pending_examples` →
  `_translate_examples`, ≤`INLINE_FILL_SENTENCES=8` per pass, skipped on
  the self-pair where a rendering would restate the sentence);
- the batch's grammar points' drills (points mapped to drill ids first,
  since `pending_drills` is keyed by drill; `_translate_drills` already
  renders hint-only on the self-pair);
- both settled into the attempt ledger with the sweep's own ref
  semantics (examples per distinct vocabulary_id, drills per drill id).

Regression tests: the no-loop convergence test now also asserts locale
example rows and drill_hint_translations exist after the fill; a unit
test pins the wiring (sentence helpers called, both kinds settled).

## Round 4 (2026-09-01) — card one was whole, card two was English

Owner's report, four screenshots, Russian interface, Greek course: the
first card arrived fully translated, sentences included; the *next* card
had an English title and English drill translations; going back to it
later, they were Russian. *"I don't know how things in the list to be
covered are being translated. Eventually they are, but still."*

Three things, all Round 3's fill working as written:

1. **It stopped after the start batch.** ≤ 8 words, ≤ 3 explanations,
   ≤ 8 sentences, ≤ 8 drills — enough for the gate, nothing for the rest
   of the session. Card two onward waited for the quarter-hour loop.
2. **Grammar titles were never on its list.** `pending_grammar_meta` /
   `_translate_grammar_meta` only ran inside `auto_translate_loop`, so a
   card whose body was translated could still carry an English heading.
3. **The page only swapped on advance.** Rows that landed while a card
   was on screen showed up on the way back, never on the way forward.

Fix, in `backend/services/auto_translate.py` and both session pages:

- `fill_start_batch` now walks the **whole session in reading order**
  (`_interleave_typed`, the order the session itself serves), two cards
  first, then six per pass, up to 30 cards / 300 s, translating per chunk
  words → grammar titles → explanations → examples → drills. The old
  `INLINE_FILL_WORDS/POINTS/SENTENCES` caps are gone.
- One fill per (user, language) at a time: `_INLINE_FILLS` is a status
  dict (`running`/`done`/`error`/`no_provider`), reported by readiness as
  `fill` and shown by the wait screen when it explains a stall.
- `LearnPage`/`ReviewSessionPage` re-fetch readiness every 15 s while a
  lane is below 1 (each poll re-arms the fill) and re-serve upcoming cards
  every 10 s as well as on advance.

Tests: `test_readiness_inline_fill.py` pins the reading order (the first
calls are word → grammar title → explanation → example for card one, only
then card two's words), the in-flight guard, and `no_provider` status in
the readiness JSON; `LearnPage.test.tsx` pins the tick swap.

**"Готово карточек: 0 из 3" in the first screenshot is the pre-#384
build** — the current one shows the batch percentage for a one-card gate.
If it appears again after this deploys, check `built_at` in Settings →
Admin → Deployment before anything else.
