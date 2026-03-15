# Roadmap: PolyglotSRS

## Overview

PolyglotSRS delivers a language-aware SRS platform in six phases, building from database foundation through NLP backends and seed data to the core review loop, then layering progressive curriculum and content enrichment. Each phase delivers a verifiable capability: correct schema with auth, testable NLP validation, populated language data, a working daily review session, structured grammar progression, and rich content with audio and definitions. The critical path runs through the first four phases -- everything exists to make the review session work.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Schema, Auth, and SRS Engine** - Database foundation with RLS, Supabase Auth, and SM-2 scheduling algorithm
- [ ] **Phase 2: NLP Backends and Answer Validation** - Three language NLP backends implementing 4-tier answer checking
- [ ] **Phase 3: Seed Data Pipeline** - Russian, Arabic, and English vocabulary and grammar data loaded from open sources
- [ ] **Phase 4: Core Review Experience** - Full review session with drills, NLP feedback, dashboard, RTL support, and on-screen keyboards
- [ ] **Phase 5: Progressive Content and ESL** - CEFR-ordered grammar curriculum, prerequisite chains, ESL translations, and content browsing
- [ ] **Phase 6: Content Enrichment and Language Polish** - Wiktionary definitions, Forvo audio, Tatoeba sentences, and language-specific display features

## Phase Details

### Phase 1: Schema, Auth, and SRS Engine
**Goal**: Users can authenticate and the system can schedule SRS reviews against a correct, secured database
**Depends on**: Nothing (first phase)
**Requirements**: DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07, SRS-01, SRS-02, SRS-03, SRS-04, SRS-05, AUTH-01, AUTH-02, AUTH-03
**Success Criteria** (what must be TRUE):
  1. User can create an account with email/password and log in with Google OAuth, with session persisting across browser refresh
  2. All database tables exist with language_id parameterization, morphology JSONB, translations table, and drill sentence support
  3. RLS policies enforce that users can only read/write their own data (tested with two separate user accounts)
  4. SM-2 algorithm correctly computes next interval, ease factor (floor 1.3), and resets on failed reviews, with ease recovery mechanism
  5. Review log records every review event with quality rating, time taken, and timestamp
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md -- Project scaffold, database schema migrations, RLS policies, and language seed data
- [x] 01-02-PLAN.md -- SM-2 algorithm with ease recovery, quality auto-mapping, and interval fuzzing (TDD)
- [ ] 01-03-PLAN.md -- FastAPI app, JWT auth, RLS-aware repository layer, and API endpoints

### Phase 2: NLP Backends and Answer Validation
**Goal**: The system can validate typed answers in Russian, Arabic, and English with nuanced morphological feedback
**Depends on**: Phase 1
**Requirements**: NLP-01, NLP-02, NLP-03, NLP-04, NLP-05, NLP-06, NLP-07, NLP-08, NLP-09, NLP-10
**Success Criteria** (what must be TRUE):
  1. BaseNLP interface exists and all three language backends (RussianNLP, ArabicNLP, EnglishNLP) are registered and callable
  2. 4-tier validation returns correct AnswerResult for each tier: CORRECT (exact match), CORRECT_SLOPPY (normalized match or transliteration), WRONG_FORM (right lemma/root wrong inflection), WRONG (no match)
  3. Russian backend accepts Latin-to-Cyrillic transliteration as CORRECT_SLOPPY and returns WRONG_FORM with aspect explanation when wrong aspect partner is used
  4. Arabic backend never fails on diacritic presence/absence and returns WRONG_FORM with root + form table when wrong verb form is used
  5. Answer alternatives array is checked before returning WRONG for all languages
**Plans**: 5 plans

Plans:
- [ ] 02-00-PLAN.md -- Wave 0: failing test scaffolds for all NLP backends (RED phase)
- [ ] 02-01-PLAN.md -- BaseNLP interface, 4-tier check_answer pipeline, AnswerResult relocation, NLP registry
- [ ] 02-02-PLAN.md -- Russian NLP backend with pymorphy3, transliteration, aspect detection (TDD)
- [x] 02-03-PLAN.md -- Arabic NLP backend with camel-tools, diacritic invariance, verb form detection (TDD)
- [ ] 02-04-PLAN.md -- English NLP backend with spaCy, lemminflect, article stripping (TDD)

