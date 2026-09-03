# Owner notes, 3 September 2026 — consolidated brief, ordered by ease

*Seven notes the owner wrote in one sitting, each verified against the
repository on the day, turned into items an AI session can pick up in
order. Easiest first. Every "what exists" line names the file so the next
session does not have to rediscover it. Where the owner asked for an
opinion, the item carries a recommendation and the reasoning.*

Owner decisions already taken for this brief: it lives here and is
maintained; recommendations are included; the Contribute → Workshop rename
is labels only (the `/contribute` route stays so old links keep working).

---

## 1. Rename "Contribute" to "Workshop" — labels only

**Shipped 3 Sep 2026.**

**Effort: an hour.** Six locales, a handful of hardcoded strings, two tests.

What exists: the workspace header already reads "Workspace · Spanish"
(`frontend/src/features/contribute/ContributorPage.tsx:903`) and the More
page link already says "Staff workspace →" (`dashboard.contribute`, six
locales). The word "Contribute" survives in:

- `settings.tabs.contribute` in all six `frontend/src/i18n/locales/*.json`
  (the Account page's tab set, `SettingsPage.tsx:64,94,486`);
- the hardcoded tab labels `'Contribute' | 'Review' | 'Admin'` at
  `ContributorPage.tsx:950-957` (and `WorkspaceTab` at `:762`);
- `SettingsPage.tsx:496-510` — the "Contribute" heading and "Open the
  workspace" button; `RoleGuide.tsx:36` "How contributing works";
- tile hints in `frontend/src/lib/reviewTaxonomy.ts:103,125`;
- tests `frontend/src/__tests__/ContributorPage.test.tsx:154,306`.

Work: change the labels to "Workshop" (the first tab becomes "Author" or
"Build" — "Workshop / Review / Admin" reads as the workspace's name, not a
tab). Keep `?tab=contribute`, the route, and the type names. Update the two
tests and the two docs lines (`DEBT.md`, `LEARN.md`) that say "Contribute
tab".

## 2. Speak corrects a little too much

**Shipped 3 Sep 2026** (prompt rule and summary-model fix; the optional flag is still open).

**Effort: half a day** for the prompt fix; a day with the setting.

What exists (`backend/services/speak.py:229-290`): one model call per turn
returns the reply *and* a structured error list. The prompt already says
"Only real mistakes… An empty list is a good answer" and "Never say 'good
job'", and coach mode shows at most one correction per turn
(`backend/routers/speak.py:535-538`); flow mode shows none until the end.

Why it still corrects: nothing in "How you talk" tells the **reply** not to
recast the learner's sentence. A partner that echoes the fixed form ("Ah,
*fuiste* al mercado…") is correcting, whatever the errors list says, and
that is the teacherly reflex the owner is seeing. The errors list and the
reply are two different channels; only one of them was told to hold back.

Work:

1. Add two lines to `_system_prompt` under "How you talk": *do not repeat
   or recast what they said in corrected form — respond to the meaning;
   the mistake goes in the list, not in your reply* — and *if they were
   understandable, treat them as understood*. Pin it with a test in
   `backend/tests/test_speak.py` that the prompt carries the rule (the
   existing tests assert prompt content the same way).
   Pass `session["mode"]` into `_system_prompt` (it does not receive it
   today) so coach mode can say instead "at most one correction, and only
   where the errors list puts it — your reply still answers the meaning".
2. Optional: "no corrections — I just want to talk". Two shapes: a third
   mode `chat` in `_MODES` (`routers/speak.py:69-77`, migration-free since
   `speak_sessions.mode` is text) or a per-session `corrections: bool`
   flag (a nullable column) that drops the "What you record" block from
   the prompt and skips the error grouping at `/end`. Prefer the flag:
   `mode` is load-bearing in the summary reader and a third value touches
   every branch. Picker: a checkbox under the mode cards
   (`SpeakPage.tsx:468-508`), six locales.
3. While there: `routers/speak.py:580` runs the end-of-session summary on
   the chat model instead of `settings.tutor_summary_model`, which
   `summarize_speak_session` already defaults to. Drop the override — the
   summary is a fixed-rubric job and the tutor's own summarizer already
   uses the cheaper model.

## 3. MCPs worth connecting

**Effort: none now.** Recommendation: **connect nothing for the app; one
for the owner, later.**

There is no MCP anywhere in the repo, and the app's integrations (Anthropic,
Supabase, Azure Speech, Stripe, Resend, Sentry, DigitalOcean, Redis,
Apertium) are all called through their SDKs or HTTP from `backend/` —
that is the right shape for a server, and MCP would add a hop with no gain.
MCP is a tool surface for *agent sessions*, so the question is which
sessions would use one:

