# Guardrails, telemetry, and a Content Health panel — across all 27 courses (18 Sep 2026)

**For review before anything is built.** The owner's ask: *"a plan that adds
guardrails for accuracy and relevancy and telemetry across the board for all
languages … add this to the admin panel — something to showcase errors and
problems like this."*

Everything in §1–§2 was read from the code this week, not remembered. §3–§8
is the proposal. §9 is what the owner has to decide. Nothing here spends the
API key or writes to production until a decision in §9 says so.

---

## 0. The one-paragraph version

Every defect that reached a learner this month was found by a person reading
a card, and every one of them passed every automated check we have. That is
not because the checks are bad. It is because **each of them asks whether a
row is well-formed, and none of them asks whether it is right.** The
instruments that *did* find the defects — the Arabic register judge, the
English sense audit, the gloss-faithfulness audit — were models reading the
row, calibrated against a gold set, run by hand in a session, and thrown away
afterwards. Nothing in the app stores a quality number with a date on it, so
nothing can show a trend, and the admin panel has no quality surface at all.
The plan is to make those judges permanent and scheduled, store every verdict
and every audit run, close the two loops that currently lose human fixes, and
put one panel in front of it — shaped like the deployment panel that already
answers "is the database in step with this build?", but for content.

---

## 1. The evidence: what reached learners and which layer should have caught it

Twelve defect classes, all from this month. "Layer" is where in the pipeline
the check belongs: **1** when a model writes content, **2** when content is
admitted to a file or the database, **3** when existing content is audited.

| # | What a learner saw | Should have been layer | Why it was not caught | Found by |
|---|---|---|---|---|
| 1 | A Russian alphabet card serving "Oh sod." as its example, because the letter matched inside an ordinal suffix | all three, by construction | every rule asks *is this sentence good for this word*; none asks *should this card have a sentence at all* | a person, CHECKS §37 |
| 2 | Two grammar tables each missing the row an editorial instruction had described — the instruction shipped as the row | 2 | no gate read the text as a reader would | owner's question, CHECKS §39/rule 64 |
| 3 | The tutor speaking Egyptian to an Arabic speaker learning English | 1 | the register pin covered the language *taught*; the support locale was told "converse in Arabic" with no register | a beta reviewer, #476 |
| 4 | Three Arabic vocabulary definitions in colloquial Arabic (`شاف`, `مراية`, `مليان`) | 1 and 3 | translators unpinned until #473; no audit reads the live locale tables | judge, #477 |
| 5 | Qurʾān 18:24 and a hadith as everyday example sentences | 3 | §1.4 names the class; no rule looks for it | judge, #477 |
| 6 | `sadly` defined "in an unfortunate way", `runner` as a smuggler, `cub` as an awkward youth — 8% of English definitions, 15–17% in ranks 2,001–6,000 | 3 | `wrong_sense` fires only inside rank 1,000 and only for letter-names; its band was chosen for a different defect | judge, #489 |
| 7 | 25% of Arabic glosses on English cards diverge from the sense the English definition names; `whistle` glossed with the object you blow | 1 and 3 | the maker charter says "match the part of speech"; nothing checks it; no rule reads glosses at all | judge, #489/#490 |
| 8 | 27,794 definitions saying "first-person singular of X" and no meaning, resuming at exactly rank 201 | 3 | no rule; the band edge of a previous pass | owner, CHECKS §36 |
| 9 | The audit grading text nobody is shown — the file column instead of the override production serves; 1,734 rows differ | 3 | the override file had a write path to production and no read path into the audit | CHECKS §36a |
| 10 | 544 headwords missing a mark their language requires; Romanian `și` at rank 4 held by a misspelling | 3 | nothing measured orthography against the dictionaries already declared in the pipeline | CHECKS §38 |
| 11 | 874 Yoruba headwords about to ship twice — `ati` and `àti` as separate cards — after a file rename | 2 | the database has no rename; `reconcile` reports the orphan and by design never deletes | owner's reconcile run, #482 |
| 12 | A reviewer's definition fix reverted by the next `reconcile --apply` | 2 | `_edit_vocab_card` never sets `vocabulary.curated`; reconcile compares DB to file with no edited-since check (`reconcile.py:338`) | this plan's reading, §2.5 |

Two structural facts sit under the table:

- **The tripwire we had for #3–#5 was measured at under 5% precision** and
  flags one row in 13,025. A regex cannot read a sentence.
