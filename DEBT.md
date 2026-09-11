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


### The prune's source exemption shielded thin rows (fixed 6 Sep 2026)

Kept as the reason, not the problem: `prune_sentences` exempted `curated`
and `ai` rows because no rebuild reproduces them, which left **15,802 rows
under five tokens** in production — 48% of every `ai` row — including the
"You are human." / "I am human." set behind the owner's `human` card. The
files had carried §24's floor since 31 Aug; production had not, which is why
pruning ru and ar reported 0 and 31 rows while thousands of thin ones
stayed. Now `FLOOR`, the tokenizer and the Thai exemption live in
`prune_sentences.py` and `scripts/enforce_sentence_floor.py` imports them,
so the file pass and the production prune cannot drift. **The rows only
leave production when the owner re-runs the prune per course**
(`docs/quality/refeed.md`) — every course needs a second pass, including
en/ru/ar which were pruned before this existed.

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

### Korean teaches four topics twice — RESOLVED 8 Sep 2026

Judged by two readers of Korean and merged: five points retired, salvaged
drills moved into the keepers, the keeper's own wrong answer fixed. The
retire path that blocked it is built — migration 20261017
`grammar_points.retired_at`, `data/grammar_exclusions.tsv` as the source of
truth in both directions, `reconcile` setting and clearing it, every offer
path filtering on it (probed). Record:
`docs/decisions/2026-09-08-korean-duplicate-points.md`. ~~One sibling is
still open: A1 index 40.~~ **Closed 10 Sep 2026** — that sixth duplicate
(`Topic particle ~는/은`) is retired: it called 은/는 a "subject-marking
particle" in its function note and all seven hints, and this course teaches
the topic/subject split itself. Its 7 drills were salvaged into the keeper
with hints naming each noun's own 받침, 3 cross-references remapped, the
duplicate gym entry removed and `REFERENCE.md` regenerated.

### 1,264 English words below rank 2,000 still have no definition

`EnglishSeeder` can only teach a word it can define, and WordNet has no
entry for 1,389 of the frequency list's headwords — it skipped every one of
them. The 125 inside the top 2,000 are fixed (66 glossed by hand, 59
excluded as contraction debris, given names or abbreviations), and `what`,
rank 16, is in the course at last. **The remaining 1,264 all sit below rank
2,000** and are a long tail of the same three kinds. The seeder now names
them in a warning instead of skipping in silence, which is how the first 125
stayed hidden for months. Work them when a course reaches that depth.

### Written abbreviations as vocabulary: 12 held, and the judges disagreed

A sweep of every single-character and letterless headword across 24 courses
(851 candidates, judged then defended) removed 94 that are letters,
punctuation, bare diacritics or extraction artefacts. **12 are held**, not
because they are defensible but because the pass judged them
inconsistently: Portuguese `s` (segundo), `h` (hora), `d` (Dom), `c`, `n`,
`q` were called abbreviations and condemned, while the Spanish equivalents
— `s` (sur), `m` (metro), `x` (por), `d`, `c`, `n`, `t`, `i` — were defended
as written abbreviations a learner meets. Both readings are reasonable and
they cannot both be the standard.

Also held: Arabic `ي` and `ت` and Korean `잡`, `갖`, `걷`, `찢`, called
clitics or bare verb stems that never stand alone.

**The decision needed is one rule, not twelve verdicts:** is a written
abbreviation a vocabulary card? A card asks the learner to PRODUCE the
string from a definition, and "por, in texting" → `x` is a poor card by
that test — but it is a real thing Spanish writers write. Whichever way it
goes, it must apply to every course at once (quality rule 1).

### Rows the card can never show, and a fallback that hides it