- **A Postgres/Supabase MCP for the owner's own Claude sessions** — the one
  that would earn its place, once the owner is asking "which accounts
  hit their pool this month" or "how many change requests are open per
  language" in chat. Read-only credentials, production replica if one
  exists. Not before then.
- **Stripe MCP** — only once money is on, and only if the owner would
  rather ask than open the dashboard. Everything the app needs from Stripe
  is already wired.
- **Sentry MCP** — the same: useful for an agent triaging errors, but the
  Sentry DSN is currently empty in production, so there is nothing to
  connect to yet.

Nothing else on the market fits: there is no ticketing system, no CI beyond
GitHub Actions (already reachable through the GitHub tools these sessions
use), and no analytics vendor.

## 4. Are the quality agents using the skills, and updating them?

**Steps 1 and 2 shipped 3 Sep 2026** (`services/quality_rules.py`; brief on the drill and example makers). Step 3 is a practice, recorded in `docs/quality/CHECKS.md` → "Prompt ↔ rule parity". Note: the translation lane's target is the support locale, so the course brief does not apply there.

**Effort: a day** to close the two gaps that matter; the third is a
practice, not code.

What exists, precisely:

- **Runtime AI checks do not read the skills.** Every runtime prompt is an
  inline Python string: drill/example makers and auditors in
  `backend/services/generate.py:181,373,629,764,1124`; the translation
  maker/checker/sentence-checker in `backend/services/translate.py:86,105,118`;
  definitions in `define.py:138,174`; the advisory semantic reviewer in
  `semantic_check.py:74,118`. Nothing in `backend/` opens
  `.claude/skills/quality-rules/SKILL.md` or `docs/quality/<code>.md`. That
  is by design — rule 26 of the skill says maker–checker runs *in-session*,
  never on the API key — but it means the 42-rule digest governs the
  *Claude Code sessions* that clean data, not the runtime models that
  generate it.
- **The per-language briefs reach some prompts, not others.**
  `backend/services/tutor_skills/<code>/SKILL.md` (27 languages) is
  appended in `semantic_check.py:63,107`, `seeder/generate_curriculum.py:131`
  and `seeder/generate_grammar.py:96` — and **not** in the drill/example
  makers, the auditors, or the whole translation lane. An Arabic example
  sentence is generated with no Arabic brief.
- **Nothing feeds findings back into the skill or the docs by code.** The
  loop is a written obligation (`quality-rules/SKILL.md` rule 3 and
  "Maintaining this skill"; `docs/quality/CHECKS.md` "Adding a check"). The
  one machine ratchet is `data/quality/baseline.json`, enforced by
  `backend/tests/test_content_quality.py` — findings become *numbers* that
  cannot regress, never prose.
- **Drift already visible:** the makers' CEFR "complexity bar"
  (`generate.py:121`) and the auditors' (`generate.py:620,756`) are
  independently worded strings.

So the honest answer to "are they using the skills": the in-session review
agents are (the skill loads in every content session, and the recent
cleaning passes updated `docs/quality/<code>.md` and the skill as they
went); the runtime generators are not, and were never wired to.

Work:

1. **One rules module.** Move `_DIVERSITY_RULES`, `_complexity_rule()` and
   the auditors' `level_rule` into `backend/services/quality_rules.py`, and
   have both makers and both auditors import from it, so the bar cannot
   drift. Add a test that the maker's and auditor's bar text is the same
   function's output.
2. **Give the makers the language brief.** Append `_load_skill(code)` (the
   tutor brief, already `@cache`d, `tutor.py:76`) to the drill and example
   makers and the translation sentence maker, the way `semantic_check.py`
   already does. Watch the prompt size — SKILL.md is capped at 2,500 chars
   by test, so it is affordable per batch.
3. **Keep the feedback loop human, but make it visible.** Do *not* have
   runtime agents edit `SKILL.md` — a prompt rewriting its own rules from
   its own rejections is how a rule set drifts toward whatever is easiest
   to pass. Instead, add a "rules touched" line to the review-session
   protocol: a cleaning session ends by listing which `docs/quality/<code>.md`
   sections and which skill rules it changed, and the PR body carries it.
   The `explain-decisions` skill already writes to `docs/decisions/`; the
   same habit, one line per rule.

## 5. Translation: is a specialist-agent taxonomy worthwhile?

