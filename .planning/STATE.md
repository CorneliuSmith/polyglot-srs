---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Backend review API complete — validate-answer, learn, dashboard endpoints with 282 tests passing
stopped_at: Completed 04-01-PLAN.md
last_updated: "2026-03-15T00:00:00.000Z"
last_activity: 2026-03-15 -- 04-01 review API endpoints with NLP dispatch and dashboard stats
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 17
  completed_plans: 14
  percent: 47
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** Smart SRS review loop with language-aware answer checking -- users type answers and get nuanced feedback powered by per-language NLP backends
**Current focus:** Phase 4 in progress. Plan 04-01 complete (backend API). 04-02 (frontend scaffold) also complete. 04-03 remaining.

## Current Position

Phase: 4 of 6 (Core Review Experience) — IN PROGRESS
Plan: 2 of 5 in phase — 04-01 and 04-02 complete, 04-03 through 04-05 remaining
Status: Backend review API complete — validate-answer, learn, dashboard with 282 tests
Last activity: 2026-03-15 -- 04-01 review API endpoints with NLP dispatch and dashboard stats

Progress: [██████░░░░] 47%

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: ~5 min/plan
- Total execution time: ~49 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-schema-auth-and-srs-engine | 3/3 | ~24 min | ~8 min |
| 02-nlp-backends-and-answer-validation | 5/5 | ~16 min | ~3 min |
| 03-seed-data-pipeline | 3/4 | ~21 min | ~7 min |
| 04-core-review-experience P04-02 | 12 | 2 tasks | 20 files |
| 04-core-review-experience P04-01 | ~8 min | 2 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 6 phases derived from requirement clusters; Phases 5 and 6 can parallelize after Phase 4
- [Roadmap]: Stripe subscriptions and note import deferred to v2 per REQUIREMENTS.md
- [01-02]: LOCKED quality map: AnswerResult.CORRECT=4, CORRECT_SLOPPY=3, WRONG_FORM=2, WRONG=1
- [01-02]: Ease recovery threshold uses incoming streak (not post-increment) — streak=4 no trigger, streak=5 triggers
- [01-02]: Interval fuzzing applies only to intervals > 2 days (short intervals are deterministic)
- [01-03]: App factory pattern defers settings access for clean test imports
- [01-03]: RLS context manager uses set_config(..., true) for transaction-scoped user context
- [Phase 01]: Per-operation RLS policies (SELECT/INSERT/UPDATE/DELETE separately) on user tables
- [Phase 01]: morphology JSONB on vocabulary for per-language grammar features
- [Phase 01]: Polymorphic card_id + card_type discriminator on user_cards
- [Phase 02-00]: get_aspect_partner(verb, card_context=None) standardized two-parameter signature
- [Phase 02-00]: Arabic tests use pytest.importorskip('camel_tools') for graceful skip
- [Phase 02-00]: Taa marbuta vs ha tested as CORRECT_SLOPPY — not normalized away
- [Phase 02-01]: AnswerResult relocated to nlp/base.py; srs.py re-exports
- [Phase 02-01]: NFC normalization applied as first step in check_answer
- [Phase 02-01]: init_nlp_backends() uses importlib + try/except per backend
- [Phase 02-02]: Russian normalize is lowercase+strip only — no diacritics in Cyrillic
- [Phase 02-02]: Aspect partner from card_context only — pymorphy3 doesn't provide aspect data
- [Phase 02-02]: Transliteration pre-check fires only when input is ASCII
- [Phase 02-03]: normalize() does not map taa marbuta to ha — kept distinct for pedagogy
- [Phase 02-03]: Arabic get_aspect_partner() returns None — verb form detection handles aspect
- [Phase 02-03]: Root resolution: card_context > camel-tools Analyzer
- [Phase 02-04]: English normalize strips leading articles (the/a/an) case-insensitively
- [Phase 02-04]: English get_aspect_partner() always returns None
- [03-01]: WORDS_FILENAME/TRANSLATIONS_FILENAME as module-level constants so tests can patch seeder file paths
- [03-01]: morphology passed as JSON string to asyncpg with ::jsonb cast — asyncpg does not auto-serialize dicts for jsonb
- [03-01]: reading=None when accented == bare — avoids redundant data for words without accent markers
- [03-01]: CLI runner gracefully skips ar/en seeders with ImportError for incremental rollout
- [03-04]: Fail-fast CSV validation — all row errors collected before any DB write; ValueError lists every failure
- [03-04]: Unknown language codes skip script validation rather than failing — forward-compatible for new languages
- [03-04]: DictReader None-safety: (row.get(key) or '') pattern — DictReader yields None for empty cells when column exists in header
- [03-02]: Curated 225-word seed over Arabic Wordnet — better quality, stable, 31.7 KB
- [03-02]: setdefault for camel-tools enrichment — seed file morphology takes priority over analyzer
- [03-02]: if v is not None strips morphology Nones while preserving falsy strings
- [Phase 04-core-review-experience]: QueryClientProvider wraps AppInner inside App.tsx — App owns its providers for encapsulation
- [Phase 04-core-review-experience]: [04-02]: axios 401 retry uses double cast (as unknown as Record<string,unknown>) to set _retry flag — avoids TypeScript index signature mismatch on InternalAxiosRequestConfig
- [Phase 04-core-review-experience]: [04-02]: Zustand persist key is 'polyglot-prefs' for active language selection
- [04-01]: Two separate queries merged in Python for get_due_cards (vocabulary + grammar) — cleaner than UNION ALL with type casting
- [04-01]: Vocabulary cards: sentence=definition, correct_answer=word (type-the-word, no {{answer}} marker)
- [04-01]: ValueError from get_nlp() caught and returned as HTTP 422 not 500 in validate-answer endpoint
- [04-01]: TestClient mocks: patch backend.main.init_pool/close_pool/get_settings to bypass lifespan DB init
- [04-01]: Streak grace period: if no review today but review yesterday, streak counts from yesterday

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: Railway memory limits for running 3 NLP models simultaneously need verification before Phase 4 deployment

## Session Continuity

Last session: 2026-03-15T00:00:00.000Z
Stopped at: Completed 04-01-PLAN.md
Resume file: None