### Phase 3: Seed Data Pipeline
**Goal**: The database contains usable vocabulary and grammar data for all three languages, ready for review sessions
**Depends on**: Phase 1, Phase 2
**Requirements**: SEED-01, SEED-02, SEED-03, SEED-04
**Success Criteria** (what must be TRUE):
  1. Russian vocabulary is loaded from OpenRussian TSV with translations, morphology JSONB (gender, aspect, animacy), and frequency ranking (aspect_partner deferred to Phase 6 enrichment — pymorphy3 doesn't provide it)
  2. Arabic vocabulary is loaded from curated 225-word seed file with root extraction and morphology JSONB populated (Arabic Wordnet XML too unstable; curated data preferred)
  3. English vocabulary is loaded from subtitle-derived frequency list + WordNet definitions with lemma and morphology data (COCA requires license)
  4. Seed scripts are repeatable (download, transform, load) and produce data shaped for the application schema, not raw external formats
**Plans**: 4 plans

Plans:
- [ ] 03-01-PLAN.md -- Seed infrastructure (BaseSeeder, CLI, migration) + Russian seeder (OpenRussian TSV + pymorphy3)
- [x] 03-02-PLAN.md -- Arabic seeder with curated seed file + optional camel-tools enrichment
- [ ] 03-03-PLAN.md -- English seeder (WordNet + frequency list) + integration validation
- [x] 03-04-PLAN.md -- Generic CSV/TSV importer with validation (script checks, schema checks, error reporting)

### Phase 4: Core Review Experience
**Goal**: Users can complete a full daily review session -- see due cards, type answers, receive NLP-powered feedback, rate difficulty, and track progress
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: REV-01, REV-02, REV-03, REV-04, REV-05, REV-06, REV-07, REV-08, UX-01, UX-02, UX-03, UX-08, PROF-01, PROF-02
**Success Criteria** (what must be TRUE):
  1. User sees a per-language dashboard with due card count, current streak, and CEFR progress, scoped to their active language selection
  2. User can complete a review session: due cards presented in queue, fill-in-the-blank drill with typed answer, NLP validation feedback (including WRONG_FORM grammar explanations and CORRECT_SLOPPY warnings), quality rating buttons, and session summary with accuracy and time
  3. User can start a Learn session that adds a batch of new items from subscribed lists, and a Review session that drills only previously learned items via SRS queue
  4. Arabic content renders correctly in RTL layout with proper bidirectional text handling, and on-screen keyboards work for Cyrillic and Arabic input
  5. Interface is mobile-responsive with touch-friendly targets (44px+)
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD
- [ ] 04-04: TBD

### Phase 5: Progressive Content and ESL
**Goal**: Grammar content is structured as a progressive CEFR curriculum with prerequisite chains, and ESL learners see content in their native language
**Depends on**: Phase 4
**Requirements**: PROG-01, PROG-02, PROG-03, PROG-04, PROG-05, ESL-01, ESL-02, UX-04, PROF-03
**Success Criteria** (what must be TRUE):
  1. Grammar points are ordered by CEFR level (A1 through C2) per language, with prerequisite chains enforced (concept Y requires concept X)
  2. Each grammar point has multiple varied drill sentences testing the concept in different contexts
  3. ESL learners (Russian/Arabic speakers learning English) see vocabulary definitions and drill translations in their native language
  4. User can browse grammar points and vocabulary filtered by language and CEFR level
  5. User can manage which grammar/vocab level lists they are subscribed to within each language
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

### Phase 6: Content Enrichment and Language Polish
**Goal**: Cards feel complete with definitions, audio, example sentences, and language-specific display features
**Depends on**: Phase 4
**Requirements**: ENRICH-01, ENRICH-02, ENRICH-03, UX-05, UX-06, UX-07
**Success Criteria** (what must be TRUE):
  1. Vocabulary cards show Wiktionary definitions and inflection tables (cached in DB, not fetched on every view)
  2. User can hear native speaker pronunciation via Forvo audio, with Web Speech API fallback when Forvo audio is unavailable
  3. Vocabulary items display Tatoeba example sentences for context
  4. Arabic cards have a tashkeel toggle (show/hide diacritics) and display trilateral roots as spaced consonants
  5. Russian cards display stress marks on vocabulary (never required in typed answers)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5/6 (5 and 6 can run in parallel after Phase 4)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Schema, Auth, and SRS Engine | 2/3 | In Progress|  |
| 2. NLP Backends and Answer Validation | 3/5 | In Progress | - |
| 3. Seed Data Pipeline | 3/4 | In Progress|  |
| 4. Core Review Experience | 0/4 | Not started | - |
| 5. Progressive Content and ESL | 0/3 | Not started | - |
| 6. Content Enrichment and Language Polish | 0/3 | Not started | - |
