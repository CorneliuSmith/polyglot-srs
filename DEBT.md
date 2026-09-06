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

### Production data is pushed by the owner, by hand, and the push has run

Until 30 Aug 2026 the repository was deliberately ahead of the deployed
app — `docs/decisions/2026-08-26-owner-decisions.md` gated the content push
on the Gym level and a comprehensive grammar review. The owner released that
gate by running the sequence themselves on 30 Aug, and has run
`prune_sentences --apply` for en/ru/ar since. What remains true, and is
easy to get wrong from either direction: **code deploys itself from
`main`; data does not.** A merged TSV or grammar JSON changes nothing a
learner sees until the owner runs `docs/quality/refeed.md` for that course,
and this agent must not run it (a bulk DELETE attempt was blocked by the
auto-mode classifier). 24 courses have never been pruned, so their cards can
still serve sentences no committed bank endorses (CHECKS §18).

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

### The first-session wait only holds new learners, and only for one card

If the waiting room (`TrailblazerWait`) looks like it "isn't gating any
more", that is the design as of this change, not a regression: `new_here`
false → lanes open regardless of `pct`; new learner → the gate opens at the
first ready card (`START_CARDS = 1`, the old 60 % `READY_ENOUGH` is gone);
translations that are still missing swap in while the session runs. The
owner asked for exactly this — the game stays for new learners, nobody
else waits, and the app fills in around them. LEARN.md → *The first-session
gate*. What is still true and easy to misread: `review.pct` can sit below 1
for a returning learner for a long time — that is the live swap's signal,
not a stuck fill.

### The inline session fill is per-process, and needs the key on the web service

`fill_start_batch` keeps its in-flight guard and cooldown in a module dict
(`_INLINE_FILLS` in `backend/services/auto_translate.py`). Under more than
one uvicorn worker, readiness polls from the same learner can land on
different workers and each start its own fill for the same session. This
is bounded — every pass re-queries what is *still* pending and the inserts
are `ON CONFLICT DO NOTHING` — so the cost is duplicated model calls for a
chunk, not wrong data. Moving the guard to Redis (`SET NX` with a TTL)
would fix it; not done because the deployed service runs one worker.

Separately: the fill runs *in the web process*, so `ANTHROPIC_API_KEY` must
be set on the web service, not only on whatever runs `auto_translate_loop`.
Without it the fill declines with status `no_provider`, readiness reports
that as `fill.status`, and the wait screen says so
(`trailblazer.noProvider`). A wait screen showing that message is a config
problem, not a code one. Before this change the same situation was a bar
sitting at 0 % with no explanation.

### Findings from the 3 September notes review (brief: docs/plans/owner-notes-2026-09-03.md)

Every finding the exploration behind that brief established was fixed
the same day (the translation checker tier, the Speak summary model, the
makers' missing language brief, the unbounded tutor memory, and the edit
history being mounted only for example sentences). The entry stays as a
pointer to the brief, which tracks what is still open per item.

Two things that pass the tests but are not finished:

- **No tutor has been through the skill digest yet.** All 27 languages sit
  in `NEVER_DIGESTED` (`services/tutor_skill_digest.py`), which is what
  lets `test_every_standard_has_a_current_digest_or_a_listed_exemption`
  pass. The digest calls the summary model once per language; that is the
  owner's spend to authorise. To turn the check on for a language: run
  `scripts/tutor_skill_digest.py <code> [--db-url …]`, fold the bullets you
  accept into `ERRORS.md` together with the stamp line it prints, and
  remove the code from `NEVER_DIGESTED` — the test then fails whenever
  `docs/quality/<code>.md` changes again without a re-digest.
- **Markdown cards have no colour or Anki-style classes yet.** The
  brief's phase 2 pictured "a small set of allowed classes"; that needs
  raw HTML (`<span class="…">`) parsed by rehype-raw before the
  sanitiser, and today raw HTML is refused on both sides on purpose. Add
  rehype-raw plus a `span` + `className` allow-list in
  `components/CardMarkdown.tsx` and the same classes in
  `services/markdown.py` if the owner wants colour; nothing else changes.
- **Korean's regenerated REFERENCE.md is 18k chars**, three times its old
  hand-written size, because the course has 156 points and the old file
  listed a third of them. The on-demand bound in `test_tutor` went from
  12k to 20k for it. If the tutor's `consult_reference` answers for Korean
  start reading as padded, split the map by level rather than trimming
  points — the whole point of generating it is that it lists them all.


### The card draws a word's SHORTEST sentence first