`make_cloze` (`backend/services/extract.py`) whole-word-matches the surface
headword; `cards.py` skips any example row it rejects and, when every row of
a word is rejected, silently serves the definition-only prompt. Korean (54% of rows — dictionary-form
headwords), Arabic (47% — stem headwords) and Yoruba (50% — toneless
headwords) are mostly in that state: 566 / 491 / 182 top-2,000 words with no
usable sentence. **Thai is fixed** (6 Sep): segmentation replaced the
boundary regex, 311 → 3,675 rows, 110 words left — CHECKS §29.
No log, no metric, no test says so. The 31 Aug Russian authoring applier
made it worse by accepting LEMMA presence (pymorphy3), so an unknown share
of its 6,517 rows are dead on arrival. Fix design and order in CHECKS §29;
the `unclozable_rows` audit rule is the instrument that has to exist before
any coverage table is believed for those four courses.

### Vocabulary grading scolds for a form the card never specified

`nlp/base.py` layer 3 grades a lemma match on a vocabulary card
`CORRECT_SLOPPY` with "Correct meaning, but check the exact form" — right
when the card named the form, wrong when it did not, and CHECKS §28 found
a third of top-band cards do not. Until the content carries the form (or
the grader checks whether it does), that string blames the learner for
the card's gap. `frame_collision` — the mechanical half of the §28 check
— is designed, not built; it belongs beside `ar_register` in
`audit_content.py`.

### `prune_sentences` keeps a word's fragments rather than empty it

The "never strand a word" guard leaves every row of a word whose whole set
would go. On 6 Sep that was 100 Russian and 72 Arabic words — names
(`лиза`, `донна`, `كارلوس`), slang (`чё`, `бля`), inflected forms
(`родился`), letters (`ن`, `ج`) — each still showing a bare fragment in
production because the committed bank has nothing for them. Two ways out,
neither built: exclude and retire them (the DEBT entry above), or a
`--allow-strand` that prunes to zero, since a definition-only card is an
honest fallback and "И?" is not. Until then a `stranded` count in the dry
run is a list to act on, not a number to ignore (`docs/quality/refeed.md`).

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

### Write, Phase 1: what Free write does not do yet

Shipped 11 Sep 2026 (`docs/plans/handwriting.md`, Phase 1). Three gaps a
reader of the plan would expect to find built, and will not:

- **No staff queue for low-confidence reads.** The plan sends a *low*
  confidence assessment to a Workshop queue with its PNG kept for 30
  days. Not built: the ink is never stored (by design) and no queue kind
  exists, so a learner who keeps getting "not sure I read that right" has
  the transcription to go on and nothing else. Build it when the
  Workshop's feedback queue gains a `writing` kind; until then the answer
  to "the reader keeps misreading my Thai" is the transcription itself.
- **No per-letter stroke verdict.** "Correct" is the model's reading of
  the text, and "legible" its judgement as a reader. The form / order /
  direction check per letter needs the script's authored templates
  (Phase 2–4). The neatness panel is the exact, on-device half until then.
  The writer's own strokes ARE kept with each sample now (§11, Phase A),
  so the material for a personal tolerance exists before the matcher does.
- **The accuracy readout counts only what the writer confirms — plus
  sure matches.** A Check on expected text that the reader was sure of
  and got right counts as *right*; a Check the writer never confirms and
  the reader got wrong counts as nothing. So the number leans favourable
  until the writer presses *No* on misreads. The baseline session (§12
  Phase C) is the fix: eight confirmed readings in one sitting give the
  readout a fair denominator from the start.
- **Ink retention is now conditional, not absent.** With *Adapt to my
  handwriting* on (the default), up to twelve canvases per language are
  kept as the writer's samples; the switch and its Reset delete them.
  The earlier "the ink is never stored" is true of the attempt log only.
- **No handwriting face for Hebrew or Greek.** `handFont.ts` maps each
  script to a Google Fonts handwriting family (Caveat for Latin and
  Cyrillic, Aref Ruqaa for Arabic and Persian, Kalam, Nanum Pen Script,
  Sriracha). Google serves nothing handwritten for Hebrew or Greek, so
  their compare view falls back to the browser's generic `cursive`, which
  on most systems is a Latin face and shows the text in the default UI
  font. An OFL Hebrew cursive font can be self-hosted (the plan names
  the option); nobody has picked one.