- **The judges that found #3–#7 have no CI path and no schedule.** Four of
  the six audit modules under `backend/services/quality/` cannot run in CI —
  `audit_wrong_lexeme` because its dictionaries are gitignored,
  `audit_locale_rows`, `register_pass` and `db_snapshot` because they need a
  live database or a key. They run when someone remembers.

---

## 2. What exists today, precisely

Read from the code on 18 Sep. Kept short; the file:line references are the
audit trail.

### 2.1 Layer 1 — generation

Strong, and mostly closed this month. Every one of the 35 `messages.create`
sites in `backend/services/` is walked by
`test_every_model_call_carries_the_register_pin` (`test_quality_rules.py:95`);
the makers carry the CEFR bar, the diversity charter and the per-language
brief (`quality_rules.py:33–113`); every checker resolves one model tier up
(`models.py:28`); output schemas are enforced (`generate.py`, `define.py`,
`translate.py`); accepted AI content lands `reviewed=false` (`generate.py:14`).
Rendering gates exist for translations (`translate_checks.gate`:
answer-leak, cloze-altered, identity echo, locale punctuation).

Gaps: `REGISTER` has **one entry** (`ar`); Persian, Hindi, Greek and Tagalog
have the same standard/colloquial shape and are unmeasured. The translation
checker does not verify part of speech although its charter demands it. The
definition maker takes the dictionary's first sense, and the dictionary's
sense order is not frequency order.

### 2.2 Layer 2 — admission

Thorough, entirely owner-run. `apply_authored_sentences.py` refuses any row
the card cannot blank; `enforce_sentence_floor.py` drops fragments but never
strands a word; `prune_sentences.py` writes a rollback file before deleting;
`reconcile.py` never deletes vocabulary and retires bidirectionally from
`vocab_exclusions.tsv`; `apply_grammar_explanations.py` refuses anything the
renderer would mangle; `apply_register_fixes.py` refuses a rewrite that
removes the headword and refuses a culture note not in the owner's shape.

Gaps, and two are bugs:

- **A Workshop fix to a vocabulary definition does not survive reconcile.**
  `_edit_vocab_card` (`contributor.py:4435`) updates `translations` and never
  sets `vocabulary.curated`; `reconcile --apply` computes `gloss_changes` as
  "DB ≠ file" (`reconcile.py:338`) and writes the file back. Grammar is
  protected (`curated` set at `contributor.py:2533`); vocabulary is not.
- **Retitling a grammar point re-inserts the original beside it**, because
  `seed_grammar` upserts `ON CONFLICT (language_id, title)` and finds curated
  points by title.
- **"Accept" on a change request applies nothing.** `resolve_request` is one
  `UPDATE … SET status` (`change_requests.py`). The suggestion is not applied,
  no content table is touched, no `content_change_log` row is written.
- **A headword rename in a file is an add plus an orphan in production**
  (rule 73), and nothing detects it until the owner reads reconcile's `gone`
  column.
- The gates are five scripts that each re-implement blank-ability, length and
  duplication. One definition per check would be safer than five.

### 2.3 Layer 3 — audit

`audit_content.py`: 9 fail-level rules ratcheted against
`data/quality/baseline.json` in CI (`test_content_quality.py:45`), 4 warn,
5 report. Reads **files**, never the database — the docstring of
`db_snapshot.py` records 18,735 production definitions diverging from the
files while the audit passed. The judges — `register_pass.py`, and the sense
and gloss passes in `data/eval/` — exist as scripts and evidence files.

Gaps: no rule reads a sentence for meaning; `wrong_sense` stops at rank
1,000; `relation_only_gloss` has a zero target but is report-level; nothing
reads the live locale tables except `audit_locale_rows`, by hand.

### 2.4 Telemetry

| exists | per language | time | aggregated | shown |
|---|---|---|---|---|
| `tutor_usage` — every model call, tokens, kind (`repositories/tutor.py:99`) | yes | yes | AI-costs window total | AI costs panel |
| `content_change_log` — every staff edit, before/after | yes | yes | never | per-card history only |
| `grammar_points.ai_check_status`, `vocabulary.ai_check_status` — `pass`/`concerns` per row | yes | `ai_checked_at` | never | per point |
| `data/quality/baseline.json` — 11 fail counts | yes | **no** | — | — |
| queue depths (`review_inbox_by_language`, 18 queues) | yes | **no** — `count(*)` now | per language | inbox, bell, daily email |
| learner reports (`card_feedback`, `app_feedback`, `card_change_requests`, `point_review_notes`) | yes | yes | open-count only | five panels |
| Sentry, both ends | — | yes | — | no-op without a DSN |

