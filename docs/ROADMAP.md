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
  deterministic **gap-hunting** sentence rotation (unseen drills first, then
  the most-missed, else uniform — stable across reloads, rotates per
  recorded review) with per-sentence logging
  (`review_log.prompt_sentence`); paradigm points declare their cells and
  the seeder fails on uncovered cells (tagged across
  es/el/tr/ru/fr/de/it/ca/ro/ar A1 tiers — 87 points, ~35 gap drills
  authored; remaining: sw/yo/ha/xh noun-class concords fold into WP4's
  native review, mi/en have no strict morph paradigms — see
  curriculum-design.md "Paradigm points"); in-session re-drill of misses;
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
  browsable grammar path (`/grammar`) with per-point learning; onboarding
  with ADAPTIVE placement (WP11 — level staircase, one item at a time,
  early stop, 12-item cap); personal notes → cloze cards; AI tutor with memory,
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
- **Grammar paths seeded — ALL 17 languages, full A1→C2 for every
  documented one** (2026-07): es 43 · ru 51 · tr/fr/de/it/ca/ro/el/ar/pt 40
  each (pt authored 2026-07-11: Brazilian register, futuro do subjuntivo /
  infinitivo pessoal / tenho-falado trap / crase / mesóclise), en 12,
  mi 29 (A2/B1 drafts), sw 50 · yo 40 · ha 40 · xh 40 (deepening points are
  `reviewed: false` drafts awaiting WP4 native review). ~4,600 drills total,
  ≥6 per point, ≥2 per paradigm cell, validated (markers, leaks, hints,
  display_order). Hint layers seeded where needed (ru/el/ar transliterations,
  mi glosses). **Every point leads with its verified authoritative reference
  (§3b registry) — regression-guarded in test_grammar_seeder.py.**
- **Vocabulary + sentences at corpus scale (WP5, 2026-07)**:
  10k-word frequency decks (HermitDave + kaikki Wiktionary enrichment) for
  es/fr/de/it/ca/ro/el/ru/tr/pt (ar 8.9k), i+1-graded Tatoeba example
  sentences for all of them (~220k rows; pt 24k), en word-translations in
  12 support locales + per-locale example sentences (support_locale
  feature). Legacy curated starters remain beneath the corpus upserts
  (curated wins). Thin: sw 3.5k/1.8k, yo 1.5k/81, xh 1.2k/9, ha words
  pending a rights-clean corpus, mi curated-only.
