# Requirements: PolyglotSRS

**Defined:** 2026-03-12
**Core Value:** Smart SRS review loop with language-aware answer checking — users type answers and get nuanced feedback powered by per-language NLP backends

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Schema & Database

- [x] **DB-01**: PostgreSQL schema with all tables language-parameterized via language_id FK
- [x] **DB-02**: Row-level security policies on all user tables (user_cards, review_log, user_subscriptions, user_notes_import) ensuring users only access own data
- [x] **DB-03**: Language seed data (Russian, Arabic, English) inserted on schema creation
- [x] **DB-04**: Morphology JSONB on vocabulary stores per-language grammar features (gender, aspect, root, form, etc.)
- [x] **DB-05**: Translations table storing vocabulary definitions per UI language (not just English definitions)
- [x] **DB-06**: Drill sentences support multiple varied sentences per grammar point to prevent rote memorization
- [x] **DB-07**: User content subscriptions table tracks which grammar/vocab level lists a user is subscribed to within a language

### SRS Engine

- [x] **SRS-01**: SM-2 algorithm correctly schedules cards based on quality rating (0-5)
- [x] **SRS-02**: Card state tracks ease_factor (floor 1.3), interval, repetitions, streak, lapses
- [x] **SRS-03**: Failed reviews (quality < 3) reset repetitions and interval to 1
- [x] **SRS-04**: Review log records every review with quality, time taken, and timestamp
- [x] **SRS-05**: Cards sorted by next_review ascending for review session queue

### NLP & Answer Validation

- [x] **NLP-01**: BaseNLP abstract interface with normalize, lemmatize, get_morphological_family, get_aspect_partner, check_answer
- [x] **NLP-02**: 4-tier answer validation: exact → normalized → lemma → morphological family, returning AnswerResult enum (CORRECT / CORRECT_SLOPPY / WRONG_FORM / WRONG)
- [x] **NLP-03**: Russian NLP backend (pymorphy3) with morphological analysis, lemmatization, case/gender/aspect detection
- [x] **NLP-04**: Russian answer validation accepts Latin→Cyrillic transliteration as CORRECT_SLOPPY
- [x] **NLP-05**: Russian aspect partner detection returns WRONG_FORM with explanation when wrong aspect used
- [x] **NLP-06**: Arabic NLP backend (camel-tools) with tashkeel stripping, alef normalization (أإآ→ا), tatweel removal, root extraction
- [x] **NLP-07**: Arabic answer validation never fails purely on diacritic presence/absence
- [x] **NLP-08**: Arabic verb form detection returns WRONG_FORM with root + form table when wrong form used
- [x] **NLP-09**: English NLP backend (spaCy) with lemmatization, article stripping, irregular verb handling
- [x] **NLP-10**: Answer alternatives array checked before returning WRONG (regional spellings, archaic forms, aspect partners)

### Seed Data

- [x] **SEED-01**: Russian seed data imported from OpenRussian TSV dumps (words + translations), transformed for our schema
- [x] **SEED-02**: Arabic seed data from curated 225-word JSON (Arabic Wordnet XML too unstable; curated data has verified roots, forms, tashkeel)
- [x] **SEED-03**: English seed data from subtitle-derived frequency list + WordNet definitions (COCA requires license; open frequency list used instead)
- [x] **SEED-04**: Seed scripts download, transform, and load data into Supabase — data lives in our DB shaped for our needs

### Progressive Content

- [ ] **PROG-01**: Grammar points structured in progressive curriculum per language, ordered by CEFR level (A1→C2)
- [ ] **PROG-02**: Each grammar point has multiple varied drill sentences testing the concept in different contexts
- [ ] **PROG-03**: Platform architecture supports adding new languages with their own grammar curricula and progression
- [ ] **PROG-04**: Grammar points include prerequisite chains (concept Y requires concept X)
- [ ] **PROG-05**: Users subscribe to grammar and vocabulary lists per CEFR level within their active language

### ESL Support

- [ ] **ESL-01**: ESL learners see vocabulary definitions and drill translations in their native language (Russian, Arabic, Spanish, or Portuguese)
- [ ] **ESL-02**: Vocabulary supports multiple translations per UI language via translations table (UI languages: en, ru, ar, es, pt)

### Review Experience

- [ ] **REV-01**: Review session presents due cards in queue, sorted by next_review
- [ ] **REV-02**: Fill-in-the-blank drill mode with {{answer}} markers in sentences
- [ ] **REV-03**: Quality rating buttons (Again/Hard/Good/Easy) map to SM-2 quality scores
- [ ] **REV-04**: WRONG_FORM feedback shows grammar explanation (aspect distinction, case needed, verb form table)
- [ ] **REV-05**: CORRECT_SLOPPY shows warning with nudge toward correct form
- [ ] **REV-06**: Session summary shows accuracy %, time spent, cards reviewed
- [ ] **REV-07**: Learn mode adds a batch of new items from user's subscribed grammar/vocab level lists within the active language
- [ ] **REV-08**: Review mode drills only previously learned items from the active language via SRS queue

### Content Enrichment

- [ ] **ENRICH-01**: Wiktionary integration fetches definitions and inflection tables, cached in DB
- [ ] **ENRICH-02**: Forvo integration fetches native speaker audio with Web Speech API fallback
- [ ] **ENRICH-03**: Tatoeba integration fetches example sentences per vocabulary item

### Frontend & UX