`get_due_cards` orders a word's sentences `difficulty_rank ASC, id`, and
every row of a word carries the word's frequency rank on purpose (CHECKS
§24), so `id` — insertion order — decides. Corpus rows were inserted before
authored ones and Tatoeba lists short sentences first. Result: 89% of
English and 58% of Russian top-2,000 words that own a 7–14-word sentence
show a shorter one — after 6,517 Russian sentences were authored to fix
exactly that. The fix is a single ORDER BY preferring the §23 band (the
SQL is in CHECKS §26), with Thai degrading to today's order. Designed 6 Sep,
not built; first item in `docs/decisions/2026-09-06-review-pass.md`.

### The English course shows its drill usage note under "Translation"

By convention (`docs/quality/en.md` note 0) an English drill's
`translation` field holds a usage note and the real translations live in
`data/grammar/en_drill_hints.<locale>.json`. With an English UI locale no
`drill_hint_translations` row exists, `COALESCE(dht.translation,
ds.translation)` falls through, and the note renders under the "Translation"
heading — "do — the participle." (CHECKS §27). Fix is a `context` field
under its own label in all six locales, plus 11 notes that merely restate
the hint. Not a data bug; do not "fix" it by writing English-for-English
translations, which hand over the answer.

### Exclusions have no production write path

`data/vocab_exclusions.tsv` (727 rows; 764 once `fix/en-symbol-glosses` merges) is applied by the FILE loader
(`source_data.apply_vocab_exclusions`), and no seeder deletes a vocabulary
row because `user_cards` references it. So every excluded word — the 645
"a male given name" cards retired on 25 Aug, and the 37 in
`fix/en-symbol-glosses` (`em` glossed as a printer's quad, `er` as erbium,
`ya`, `wanna`) — is still served in production. What is needed: a
`vocabulary.retired_at` column (migration, owner-applied; readers degrade),
a retire step in `reconcile` that sets it from the exclusions file, and the
card draw / lesson intake filtering it while keeping the learner's
`user_cards` row. CHECKS §12's class: a layer with no write path.

### The lesson's Gym link is English in five locales

`GrammarPathPage` links a lesson to its Gym drill set (#397) using
`path.practiseForms` and `path.drillCount`, which exist only in `en.json`;
ar, es, fr, pt and ru fall back to the English string on that line. Add the
five keys with the next frontend change — and the `card.context` key from
the entry above should ship in all six at once.

### `EnglishSeeder` stops at 8,600 of 10,000 headwords

~1,400 English headwords have no WordNet gloss and are skipped rather than
inserted, and they include `what`, `how` and `because` — absent from
production today while `en_frequency.tsv` lists them. Diagnosed 5 Sep,
not fixed. Two routes: gloss them through `gloss_overrides.tsv` (the
mechanism exists and `circular_gloss` gates it) or lift the cap and let
the audit decide. Either way the count to watch is production `en` rows
against the file's 10,000 (9,963 once `fix/en-symbol-glosses` merges).

### The Workspace chrome is translated; its 42 panels are not

Since 4 Sep 2026 the Workspace (`/contribute`) is the only staff console
(`docs/plans/staff-console-consolidation.md`), and its heading, tab and
section labels, content switch and no-role copy follow the UI language
(`workspace.*` in the six catalogs). Every panel under
`features/contribute/` is still hardcoded English — 42 files, zero `t()`
calls — as is `settings/DeploymentPanel.tsx`. That is a scope decision,
not an oversight: the panels are staff tooling used by a handful of
people who all read English, and a full pass is a multi-day translation
job that should be done once, panel by panel, when a non-English-reading
reviewer actually joins. Until then a French reviewer sees a French frame
around English tools.

### A phrase card from the Reader carries no gloss

Since 4 Sep 2026 a learner can highlight a run of words in a reading and
add it as a card. The Reader glosses tokens one at a time, so the phrase
itself has no gloss: the card is built from the sentence, the phrase as
the answer and the sentence's translation, and `gloss` is sent empty.
The server builds a cloze (the phrase was selected from the sentence, so
it is found verbatim); the fallback "type the word" prompt for an
inflected answer never applies here. If phrase glosses turn out to
matter, gloss them at add time with one small maker call — not by
joining the token glosses, which reads as word salad.

### The four plan options lean on three Stripe facts nobody enforces

LEARN.md → *Plans: four options, one subscription*. Three assumptions the
code cannot check for you:

- **The plan Prices and the AI add-on Price must bill on the same
  interval** (monthly). Stripe refuses a subscription Checkout whose line
  items recur differently, and the error surfaces as a 500 from
  `/plan/checkout`, not as a message. If annual plans are ever added, they
  need an annual add-on Price beside them.
- **The Billing Portal's configuration** (Stripe dashboard → Settings →
  Billing → Customer portal) decides what "Manage billing" can do. Cancel
  and update-payment-method work by default; switching between the plan
  Prices there only works if the portal is configured with those products.
  The in-app "Change plan" path does not depend on it.