Also worth knowing: the `style` flag (print / cursive) reaches the model
only for scripts `hasCursiveToggle` allows — Arabic, Persian, Hangul,
Thai, Devanagari and Hebrew send none, and Russian defaults to cursive
because that is what Russians write.

### A fill predicate stricter than the serve predicate is a permanent English row

Fixed twice on 8 Sep 2026 (examples: `reviewed` alone versus the review
page's `reviewed OR ai_ok/all`; drills: "any overlay row" versus field by
field — LEARN.md → *What is pending is exactly what is served*). What is
still true: the **learn-page** readers are stricter than the review page.
`get_card_details_bulk`, `get_card_detail` and the word-detail read in
`repositories/cards.py` take example sentences with `es.reviewed` alone,
while `get_due_cards` (the review session) also serves generated
sentences when the course's `grammar_review_policy` lets AI content
through. So on an `ai_ok` course a learner meets a generated example on a
review card that was not on the learn card for the same word. The fill
now follows the more permissive read (the sentence is served *somewhere*),
so nothing stays English — but the two pages disagree about what a learner
may see, and that is a product decision, not a predicate to align
silently: either the learn page adopts `served_example_sql` too, or the
review page stops serving drafts. Not done here because it changes what
learners are shown, and the owner has not chosen.

Related and unchanged: the sweep's baseline lane (`baseline_pairs`) counts
*words* only. A switched-off course whose starter-corpus allowance is
spent drops out of the sweep entirely, sentence layer included; those rows
reach a learner only through the demand lane (recorded on every card read
they appear in) and the inline fill. That is by design — the toggle
governs bulk spend — but it means "the sweep has the rest" in the inline
fill's status is only true for switched-on courses.

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

## Linked spellings (Turkish harmony — 7 Sep 2026)

### Two foreign words the Turkish span finder refuses

`pin` r6014 ("PIN kodu", 2 rows) and `instagram` r9193 (1 row) are written
with a dotted capital I in Turkish text, and `nlp/turkish.py::answer_span`
lowers `I` to `ı` before matching, so their cards now serve the definition
alone. Left that way on purpose: a fallback to the plain regex for words that
"look foreign" would re-admit the mis-casings the finder exists to catch
(`işık`, `irak` — CHECKS §30). Fix, if the rows matter: give those two an
`alt` entry (`PIN`, `Instagram` are not shapes of the word, so no) — or
retire them; both are past rank 6,000 and neither is a Turkish word.

### One orphan sentence row: `irmak`

`data/tr_sentences.tsv` has 1 row tagged `irmak`, a default-lowercase of
`Irmak` (river, properly `ırmak`), which is not a headword. Inert — the
loader has no vocabulary row to attach it to — and it would go on the next
regeneration. Re-tag it if `ırmak` ever becomes a headword.

### `alternatives` means two things, by course

The column is one mechanism with a per-language meaning: another right
answer by default (Jamaican `likkle`/`little`, English colour/color — grades
CORRECT), the harmony shapes of one word in Turkish (grades CORRECT_SLOPPY
when a sentence fixed the shape). The meaning lives in
`BaseNLP.alternative_result` and its Turkish override, and `tr.md` says not
to put a synonym in the column. Jamaican also copies its `alt` column into
`morphology["spellings"]` — the same list twice; nothing reads the copy. A
course adding an `alt` column should read CHECKS §30 first.

## Romanian's frequency mass sits on three diacritic-stripped twins (10 Sep 2026)

Found by a checker during the definition residue pass, and confirmed against
production. `politia` sits at rank **520** and the real `poliția` at **3,470**;
`tara` at **563** and `țara` at **5,528**; `arat` at **614** while `arăt` is
absent from the file entirely. The stripped twin has inherited the frequency
mass in each case, so the learner meets the misspelling early and the correct
word late or never.

This is not diacritic loss in general — `data/ro_frequency.tsv` carries 321
headwords with `ș`/`ț`, and both correct forms are present at their true
ranks. It is the class `vocab_exclusions.tsv` already handles for Romanian
with nine rows of the same shape (`in`, `ma`, `daca`, `imi`, `inca`, `il`,
`ii`, `neagra`, `lânga`, each "the frequency is the unaccented twin"). The
three are now excluded with twin pointers.