**There is no table, endpoint or panel for content quality, and no content
metric anywhere carries a date.** `tutor_usage` records no latency, outcome,
retry or fallback. `card_feedback` on a grammar card records the *point*, not
the drill the learner saw, and no channel except `translation_reviews`
records the locale the reporter was reading in — which is why the reviewer's
"the Arabic is Egyptian" arrived as a chat message and not a row.

### 2.5 The admin surface

`ContributorPage` → Admin tab → **Insights / Languages / Content / People /
Rollouts / Costs**. `DeploymentPanel` sits in Rollouts and answers "which
build, is the schema in step" from `/api/health` and `/api/health/schema` —
**both unauthenticated; the gating is UI-only.** The nearest thing to a
quality view is `GenerationPanel`'s coverage table, which measures whether a
row *exists*. `GET /api/contribute/admin/audit` (a language-wide change feed)
exists with no frontend caller. Roles are `contributor / trial_reviewer /
reviewer / ambassador / admin`; there is no `staff` role, only "holds any
role".

### 2.6 The runner

The app already runs four background loops from FastAPI's lifespan
(`main.py:128–147`): reminders, the admin digest, retention, and
`auto_translate_loop` — which **spends the production API key server-side**,
behind `auto_translate_loop_enabled` and capped by
`auto_translate_words_per_cycle = 50` (`config.py:62–65`), with a wake event
for on-demand runs. A nightly quality job is a fifth loop in that exact
shape. There is no external scheduler, CI has no production access, and the
kaikki dictionaries are local-only — so file-and-dictionary audits stay on
the owner's machine and database judges run in the app.

---

## 3. Seven principles the design follows

1. **Judge the row, not its shape.** A model reading the row is the
   instrument for meaning, register and sense. Regexes stay as tripwires.
2. **Calibrate before trust, and expect the first result to be a prompt
   defect.** The register judge went 53/56 → 56/56 by fixing the question it
   was asked. Every judge question gets a gold set and three gates (§3.2 of
   the register programme) before its verdicts can do anything but report.
3. **Nothing computed is thrown away.** Every audit run, judge verdict,
   reconcile survey and queue depth is a row with a timestamp and a build sha.
4. **Report-only until precision is measured; gate only what clears 95%.**
   A false alarm has cost this programme more than a miss every time.
5. **Never self-certify, never write production from a judge.** Verdicts are
   queue items; a person disposes; the owner runs writes.
6. **The support locale is a corpus of its own.** Every metric is keyed by
   `(language, locale)`, never by language alone.
7. **Fix upstream.** One English definition repair fixes nine locales. The
   English course is the pivot and gets judged first.

---

## 4. Guardrails to add

### 4.1 Layer 1 — generation

| id | change | why | size |
|---|---|---|---|
| G1 | `translate_checks.gate` verifies part of speech: a nominal head on a verb row (the `nominal_gloss_on_a_verb` predicate, 76% precision) **withholds** the rendering for a second attempt with the POS named | the charter demands it; 23% of divergences are this | ½ day |
| G2 | Definition maker asks for "the sense a learner at rank N meets, not the dictionary's first"; the checker rejects a rare sense | #6; WordNet order ≠ frequency order | ½ day |
| G3 | `REGISTER` entries for `fa`, `hi`, `el`, `tl` **after** a 200-row measurement each, with the same gold-set shape as `ar` | rule 1 — a class, not an Arabic quirk | 1 day per language, measurement first |
| G4 | The support-locale test (`TestTheSupportLocaleIsPinnedToo`) renders every surface × every pinned locale, not one | the guard that reads a declaration measures the declaration | ½ day |

### 4.2 Layer 2 — admission