- **`Subscription.cancel(prorate=True)`** on upgrade credits the unused
  period to the customer's balance; it does not refund a card. Fine for
  monthly, worth a look if annual plans arrive.

Also deliberate: cancelling a plan clears `plan_ai` (the pool was what the
subscription paid for) but leaves `plan_scope` alone — what a lapsed
account keeps of its CONTENT is still the pending owner decision (ROADMAP
WP16e). With the profile default being `'all'`, an unpaid account today
sees all languages' content and the free AI tier. Decide before launch
whether lapsed and never-paid accounts should be narrowed to one language.

### `docs/pricing-and-launch.md` is superseded twice over

That memo (17 August 2026) proposes a $8/$14/$24 tiered ladder with
weighted-unit metering. Monetization v2 replaced the ladder with a
single-language plan (no AI) + AI add-on + top-up, and the four-option
picker now sells the combinations as one subscription. The memo's cost
arithmetic (per-action Claude costs, the Reader-text-is-30×-a-tutor-message
problem) is still the best in the repository; its prices are not. Its one
engineering recommendation that has NOT been done — **weighting the
allowance draw** so a Reader text costs 3 units and a Gym set 2 — is the
open margin risk: every kind in `ALLOWANCE_KINDS` still draws one message.

### The queue card editor writes English, and cannot touch three things

`PUT /api/contribute/review/card/{type}/{id}` (LEARN.md → *Editing the card
from the queue*) is deliberately narrower than "edit this card":

- **A vocabulary edit writes the ENGLISH definition**, never the support
  locale the reviewer happens to be reading in. English is the source every
  locale is translated from, so fixing only the Russian gloss leaves the
  next locale to inherit the same fault — but it does mean the locale
  renderings stay stale until the translator re-derives them, and the
  AI-translations queue is what catches those. A reviewer who edits a word
  and expects the Spanish gloss to change on the spot is not seeing a bug.
- **A word's own text is not editable at all.** `user_cards`, audio clips
  and every example sentence point at that row; renaming it in place would
  silently re-target all of them. A wrong word is retired and replaced. The
  editor simply does not draw the box, and the server drops the field.
- **`context` and `level` are not editable** — they belong to the parent
  (the grammar point a drill sits under, the word an example illustrates),
  and editing them from a child card is how two cards end up disagreeing
  about the same point.

If a fifth reviewable kind appears, it needs an entry in BOTH `_CARD_SQL`
(`repositories/change_requests.py`, the read) and `CARD_EDIT_FIELDS`
(`repositories/contributor.py`, the write). Only the read is required for
the queue to render, so the failure mode is a card that displays and
quietly offers no Edit button.

---

## Real gotchas — already hit once, will bite again if forgotten

### A wrong-language row can still be STORED; it is only hidden at serve time

Since 6 Sep 2026 a card never shows a third language: `locale_guard`
strips a field that is provably neither the learner's locale nor English.
That fixes what the learner sees. **It does not fix the row.** The Spanish
sitting in an `example_sentences` row filed as `translation_locale='en'`
— or in `drill_sentences.translation`, which has no locale column at all —
is still there, still counts as filled, and so still suppresses the
demand queue that would otherwise translate it properly.

`services/quality/audit_locale_rows.py` now finds them (`_foreign_latin`,
reusing the same conservative function-word test), so the fix is: run the
audit against the deployment, and correct or delete what it lists. Until
someone does, affected cards show no translation line where they used to
show a wrong one — better, but not right.

The detector is a heuristic and says so: two closed-class function-word
hits and a margin over English. It will not catch a short mislabelled
string with no function words ("Buenos días."), and it knows nothing
about languages outside its ten-language table. Both are deliberate — the
cost of a false positive is a deleted English cue, so it is tuned to stay
quiet when unsure.

### The two translation lanes disagree about what a support locale is

`fill_start_batch` (the inline, session-time fill) resolves the locale with
a LEFT JOIN on `languages` and carries on when there is no row, naming the
locale by its code. `discover_pairs` (the background sweep) INNER JOINs the
same table and drops the pair entirely. Both are in
`services/auto_translate.py`.