- [ ] **UX-01**: Per-language dashboard showing due card count, current streak, CEFR progress bars
- [ ] **UX-02**: RTL layout for Arabic (dir="rtl", Noto Naskh Arabic font, mirrored layouts, large font size)
- [ ] **UX-03**: On-screen keyboards for Cyrillic and Arabic script input
- [ ] **UX-04**: Browse grammar points and vocabulary by language and CEFR level
- [ ] **UX-05**: Tashkeel toggle on Arabic vocabulary cards (show/hide diacritics)
- [ ] **UX-06**: Arabic root display (trilateral root as spaced consonants, e.g., ك-ت-ب)
- [ ] **UX-07**: Russian stress marks displayed on vocabulary cards (never required in answers)
- [ ] **UX-08**: Mobile-responsive design with 44px+ touch targets

### User Profile

- [ ] **PROF-01**: User profile stores batch size setting (default 5 new items per Learn session per list)
- [ ] **PROF-02**: User selects active language in UI — all Learn/Review/Dashboard scoped to that language
- [ ] **PROF-03**: User manages which grammar/vocab level lists they are subscribed to within each language

### Authentication

- [x] **AUTH-01**: User can create account with email/password via Supabase Auth
- [x] **AUTH-02**: User can log in with Google OAuth
- [x] **AUTH-03**: User session persists across browser refresh

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Monetization

- **PAY-01**: Stripe per-language subscriptions ($8/mo per language)
- **PAY-02**: All-access tier ($18/mo for all 3 languages)
- **PAY-03**: Lifetime tier ($149 one-time)
- **PAY-04**: 7-day free trial on first language pack
- **PAY-05**: Free tier (1 language, 20 cards/day cap, no import)

### Note Import

- **IMP-01**: Markdown file upload parsed into grammar points and vocabulary cards
- **IMP-02**: PDF file upload parsed into grammar points and vocabulary cards
- **IMP-03**: Claude API structured extraction for card generation from notes

### Polish

- **POL-01**: Review heatmap (last 365 days)
- **POL-02**: UI language localization (Arabic/Russian UI)
- **POL-03**: PWA manifest + offline review mode
- **POL-04**: Word-by-word sentence breakdown toggle
- **POL-05**: Conjugation table pages from Wiktionary inflection data

## Out of Scope

| Feature | Reason |
|---------|--------|
| Native mobile apps | Web-first, PWA in v2 covers 90% of mobile use |
| Social features (friends, sharing, chat) | Enormous surface, low impact on core SRS value |
| Gamification (XP, leaderboards, gems) | Signals "not serious" to adult learners; streaks suffice |
| AI-generated cards from scratch | Hallucination risk in language content destroys trust |
| 20+ language support | Depth over breadth; 3 languages done deeply beats 30 shallow |
| Anki deck import | Complex format, creates expectations of Anki-level customization |
| Custom card templates | Opinionated layouts > flexible but fragile templates |
| Grammar chatbot / AI tutor | Expensive per-query, hard to make consistently accurate |
| Speaking / speech-to-text modes | STT unreliable for Russian/Arabic; defer indefinitely |
| General-purpose SRS (non-language) | Language NLP is the moat; stay focused |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | Phase 1 | Complete |
| DB-02 | Phase 1 | Complete |
| DB-03 | Phase 1 | Complete |
| DB-04 | Phase 1 | Complete |
| DB-05 | Phase 1 | Complete |
| DB-06 | Phase 1 | Complete |
| DB-07 | Phase 1 | Complete |
| SRS-01 | Phase 1 | Complete |
| SRS-02 | Phase 1 | Complete |
| SRS-03 | Phase 1 | Complete |
| SRS-04 | Phase 1 | Complete |
| SRS-05 | Phase 1 | Complete |
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| NLP-01 | Phase 2 | Complete |
| NLP-02 | Phase 2 | Complete |
| NLP-03 | Phase 2 | Complete |
| NLP-04 | Phase 2 | Complete |
| NLP-05 | Phase 2 | Complete |
| NLP-06 | Phase 2 | Complete |
| NLP-07 | Phase 2 | Complete |
| NLP-08 | Phase 2 | Complete |
| NLP-09 | Phase 2 | Complete |
| NLP-10 | Phase 2 | Complete |
| SEED-01 | Phase 3 | Complete |
| SEED-02 | Phase 3 | Pending |
| SEED-03 | Phase 3 | Pending |
| SEED-04 | Phase 3 | Complete |
| REV-01 | Phase 4 | Pending |
| REV-02 | Phase 4 | Pending |
| REV-03 | Phase 4 | Pending |
| REV-04 | Phase 4 | Pending |
| REV-05 | Phase 4 | Pending |
| REV-06 | Phase 4 | Pending |
| REV-07 | Phase 4 | Pending |
| REV-08 | Phase 4 | Pending |
| UX-01 | Phase 4 | Pending |
| UX-02 | Phase 4 | Pending |
| UX-03 | Phase 4 | Pending |
| UX-08 | Phase 4 | Pending |
| PROF-01 | Phase 4 | Pending |
| PROF-02 | Phase 4 | Pending |
| PROG-01 | Phase 5 | Pending |
| PROG-02 | Phase 5 | Pending |
| PROG-03 | Phase 5 | Pending |
| PROG-04 | Phase 5 | Pending |
| PROG-05 | Phase 5 | Pending |
| ESL-01 | Phase 5 | Pending |
| ESL-02 | Phase 5 | Pending |
| UX-04 | Phase 5 | Pending |
| PROF-03 | Phase 5 | Pending |
| ENRICH-01 | Phase 6 | Pending |
| ENRICH-02 | Phase 6 | Pending |
| ENRICH-03 | Phase 6 | Pending |
| UX-05 | Phase 6 | Pending |
| UX-06 | Phase 6 | Pending |
| UX-07 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 58 total
- Mapped to phases: 58
- Unmapped: 0

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 after roadmap creation*