| id | change | why | size |
|---|---|---|---|
| A1 | **Bug:** `_edit_vocab_card` sets `vocabulary.curated = true` and records `edited_at`; `reconcile` skips `gloss_changes` on curated rows and reports them separately | #12 — reconcile reverts human fixes | ½ day + test |
| A2 | **Bug:** `seed_grammar` matches curated points by id, with title as fallback; a retitle is logged, not duplicated | §2.2 | ½ day + test |
| A3 | `reconcile` gains a **rename detector**: a `gone` row whose rank matches a `new` row is reported as "rename — needs an exclusion", and `--apply` refuses to proceed for that course until it has one | #11, rule 73 mechanised | ½ day |
| A4 | "Accept" on a change request that carries a `suggestion` **applies it** through `edit_reviewed_card` and writes `content_change_log`; without a suggestion the button reads "Agree" | §2.2 — today "accepted" means nothing happened | 1 day |
| A5 | One `backend/services/quality/admit.py` holding blank-ability, length band, floor, duplicate/frame, POS, register tripwire and orthography inventory; every `apply_*` script imports it | five re-implementations today | 1 day, mostly moving code |
| A6 | `card_feedback` gains `field`, `drill_id`, `locale`, `support_locale`; `card_change_requests` gains `locale`; the review-session form offers the field chips the reviewer form already has | the reviewer's report could not have been a row | ½ day + migration |

### 4.3 Layer 3 — the continuous judge