So a support locale that is not also a course language translates the
session a learner is sitting in and **never fills its backlog** — and
`translation_status`, the readout built precisely so this feature cannot
fail silently, does not cover it: it reports courses with
`auto_translate_enabled` off, but never a locale it could not resolve. The
admin sees an empty pair list and a green panel.

Nothing is broken today because all seven UI languages are also course
languages. It breaks the first time one is not — a UI language for a
market whose language the app does not teach is the obvious case, and is
exactly the kind of thing that gets added without touching this file.

Two fixes, both small, neither done: make the sweep LEFT JOIN like the
inline fill so the lanes agree, and add an "unresolved locale" line to
`translation_status` so the panel says so either way. Surfaced 5 Sep 2026
while answering why Turkish content was still English (it was not this —
see `docs/seeding.md`, "The three roles one language code plays").

### The Turkish catalog is a machine translation nobody has read

All 1,491 strings of `frontend/src/i18n/locales/tr.json` were translated
in one session on 5 Sep 2026, against the choices the five existing
catalogs had already made for the product's own vocabulary (Deck →
Deste, Gym → Antrenman, Review → Tekrar, Tutor → Öğretmen). It is
structurally sound — parity, placeholders, tags and the Gym's
course-language affixes are all pinned by tests — but **no Turkish
speaker has read it**, and structure is not idiom. Expect the wrong
register somewhere, and expect the grammar terminology in `gymForms`
(262 labels: `Belirtme durumu`, `İstek kipi`, `Bitmemiş geçmiş`) to be
the part a teacher argues with, since Turkish grammar names its own
categories and those names do not always map onto the Latin ones the
labels were written in.

The fix is a reading, not a rewrite: hand `tr.json` to one Turkish
speaker beside a running app. Until that happens, treat a Turkish
learner's complaint about wording as probably right. The same caveat
applies to any future catalog produced this way — which is why this
entry is about the process, not just this file.

### On a phone, whatever CAN shrink pays for whatever cannot

Two reports a day apart, same shape, different CSS. A row or grid is
wider than the viewport; one part of it is pinned (`shrink-0`, or an
implicit `auto` grid track); so the *other* part absorbs the entire
shortfall, and past zero the overflow spills anyway. You get two symptoms
from one cause — something important vanishes, AND the page still
overflows — which is why it reads as two bugs.

- **5 Sep, Language visibility** (`LanguageVisibilityPanel`): the control
  cluster — swap, review badge, open-reports count, "Auto-translate" and
  "Visible" toggles, settings — was `shrink-0` beside a `min-w-0` name
  button. Every row rendered as a flag and some checkboxes with **no
  language name on it**, and the settings icon still sat outside the
  card. Fixed by letting the row wrap: the name takes its own line below
  `sm`, controls wrap underneath, single row from `sm` up.
- **4 Sep, admin Insights** (`CARD_COLUMNS`): the entry below.

**The rule when adding a row of controls:** on a phone, ask what gives.
If the answer is "the label", the row needs to wrap, not to shrink — a
truncated name is a worse outcome than a second line. `shrink-0` is right
for two or three icons and wrong for a cluster carrying text labels.

jsdom does no layout, so neither of these can be caught by measuring;
both regressions are pinned by asserting the class decisions instead
(`LanguageVisibilityPanel.test.tsx`, `pageWidth.test.ts`). That is weaker
than a real check and worth replacing if visual testing ever arrives.

### A grid track without an explicit `grid-cols-*` floors at its content width

Cost an hour on 5 Sep 2026, and will again: the admin Insights page
scrolled sideways on a phone, showing a band of bare body background down
the right of the screen. The retention table was already inside an
`overflow-x-auto` wrapper, which is what makes this one hard to see — the
wrapper scrolls the table, but it still REPORTS the table's full width to
its ancestors, and the card was a grid item.

`CARD_COLUMNS` read `grid gap-4 lg:grid-cols-2`. Below `lg` that is an
IMPLICIT track, sized `auto`, and a grid item in an auto track takes its
content-based minimum width — so the column could not shrink below the
~700px table, the card grew past the viewport, and the page's scroll
width went with it. `lg:grid-cols-2` was never affected, which is why it
only ever broke on small screens: Tailwind's `grid-cols-N` compiles to
`minmax(0, 1fr)`, and that zero minimum is what switches the automatic
minimum size off.

**Writing any new grid: name the base track (`grid-cols-1`), not just the
breakpoint variants.** The same trap exists for flex — a flex item needs
`min-w-0` for the identical reason. `pageWidth.test.ts` pins
`CARD_COLUMNS`; it cannot pin a grid someone writes inline tomorrow.

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

### `try/except` a SQL error inside a transaction is a no-op (fixed, 36 sites)