**Checker tier (5.1) shipped 3 Sep 2026; the non-vocab review queue (5.2) is open.**

**Effort: a day** for the two real gaps. Recommendation: **no new agent
layer; fix the tier gap and give every kind a review queue.**

What exists is already the taxonomy the owner describes, built and tested:

- **Maker → checker, two separate calls** (`translate.py:233`
  `maker_check_batch`: `make_glosses` then `check_glosses`, verdict
  `ok` / `fixed` / `reject`, an unparseable verdict defaulting to reject).
  Sentences and UI text add a mechanical gate after the checker
  (`translate_checks.py`: answer leaks, identity renderings, blank
  integrity, locale punctuation).
- **Rejects are kept, not dropped**: vocabulary rejects land in
  `translation_reviews` with the proposal retained, surfaced as the
  "AI translations" queue with Approve / Reject / Dismiss and, since #386,
  the card editor.
- **Counts reach the loading screen exactly as the owner describes**:
  `GET /api/review/readiness` (`routers/review.py:211`,
  `repositories/cards.py:1192`) returns per-lane `total / ready / pct /
  cards / cards_ready / start_cards / ready_enough`, the word pairs for the
  match game, and `fill` (the inline fill's status); the inline fill
  (`auto_translate.py:262 fill_start_batch`) translates the session in
  reading order on the web worker and the 15-minute sweep is the backstop.
- **Attempt ledger with backoff** (`auto_translate.py:78 RETRY_BACKOFF`,
  `_backoff_sql`, `_settle`): a failure is paced, never final.

A "translation agent that returns the set count, then a QA agent" would
be these same two calls with new names. What a separate agent framework
would add is latency (a third hop), a second place for prompts to drift,
and orchestration code to maintain; what it would not add is quality,
because the checker is already a separate model call with its own charter.
Specialisation is worth doing **inside** the existing pair, on two points
the exploration found:

1. **The checker is not one tier up in the locale lane.** `models.py:26`
   states the doctrine — a checker verifies on a stronger model than the
   maker ("never self-certify") — and the generation lane honours it
   (`sentence_checker` → Opus). The translation lane does not:
   `auto_translate.py` never passes `maker_model` / `checker_model`, so the
   sweep, the demand lane and the inline fill run maker **and** checker on
   `resolve_model("translate")` — the same Sonnet. Only the CLI
   (`seeder/translate_english.py --maker-model/--checker-model`) can split
   them, and `.env.example:107-108` documents that as the intent. Fix: add
   `translate_checker: "tutor_model_low_resource"` to `TASK_MODELS` in
   `models.py` and make `check_glosses` and the sentence/text checkers
   (`translate.py:212, ~359, ~455`) default to
   `resolve_model("translate_checker")`. `resolve_model` already refuses
   per-language overrides on that field, so no call site changes and no
   admin dial can weaken the floor. Pin it with a test that maker and
   checker resolve to different settings fields. Cost: the checker sees
   only what the maker produced, ~25 rows per call — cents per session.
2. **Only vocabulary rejects have a queue.** A rejected drill, explanation,
   grammar title or example sentence is simply not written and waits for
   the backoff — nobody sees it. Extend `translation_reviews` with a
   `kind` + `target_id` (migration) or add a parallel table, write the
   reject and its reason from `_apply()`'s siblings, and list them in the
   same panel grouped by kind. The panel already carries the card editor,
   so the reviewer can fix the English source on the spot.

Then the taxonomy is: **maker (Sonnet, with the language brief from item
4) → checker (Opus, own charter) → mechanical gate → review queue for
anything rejected**, per kind. That is the whole "team"; it just needs to
be the same team in every lane.

## 6. Tutor: are personas updated with language insights, and what phases out?

**Memory bounds and "forget everything" shipped 3 Sep 2026** (steps 1–3 of the memory work). Open: the persona fold-in script and REFERENCE generator, and the retention sweep (step 4).

**Effort: two days** — one for bounding memory, one for the fold-in tooling.

**Personas.** Each language's tutor is `backend/services/tutor_skills/<code>/`:
`SKILL.md` (always in the prompt, ≤2,500 chars by test), `ERRORS.md`
(common interference errors) and `REFERENCE.md` (the grammar path, generated
from `data/grammar`) — the latter two loaded on demand through the
`consult_reference` tool. They are hand-written, `@cache`d at import
(`tutor.py:76` — a restart picks up edits), and **nothing updates them from
the cleaning work**. The one documented bridge is manual:
`docs/ingestion-interchange.md:25` defines `ERRORS.extracted.md` as "a
review artifact — a human folds it into `ERRORS.md`", and only French has
ever had one. So the answer is: the tutors have *not* been getting the
language insights, and there is no mechanism by which they would.

Work:

1. Make the fold-in a script, not a habit: `scripts/tutor_skill_digest.py
   <code>` reads `docs/quality/<code>.md` (the per-language standard the
   cleaning passes maintain) and the language's open review notes, and
   emits an `ERRORS.extracted.md` diff for a human to accept into
   `ERRORS.md`. Add a test that every language with a `docs/quality` file
   has an `ERRORS.md` newer than its last `docs/quality` edit, or a listed
   exemption — that is the "have they been updated" check, made
   mechanical.
2. `REFERENCE.md` has no generator in the repo (ROADMAP says "regenerate
   when paths change"). Write the generator and pin it with a test against
   `data/grammar`, so the tutor's map of the course cannot drift from the
   cards.

**Memory, and what phases out.** Between sessions the tutor keeps: a global
profile and a per-language profile (JSONB, each fact tagged `stated` or
`inferred`), a rolling `session_summary` (rewritten, not appended, each
session end), an append-only `tutor_sessions` log, and it re-queries the
12 weakest SRS items every turn. Within a session, history is the last 40
messages (`MAX_HISTORY_MESSAGES`, truncation — the 41st simply drops, no
mid-session summary), 4,000 chars each.

What is **not** bounded, and will matter in production:

- the **number of profile facts** — nothing caps, expires or decays a key;
- **fact values that grow into lists**: writing a key again with a
  different non-stated value appends (`merge_remembered`,
  `tutor.py:613-619`, deliberately, "so the tutor can record several error
  patterns") with no cap and no recency, so a mistake from March rides in
  every prompt in September;
- the whole profile JSON is dumped into every turn's system block
  (`_format_memory`, `tutor.py:399-422`) — growth here is a per-turn token
  cost forever;
- `tutor_sessions` and `tutor_usage` rows (read-bounded only).

There is **no pre-flight estimate** of the assembled prompt. Work:

1. Cap list-valued facts at the **5 most recent** (`[*existing, value][-5:]`
   — newest wins, matching the existing "learner's word beats inference"
   rule); cap facts per scope at ~40, evicting the oldest **inferred** key
   first (add a `_touched: {key: iso}` map beside `_sources`; `stated`
   facts and `IDENTITY_KEYS` are never evicted); cap `session_summary` at
   ~2,000 chars, truncated at a sentence boundary on write — the
   summarizer's 1,024-token output cap is not a cap on the stored column.
2. Add a character budget to `build_system_blocks` (block 1 only — block 0
   is the cached charter) that logs a warning at 12k chars and trims the
   oldest list entries first. Log the size into `tutor_usage` so the admin
   cost view can chart prompt growth per learner.
3. Extend the "What your tutor remembers" panel: show the session summary
   and the focus list (read-only, deletable) and add **Forget everything
   for this language** — `DELETE /api/tutor/memory/all?language_id=`,
   clearing both profile scopes' facts, `_active_focus` and
   `session_summary`, and leaving `tutor_sessions` (usage history; say so
   in the copy). Today a learner can delete facts one by one but cannot
   see or clear the summary, the focus list, or the session log.
4. Retention: prune `tutor_sessions` older than 180 days and `tutor_usage`
   older than 13 months in the existing nightly sweep.

## 7. Working through feedback: popup, sliding window, and markdown cards

**7c phase 1 (the editor preview) and 7a (card in every card-bearing queue, `a`/`r`/`u`/`d` hotkeys in focus mode, edit history behind a toggle) shipped 3 Sep 2026.** Open: 7b (the popup, only if asked for on the phone), the optional cross-queue stream, and 7c phase 2 (markdown) which waits on the backtick guard.

**Effort: three to four days**, in three separable pieces. Recommendation:
build on what shipped this week rather than a new modal.

What exists after #386: every focusable queue is a one-at-a-time stepper
(`useFocusList.tsx`: ‹ ›, arrow keys, the next item slides in when you act),
and three queues — learner feedback, change requests, AI translations —
render the full card inline with an editor (`ReviewedCardView.tsx`). Votes
exist only on change requests. `CardHistory.tsx` (the edit timeline with
roll-back, backed by `GET /api/contribute/review/history/{type}/{id}`) is
mounted only in `ExamplesEditor.tsx:167` for example sentences — no queue
shows it for a card. No queue opens a popup.

**7a. The sliding window (a day).** The stepper *is* the sliding window;
what it lacks is reach and speed.

- Mount `ReviewedCardView` in the remaining queues that name a card:
  review notes (`IssuesPanel`), suggestions (`SuggestionsPanel`, as the
  "current" side of its diff), tester recommendations, generated drills.
  The server already attaches cards via `load_cards` for any row with
  `target_type` / `target_id`; those queues need the two fields exposed.
- Action hotkeys in focus mode: `a` accept/approve/resolve, `r` reject,
  `e` edit, `u`/`d` vote — registered in `useFocusList` beside the arrows
  (it already ignores keys while typing).
- Mount `CardHistory` under the card in every queue that shows one, so
  "what changed here before" and roll-back are one click away.
- Optional: an "everything for this language" stream that walks all queues
  in taxonomy order — one `useFocusList` over a concatenated list. Cheap
  once the panels share the card view.

**7b. The popup (half a day, if still wanted after 7a).** Clicking the
feedback text opens the same `ReviewedCardView` in a dialog. The app has
no shared dialog primitive (`SuggestEditModal`, `Annotatable`'s popover and
the walkthroughs each roll their own), so this means extracting one. The
inline card makes it mostly redundant; do it only if reviewers ask for it
on the phone, where the inline card pushes the actions below the fold.

**7c. Markdown cards, "like Anki" (two days, phased).** The confusing
rendering has a specific cause: explanations are plain text, learners see
them **typeset** by `components/ExplanationView.tsx` (term/gloss tables,
arrow derivations, `label: forms` chips), and contributors edit a raw
`<textarea>` with **no preview** (`ContributorPage.tsx:553-578`). The
reviewer never sees what the learner sees. Phase it:

1. **Preview first, zero risk.** Render `ExplanationView` beside every
   explanation/culture-note textarea in the editor and in
   `ReviewedCardView`'s editor. Most of the "confusing" cases are the
   typesetter's shapes being invisible to the person writing them.
2. **Then decide on markdown.** `react-markdown` + `remark-gfm` are
   installed but confined to the tutor chat; there is **no sanitiser
   anywhere** (no dompurify / rehype-sanitize / bleach), explanations are
   model- and contributor-authored, and `docs/quality/jam.md:129` reasons
   from "a backtick prints literally on the card". Moving to markdown means:
   a whitelist subset (bold, italic, lists, tables, links through the
   existing `services/references.py` URL rules) rendered with
   `rehype-sanitize`; keeping `ExplanationView`'s three typeset shapes as a
   pre-pass, since markdown has no equivalent for them; sanitising on the
   server too (a `services/markdown.py` allow-list beside `references.py`,
   because seeders and the AI write the column, not only the editor); and
   a `test_content_quality.py` guard that counts backticks, asterisks and
   underscores in glosses and explanations and fails on new ones — after
   this change a backtick *renders*, which silently alters every gloss
   that ever carried one, so `docs/quality/jam.md` and the quality-rules
   skill must stop assuming it prints literally. Colour and other
   Anki-style styling then come through a small set of allowed classes.
3. References already have their own model (`reference_links` jsonb,
   `ResourceList.tsx`) — leave them out of the markdown body.

---

## Suggested order and dependencies

1 → 2 (prompt + summary-model fix) → 5.1 (checker tier; shares
`models.py` with 2) → 4 → 6 → 7c phase 1 → 7a → 5.2 → 2 optional flag →
7c phase 2 → 7b / the cross-queue stream. 7c phase 2 must not start before
the backtick guard and the `jam.md` update are in place.

---

## Verification, per item

1. Grep for "Contribute" in `frontend/src` and the six locale files
   returns only code identifiers; `npx vitest run` green.
2. `backend/tests/test_speak.py` pins the no-recast rule; a manual session
   in coach mode shows the partner answering the meaning, not the form.
3. Nothing to verify — a decision.
4. `test_content_quality.py` still green; a test asserts the maker and
   auditor share one complexity bar; a generated Arabic example batch's
   request carries the Arabic brief (log the prompt length).
5. `auto_translate` unit tests assert `check_glosses` is called with the
   checker model; the integration matrix test still converges; a rejected
   drill appears in the AI-translations panel with its reason.
6. Tests for the fact caps and summary truncation; a long dev-mock
   session's prompt size is logged and flat; the memory panel shows and
   clears the summary.
7. Every focusable queue renders a card where one exists; hotkeys covered
   by `useFocusList` tests; the editor preview matches `LearnPage`'s
   rendering for the same text.