**The checker was right not to swap the lemma.** Re-pointing `politia` at
`poliție` would launder a typo-mass row into a real word (quality rule 10) —
the row's rank is evidence about the misspelling, not about the word. None of
the three has a sentence in the bank, so they were shipping as
definition-only cards.

Same pass, same shape: `tr korum` (1,394) is extraction debris from `koruma` —
both of its sentences are `koruma`/`korumak` and neither contains the form.
Excluded. And `tr hal` (755) was glossed **"covered market"**, the rare
market-hall sense, when the frequent word means *state, condition*
(`ne haldesin?`); re-glossed. That one is a `wrong_sense_gloss` the audit's
own rule does not catch because the gloss is a real sense, just not this
word's common one.

## Eight rows the definition pass refused to define (10 Sep 2026)

The 201–1000 definition pass (CHECKS §36) wrote 1,826 definitions and
**declined 8**, on the standing instruction that an omission is recoverable
and a wrong definition is not (quality rule 30). Every one turned out to be
extraction debris rather than a hard word, which makes the list worth keeping:

- `mi tute` (777) — "masculine equivalent of tūī". A tūī is a bird; there is
  no masculine of it. Cross-language contamination.
- `es i` (783) — labelled "second-person singular voseo imperative of ir",
  but both of the course's own sentences use it as the Roman numeral one
  (Elizabeth I, Carlos I).
- `it finche` (775) — an accent-stripped twin of `finché` whose lemma record
  is Spanish debris (`finca`, no definition).
- `sw kukawa` (979) — given as the infinitive of `-kawa`; there is no such
  standard verb (delay is `-kawia`, stay is `-kaa`).
- `xh izagwityi` (658), `izigxina` (758), and two more with no lemma
  definition and no example sentence.

These are candidates for `data/vocab_exclusions.tsv` rather than for
authoring, but each needs a reader of its language to confirm before a
durable deletion — which is why they are written down instead of swept
(quality rule 27 and the Romanian `-ă`/`-a` refusal).

## The alphabet decks carry a frequency rank they have no business having (10 Sep 2026)

All 166 alphabet rows sit in `vocabulary` with `frequency_rank` **1–40**,
colliding one-for-one with the most frequent real words: Korean rank 1 is both
`그` ("that") and `ㄱ`, rank 2 both `우리` ("we") and `ㄴ`, and so on through
Korean's first forty. That number is a sequence position inside the Alphabet
deck wearing a frequency column's clothes.

**No learner is harmed.** The Learn draw joins `cl.level = v.level`
(`cards.py`), the deck is level A0 and vocabulary is A1+, so the two never mix
at draw time, and the UI switches input mode for a `letter` card.