- **Learner identity & control (2026-07)**: every language carries a full
  flag-derived palette (primary/dark/accent/soft/on + flag emoji,
  frontend/src/lib/languageColors.ts; Māori palette owner-specified:
  #CC0000/#000000/#FFFFFF/#BCBCBC/#778E46) applied APP-WIDE while that
  language is active — LanguageThemeApplier writes `--lang-*` CSS vars and
  the Tailwind `lang` tokens (bg-lang, text-lang, bg-lang-dark,
  bg-lang-soft, text-lang-on) recolor buttons, progress bars, chips, and
  links on every page (signed out = original indigo). The five SRS stage
  tiles + badges walk THROUGH the flag palette (stageRamp: grey → accent →
  primary → darkened → near-black; Māori hits the owner's sample exactly)
  and the activity chart's Vocab/Grammar series use primary/accent — so
  multi-color flags get genuinely multi-color dashboards. Reviewers/admins
  can edit live cards in Contribute (drill sentence/answer/hint/
  translation) behind friction guards: NLP answerability gate, no
  answer-leak, no hint-reveal, single-token answer, REQUIRED change_note
  (≥10 chars, filed to point_review_notes), the edit de-certifies the
  point (reviewed=false), and the editor cannot approve their own change
  (self-approval 403). Studies can be reset
  per deck (dashboard row), per language, or account-wide (Settings danger
  zone) — deletes cards AND review history (FK cascade), never
  notes/personal sentences/subscriptions. Signups choose a plan: Single
  language vs All languages (WP16; scope enforced, billing pending).
  Coverage is EVEN across all 17 languages (2026-07-12): the grammar
  seeder synthesizes a deck for every level that has points (eight
  languages once showed only their A1 deck); vocab banding includes C2
  and goes proportional for corpora under 10k words (floor 500), so
  mi (781 words, bible-corpus + kaikki), ha (1,143, Leipzig CC-BY +
  kaikki), and xh/yo/sw all span A1→C2; mi grammar authored to 40
  points and en grammar authored A2→C2 (40 points, ESL-focused:
  perfect-vs-past, conditionals, inversion, clefts, mandative
  subjunctive, ellipsis, formal connectors); mi/sw/yo/ha/xh run the
  ai_ok review policy with all 96 draft points AI-checked 'pass', so
  full paths are VISIBLE as labeled drafts (named-native gate intact).
  Invite-only beta: VITE_INVITE_ONLY hides self-serve signup + Google
  (Supabase-side disable is the enforcement — DEPLOY.md), and admins
  mint accounts from the Accounts panel.
  Grammar explanations are short-paragraph formatted (see §3b layout
  standard) AND typeset by ExplanationView: term-(gloss) enumerations
  render as two-column tables, arrow derivations as from→to tables,
  form runs as label chips, quoted glosses dimmed — content stays plain
  text, the renderer does the typography. A Bunpro-style deck browser
  (/decks → deck page with search + every item expandable to its real
  content; grammar rows deep-link to the grammar path and, for
  role-holders, to Contribute with issue flagging) makes every card
  visible outside reviews. Definitions are human-cleaned at the source
  (letter-name/cross-reference senses filtered, inflection senses kept
  as informative fallbacks — я = "I (first-person singular subject
  pronoun)", είναι = "third-person singular present of είμαι"). Speech
  synthesis matches an installed voice explicitly (ro/el/pt locales were
  missing entirely) and dodges Chrome's cancel-then-speak race. English vocabulary carries
  definitions in 12 support locales and ~187k example sentences with
  per-locale translations (rebuilt 2026-07-12 at 10k-word scale — the
  8-hour build was a spaCy-per-token pathology, now cached and ~20 min).
  Translation extraction is POS-keyed with the LARGEST translation table
  as the primary sense, letter/symbol entries excluded, core subject
  pronouns hand-curated, and articles pinned to NO translation: when a
  language has no equivalent, the card shows the English grammar gloss —
  never a wrong-sense extraction (the a→"т" bug class). Reseeding en
  translations REQUIRES the purge first (upserts cannot remove stale
  locale rows): DELETE non-'en' locales for en vocab, then
  run.py --language en.
- **Ops**: `scripts/setup_db.sh` rebuilds or repairs any database end-to-end
  (tracked migrations that self-baseline on pre-migrated DBs, offline seed,
  verification; `--local` targets a local Postgres via the auth shim).
- **Suites**: `backend/tests` (724 unit + 32 integration against a local
  Postgres via INTEGRATION_DATABASE_URL) and `frontend` vitest (183) green,
  plus ruff and strict tsc (CI-enforced).

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

## 3b. Content Standards — the bar for every language (2026-07)

This section is the durable quality contract. It was calibrated against a
private library of professional courses (Glossika grammar guides, the Teach
Yourself series, Michel Thomas, BrazilianPodClass, and similar) — **those
materials are NEVER cited, quoted, or copied in the app**; they set the bar,
public sources provide the content. The library is indexed per-language in
`docs/resource-library.md` — consult it before authoring or auditing any
language's content. Any model authoring or reviewing content follows this
checklist verbatim — it encodes judgment so quality survives model changes.

### Grammar points (per language)
- **Full A1→C2 ladder, 40+ points.** Major documented languages
  (es/fr/de/it/ca/ro/el/ru/tr/ar/en/pt) land `reviewed: true` on the curated
  precedent; African + indigenous languages (sw/yo/ha/xh/mi) land
  `reviewed: false` behind the named-native-reviewer gate — no exceptions,
  and advanced oratory/cultural registers (whaikōrero, karin magana, òwe,
  amaqhalo) are drafted only up to the level a non-native can verify from
  descriptive grammars; beyond that a fluent speaker AUTHORS, not reviews.
- **Anatomy of a point**: `title` (native term + English, e.g. "The passive
  (المبني للمجهول)"), `function` (a can-do: "Say an action was done without
  naming the doer"), `explanation` ≤120 words that teaches the FORM and the
  *ingredients* that trigger it (see Drills below), `culture_note` whenever
  social register is at stake, `references` (see Sources), `related`
  [{title, contrast}] for confusable neighbours, `paradigm` cells whenever
  the point is really a table (pronouns, conjugations, concords).
- **Explanation LAYOUT is part of the standard (2026-07)**: no dense
  paragraph walls. Short paragraphs of 1–2 sentences separated by blank
  lines; every form run / paradigm row / pattern list (`-ar: falei, falou,
  …`, `falaram → falar`) on its OWN line; one full example with translation
  set off on its own line where the point needs it. The UI renders
  explanations `whitespace-pre-wrap`, so the newlines in the JSON are the
  formatting. `scripts`: a reflow pass exists (sentence-split, ≤2 sentences
  per paragraph, form-lines isolated) — new content should be BORN in this
  shape, not reflowed after.
- **Sequencing follows a canonical course order** for the language (official
  CEFR inventories where they exist: Plan Curricular, TORFL, Goethe,
  DELF/DALF, CELI, ΚΠΓ; otherwise the established reference-course sequence
  for that language). A drill may only use structures earlier in the path.

### Drills (per point)
- ≥6 drills; paradigm points cover EVERY declared cell with ≥2 drills each
  (seeder hard-fails otherwise — do not weaken the gate, fix the content).
- **Complete, natural, communicative sentences** — something a native
  speaker would actually say ("Enjoy your vacation", "It depends on you"),
  never grammar showcases ("The man who the dog that barked bit ran").
  Vary person, tense, vocabulary, and register across the drills.
- **Ingredients rule** (aspect/tense points especially): the sentence must
  contain the co-occurring cue that *forces* the target form — 'yesterday'
  with perfective/preterite, 'every summer' with imperfect/habitual, 'by
  tomorrow' with future perfect. A learner should be able to infer WHY this
  form from the sentence alone.
- Single-token answers (hyphenated/apostrophized clitics count as one);
  the answer never appears in the visible frame (echo-frames where the
  construction repeats the word are the only exemption); hints are English
  recipes that never contain the answer string.
- Every drill carries a natural English translation; every translation
  reads like English, not gloss-ese.

### Script & hint layers
- Non-Latin scripts (ru/ar/el): **transliteration on every drill and
  example sentence**, reflecting SURFACE pronunciation, not letter-mapping —
  Russian marks stress (and ideally vowel reduction), Arabic uses scholarly
  romanization (ḥ/ṣ/ā), Greek follows the shared el romanizer. Letter-by-
  letter transliteration that a reader can't pronounce from is a defect.
- Gloss-first languages (mi/sw/yo/xh/ha): word-by-word gloss on every
  drill (`·`-separated, `___` for the blank).
- Tone & length: Yoruba is always fully diacritized (grading stays
  lenient); Hausa tone/vowel length are real but unwritten — teach them in
  explanations ("teach by ear"), never mark a learner wrong for them.

### Vocabulary & example sentences
- Corpus languages: ≥10,000 frequency-ranked words (HermitDave/OpenSubtitles
  frequency merged with kaikki/Wiktionary glosses; inflections folded onto
  headwords via the language's NLP), rank→CEFR banding, POS + morphology.
  Curated starter entries upsert AFTER the corpus so hand-authored quality
  wins on shared words.
- Example sentences: Tatoeba-graded (difficulty = frequency rank of the
  rarest word — the i+1 principle), ≥3 per word where the corpus allows;
  sentences rotate per appearance and never repeat the last-shown.
- English (reverse direction): word translations + example-sentence
  translations in every support locale (`support_locale`), so "learning
  English from X" is first-class.

### Vocabulary morphology — language-shaped word forms (2026-07)
Every vocabulary card carries what a learner of THAT language needs for
THAT part of speech — not a generic template. The data lives in
`vocabulary.morphology` as `chips` ({label, value} facts) + `charts`
({title, columns?, rows} tables), built per language by
`backend/services/seeder/morphology_charts.py` from the kaikki extracts
(committed as `data/{code}_morphology.json`, merged automatically in
`BaseSeeder.load`) and rendered generically by `FormsPanel` on lesson and
item pages. The per-language bar:

| Lang | Verbs | Nouns | Adjectives |
|---|---|---|---|
| ru | aspect + aspect pair(s), present/future + past (by gender) + imperative charts | gender, animacy, 6-case × sg/pl declension | comparative, short forms |
| es/pt/it/fr/ca/ro | gerund + past participle chips; core tense charts (present, preterite/passé-simple family, imperfect, future/conditional, present subjunctive) | gender + plural | feminine + plural |
| de | Präteritum, Partizip II, auxiliary chips + present chart | der/die/das + genitive + plural (the dictionary triple) | comparative + superlative |
| ar | verb form I–X, non-past, maṣdar, active participle + past/non-past person charts | gender, (often broken) plural, dual | — |
| el | aorist + passive chips, present chart | gender + 4-case declension | — |
| tr | (kaikki verb tables too noisy — grammar path teaches the regular machinery) | 6-case × sg/pl chart | — |
| sw | infinitive, imperative sg/pl, habitual chips | plural + noun class | — |
| xh/yo | plural where the extract has it — full treatment blocks on WP4 native review + better sources | | |
| en/mi | PENDING: en irregular parts (from the en kaikki extract), mi has no kaikki — curate with WP4 |||

Rules: the chart set stays SMALL (core tenses, not the full 60-form table
— the grammar path teaches the rest); forms come from Wiktionary, never
generated by a model; a language adding charts adds a builder + unit test
in `test_morphology_charts.py`; regenerate with
`python -m backend.services.seeder.morphology_charts -l <code>` after a
frequency-deck change.

### Sources & references (in-app)
- References on points must be **public and authoritative**. Wikipedia is
  fine as a supplement but never the lead reference. Every grammar point's
  `references` list OPENS with its language's registry entry below
  (enforced by `test_every_point_leads_with_authoritative_reference`).
- **Verified reference registry** (every URL fetch-checked 2026-07-11; when
  adding a language, verify the URL actually resolves before shipping it —
  never cite a source you haven't loaded):

  | Lang | Lead reference | URL |
  |---|---|---|
  | es | RAE — Diccionario de la lengua española | https://dle.rae.es/ (renders in browsers; blocks curl — that's fine) |
  | fr | Vitrine linguistique / BDL (OQLF) | https://vitrinelinguistique.oqlf.gouv.qc.ca/ |
  | de | grammis (Leibniz-IDS) | https://grammis.ids-mannheim.de/ |
  | it | Treccani — La grammatica italiana | https://www.treccani.it/enciclopedia/elenco-opere/La_grammatica_italiana |
  | ca | GIEC (Institut d'Estudis Catalans) | https://giec.iec.cat/ |
  | pt | Ciberdúvidas da Língua Portuguesa | https://ciberduvidas.iscte-iul.pt/ |
  | ro | dexonline | https://dexonline.ro/ |
  | el | Portal for the Greek Language | https://www.greek-language.gr/greekLang/index.html |
  | ru | Russian National Corpus | https://ruscorpora.ru/en (gramota.ru geo-blocks scripted checks; RNC verified) |
  | ar | Al Jazeera Learning Arabic (MSA) | https://learning.aljazeera.net/en |
  | en | Cambridge Dictionary — English Grammar | https://dictionary.cambridge.org/grammar/british-grammar/ |
  | tr | Türk Dil Kurumu sözlükleri | https://sozluk.gov.tr/ |
  | mi | Te Aka + Te Whanake | https://maoridictionary.co.nz/ + https://www.tewhanake.maori.nz/ |
  | sw | Kamusi Project + Live Lingua (FSI/PC) | https://kamusi.org/ + https://www.livelingua.com/courses/swahili |
  | ha | Live Lingua (FSI/PC Hausa) | https://www.livelingua.com/courses/hausa |
  | yo | Live Lingua (FSI/PC Yoruba) | https://www.livelingua.com/courses/yoruba |
  | xh | Live Lingua (PC Xhosa) + IsiXhosa.click | https://www.livelingua.com/project/peace-corps/xhosa + https://isixhosa.click/ |

  Es also carries CVC Cervantes on many points; keep both. Public-domain
  FSI/Peace Corps courses (Live Lingua) are the "prime tools" for languages
  without an academy portal — quotable AND linkable, unlike the private
  library.
- The private course library is calibration only. Never cite it, never
  copy a sentence from it.

### Verification (who checks what)
- Structural gates are automated (validator + seeder: markers, leaks,
  density, coverage, display_order). They CANNOT check linguistic truth.
- Machine-authored content is provisional by definition. The named-human
  gate (Contribute → Roles, point_review_notes) is the only thing that
  makes it trustworthy; recruiting those reviewers is WP4(a) and applies
  to EVERY language, not just the African tier.
- When authoring at Opus/Sonnet class: follow this section as a checklist,
  self-audit each point against "Drills" line by line, and run
  `scratchpad validators + GrammarSeeder.transform()` before seeding. If a
  form's correctness is uncertain, mark the point `reviewed: false` rather
  than guessing confidently.

### Resource-informed improvement backlog (calibration notes, 2026-07)
- ru: transliterations are letter-mapped today — regenerate with stress
  marks (minimum) or surface pronunciation (goal). Aspect drills: audit
  that every perfective/imperfective drill carries its time-expression cue.
- ha: audit path order against the canonical Teach Yourself sequence —
  confirmed gaps to add as drafts: the genitival link (-n/-r) as its own
  point, the habitual aspect (-kan), a "choosing between aspects" contrast
  point, reduplication patterns beyond ideophones.
- All languages: sentence-naturalness pass — replace any drill that reads
  like a textbook example with an everyday communicative sentence.

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

### WP3b — Deepen the A1-only tier to C2 (ar, el, ro, mi, then fr/de/it/ca)
**Goal:** the nine languages WP3/WP7 left at a 12-point A1 tab need the full
A1→C2 grammar ladder, like WP2 did for es/tr/ru. **Arabic DONE 2026-07 (12
→ 40, full A1→C2):** +28 MSA points — A2: past tense, future سـ/سوف, sound &
broken plurals, the dual, prepositions, comparative أفعل, kāna, object
pronouns, numbers 3–10 polarity; B1: subjunctive المنصوب, jussive & لم,
inna's sisters, imperative, the maṣdar, participles, relative clauses; B2:
passive المبني للمجهول, derived forms II–IV and V–X, conditionals إذا/إن/لو,
the ḥāl, the tamyīz; C1: weak verbs, the exception إلّا/غير/سوى, vocative &
energetic nūn; C2: fronting/restriction (إنّما/القصر), literary discourse
(أمّا…فـ، قد، لقد). Every drill transliterated (SCRIPT_FIRST hint layer),
paradigm points meet the 2/cell gate, landed reviewed:true per the es/tr/ru +
ar-A1 precedent — a native-speaker verification pass is still welcome (the
Contribute Roles panel + issue tracker are ready for it). **Greek DONE
2026-07 (12 → 40, full A1→C2):** +28 Modern Greek points — A2: aorist,
genitive, plurals, imperfect, future θα, object clitics, comparatives,
prepositions, possessives, modal + να; B1: subjunctive aspect, imperative,
clitic clusters, relatives (που/ο οποίος), mediopassive -ομαι, perfect
παρακείμενος, conditionals αν; B2: passive aorist, unreal conditionals,
contracted -άω verbs, synthetic comparatives, participles (-οντας/-μένος),
reported speech; C1: pluperfect/future perfect, deponent verbs, subordinating
connectors; C2: clitic doubling/topicalization, register & fixed expressions.
Transliterations auto-generated by the shared el romanizer. **Romanian DONE
2026-07 (12 → 40, full A1→C2):** +28 points — perfectul compus, genitive-
dative, the imperfect, both futures, clitics, the subjunctive/conditional,
passive/gerund/supine, pluperfect & past conditional, clitic doubling,
literary register. **Māori A2+B1 DRAFTED 2026-07 (12 → 29, reviewed:false):**
+17 Draft points behind the fluent-speaker review gate (kua, e…ana, dual/
plural pronouns, a/o possession, passives, nominalisation, whaka- causative,
actor-emphatic nā/mā, kia, ki te/mehemea, directional particles), each with a
word-by-word gloss (GLOSS_FIRST layer). Māori is held to the WP4 differentiator
bar — unlike the major documented world languages ar/el/ro (reviewed:true),
its deepening waits for a fluent speaker, and advanced oratory register (C1–C2
whaikōrero) is deliberately NOT machine-drafted. **French, German, Italian,
Catalan DONE 2026-07 (each 12 → 40, full A1→C2, reviewed:true):** the European
tier now matches es/tr/ru — fr (passé composé/subjonctif/conditionnel/passé
simple), de (cases, Konjunktiv I/II, Nominalstil, modal particles), it
(passato prossimo/congiuntivo/passato remoto/dislocation), ca (perfet + passat
perifràstic, pronoms febles combinats, passat simple). **With this, every
Latin- and non-Latin-script language except Māori reaches a full, live A1→C2
grammar path.** Remaining: mi B2–C2 (needs a fluent-speaker author); en stays
A1 (targets learners *from* other languages, deepened on demand). A native-
speaker verification pass is welcome on all machine-authored deepening (the
Contribute Roles panel + issue tracker are ready) — no gate checks *linguistic*
correctness, only structure.
**Model:** authoring `claude-opus-4-8`; native review is the human gate.
**Effort:** M per language.

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
speakers/linguists as contributors (roles exist — grant `reviewer` per
language from the Contribute page's Roles panel; ContributorPage supports
review + approval + AI checks); have them audit tone marks (yo), concords
(xh), aspect glosses (ha), and approve or fix each point. (b) Extend sw to
~50 points and yo/ha/xh to ~40, through C2-equivalent. **Swahili DONE
2026-07 (32 → 50):** +18 B1–C2 drafts (`reviewed: false`, awaiting the
human gate) — U-class and Ku-class nouns, place classes 16–18,
demonstratives across classes (paradigm-tagged), comparatives, -po- time
and -vyo- manner relatives, reported speech (kwamba/kuwa/eti), compound
tenses, reversive -ua, concessives, ndi- emphatics, -sipo- 'unless',
ili + subjunctive, participial -ki-, kupiga idioms, methali, respect
register. **Yoruba DONE 2026-07 (24 → 40):** +16 drafts — ní/sí, the full
question-word paradigm (tagged), modals fẹ́/lè/gbọ́dọ̀, láti purpose,
kí-clauses and blessings, post-nominal numerals + mélòó, olù-/oní-/ì-
nominalization, fi/fún serial idioms, nígbà tí time clauses, sì chaining,
reduplication (jíjẹ/kíákíá), ideophonic intensifiers (láúláú/roro —
regional spellings flagged for the native reviewer), bí…ṣe how-clauses,
òwe, the ẹ/ẹ̀yin respect register, discourse particles (o/ná/ṣebí).
**Hausa DONE 2026-07 (22 → 40):** +18 drafts — demonstratives (tagged),
da-possession, mai/masu adjectives, the relative completive
(suka/muka/aka — tagged), post-nominal numerals + nawa, sai, verbal nouns
in the continuous, don/domin/saboda, kafin/bayan, connectors
kuma/har/ma/amma, ideophonic intensifiers (fat/ƙirin/wur), verb grades
(saya/sayar, dafa/dafu), indirect objects mini/maka/masa (tagged),
ɗan-compounds, karin magana, greeting protocol (Ranka ya daɗe),
discourse particles (fa/dai/mana/ashe), ko.
**Xhosa DONE 2026-07 (24 → 40):** +16 drafts — classes 11/14/15, absolute
pronouns (tagged), persistive -sa- (still / no longer), counting with
concords + -ngaphi, instrumental nga-, xa + participial when-clauses,
potential -nga- (can/may + andinako), statives -eka/-akala (kufuneka),
past continuous bendi-/ebe- (tagged), ukuze purpose, kuba/ngoba/kutheni,
ukuthi ideophones (cwaka/gqi/tu), amaqhalo (umntu ngumntu ngabantu),
hlonipha register, discourse particles (ke/nje/phofu/kaloku), full
greeting protocol. **All of (b) is now authored — sw 50 · yo 40 · ha 40 ·
xh 40; every deepening point is a Draft awaiting (a)'s named reviewers.**
(c) WP1 variation drills for all four.
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
**(a) DONE 2026-07-16 — cached neural TTS.** POST /api/audio/tts:
content-verified text only (drill sentences with answers filled, example
sentences, vocab words — never an open TTS proxy), rate-limited on cache
misses, synthesized via edge-tts (keyless neural voices), stored in the
public 'tts' Supabase Storage bucket (created live), cached by
(voice, sha256(text)) in tts_audio (migration 20260723000000, applied
live). SpeakButton tries explicit audioUrl → cached neural TTS →
browser speechSynthesis (now only the fallback). Coverage: 13/17
languages (en es fr de it ca pt-BR ro el ru tr ar-SA sw-KE); yo/ha/xh/mi
keep the browser fallback.
**(d) DONE 2026-07-17 — Azure Speech provider.** The keyless endpoint
proved flaky in the worst way: Microsoft rejects edge-tts from
datacenter IPs, so prod synthesis failed on EVERY request (tts_audio
stayed at 0 rows; beta heard the browser robot voice throughout) while
local dev worked perfectly. synthesize() is now a chain: Azure Speech
(same neural voices, official REST API, SSML with the -10% learner
rate) when AZURE_SPEECH_KEY is set → edge-tts otherwise (local dev).
**Owner setup (REQUIRED for prod audio):** create a free Azure Speech
resource (F0 tier: 500K chars/month ≈ thousands of clips), then in DO
set `AZURE_SPEECH_KEY` (encrypted, no quotes) and `AZURE_SPEECH_REGION`
(the resource's region, e.g. eastus) on the backend component and
redeploy. Also still recommended: `SUPABASE_SERVICE_ROLE_KEY`, so clips
cache to the CDN instead of re-synthesizing per session.
**Remaining:** (b) yo/ha/xh/mi via local MMS-TTS bulk-generated offline
into the same bucket — quality-check each before shipping; (c) human
recordings for the highest-value items (A1 first).
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
checks on `claude-sonnet-5` (now default). (b) Per-user usage tracking —
**message logging + tiered allowances DONE 2026-07** (`tutor_usage` table;
flat pricing, never per message: free = 20 msgs/month, plus = 100/day fair
use, both shown as a meter in the tutor UI with structured 402s — see
docs/accounts-and-roles.md "Account tiers"); **token/cost capture DONE
2026-07**: every chat turn logs input/output + cache read/write tokens
(summed across tool-loop calls; dev-mock produces deterministic
pseudo-counts), the post-session summarizer logs a kind='summary' row
that never counts against allowances, and GET /api/contribute/tutor-usage
(admin-only) rolls usage up per (language, model, kind) priced at list
rates — shown as the "Tutor costs" panel on the Contribute page
(pricing table: backend/services/tutor_costs.py; update when Anthropic
list prices change). Remaining: per-user drill-down if ever needed.
(c) Tutor should propose drills from GRAMMAR weak areas
(data now flows; prompt already tags kind=grammar — verify behavior with
real key and tune the charter). (d) **Streaming DONE 2026-07**: POST
/api/tutor/chat/stream emits SSE delta/reset/done events (same
allowance + rate gating as /chat; persistence lands before the done
event); the chat UI renders the reply as it streams with a cursor, and
falls back to the plain endpoint if the transport fails.
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
**Status: DONE 2026-07.** Placement is a deterministic level staircase
(`adaptive_next` in repositories/onboarding.py): probe starts at A2, steps
up on a correct answer and down on a miss, choice weighted 60% grammar,
and it stops early once the estimate is stable — 2 consecutive misses at
the A1 floor (beginners exit in 3 items), 2 consecutive passes at the C2
ceiling (experts in ~6), 4 direction reversals (boundary oscillators in
5–8), hard cap 12. Stateless endpoint
`POST /api/onboarding/placement/{id}/next` re-grades the replayed answer
history each round (same NLP validator as scoring); the final estimate
reuses `estimate_level`. Onboarding UI asks one item at a time with a
Skip button and a progress line; the old batch endpoints remain as
fallback. 10 unit tests drive the walk end to end.
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
accuracy, streak, misses, next review). **(f)–(h) DONE 2026-07:**
(f) Quick-Cram — "⚡ Quick cram this + related" on item pages and the path
launches /cram?points=…, an ungraded twin of the review session (GET
/api/review/cram builds cards straight from content tables, 3 drills/point
seeded per day; nothing is ever submitted — no FSRS, no log, no ghosts);
(g) in-app search — /search (Dashboard → Search) over the active language's
grammar + vocabulary (GET /api/curriculum/search, review-policy-aware,
ILIKE-escaped), grammar hits deep-link into the path (?point= opens +
scrolls); (h) theme switcher — System/Light/Dark in Settings, persisted in
prefs, `.dark` on <html> (no-flash inline script in index.html); the dark
palette remaps the Tailwind v4 gray-ramp CSS variables in index.css so no
component needed dark: variants. Remaining: authoring `related` + offline
refs beyond the tr/es/ru A1 tiers.
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
**Tile interaction (owner feedback + screenshots, 2026-07-16, DONE):** the
big Learn button STARTS a learn session (next queued deck with items left);
its chevron expands the deck rows. The big Review button starts all reviews;
its chevron expands Grammar Only / Vocab Only rows with live due counts
(`/api/review/due?card_type=`, personal cloze cards count as vocab).
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
the Contribute page's Roles panel (and inline per account in the Accounts
table), bootstrapped once via `scripts/grant_admin.sh`.
(b2) **Tutor skills + per-account access — DONE 2026-07-13 (local, ships
with next deploy)**: every language with a grammar path has a tutor (17/17;
pt/el/ro added). Per-language knowledge lives in skill bundles at
`backend/services/tutor_skills/{code}/` — SKILL.md (core brief, always in
the prompt, <2.5KB), REFERENCE.md (the app's actual grammar path with the
learner's card titles, generated from data/grammar — regenerate when paths
change), ERRORS.md (interference errors + coaching moves). The deep files
load on demand through the tutor's `consult_reference` tool (progressive
disclosure — deep knowledge never bloats the per-turn context), and the
regression suite bounds every file's size. Content is derived expertise:
NEVER quotes of the private resource library. Learner memory (weak items,
`remember` facts, session summaries) was already per-turn context and now
pairs with the skills. Admin per-account tutor override on the Accounts
table: `user_profiles.tutor_access` default/enabled/blocked +
`tutor_daily_cap` (migration `20260720000000`, NOT yet applied live —
beta freeze); blocked wins over everything including TUTOR_FREE_ACCESS
(403 tutor_blocked), enabled grants a capped daily allowance with no
billing entitlement (tier "granted") — the bounded-cost way to let a
friend try the tutors.
Remaining, in order:
(a) **Per-language tutor model selection — DONE 2026-07**:
`languages.tutor_model` (NULL = the `TUTOR_MODEL` global default), admin
picker on the Contribute page (allowed ids: `claude-fable-5`,
`claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`), and
both chat endpoints + the usage log resolve the override, and the WP9(b)
"Tutor costs" panel shows per-language spend to inform the choice.
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

### WP16 — Language plans: Single vs All, different prices
**Shipped (2026-07-11, model + UI):** signups choose a plan at the end of
onboarding — "{Language} only" (lower price) or "All languages".
`user_profiles.plan_scope` ('single'|'all', migration
20260718000000) + `plan_language_id`; existing accounts grandfathered as
'all'. Enforcement: the profile upsert 403s a single-plan account switching
`active_language_id` away from its licensed language, and the language
picker disables (labels) the locked options. Early accounts keep free
access to their choice; the onboarding copy promises they keep their
price when billing goes live — honor that.
**Stripe wiring shipped locally (2026-07-14, deploys with next push):**
(a) `STRIPE_PRICE_SINGLE`/`STRIPE_PRICE_ALL` envs; POST
/api/billing/plan/checkout (dev-mock grants directly) + the shared
/webhook (metadata.kind='plan' separates plan events from tutor events;
revokes are subscription-id-scoped so the two products can't cross-fire);
`plan_subscriptions` table (migration 20260721000000, NOT applied live —
beta freeze) records the backing subscription while user_profiles stays
the enforced plan; cancellation deactivates the row but never touches the
profile — see (e).
(b) Settings "Plan" card: current plan, single→all upgrade via checkout,
"Manage billing" via Stripe Billing Portal (proration happens there).
(c) Router tests for the single-plan 403 in test_auth.py.
(d) Onboarding + Settings pull prices from GET /api/billing/plan/prices
(live Stripe Price reads; never hardcoded; null until configured, with
free-beta copy as fallback).
**Remaining:**
(e) Decide the free tier's shape before launch (e.g. A1 free in one
language) AND what a canceled plan downgrades to — pricing decisions for
the owner, not a model. Then create the two Prices in Stripe, set the
envs + webhook secret in DO, and flip off dev-mock.
**Recommended pricing (2026-07-14 analysis, anchored to Bunpro $5 /
WaniKani $9 / Duolingo Super ~$13 and Sonnet-5 tutor COGS of
~$0.01–0.02/message):** Single $7/mo or $60/yr; All $14/mo or $120/yr;
Tutor+ add-on ~$10/mo. Tutor allowances (implemented, env-tunable):
free 20/mo, single plan 100/mo, all plan 300/mo, Tutor+ 50/day fair
use. Tutor default model is now `claude-sonnet-5` with low-resource
languages pinned to Opus — roughly halves projected tutor COGS. Prices
live in Stripe only (never hardcoded); revise against the WP9b cost
panel once real usage exists.
**Model:** `claude-opus-4-8` (billing = security-sensitive). **Effort:** M.

### WP17 — English drill hints in the learner's language
**State (2026-07-12):** vertical slice landed locally, NOT yet deployed
(beta freeze — migration `20260719000000_drill_hint_translations` is
committed but unapplied; apply it live together with the code).
`drill_hint_translations (drill_id, locale, hint, translation,
reviewed)` + eff_locale COALESCE in all four drill read paths (reviews,
lesson bulk, card detail, quick-cram). GrammarSeeder merges companion
files `data/grammar/{code}_drill_hints.{locale}.json` keyed by point
title + exact drill sentence (drill ids are reborn every reseed, so the
sentence is the only stable key; a stale key fails the seed loudly).
Spanish, Portuguese, and Russian authored for the FULL English path
(2026-07-13): 40 points × 6 drills × 3 locales = 720 pairs, all through
the seeder gate (title/sentence match, no empties, no answer leaks) —
these three first because they're the active beta testers' languages.
`reviewed:false` pending the per-locale reviewer. UI unchanged — the
payload already carried hint/translation.
**Remaining:** (a) the other 9 support locales (fr, de, it, ca, ro, el,
tr, ar, sw), machine-assisted (Sonnet, batch) then a reviewer pass per
locale before flipping the file's `reviewed` flag (never
self-certified — §3b); (b) apply the migration + reseed en when the
freeze lifts. **Model:** draft `claude-sonnet-5`, verify per-locale
reviewer. **Effort:** M.

### WP18 — Tutor memory parity with the owner's Obsidian workflow
**(a)–(c) DONE 2026-07-16** — tutor_sessions append-only log (migration
20260722000000) + summarizer continuity (last 3 session summaries in its
context) + "Past sessions" in the tutor UI; Active Focus via `remember`
scopes focus_add/focus_retire (bounded 5, FIFO, `_active_focus` in the
language profile, chips in the UI, /status carries it); Practice/Reference
toggle — reference turns add a MODE flag to the volatile system block,
never persist `remember` output, and reference-only sessions skip the
summarizer client-side. WP9(c) charter tuning landed with it: grammar
weak items are drilled as fill-in-the-blank patterns (consulting the
curriculum reference for staging), never vocabulary flashcards — observe
real transcripts + the cost panel to tune further. Remaining: (d) media
library, below.
**Spec source:** the owner's Obsidian language-learning system
(https://gist.github.com/CorneliuSmith/127de0fa43274523bc28647c5d38b01b) —
the tutors were always meant to work like it. What already maps: the
learner/language profiles + rolling summary ≈ claude_context.md; SRS
weak-area grounding ≈ the 🔴/🟡 flags (computed from review telemetry,
stronger than hand-flagging); the `remember` tool ≈ mid-session capture;
the end-of-session summarizer ≈ session-closure file writes; the
pre-turn grounding ≈ "check all tracking files before engaging."
**Gaps to close, in order:**
(a) **Session log (≈ claude_practice.md).** New `tutor_sessions` table:
one APPEND-ONLY row per ended session (language, started/ended, summary,
message count, weak items drilled). The rolling summary stays as "current
state" but the summarizer also writes the per-session row, and its prompt
gains the last N session summaries as context so continuity stops washing
out. Surface a "Past sessions" list in the tutor UI. Effort: S.
(b) **Active Focus (≈ claude_grammar.md's 📍 list).** A structured,
tutor-managed focus list per language: extend the `remember` tool with
`focus_add` / `focus_retire` scopes writing to a bounded list (≤5 items,
each {structure, reason, added_at}) in the language profile; charter
instructs the tutor to open sessions from the focus list, drill it, and
retire items when mastered (retirements land in the session log). Show
the list as chips in the tutor UI. Effort: S.
(c) **Mode awareness.** The gist's practice/reference distinction: a
lightweight mode hint on /chat (client sends mode; charter: reference
questions get answers WITHOUT logging weak-item drilling or profile
writes — no `remember`, session/end skips the summarizer when the whole
session was reference). Resource-processing mode stays out of scope for
the tutor (the notes→cloze feature is its home). Effort: S.
(d) **Media library (≈ claude_media.md).** Per-language native-content
library with the gist's comprehension tiers (Tier 1: 75–85%, Tier 2:
60–75%, Tier 3: 45–60%): content rows (title, url, kind, level tags),
per-user tier placement estimated from vocab coverage against the item's
word list, tutor recommendations pulled from the learner's current tier
("watch X, you know ~80% of its vocabulary"). This is real product
surface (curation + coverage computation) — own migration, seeder,
browse UI. Effort: M–L; do (a)–(c) first.
**Model:** implementation `claude-sonnet-5`; charter tuning + coverage
heuristics `claude-opus-4-8`+. **Never store secrets in tutor memory.**

### WP19 — Engagement, trust & platform (owner priorities, 2026-07-16)
Adopted from the product assessment; the owner confirmed these as goals.
**(a) Listening / dictation mode — DONE 2026-07-17.** A 🎧 toggle in the
review session (persisted like hintLevel): cloze cards hide the sentence,
a prominent play button speaks the COMPLETED sentence (the missing word
included), and the learner types the blank by ear. Same NLP grading with
all its tolerance; the text reveals after grading. Gated to cloze cards
in the 13 neural-voice languages (TTS_LANGUAGES mirrors the VOICES map);
hints are suppressed while listening. Lights up fully once the Azure
Speech key lands (WP7d).
**(b) PWA installability — DONE 2026-07-17.** manifest.webmanifest
(standalone, theme #172554, 192/512 + maskable icons, apple-touch-icon)
+ a deliberately minimal sw.js registered in prod only: network-first
navigations falling back to the cached shell offline, cache-first for
hashed /assets (immutable), API calls untouched — a deploy can never be
broken by a stale cache. Install from the browser menu ("Add to Home
Screen" / "Install app").
**(c) Review reminders — OPT-IN ONLY, never default (owner directive
2026-07-16).** A Settings toggle, off by default; daily "N cards due" nudge
via email first (push once (b) ships). No reminder of any kind unless the
learner turns it on. Effort: M.
**(d) Error telemetry (Sentry) — code DONE 2026-07-16, awaiting DSNs.**
Backend: sentry-sdk[fastapi] init in create_app (errors only,
traces_sample_rate=0, send_default_pii=False). Frontend: @sentry/react
init in main.tsx + ErrorScreen reports route crashes. Both are complete
no-ops until the owner creates a Sentry org with two projects and sets
`SENTRY_DSN` (backend component env) and `VITE_SENTRY_DSN` (static-site
BUILD-time env) in DO — encrypted, no quotes, then redeploy. ToS §8
discloses anonymous error reports. Satisfies the WP10(b) overlap.
**(e) Tutor mastery suggestions ⭐ — DONE 2026-07-16.** The tutor stars cards
it believes the learner already understands via the `suggest_mastered` tool —
only from evidence in the session, at most a couple per session, never in
reference mode. Stars are pending rows in `tutor_card_suggestions` (migration
20260724); the tutor page shows them with the evidence and two verdicts:
"I know it" advances the card to the seasoned floor (stability/interval ≥ 30
days, next review ~a month out), "Keep drilling" dismisses. NEVER automatic:
`merge_remembered` refuses the reserved `_mastery` scope, and the resolve
endpoint is the only path that touches SRS state.
**(f) Terms of Service — DONE 2026-07-16.** Public `/terms` route (plain
language: beta caveats, AI content accuracy, tutor allowances, billing via
Stripe, what we store), linked from the login screen and Settings.
**Model:** `claude-sonnet-5`; (e) charter wording one tier up.

### WP20 — Content depth & gloss audit (owner escalation, 2026-07-16)
Beta caught two classes of shallow content the gates missed:
**(a) Grammar coverage gaps.** The ru A1 possessives point taught мой/твой/
наш/ваш but omitted the invariable его/её/их entirely (fixed 2026-07-16 —
свой was already its own B1 point, so staging was right; the MEMBER list
was incomplete). Audit every point against the resource library: does the
explanation cover the topic's full member set and its exceptions at that
level, do the drills exercise each member, and is anything deferred
actually staged later in the path (link it in `related` when it is)?
Sweep order: beta-active languages first (en, ru, es, pt), then the rest.
The audit writes findings into point_review_notes so reviewers can verify.
**(b) Support-locale glosses for grammatical words.** Extraction gave case
languages bare suffixes ("of" → ru "-ов"), neuter-less glosses the wrong
gender ("it" → ru "он"), auxiliaries noun senses ("will" → ru "завещать").
Curated hand table now covers ~20 closed-class words × 12 locales (fixed
2026-07-16); the audit should eyeball every remaining function word's
glosses per locale. Rule: where no one-word equivalent exists, a short
parenthesized hint beats a wrong word.
**Model:** `claude-fable-5` (this is exactly the low-resource-linguistics
row of §6 — wrong-but-plausible content is the failure mode).
**Effort:** M–L, chunked per language.
**en + ru pass DONE 2026-07-16.** Findings and fixes: en drills never
exercised They (subject pronouns), his/our (possessives), don't/doesn't
(do-support — the title promised negation), often (frequency), or the
running/writing spelling allomorphs (continuous) — all patched. Three
missing en points authored: Past simple — regular verbs (-ed) (now FIRST
at A2, before irregular), Object pronouns (me, him, them) (A1), and
Imperatives (Open…, Don't…) (A1), each with es/pt/ru hint translations
(the answer-leak gate rejected two draft hints — the gate works). Four
missing ru points authored: Adjective agreement (новый/новая/новое,
paradigm-gated 2-per-cell), Question words (кто, что, где), Conjunctions
и/а/но (the а-contrast), and general Genitive (possession + у/из/после/
для/без) linked to the genitive-of-absence point. **es + pt pass DONE 2026-07-16.** es (43 → 47): Possessives (mi, tu, su —
taught NOWHERE despite adjective agreement existing), Stem-changing verbs
(quiero/puedo/pido — the present points were regular-only), Demonstratives
(este/ese/aquel — pt had them, es didn't), Personal a; Quién/Cuál drills
added to question words. pt (40 → 42): Key irregular presents (vou, faço,
posso, quero — only ser/estar/ter + regulars were taught) and Pretérito
perfeito irregulares (fui, fiz, tive — es had a dedicated point, pt
didn't); O que / Por que drills added to question words. **fr + de + it + ca pass DONE 2026-07-16.** fr (40 → 42): Key irregular
presents (vais, fais, peux, veux — never taught despite the near-future
point USING vais at B1) and The imperative (missing entirely; it/ca had
one); Qui/Quel + mes/notre/leurs/cet drills. de (40 → 43): Stem-changing
presents (du fährst, er spricht), Personal pronouns accusative & dative
(mich, dir — the path taught case articles but a learner couldn't say
"ich liebe dich"), and The imperative; Warum/Wohin drills. it (40 → 42):
Key irregular presents (vado, faccio, posso, voglio) and Stare + gerundio
(the progressive — es/pt had theirs); Chi + possessive drills. ca (40 →
42): Key irregular presents (faig, puc, vull — anar disambiguated from
its past-auxiliary use) and Estar (missing ENTIRELY — the path had ser
and tenir but no estar); Per què + possessive drills. **ro + el + tr + ar + sw pass DONE 2026-07-16 — reviewed-tier sweep
complete (13/17).** ro (40 → 42): Demonstratives (acest/acel incl. the
postposed cartea-aceasta pattern) and Key irregular presents (vreau,
pot, știu — with the vor want/future ambiguity taught); De-ce drill.
el (40 → 41): Demonstratives with the retained article (αυτό ΤΟ βιβλίο,
εκείνος). tr (40 → 42): Question words (ne, kim, nerede — the path had
only the mı particle) and Negation with değil (verbs and var/yok could
be negated, 'to be' sentences could NOT). ar: ذلك/تلك added to
demonstratives (point taught هذا/هذه only) + لماذا/ماذا question drills.
sw (deepest path, 50 points — held up best): only kwa nini and -ngapi
drills were missing. yo/ha/xh/mi: audited WITH the native reviewers as
part of the WP4 gate, not before.

### WP21 — The Reader: comprehensible input on demand (owner, 2026-07-16)
The tutor's third surface after Practice and Reference: the learner names
a topic, the app writes them a short text at exactly their level.
**(a) Level-locked generation.** One Claude call produces the whole
artifact as strict JSON: a ~150–250-word text on the requested topic
constrained to the learner's LEARNED grammar (point titles from their
cards) and known-vocabulary level, deliberately seeding 5–8 new words
chosen to be guessable from context — plus a token-level gloss map,
per-sentence translations, the new-word list, and the list of grammar
structures used. Weak items and Active Focus words are woven in for
re-exposure. Everything the reader UI needs ships in that one response —
hovers and translations never cost a second API call. Costs ride the
existing tutor allowance (1 message per generation).
**(b) Three-stage disclosure (the pedagogy).** Stage 1 — guess first: no
translations available; seeded new words are subtly marked; tapping one
asks "What do you think it means?" and reveals the gloss only after the
learner commits a guess (the generation effect: a produced guess, right
or wrong, beats a passive lookup). Stage 2 — after the first pass, hover/
tap glosses unlock for every word, plus per-sentence translations. Stage
3 — "Explain this sentence" on demand (allowance-gated) with links into
the app's grammar points when a used structure matches one.
**(c) Capture to SRS.** Any new word → one tap "Add to my reviews": the
reading's own sentence becomes a personal cloze card via the existing
notes pipeline, so words learned in context are reviewed in that context.
**(d) Grammar gap collector (owner request).** The generator reports the
structures it used; anything not matching a grammar point title for that
language upserts into `grammar_gap_log` (count-incremented, statused
new/planned/covered/dismissed). The app collects its own curriculum
TODOs from real usage — WP20's audit, automated forward. Surfaced to
admins in Contribute.
**Scope notes:** generated text, not scraped web text — real articles
can't be level-locked and carry copyright; the "internet" advantage lives
in the model's knowledge of the topic. Reading length/frequency naturally
bounded by the tutor allowance. Dev-mock (like tutor_dev_mock) makes the
whole flow CI-testable without an API key.
**Model:** generation `claude-sonnet-5` (low-resource languages pin the
stronger model, same rule as the tutor); UI `claude-sonnet-5`.
**Effort:** L (migration DONE 2026-07-16; service, router, reader UI).

### WP22 — English from X: the full support-locale treatment (owner, 2026-07-17)
English is the app's hardest teaching problem: every learner arrives from a
different L1, so "the best it can be" means localized AND contrastive.
**(a) DONE 2026-07-17 — switcher + explanation infrastructure.** The
translation-language switcher now lives in BOTH the review session and the
lesson walkthrough (switching remounts; suspended lessons re-teach in the
new language by design). New `explanation_translations` table (migration
20260726, applied live) + `en_explanations.{locale}.json` seed format +
COALESCE in the lesson payload and review detail: the whole explanation
renders in the learner's support locale when a row exists.
**(b) L1-aware explanations — ru/es/pt full sets DONE 2026-07-17.**
43 points × 3 locales = 129 rows live, each written FOR that L1: articles
explained to a no-article language (ru) vs cognate-article languages
(es/pt), the missing-copula trap, do-support vs intonation questions,
Continuous framed against Russian aspect / estar+gerundio / estar+gerúndio.
reviewed:false until native review. Remaining: other locales by learner
activity.
**(c) Vocabulary translation overrides — ru, es, pt DONE 2026-07-17.**
Mechanism: data/en_translation_overrides.tsv (word/locale/translation),
applied LAST in the seeder — beats extraction and the curated table —
plus a direct-DB upsert for live rows the current seed records no longer
reach. 666 rows live (ru 193, es 243, pt 230): every sampled wrong-sense
fix (grand→штука-class errors) and every A1/A2 coverage gap in all three
locales. Articles a/an/the now carry contrastive glosses ("определённый
артикль (в русском нет)" / "el; la (artículo definido)") instead of
sitting empty. A1/A2 gap count across ru+es+pt: 0 (verified live).
B1–C2 words without a locale row fall back to the English definition
deliberately — monolingual definitions are the standard pedagogy from B1
up, and the pipeline-wide gap there (~1.4–1.9k/locale) is a
reviewer-era task, not a launch blocker. Tokenizer shrapnel
(ain/isn/de/mm) blocklisted in the seeder and purged from the live DB.
Remaining: other locales' A1/A2 passes by learner activity.
**Original measurement:** Sampled
defect rate ~10–15% wrong-sense at A1/A2 (grand→штука, mine→шахта,
most→наи-) plus 185/1521 A1-A2 words missing ru rows entirely (ro: 390
missing; sw: 821). Plan: an overrides file that beats the extraction TSV,
authored word-by-word for A1+A2 per locale, uncertain pairs flagged for
native reviewers ("double review" = extraction + my check + reviewer).
**Model:** `claude-fable-5` for all content authoring (contrastive
pedagogy in 12 locales is the low-resource-linguistics row of §6).

## 6. Model selection guide

| Task type | Model | Why |
|---|---|---|
| Low-resource linguistics (sw/yo/ha/xh/mi/ar authoring, review triage) | `claude-fable-5` (else `claude-opus-4-8`) | Accuracy is the constraint; errors here damage the differentiator |
| High-resource grammar authoring (es/fr/de/it/tr/ru/en) | draft `claude-sonnet-5` → verify `claude-opus-4-8` | Volume work with a cheap drafter, correctness held by a stronger verifier |
| Variation-sentence generation (WP1) | as above, per language tier | Same split |
| Security/eval-sensitive code (billing, RLS, FSRS gate) | `claude-opus-4-8`+ | Subtle failure modes |
| Well-specified feature code (UI, endpoints, pipelines) | `claude-sonnet-5` | Fast, reliable on scoped specs |
| Mechanical ETL, string extraction, bulk edits | `claude-haiku-4-5-20251001` | Cheapest that does the job |
| Tutor chat runtime (paid) | `claude-sonnet-5` (config default); low-resource languages (mi/sw/yo/ha/xh/ar) pin `claude-opus-4-8` via `TUTOR_MODEL_LOW_RESOURCE` (admin per-language override wins) | Sonnet handles scaffolded coaching at ~40% of Opus cost; accuracy-critical languages keep the stronger model |
| Tutor summarizer / AI semantic checks | `claude-sonnet-5` (config default) | Off hot path, good judgement per dollar |
| Adversarial verification of any generated content | one tier above the generator | Never self-certify |

Two standing rules: **generated content is never self-certified** (a different,
stronger model or a human verifies), and **African-language content always gets
the strongest available model plus a human gate**.

**Fable sunset note (2026-07, updated 07-11):** `claude-fable-5` access is
ending. Everything judgment-heavy that Fable was reserved for has been
front-loaded and is DONE: the full A1→C2 grammar ladders for all thirteen
documented languages (Portuguese included, 40 points/260 drills, Brazilian
register per the library calibration), the African + Māori deepening drafts,
the verified authoritative-reference registry (§3b table — every point now
leads with its academy/corpus/public-domain source, regression-guarded),
and §3b itself (which encodes the authoring judgment as an executable
checklist). After the sunset, Opus-class models author against §3b
line-by-line — the checklist IS the quality bar, so treat any §3b deviation
as a bug, not a style choice. Remaining content work needs no Fable: WP1
sentence-naturalness passes, §3b backlog items (ru stress-marked
transliterations, ha canonical-sequence gaps), Hausa corpus sourcing, and
thin-corpus growth for yo/xh.

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