| id | change | why | size |
|---|---|---|---|
| J1 | **`content_judge.py`** generalises `register_pass.py` to a table of *questions*, each with its own system rules, §3.1-shaped schema, gold set and gates: `register` (ar today), `sense` (is the definition the sense a learner meets), `gloss` (does the locale gloss render that sense, matching POS), `scripture` (Qurʾanic/liturgical text as an everyday example), `card_shape` (should this card carry a sentence at all — #1) | one instrument, one calibration discipline | 3 days |
| J2 | **`quality_loop`** in lifespan behind `quality_loop_enabled`, capped by `quality_rows_per_cycle`, reading rows in priority order — top band first, never-judged first, newest content first — and writing `content_verdicts`. Judge calls log to `tutor_usage` as `kind='judge'` so they appear in AI costs beside `summary` | §2.6 — the runner exists; the key is already spent server-side | 2 days |
| J3 | The mechanical audits that can run without local dictionaries run in the same loop and persist: `audit_locale_rows` (script + verb-gloss), `db_snapshot` counts, `reconcile` in report mode, queue depths | four modules have no path to CI | 1 day |
| J4 | `wrong_sense` band lifted and the letter-name predicate kept; the sense judge is the rule for the general class. `relation_only_gloss` promoted to fail when a course reaches zero | #6, #8 | ½ day |
| J5 | Judge output routes into the **existing** queues: a `dialect` or `rare` verdict with confidence ≥ 0.7 creates a `card_change_requests` row with `author_id` = a service account, `quote` = the evidence, `suggestion` = the rewrite | reviewers already work those panels; no new queue | ½ day (needs the service account, §9) |

---

## 5. Telemetry — the tables

Three new tables, two extensions, no new infrastructure.

```sql
-- One row per (run, language, locale, metric). The trend source.
CREATE TABLE quality_runs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_at      timestamptz NOT NULL DEFAULT now(),
  kind        text NOT NULL,          -- audit | judge | reconcile | snapshot | queues
  language_id uuid REFERENCES languages(id),
  locale      text,                   -- NULL = the course's own content
  metric      text NOT NULL,          -- 'leak_hard', 'sense.rare', 'gone', 'pending_drills' …
  value       numeric NOT NULL,
  population  integer,                -- what the value is out of, when it is a count
  build_sha   text,                   -- from build_info(); "since last deploy" needs it
  meta        jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX ON quality_runs (language_id, metric, run_at);

-- One row per judged (row, question, locale). The evidence and the queue.
CREATE TABLE content_verdicts (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  judged_at    timestamptz NOT NULL DEFAULT now(),
  run_id       uuid REFERENCES quality_runs(id),
  language_id  uuid NOT NULL REFERENCES languages(id),
  locale       text,
  entity_type  text NOT NULL,          -- vocabulary | example_sentence | drill | grammar_point | translation
  entity_id    uuid NOT NULL,
  field        text NOT NULL,
  question     text NOT NULL,          -- register | sense | gloss | scripture | card_shape
  verdict      text NOT NULL,          -- per question, e.g. dialect|classical|msa|unsure
  category     text,                   -- e.g. lexeme|morphology|orthography_only
  evidence     text[] NOT NULL DEFAULT '{}',
  confidence   numeric NOT NULL,
  expected     text,                   -- the rewrite / the sense the card should carry
  note         text,
  judge        text NOT NULL,          -- model id or local:<model>@host
  disposition  text NOT NULL DEFAULT 'open',   -- open | accepted | rejected | fixed | superseded
  disposed_by  uuid REFERENCES auth.users(id),
  disposed_at  timestamptz
);
CREATE INDEX ON content_verdicts (language_id, question, verdict, judged_at);
CREATE UNIQUE INDEX ON content_verdicts (entity_type, entity_id, field, question, locale, run_id);

-- Per-course targets, so "red" is a setting and not a constant.
CREATE TABLE language_quality_targets (
  language_id       uuid PRIMARY KEY REFERENCES languages(id),
  max_bad_card_pct  numeric NOT NULL DEFAULT 15,
  max_judge_flag_pct numeric NOT NULL DEFAULT 5,
  updated_at        timestamptz NOT NULL DEFAULT now()
);
```

Extensions:

- `tutor_usage` + `outcome text` (`ok | schema_reject | checker_reject | error | fallback`) + `latency_ms integer`. Cheap, and the local-model plan's fallback counter needs it.
- `card_feedback` + `field`, `drill_id`, `locale`, `support_locale`; `card_change_requests` + `locale` (A6).

Weekly aggregation is SQL views over these — reports per language × field ×
week, verdict rates per language × question × week, queue depth per language
× week from `quality_runs` where `kind='queues'`. Retention: same 13-month
sweep as `tutor_usage`, added to `retention.py`.

The per-row `ai_check_status` columns stay for the existing button; new
questions do not widen that two-value CHECK.

---

## 6. The admin surface — "Content health"

**Where.** Two places, both in the Admin tab, both copying `DeploymentPanel`'s
frame and its test pattern (`DeploymentPanel.test.tsx`).

1. **Admin → Content → `ContentHealthPanel`**, beside the Generation panel it
   complements (Generation measures whether rows exist; this measures whether
   they are right).
2. **Admin → Rollouts → Deployment gains a "Content" section**: *files versus
   database, since the last deploy* — words retired pending reconcile, rows
   new pending seed, glosses drifted, headword renames needing an exclusion,
   last reconcile date. That is reconcile's survey, persisted (J3), and it is
   the content answer to the panel's existing schema question.

**The panel, per course — one row each, worst first, exactly the shape of
the "Twenty-Seven Courses" page the owner already reads:**

| column | source | colour |
|---|---|---|
| Bad cards (top-2,000 with no blankable sentence) | `quality_runs` `unclozable_rows` / band | vs `max_bad_card_pct` |
| Top-1,000 covered | same | ≥95 green, ≥80 amber |
| Audit fails vs baseline (Δ) | `quality_runs` `kind='audit'` | any increase red |
| Judge-flagged, per question, confidence ≥ 0.7 | `content_verdicts` | vs `max_judge_flag_pct` |
| Open reports (learner / staff) and pending queues | existing counts + `quality_runs` `kind='queues'` for the trend | growth over 7 days amber |
| Last judged / last audited | `quality_runs` max `run_at` | > 7 days grey |
| 30-day sparkline of bad cards and judge-flag rate | `quality_runs` | — |

**Drill-down per course:** defect classes with counts and one example each;
the open verdicts as a list with accept/reject that writes `disposition`;
links into `ChangeRequestsPanel` / `TranslationReviewsPanel` /
`FeedbackPanel` pre-filtered; "since last deploy" using `build_sha`.

**Auth.** New `GET /api/contribute/admin/content-health` and
`/content-health/{code}` behind `_require_admin`. **And `/api/health` and
`/api/health/schema` get auth too** — migration filenames and build shas are
not public information (§9).

**The bell.** The staff bell gains a *Quality* section: a course whose
judge-flag rate crossed its target or whose bad-card share rose since the
last run. And `_BELL_DEGRADES` stops making a broken bell look like a clean
one — the payload carries `degraded: true` and the icon shows it.

---

## 7. Sequence, with what each phase proves

| phase | what | spend | days | gate to next |
|---|---|---|---|---|
| **A — persist what already computes** | `quality_runs` migration; `audit_content`, `reconcile` (report), `db_snapshot`, queue depths write rows; a `quality_loop` runs the mechanical ones nightly | none | 2 | rows exist for 27 courses with a `build_sha` |
| **B — the panel** | endpoint + `ContentHealthPanel` + Deployment "Content" section + targets table; auth on `/api/health`. **Backend landed 18 Sep 2026:** `GET /api/contribute/admin/content-health`, `…/content-health/{code}`, `…/content-health/deploy`, `POST …/content-health/verdicts/{id}`, `GET`/`PUT …/quality-settings`, `PUT …/quality-targets/{code}` (`routers/contribute.py`; status rules in `services/content_health.py`, reads in `repositories/content_health.py`; 66 tests in `test_content_health.py`). GETs degrade to `available: false` before migration 20261029, writers 503 naming it. The panel and the Deployment section are the parallel frontend unit; auth on `/api/health` waits on decision #3; DEBT "Content Health, phase B" lists what is left out | none | 3 | the owner can read a trend that was previously impossible |
| **C — telemetry extensions** | `tutor_usage.outcome/latency_ms`; `card_feedback` field/drill/locale; `card_change_requests.locale`; the review form's field chips | none | 1 | a learner report can say which layer and which locale |
| **D — the admission bugs** | A1 curated + reconcile skip; A2 title/id; A3 rename detector; A4 Accept applies; A5 shared `admit.py` | none | 3 | a Workshop fix survives a reconcile, proven by test |
| **E — the judge** | `content_judge` with five questions; gold sets for `sense`, `gloss`, `scripture`, `card_shape` (register's exists); calibration page per question; `content_verdicts`; verdicts routed to existing queues; judge loop behind its flag and cap | **yes** (§9.1) | 5 | each question clears the three gates on its gold set before it can write anything but `report` |
| **F — widen** | `REGISTER` for `fa/hi/el/tl` after measurement; local model per `arabic-msa-local-llm.md` §5 for volume | measured first | per language | — |

A–D are ten days of work that spend nothing and stand alone. E is where
the plan's value is, and it is the phase that needs the decision.

---

## 8. What it costs, in numbers we measured

This month's judge runs, in-session:

| pass | rows | tokens | per row |
|---|---:|---:|---:|
| Arabic surfaces (5 tables) | 1,244 | 3.66M | ~2,900 |
| English sense + gloss | 360 | 0.98M | ~2,700 |
| Topic classification | 6,382 | 5.85M | ~900 |

A nightly loop at 500 rows is roughly **1.5M tokens a night** at the checker
tier; the AI-costs panel already prices that model, and the `judge` kind will
show it beside `summary`. The 27 courses' top-2,000 bands are ~54,000 rows,
so a full first pass is ~110 nights at 500, or ~11 at 5,000. After the first
pass the loop only needs new and edited rows, which `content_change_log`
already identifies.

The local-model plan's §5 is the answer to volume; nothing here conflicts
with it, and `content_judge` takes `--base-url` from the first day exactly as
`register_pass` does.

---

## 9. Decisions for the owner

1. **Spend the key on a nightly judge, and at what cap.** The standing rule
   is that *this agent* never spends it; the app already does, in
   `auto_translate_loop`. Recommend: yes, `quality_rows_per_cycle = 500`,
   flag off by default, on per language from the Languages section.
2. **A service account for judge-authored change requests.**
   `card_change_requests.author_id` is NOT NULL against `auth.users`. Either a
   `quality-judge@` account, or the column becomes nullable with a `source`
   field. Recommend the account: nothing else changes.
3. **Auth on `/api/health*`.** Recommend requiring an admin session; keep an
   unauthenticated `{"status":"ok"}` for the platform's probe.
4. **What makes a course red.** Recommend the defaults in
   `language_quality_targets`: bad cards > 15%, judge-flagged > 5%, any audit
   fail above baseline.
5. **"Accept" applies the suggestion, or is renamed "Agree".** Recommend
   apply, because today's label is misleading and reviewers act on it.
6. **Fixing the vocabulary `curated` bug changes reconcile.** After A1, a
   reconcile will *report* curated rows that differ from the file instead of
   overwriting them. That is the intent; say so, because the numbers in the
   `gloss` column will drop.
7. **Retention for `content_verdicts`** — 13 months like `tutor_usage`?
8. **Order.** A–D first (ten days, no spend, two bugs fixed), then E; or E
   first because it is where the findings come from. Recommend A–D first:
   E's verdicts need `quality_runs` to be visible and A1 to be safe.

---

## 10. What this does not do

- It does not replace native reviewers. A judge verdict is a queue item and
  `reviewed` stays false until a person says otherwise.
- It does not backfill history. Trend starts the day Phase A ships.
- It does not touch the tutor's live replies. Shadow-judging Speak and chat
  output is the local-model plan's step 3, not this one.
- It does not make the panel a place to edit content. Every accept routes
  through the Workshop paths that already write `content_change_log`.
- It does not fix the 194 Arabic register rows, the ~853 English rare-sense
  definitions or the ~2,329 Arabic gloss divergences already measured. It
  builds the thing that finds the next ones and stops them being lost.