**Tools are harmed, repeatedly.** Anything reading by rank sees 166 phantom
high-frequency words. It is why `reconcile`'s `gone` column counted the decks
as ungoverned and a sweep nearly deleted all 166 with their 17 learner cards
(#434, the `other` column was added to stop it), and it distorted two separate
measurements during the 10 Sep definition work before being noticed each time.

**The fix is a migration plus a seeder change** — letters should carry a
distinct ordering column, or none — and it is deliberately not bundled with
the card fix (CHECKS §37), which needed no migration and could ship at once.
Until then, every query over `vocabulary` by rank should exclude
`part_of_speech = 'letter'`, and the ones that matter already do.

## 14 words serve a sentence about Tatoeba because it is all they have (10 Sep 2026)

`names_the_corpus` removed 45 of the 59 rows whose sentence is about the
corpus rather than the language (CHECKS §35). The remaining 14 are each
their word's ONLY sentence, and the never-strand rule (§24) keeps them: a
card with no example is not an improvement on one with a bad example. So
until Phase 8 authoring reaches them, these cards still teach the corpus's
press release — `ar` أطاق, بيانات, توصيل, تدقيق · `ca` exemple, droga,
enganxa · `fa` یعنی · `fr` no, saletés · `id` contohnya · `ro` suma · `tl`
sapagkat, kabuuan. Each leaves automatically the moment its word gains an
authored sentence; `test_corpus_self_naming.py` asserts none of them ever
sits beside a usable row. Nothing else is owed here — this is a supply
entry, not a bug.

## A content tool can hang for ever on a dropped pooler session (7 Sep 2026; bounded 10 Sep)

`seed_grammar -l all` printed "OK en" and then nothing for two hours. On
this machine: the process asleep at 0% CPU with one ESTABLISHED socket to
the pooler; on the server: no statement from it, and the pooled backend it
had used `RESET` minutes earlier. asyncpg has no default command timeout,
so a session the pooler drops mid-reply is waited on indefinitely, and
from the terminal it is indistinguishable from a slow course.

**What #433 fixed (7 Sep):** `COMMAND_TIMEOUT` (300 s) on every connect in
the six runbook modules of the day — `base`, `seed_grammar`, `reconcile`,
`prune_sentences`, `seed_alphabet`, `source_data` — guarded by
`test_seeder_command_timeout.py`. It said a dropped session "now fails
loudly". That was reasoned about, not measured, and it was half right.

**What 9 Sep measured:** a TCP proxy in front of a local Postgres that
forwards the handshake and then swallows server→client bytes while keeping
TCP open reproduces the 7 Sep socket exactly. The statement DOES raise
`asyncio.TimeoutError` after `command_timeout` — and then the seeder's
`finally: await conn.close()` hangs for ever behind it. Mechanism, asyncpg
0.31 `Protocol.close()`: on timeout asyncpg sends a cancel request (its
own second connection to the server) and parks a `cancel_waiter` that
resolves when the server answers the cancelled statement; `close()` awaits
that waiter BEFORE it consults the close timeout, and a dropped session
never answers. `Connection.close(timeout=...)` therefore cannot bound it.
What returns: cancel the close from outside (`asyncio.wait_for`; asyncpg
catches the cancellation and marks the connection aborted) — measured
3.0 s with a 3 s bound.

**What 10 Sep showed, on production:** the other shape surfaces by itself.
The owner's per-course loop printed "OK el", then `FAIL en: connection was
closed in the middle of operation` (the pooler closed the socket; asyncpg's
`ConnectionDoesNotExistError`), then `FAIL es/fa/fr: [Errno 54] Connection
reset by peer` from `connect()` — the pooler refused new sessions for about
a minute — then "OK ha" and the loop carried on. A one-minute outage cost
four courses that a pause and a second try would have recovered; `en` was
left with points 1–16 of 43 written until its rerun.

**What 10 Sep review found, against the proxy:** three more holes.
(1) "Cancel the close, then `terminate()`" closes the Python object, not
the socket: `Protocol.close()` sets `closing` before it waits, and
`Protocol.abort()` returns at once when `closing` is set, so neither the
cancellation nor `terminate()` after it touches the transport — the TCP
session to the pooler stays ESTABLISHED for the life of the process, one
per abandoned attempt (the fd was open and the proxy never saw EOF while
`is_closed()` said True). (2) The 7 Sep hang had a front door the command
timeout never closed: `audit.log_change` swallowed every exception, so
when the statement that met the dropped session was the audit INSERT
(once per newly inserted point, once per curated-point proposal), its
`TimeoutError` vanished, the seeder went on to the next statement on the
same connection, and asyncpg awaits the pending cancel's reply BEFORE it
arms any timeout on a later statement — that one waited for ever with no
timeout, no error, no `finally`. (3) `seed_sentences`, step 5 of the
runbook, had neither guard at either of its two connects.

**What this change does:** `close_quietly` in `base.py` — bounded close
(`CLOSE_TIMEOUT` 15 s), then `terminate()`, then abort the transport it
captured beforehand (asyncpg's private `_transport` slot; the docstring
says so) — replaces every `conn.close()` in the seven runbook modules,
`seed_sentences` now among them, and the scan test requires one
`close_quietly` per `asyncpg.connect`. `log_change` re-raises the
dead-session shapes (`audit.DEAD_SESSION`: timeout,
`PostgresConnectionError`, `InterfaceError`, `OSError`) and still swallows
audit-table errors — asyncpg's client-side bad-bind errors among them,
which inherit `InterfaceError` but are `ValueError`s too. `seed_grammar`
retries a course's `load()` on the same shapes (`CUT_OFF`, kept equal to
`DEAD_SESSION` by a test; `_cut_off` makes the same carve-out) after pauses of
10 s then 60 s (`RETRY_DELAYS` — together they outlast the one-minute
outage, so the course in flight when it starts is recovered too; `(5, 30)`
would have saved three of the four), re-using the transformed data. It
prints a `-> code: N points, M drills` line when a course starts so silence
has an owner, `RETRY code in Ns (n/2): reason` when it pauses, and a `FAIL`
reason that is never blank (`str(TimeoutError())` is ""). `transform()`
runs outside the retry: a paradigm gap must fail at once. Content rows are
never doubled by a retry — every content statement is an upsert — but the
audit log can be: a curated point whose proposal is re-walked gets a second
`suggested` entry, the same duplicate a manual rerun after FAIL has always
written. Worst case per course on the timeout shape: each attempt costs
`COMMAND_TIMEOUT + CLOSE_TIMEOUT`, so a course whose every session is
blackholed prints RETRY after ~5 min, twice, and FAIL after ~17 min; the
refused-connect shape fails at once, so there the pauses are the whole
wall clock (70 s). All of it is proven against a real socket by
`backend/tests/integration/test_dropped_session_integration.py`, which
also pins asyncpg's two behaviours as negative controls — the close-hang,
and the unbounded statement after a swallowed timeout. When either fails,
asyncpg fixed it and the matching guard can go.

**What is STILL not fixed:** the drop itself is pooler-side, cause unknown,
and not reproducible on demand — the proxy reproduces its effect, not its
trigger. Only `seed_grammar` retries: `reconcile`, `prune_sentences`,
`seed_alphabet`, `seed_sentences` and `source_data` get the bounded close,
so they fail instead of hang, but their recovery is a rerun (each is one
transaction or all upserts, so a rerun is harmless). The API-key tools
(`ai_check_vocab`, `generate_grammar`, `review_hints`,
`review_translations`, `translate_english`, `harvest_sentences`) still
connect with no command timeout and a bare close: they are not runbook
steps, every run is a paid pass the owner watches, and guarding them is
the same two-line change per connect when one of them is next touched.
Run grammar per course (`refeed.md`) so a failure costs one course.

## `seed_grammar` is the last content tool that writes one row at a time (7 Sep 2026)

`reconcile --apply` used to be: about 6,000 single-row UPDATEs in one
transaction over the Supabase pooler, twenty minutes, silent after the
rollback line — the owner asked whether it was stuck. Fixed the same day
(`APPLY_CHUNK`, UNNEST arrays, a progress line per kind), the third time
this project has paid for one round trip per row after `BaseSeeder.load`
learned it. `seed_grammar` still does it: 274-307 drills per course, one
`execute` each, plus 5,054 hint rows for English. It is the reason a
grammar reseed takes minutes per course. Same fix applies; nobody has
needed it enough yet.

## 1,612 drill rows write the answer marker where the convention is `___`

`data/grammar/{ko,th,hi,he,fa}_grammar.json` store `{{answer}}` inside the
drill's `transliteration`. The card now substitutes a blank when it serves
them (CHECKS §32), so nothing reaches the screen, but the files are still
wrong and a new drill written by copying a neighbour inherits it. A data
pass should rewrite them to `___`; until then the card fix is load-bearing.
No guard forbids the marker in the data on purpose — a test that failed on
1,612 committed rows would have to be born red.

## A dormant override fires the day someone adds the headword (7 Sep 2026)

FIXED the same evening, recorded because the failure mode is not obvious.
`gloss_overrides.tsv` had 28 rows naming a word its course's frequency file
did not carry. They shipped nothing, so they read as harmless — until
Yoruba `n` was restored to the file (a real 1SG pronoun an early junk sweep
had deleted) and woke an override written for `ń`, the progressive marker.
Production served the pronoun as "is/are doing" until a read-back caught it.

The six Latin rows were the opposite of junk — full definitions where the
file had one-word stubs ("not", "day", "son", "we", "if", "why") — so they
were re-keyed to `nōn`, `diēs`, `fīlius`, `nōs`, `sī`, `cūr`, which also
repairs six top-50 Latin cards. The other 22 were superseded by better
glosses on the marked headword, or were alphabet-letter debris, and went.
`test_reconcile_overrides.py::TestNoDormantOverrides` now makes the state
impossible rather than merely recorded.

## 101 committed sentence rows now point at a retired word (7 Sep 2026)

Retiring the 535 letter-debris and unmarked-twin rows leaves 101 rows in
the committed sentence banks tagged to a word that is no longer drawn —
mostly Turkish (`Dükkan tüm gün açık.` under `dükkan`, the misspelling of
`dükkân`) and German (`grosse`, the Swiss spelling of `große`). They are
inert: no card reaches them. They are NOT free supply for the correct
twin either, because the sentence text carries the wrong spelling — moving
`Dükkan tüm gün açık.` to `dükkân` would hand that card a sentence it
cannot blank (rule 46) and teach the misspelling besides. Correct the text
and re-tag, or drop the row, in a sentence pass. Counted per course by
joining `vocab_exclusions.tsv` against `data/*_sentences.tsv`.

The rest of the tr letter rows show why the exclusions are right rather
than wrong: the "sentences" under `tr i`, `tr c`, `tr g` are ordinary
sentences that merely contain a capital letter (`İş iyi.`, `C vitamini`,
`G.N.P.`) — extraction noise, never teaching material for a headword.

## Two content defects found while auditing something else (7 Sep 2026)

Both surfaced when a checker read the letter-debris sweep; neither is in
its scope, and neither is fixed.

- **Romanian rank 4 `si` is glossed "si (musical note B)".** Rank 4 of a
  shipped course cannot be a musical note: the frequency belongs to `și`
  ("and"), typed without its comma-below. Same class as the ro rows already
  in `vocab_exclusions.tsv` ("the stated meaning cannot carry this rank"),
  but this one is IN the file, so it needs a definition and possibly a
  re-spelling, not an exclusion. Rank 211 `i` glossed "and" is archaic
  Romanian and probably the same fault.
- **Catalan has no apostrophe headwords at all.** `data/ca_frequency.tsv`
  carries none of `l'`, `d'`, `m'`, `t'`, `s'`, `n'`, `'l`, `'m`, `'s`,
  `'ns` in 469 KB, while French and Italian carry theirs in the top 60.
  `ca.md` names elision and clitic clusters as one of the three features
  that dominate drill quality and calls the apostrophe the character
  authors get wrong most. A coverage gap, not debris.

## Rows production serves that no committed file governs (7 Sep 2026)

40,683 vocabulary rows are in production and owned by no committed source:
39,004 from older generations of the big-course lists (ru 5,913 …), 678
unmarked twins of file words (la `amo` beside `amō`), 165 single letters
glossed "the fourth letter of the Catalan alphabet". (The count was 40,861
until `gone` learned that a course has more than one source: 166 of those
rows are alphabet-deck cards from `seed_alphabet` and 12 are curated
starter words. Retiring "the letters nothing governs" would have deleted
seven alphabet decks — ask what a maintenance list CONTAINS before acting
on its size.) The reconcile REPORTS them (`gone`) and the
retire step cannot see them because they are not in `vocab_exclusions.tsv`.
They are live cards inside the decks' rank range, ungoverned by every check
in `docs/quality/`. Owner decision D (`owner-actions-2026-09-07.md`); the
cheap first step is to add the 331 glyphs to the exclusions file. Rule 27's
corollary, learned here: **a word deleted from a TSV by hand is still in
production, forever, unless it is also in the exclusions file.**

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