The profile endpoint's fallback for a not-yet-applied migration was a
ladder: try the widest SELECT, catch `UndefinedColumnError`, retry a
narrower one. It could never have worked. `rls_connection` and
`privileged_connection` each run inside one explicit transaction, so the
first failure aborted it and the retry raised `InFailedSQLTransactionError`
— uncaught — on the endpoint that renders every page. The profile endpoint
was replaced with a probe of `information_schema.columns`
(`docs/decisions/0001`), and that was called fixed.

It was not. The same shape existed at **thirty-six other sites** —
`session_readiness`, the dashboard, the tutor, recommendations, feedback,
experiments, speak, the seeders — and `/api/review/readiness` 500ed
through one of them on the deployed app the moment a migration was behind.
Those are now wrapped in `savepoint(conn)` from
`backend/repositories/pool.py` (LEARN.md → *When you must catch instead*),
which makes the retry run on a live transaction, and the integration test
`test_savepoint_integration.py` pins that the un-wrapped version really
does raise. Kept here as a *pattern* warning for new code: a `try/except`
around a statement, continuing on the same connection, needs either a probe
before it or a savepoint around it. Reviewers should grep for
`except asyncpg.exceptions.Undefined` and expect to see one of the two.

The original ladder also only dropped column groups from the right, so
"newest migration applied, an older one not" — a real state when migrations
are owner-applied and independent — had no attempt that fitted it. The
profile replacement plans per column.

### Admin overview still reads `languages.is_visible` unguarded

`backend/repositories/contributor.py`'s admin overview query
(`SELECT l.id, l.code, l.name, l.is_visible, ...` around line 940) reads
the column directly, while the inbox roll-up in the same file probes for it
(`_INBOX_COLUMNS + ("languages.is_visible",)`). Deliberately left: it is an
admin-only panel, the migration that adds the column (`20260831`) is
applied on production, and it degrades to one panel's error rather than a
page-load failure. It becomes a real problem only if the schema is ever
rebuilt from an older point; if that happens, fold it into the same probe.

### Migrations the deployed database may not have yet

Applied by the owner, never by an agent (`CLAUDE.md`). At the time of
writing the newest are `20261012000000_show_glosses.sql` (the Learner-tab
"Show glosses" setting), `20261014000000_translation_review_items.sql`
(the reject queue for non-vocabulary translations) and
`20261015000000_speak_corrections.sql` (Speak's "no corrections" flag).
The code is safe without any of them — the profile probe returns the
default and the toggle still renders; the translation writers probe for
the table and skip the queue, the list endpoint returns no items and the
inbox counts none; Speak probes for the column and records corrections
whatever the box said, telling the client so in the start response — but
the glosses *value* will not persist, a rejected drill line, explanation,
grammar title or example meaning stays invisible (the pre-September
behaviour: unwritten, retried on the backoff), and a learner who unticks
the box still gets a breakdown, until they are applied. `/api/health/schema`, or Settings → Admin → Deployment, lists
exactly which files the live database is missing; trust that over this
paragraph, which will drift.

### The Docker image usually has no commit SHA

`/api/health` reports `build.sha` null on DigitalOcean: `.git` is outside
the build context and DO does not pass a commit as a build arg. The
Dockerfile accepts `ARG GIT_SHA` for platforms that do. Left as-is because
`built_at` (written by the build, not the boot) plus `latest_migration`
already answer "what is running" — if the SHA is ever wanted, set the build
arg in the App Platform spec rather than adding a runtime lookup.

### `SpeakButton` is deliberately not gated on `TTS_LANGUAGES`

`frontend/src/api/audio.ts` has `TTS_LANGUAGES`, a mirror of the backend
`VOICES` table, and the *prefetch* paths check it so a language with no
voice never prefetches. The on-tap `SpeakButton` does not — on purpose.
Jamaican Patois (`jam`) has no synthetic voice but serves human recordings
through the same `/api/audio/tts` endpoint, so gating the button on "has a
voice" would silence exactly the language the recordings were sourced
for. The cost is one 404 per clip for a voiceless, recording-less language,
memoised per clip in `misses` so it never repeats. If a `has_tts` flag per
language is ever added, it must mean "voice *or* recordings", not `VOICES`.

The flood of TTS 404s seen on the deployed app was a different bug and is
fixed: the cloze matched case-insensitively and the UI rebuilt the sentence
with the answer in its dictionary case (`"Gato come."` → `"gato come."`),
so `_text_is_ours` found no row. `_case_variants` in
`backend/routers/audio.py` matches the first-letter-flipped form.

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
