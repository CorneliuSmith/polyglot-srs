---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: Completed 03-01-PLAN.md
last_updated: "2026-03-14T15:25:08Z"
last_activity: "2026-03-14 -- Phase 3, Plan 1 complete: Seed Infrastructure + Russian Seeder"
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 12
  completed_plans: 9
  percent: 36
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** Smart SRS review loop with language-aware answer checking -- users type answers and get nuanced feedback powered by per-language NLP backends
**Current focus:** Phase 3 in progress. Plan 03-01 complete, plans 03-02 and 03-03 ready.

## Current Position

Phase: 3 of 6 (Seed Data Pipeline) — IN PROGRESS
Plan: 1 of 3 in phase — 03-01 complete
Status: BaseSeeder + RussianSeeder implemented with 30 tests passing
Last activity: 2026-03-14 -- 03-01 Seed Infrastructure + Russian Seeder complete

Progress: [████░░░░░░] 36%

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
| 03-seed-data-pipeline | 1/3 | ~9 min | ~9 min |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: Railway memory limits for running 3 NLP models simultaneously need verification before Phase 4 deployment

## Session Continuity

Last session: 2026-03-14T15:25:08Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
