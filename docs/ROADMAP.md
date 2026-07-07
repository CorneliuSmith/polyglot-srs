# ROADMAP — operating plan & agent handoff

The plan to take PolyglotSRS from its current state to the full product, written
so that agents (or contributors) can pick up any work package independently.
Read this whole file once before taking a package.

## 1. North star

Teach languages **through sentences with context** — a learner always produces
words and grammar inside real sentences, never bare flashcards. The Bunpro
principle, exactly: **grammar points progress in a fixed, researched order,
but the sentences shown for each point VARY on every review** — exposure to
the pattern in many contexts, not memorization of one string. Bunpro-parity
on the grammar-path experience, with two differentiators: (a) **African
languages first-class** (Swahili, Yoruba, Hausa, Xhosa — the underserved
market), and (b) personal input ("learn from your own text") + AI tutors that
coach from the learner's actual failure history.

## 2. Current state (verified)

- **Engine (done, tested)**: FSRS-5 scheduling + per-language weight fitting
  with a held-out validation gate (WP8); 6-layer NLP answer grading for all
  16 languages (diacritics coach, don't fail); teach-before-quiz lessons;
  deterministic sentence rotation (stable across reloads, rotates per
  recorded review) with per-sentence logging
  (`review_log.prompt_sentence`); in-session re-drill of misses;
  teach-before-quiz is a hard gate: learn batches are created suspended, each
  lesson ends with a first-check drill (the lesson payload's `quiz`), and only
  a correct answer confirms THAT card into reviews
  (POST /api/review/learn/confirm); abandoned or failed walkthroughs re-teach;
  Bunpro-style learn decks (per-level lists with progress,
  GET /api/review/decks, level-scoped batches that auto-queue the deck);
  graduated hints are language-aware (hintLayers.ts): non-Latin scripts
  (ru/ar/el) reveal romanization → word-by-word gloss → translation → recipe;
  syntax-divergent languages (mi/sw/yo/xh/ha) reveal the gloss first; the
  rest reveal translation → recipe; the answer blank colors on grading
  (green correct / amber sloppy spelling / red wrong); non-Latin scripts
  (ru/ar/el) take QWERTY transliteration input by default — type Latin, the
  blank converts as you type (translit.ru-style for Russian, chat-alphabet
  digits + positional short vowels for Arabic, Greeklish with automatic
  final sigma for Greek), with a per-language toggle and an in-card key
  guide (features/keyboards/translit.ts); the post-answer item
  page (WP13 a–e) shows a named-stage badge + progress panel, blur-toggled
  example translations, the learner's own note sentences, a Related grid
  with contrastive one-liners, and Online/Offline resources with per-user
  read-tracking;
  browsable grammar path (`/grammar`) with per-point learning; onboarding +
  mixed placement; personal notes → cloze cards; AI tutor with memory,
  weak-area grounding (vocab + grammar), entitlements, Stripe billing;
  a full role model — learner / contributor / reviewer / admin, per-language
  or global, admin Roles panel + `scripts/grant_admin.sh` bootstrap, AI-check
  + human-approval workflow (docs/accounts-and-roles.md); RLS multi-tenancy
  proven by integration tests; CI (Python 3.11 & 3.12). Review-session UX is
  Bunpro-style: the typed answer is auto-graded by the NLP layer (no manual
  rating), a miss offers "Typo? Re-enter your answer" (nothing recorded),
  correct-but-lucky offers "I actually got it wrong", the grammar point is
  viewable on demand after any answer ("Show grammar"), and misses re-drill
  before the session ends.
- **Grammar paths seeded — ALL 16 languages**: es 43 (full A1→C2, Plan
  Curricular order), tr 40 (full A1→C2, cross-model verified), ru 51 (full
  A1→C2 per TORFL — A2+ promoted live 2026-07; native-speaker review still
  wanted, WP4), sw 32 · yo 24 · xh 24 · ha 22 (A1→C1-equivalent), and
  12-point A1 paths for fr · de · it · ca · mi · ar · en · ro · el.
  **WP1 drill bar met everywhere: 6 drills/point (2,064 drills total)**,
  validated for single-word answers, no answer leakage, no duplicate frames,
  English-functional hints. Hint-layer content is seeded where the language
  needs it: ru drills carry transliterations (cyrtranslit), el drills carry
  hand-written transliterations, ar drills carry lexicon transliterations,
  mi drills carry word-by-word glosses. Every point: can-do function,
  explanation, references.
- **Vocabulary**: sw ~1200, tr ~770, ar/en corpora; ~30-word curated starters
  for es/fr/de/it/ca/mi/yo/ha/xh/ro/el, each with 6 cloze example sentences
  per word (el sentences carry a transliteration column); ru 58
  curated starters implementing the language-shaped card design (aspect/motion
  pairs as single cards via alternatives + morphology.aspect_partner, noun
  declension samples in morphology) with 6 example sentences per word.
- **Ops**: `scripts/setup_db.sh` rebuilds or repairs any database end-to-end
  (tracked migrations that self-baseline on pre-migrated DBs, offline seed,
  verification; `--local` targets a local Postgres via the auth shim).
- **Suites**: `backend/tests` (624 unit + 24 integration against a local
  Postgres via INTEGRATION_DATABASE_URL) and `frontend` vitest (116) green.

## 3. Non-negotiable invariants (every agent, every package)

1. **Pedagogy**: new items are TAUGHT before quizzed; a grammar point without
   drills is readable, never learnable; drills only use structures earlier in
   the path (processability); every point carries a can-do `function`,
   references (official inventory where one exists), and level. Cards are
   **language-shaped**: follow "Language-shaped cards" in
   docs/curriculum-design.md — point counts differ by typology, aspect/motion
   pairs share a vocab card linking to their grammar point, case-language
   nouns carry declension samples, Bantu nouns carry class pairs + concords.
2. **Data flow**: all learner-visible content writes go through the seeders /
   privileged connection; never weaken an RLS policy; entitlements are written
   only by billing webhooks/seeders.
3. **Quality gates before any push** (all must pass):
   ```bash
   ruff check backend
   python -m pytest backend/tests -q          # with INTEGRATION_DATABASE_URL set
   cd frontend && npx tsc -b && npx vitest run
   ```
4. **Content conventions**: upsert key is (language, title) — never retitle a
   point casually; `reviewed: true` only for confident curated content, else
   `reviewed: false` (it stays hidden until linguist approval or an `ai_ok`
   policy); keep model names out of committed content.
5. **Git**: work on the designated `claude/…` branch; commit with heredoc
   (`git commit -F -`) to avoid backtick expansion; never force-push.

## 4. Runbook (local sandbox)

- Local Postgres for integration tests: port 5433, data in `/tmp/pgdata`,
  must run as `nobody`, socket dir `/tmp`. If `pg_isready -h /tmp -p 5433`
  fails (the sandbox reclaims processes — expect this):
  `su nobody -s /bin/sh -c "/usr/lib/postgresql/16/bin/pg_ctl -D /tmp/pgdata -l /tmp/pg.log -o '-p 5433 -k /tmp' start"`
  (re-`chown -R nobody:nogroup /tmp/pgdata` first if needed). Redis:
  `redis-server --port 6390 --daemonize yes --save ''`.
- Env for full suite: `INTEGRATION_DATABASE_URL` + `DATABASE_URL` =
  `postgresql://postgres@/postgres?host=/tmp&port=5433`,
  `REDIS_TEST_URL=redis://localhost:6390/0`. Integration conftest wipes and
  re-migrates the DB each session — never point it at real data.
- Seeding, envs, and deployment steps: `DEMO.md`. Design records:
  `docs/curriculum-design.md`, `data/README.md`, `docs/claude-db-access.md`.

## 5. Work packages

Effort ≈ S (<half day), M (a day), L (multi-day). "Model" = recommended Claude
model for the agent doing it (see §6 for reasoning).

### WP1 — Variation sentences everywhere  ⭐ next
**Status:** grammar half DONE — 6 drills/point for all seven seeded paths
(1,416 drills), hints rewritten to English gloss+function recipes that never
assemble the answer (422 rewritten). Sentence half DONE for every curated
starter set (~6/word: es/fr/de/it/ca/mi/yo/ha/xh/tr/ru — ~2,100 curated
sentences) and seed_sentences now also consumes the sourcing pipeline's
Tatoeba TSVs (data/{code}_sentences.tsv, graded difficulty_rank). Remaining:
corpora-scale words (sw/tr/en/ar/yo full frequency lists) need WP5 sourcing
or WP6 generation.
**Targets (owner-decided):** every grammar point gets **6 drills** (hard
minimum 4) varying person, tense, vocabulary, and register; every vocabulary
word gets **6–10 graded example sentences** (hard minimum 4) — vocab carries
AT LEAST as many sentences as grammar, matching Bunpro's long graded example
lists (grade them via example_sentences.difficulty_rank). The engine already
consumes as many as exist and picks a different one on every appearance.
**Steps:** for each `data/grammar/{code}_grammar.json`, append drills to
existing points (do not retitle); vary subject person, object, and setting;
answers must stay single whole words/word-forms; every drill validated by
`python -m pytest backend/tests/test_grammar_seeder.py` + a seed run; keep
translations natural English. Well-resourced languages can be drafted by a
cheaper model **but every batch goes through the AI semantic check**
(`semantic_check.py`) and lands as `reviewed: true` only after a stronger
model (or human) verifies each drill.
**Acceptance:** 6 drills/point (≥4 floor) for all seeded grammar; 6+ graded
sentences/word (≥4 floor) for seeded vocab (extend data/sentences/*.tsv);
seed passes; the per-appearance variety integration test passes; spot-check
10 random drills/language.
**Model:** African languages: `claude-fable-5` (or `claude-opus-4-8`); es/fr/
de/it/tr/ru/en/ca: draft with `claude-sonnet-5`, verify with `claude-opus-4-8`.
**Effort:** L (content), S (no code changes needed).

### WP2 — Deepen Spanish/Turkish/Russian to C2
**Status:** DONE — es 43 · tr 40 · ru 51, all A1→C2. Russian A2–C2 (43
points) are drafts pending a cross-model verification pass before
promotion to `reviewed: true`; the aspect-pair/motion-pair vocab card
design is implemented (data/ru_starter.tsv + csv_importer declension
columns + alternatives persisted in BaseSeeder).
**Goal:** ~45–55 points each, per official inventories, ALL THE WAY TO C2
(C2 adds discourse-level items: es — cleft/inversion, subtle subjunctive
concordance, register; tr — complex converb chains, formal registers; ru —
participial style, aspect nuance in context).
**Topic checklists** (order = display order):
- **es** (Plan Curricular B1→C1): reflexives; gustar-type verbs; preterite vs
  imperfect; future & conditional; present subjunctive (triggers); imperative
  (incl. negative); perfect tenses; object-pronoun combos (se lo); por/para;
  past subjunctive; si-clauses; passive/impersonal se; reported speech;
  relative clauses (quien/cuyo); subjunctive in relatives/concessives;
  pluperfect subjunctive; cleft sentences.
- **tr**: geniş zaman (aorist -ir); past -di; evidential -miş; ability -ebil;
  necessity -meli; conditional -se; dative/ablative/genitive; postpositions;
  comparatives (daha/en); nominalization -mek/-me/-dik; relative participles
  -en/-dik; reported speech; passive/causative/reflexive/reciprocal voice;
  converbs (-ip, -erek, -ken).
- **ru** (TORFL A2→C1): dative/instrumental; verbs of motion (uni/multi);
  aspect pairs; imperative; reflexives -ся; comparatives; short adjectives;
  numerals + case; time expressions; conditional бы; relative который;
  participles (active/passive); gerunds; impersonal constructions; verbal
  prefixes. **Russian-specific card design:** aspect pairs and motion-verb
  pairs are single vocab cards (partner in alternatives +
  morphology.aspect_partner) linking to their grammar points; noun cards
  carry declension samples — see "Language-shaped cards".
**Acceptance:** same bar as existing points (function, refs incl. official
inventory, 2+ drills each — 4+ if WP1 has landed); seed + suites green.
**Model:** `claude-opus-4-8` or `claude-fable-5` (morphology accuracy).
**Effort:** L per language.

### WP3 — A1 paths for fr, de, it, ca, mi, ar, en
**Status:** DONE — every language now has a grammar tab. 12 points × 6 drills
per language (504 drills), mirroring the Spanish A1 template with the
per-language adaptations below (de: V2 + accusative; ar: root-and-pattern,
sun/moon letters, nominal sentences, iḍāfa; mi: TAM particles kei te/i/ka +
a/o possession; en: articles, third-person -s, do-support, continuous for
learners from other languages). Landed reviewed:true (A1-core precedent);
a cross-model verification pass is still recommended, ar and mi first.
**Goal:** ~12-point A1 paths so every language has a grammar tab.
Mirror the Spanish A1 template (pronouns → nouns/gender → articles → copula →
present verbs → negation → existence → questions → agreement), adapted per
language: de adds cases/word order (V2); ar adds root-pattern intro, sun/moon
letters, nominal sentences, iḍāfa; mi adds TAM particles (kei te/i/ka), 'a'/'o'
possession; en targets learners FROM other languages (articles, 3rd-person -s,
do-support, present continuous).
**Model:** `claude-sonnet-5` draft + `claude-opus-4-8` verify; ar and mi
straight to `claude-fable-5`/`claude-opus-4-8`.
**Effort:** M per language.

### WP4 — African content: native review + deepening
**Goal:** the differentiator held to the highest bar. (a) Recruit native
speakers/linguists as contributors (roles exist; ContributorPage supports
review + approval + AI checks); have them audit tone marks (yo), concords
(xh), aspect glosses (ha), and approve or fix each point. (b) Extend sw to
~50 points and yo/ha/xh to ~40, through C2-equivalent (sw: -po-/-vyo-
relatives, -japo- concessives, comparatives, remaining classes, register;
similar discourse-level closers for yo/ha/xh). (c) WP1 variation drills for all four.
**Acceptance:** every African point re-approved by a named human reviewer
(`reviewed_by` set), or explicitly flagged Draft.
**Model:** `claude-fable-5` for authoring/triage; humans are the gate.
**Effort:** L, partly external (people).

### WP5 — Vocabulary + sentence corpora at scale
**Goal:** ≥3,000 frequency-ranked words/language with **≥4 example sentences**
per word (feeds vocab cloze + rotation). Requires internet.
**Steps:** `./scripts/refresh_seed_data.sh` (or per-language
`source_data --language X --source kaikki [--sentences]`) → generates
`data/*_frequency.tsv` + `*_sentences.tsv` → `seeder.run` + `seed_sentences`
per language → verify counts + cloze coverage (make_cloze success rate ≥80%).
Yoruba needs `--source kaikki`; Russian vocab comes from OpenRussian download.
For gaps (mi, xh sentence corpora are thin everywhere), generate candidate
sentences with a model constrained to the seeded vocab, NLP-validate, and mark
`source='ai'` for review.
**Model:** pipeline is mechanical (`claude-haiku-4-5-20251001` supervision is
fine); AI-generated sentences: `claude-sonnet-5` draft + `claude-opus-4-8`
spot-verify per language batch.
**Effort:** M (pipeline runs) + L (gap generation).

### WP6 — AI curriculum generation at scale
**Goal:** grow paths beyond hand-authoring using the existing, self-validating
generator: `python -m backend.services.seeder.generate_curriculum --language X
--generate` (needs `ANTHROPIC_API_KEY`). Output lands as `reviewed: false`
drafts with `ai_check_status`; linguists approve in the contributor UI, or an
admin sets the language's policy to `ai_ok` to surface AI-passed drafts.
**Acceptance:** drafts never surface without approval or explicit policy; every
generated drill passes the NLP answerability validation (already enforced).
**Model:** generation `claude-opus-4-8`; the semantic-check pass runs on
`tutor_summary_model` (now `claude-sonnet-5`).
**Effort:** M per language + review time.

### WP7 — Audio: cached TTS + human recordings
**Goal:** consistent pronunciation. The UI seam exists (`SpeakButton audioUrl`
prop, falls back to browser speech).
**Steps:** add `audio_url` columns to `vocabulary`, `example_sentences`,
`drill_sentences`; a pregen job that synthesizes each seeded sentence ONCE via
a neural TTS provider (Azure/Google/Polly all cover es/fr/de/it/tr/ru/ar/en;
sw partially) and stores files in Supabase Storage; wire urls into due-card /
lesson payloads. For yo/ha/xh/mi: TTS coverage is poor — collect **human
recordings** through the contributor workflow instead (upload per sentence).
**Model:** implementation `claude-sonnet-5`; provider evaluation matrix
`claude-opus-4-8`.
**Effort:** M (pipeline) + external (recordings).

### WP8 — FSRS held-out quality gate
**Status:** DONE — `fit_weights_validated` holds out the last 20% of each
card's history, fits on the rest, shrinks toward the defaults by data volume
(n/(n+300)), and adopts only when the candidate's held-out log-loss strictly
beats the defaults'. Both losses are stored in fsrs_weights
(holdout_log_loss, defaults_holdout_log_loss); rejections are logged loudly.
LANGUAGE_MIN_REVIEWS/USER_MIN_REVIEWS dropped 1000 → 300. Unit-tested:
split boundaries, tail-only scoring, adoption on genuinely divergent data,
deterministic rejection of a fit that memorized its training prefix,
shrinkage on small data.
**Goal:** adopt fitted per-language weights only when they beat the defaults
out-of-sample, then drop `LANGUAGE_MIN_REVIEWS` 1000 → ~300.
**Steps** (design already agreed): in `fit_fsrs_weights`, hold out the last
20% of each card's reviews; fit on the rest; adopt iff held-out log-loss <
defaults' held-out log-loss; optionally shrink params toward defaults by data
volume; log both losses in `fsrs_weights`.
**Acceptance:** integration test proving a bad fit is rejected and a good fit
adopted; unit tests for the split.
**Model:** `claude-opus-4-8` (subtle eval-correctness pitfalls).
**Effort:** M.

### WP9 — Tutor upgrades
**Goal:** production-quality tutoring. (a) Model config: chat on
`claude-opus-4-8` (default; operators may set `TUTOR_MODEL`), summarizer/
checks on `claude-sonnet-5` (now default). (b) Add per-user token/cost
tracking (log usage per chat into a `tutor_usage` table; surface in admin).
(c) Tutor should propose drills from GRAMMAR weak areas (data now flows;
prompt already tags kind=grammar — verify behavior with real key and tune the
charter). (d) Streaming responses in the chat UI.
**Model:** implementation `claude-sonnet-5`; prompt/charter tuning
`claude-fable-5` or `claude-opus-4-8`.
**Effort:** M.

### WP10 — Production hardening
**Goal:** safe launch. (a) **Rotate the Supabase service-role key and DB
password** (they were pasted in a chat once — treat as leaked) and set
`TUTOR_FREE_ACCESS=false` in prod. (b) Deploy Stripe live keys + webhook;
E2E-test grant/revoke. (c) Error tracking (Sentry) + request logging; DB
backups; a smoke-test script hitting the golden path against staging.
(d) Nightly cron: `fit_fsrs_weights`.
**Model:** `claude-opus-4-8` (security-sensitive).
**Effort:** M.

### WP11 — Placement adaptivity
**Goal:** placement picks the next item based on answers so far (stop early on
stable estimate), weights grammar vs vocab, and caps at ~12 items. Backend
`sample_placement_items`/scoring refactor + tests.
**Model:** `claude-sonnet-5`. **Effort:** M.

### WP12 — Learner UX
PWA/mobile packaging; `ui_language` i18n (strings are hardcoded English);
review forecast ("due tomorrow: N"); streak heatmap; per-deck settings.
**Model:** `claude-sonnet-5` (`claude-haiku-4-5-20251001` for mechanical
string extraction). **Effort:** M each.

### WP13 — Session & item-page parity (Bunpro reference shots)
Already adopted: arrow-only submit/continue pill, Undo (nothing recorded),
graduated Hint dots, per-appearance sentence change, "Show examples" for
vocab, session utility bar (exit/path/tutor/settings). **(a)–(e) DONE
2026-07:** (a) blur-until-toggled translations in example lists (BlurReveal +
per-list "Show translations"); (b) Resources split Online / Offline
(book + page) with per-user read-tracking (user_reference_reads table,
POST /api/curriculum/point/{id}/reference-read); (c) Related grid —
authorable `related` [{title, contrast}] on grammar_points, resolved at read
time to live points + the learner's stage badge (authored for the tr/es/ru A1
tiers); (d) the learner's own note sentences under vocab Examples ("Your
sentences"); (e) named SRS stages on the item page (shared
services/srs_stages.py bands) + progress panel (first studied, times studied,
accuracy, streak, misses, next review). Remaining: (f) Quick-Cram of a
related set; (g) in-app search; (h) theme switcher; authoring `related` +
offline refs beyond the tr/es/ru A1 tiers.
**Model:** `claude-sonnet-5` implementation with a design-consistency
verify pass one tier up. **Effort:** M–L.

### WP14 — Dashboard parity (owner's Bunpro dashboard screenshots)
**Status:** core DONE — Learn/Review command-center cards with live counts,
Bunpro-style learn-deck dropdown (per-level progress rows), 7-day review
forecast, 14-day activity chart (vocab vs grammar), named-stage tiles
(Beginner/Adept/Seasoned/Expert/Master from FSRS stability bands + Self-Study
+ Ghosts) with Grammar/Vocab toggle, and the profile card (streak flame week,
days studied, last-session accuracy, items studied). Remaining: hourly
forecast granularity, per-level grammar+vocab combined bars, community
section (deferred).
Home page becomes the command center, our style: top bar keeps OUR
differentiators — the **language switcher** and a **Tutor** link — alongside
Learn/Review; big **Learn N/day** and **Review N** buttons with live counts;
**review forecast** (hourly/daily, from user_cards.next_review); **activity
chart** (reviews/day, vocab vs grammar, from review_log); **named-stage
progress tiles** (Beginner/Adept/Seasoned/Expert/Master mapped from FSRS
stability bands, plus Self-Study and Ghost counts) with a Grammar/Vocab
toggle; **profile card** (streak flame week, per-level progress bars for
grammar+vocab like Bunpro's JLPT bars — ours per CEFR level, days studied,
last-session accuracy, items studied). Community section deferred until
there's a community. **Model:** `claude-sonnet-5`, design pass one tier up.
**Effort:** M–L.

### WP15 — Admin console: tutor model control + role management
**Goal:** operators run the product without touching env vars or SQL.
Role management shipped 2026-07 (see `docs/accounts-and-roles.md`): learner /
contributor / reviewer / admin, per-language or global, granted by email in
the Contribute page's Roles panel, bootstrapped once via
`scripts/grant_admin.sh`. Remaining, in order:
(a) **Per-language tutor model selection (admin UI)** — today the tutor model
is a global env var (`TUTOR_MODEL`, default `claude-opus-4-8`; summarizer on
`claude-sonnet-5`). Move to a `tutor_model` column on `languages` (NULL =
global default) + an admin panel listing each language with a model picker
(Claude model IDs: `claude-fable-5`, `claude-opus-4-8`, `claude-sonnet-5`,
`claude-haiku-4-5-20251001`) and per-language token/cost columns once WP9(b)
usage tracking lands. High-resource languages can ride a cheaper model;
low-resource languages (the differentiator) stay on the strongest.
(b) **Custom / local endpoints** — accept an OpenAI-compatible base URL +
model name per language (Ollama, vLLM, LM Studio, llama.cpp server), stored
alongside `tutor_model`, with a health-check button and automatic fallback
to the Claude default when the endpoint is down. This is the cheap path to
"local LLM" before any training happens.
(c) **Pooled per-language community models** — the ambitious arm: pool each
language's curated content (grammar + drills + sentences, already licensed)
WITH consenting learners' production (review answers, tutor conversations,
self-study sentences) into per-language fine-tuning sets for a small open
model (e.g. a 7–8B base), one adapter per language. Requirements, in order:
an explicit **opt-in consent flag** on user_profiles (off by default; tutor
data NEVER pooled without it), a PII-scrub + dedup export pipeline
(`review_log.prompt_sentence`, card answers, tutor transcripts), an eval
harness that scores the tuned model against the Claude baseline on held-out
drill grading + explanation quality per language, and the same adoption
gate philosophy as WP8: **the local model serves a language only when it
beats or matches the baseline on that language's eval; otherwise the admin
panel shows the gap and keeps Claude.** Ship (a) and (b) first — they're
days; (c) is a program.
**Model:** (a)/(b) `claude-sonnet-5`; (c) design + eval harness
`claude-opus-4-8` or `claude-fable-5`. **Effort:** (a) S, (b) M, (c) L.

## 6. Model selection guide

| Task type | Model | Why |
|---|---|---|
| Low-resource linguistics (sw/yo/ha/xh/mi/ar authoring, review triage) | `claude-fable-5` (else `claude-opus-4-8`) | Accuracy is the constraint; errors here damage the differentiator |
| High-resource grammar authoring (es/fr/de/it/tr/ru/en) | draft `claude-sonnet-5` → verify `claude-opus-4-8` | Volume work with a cheap drafter, correctness held by a stronger verifier |
| Variation-sentence generation (WP1) | as above, per language tier | Same split |
| Security/eval-sensitive code (billing, RLS, FSRS gate) | `claude-opus-4-8`+ | Subtle failure modes |
| Well-specified feature code (UI, endpoints, pipelines) | `claude-sonnet-5` | Fast, reliable on scoped specs |
| Mechanical ETL, string extraction, bulk edits | `claude-haiku-4-5-20251001` | Cheapest that does the job |
| Tutor chat runtime (paid) | `claude-opus-4-8` (config default) | Learner-facing quality |
| Tutor summarizer / AI semantic checks | `claude-sonnet-5` (config default) | Off hot path, good judgement per dollar |
| Adversarial verification of any generated content | one tier above the generator | Never self-certify |

Two standing rules: **generated content is never self-certified** (a different,
stronger model or a human verifies), and **African-language content always gets
the strongest available model plus a human gate**.

**Fallback chain when a model is retired or unavailable** (e.g. when
`claude-fable-5` goes away): substitute the next tier down and keep the
verifier one tier above the drafter —

1. `claude-fable-5` → `claude-opus-4-8` → `claude-sonnet-5` →
   `claude-haiku-4-5-20251001`.
2. If newer Claude generations exist by then, remap by role instead of by
   name: "latest frontier model" for low-resource linguistics, security, and
   verification; "latest mid-tier" for feature code and high-resource
   drafting; "latest small" for mechanical work. Check the current lineup at
   platform.claude.com/docs before assigning.
3. Never let the same model draft AND verify its own content batch — if only
   one tier is available, a human takes the verify role.

## 7. Definition of done (any package)

Suites + ruff/tsc green · invariants in §3 upheld · seed run verified against
a real Postgres · docs touched if behavior changed (`DEMO.md`,
`docs/curriculum-design.md`, this file's §2 snapshot) · committed to the
designated branch with a plain-language message and pushed · anything
learner-visible spot-checked through the actual UI flow.
