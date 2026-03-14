---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: Completed 02-03-PLAN.md (ArabicNLP backend with camel-tools)
last_updated: "2026-03-14T00:00:00Z"
last_activity: "2026-03-14 -- Completed Plan 02-03: ArabicNLP backend with camel-tools morphological analysis"
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 8
  completed_plans: 6
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** Smart SRS review loop with language-aware answer checking -- users type answers and get nuanced feedback powered by per-language NLP backends
**Current focus:** Phase 1 COMPLETE. Ready for Phase 2: NLP Backends & Validation

## Current Position

Phase: 2 of 6 (NLP Backends and Answer Validation) — In Progress
Plan: 3 of 5 in current phase — Plans 02-00, 02-01, 02-03 complete
Status: Phase 2 in progress (02-02 Russian, 02-04 English remaining)
Last activity: 2026-03-14 -- Completed Plan 02-03: ArabicNLP backend with camel-tools

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: ~8 min/plan
- Total execution time: ~24 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-schema-auth-and-srs-engine | 3/3 | ~24 min | ~8 min |

**Recent Trend:**
- Last 5 plans: 01-01 (scaffold), 01-02 (SRS engine), 01-03 (API layer)
- Trend: stable
| Phase 02-nlp-backends-and-answer-validation P00 | 4 | 2 tasks | 4 files |
| Phase 02-nlp-backends-and-answer-validation P01 | 3 | 2 tasks | 5 files |
| Phase 02-nlp-backends-and-answer-validation P03 | 8 | 1 task | 1 file |

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
- [Phase 02-00]: get_aspect_partner(verb, card_context=None) standardized two-parameter signature — Layer 5 in check_answer calls self.get_aspect_partner(correct, card_context)
- [Phase 02-00]: Arabic tests use pytest.importorskip('camel_tools') to skip gracefully when camel-tools data not installed; English uses importorskip('spacy') similarly
- [Phase 02-00]: Taa marbuta vs ha tested as CORRECT_SLOPPY — not normalized away — avoids conflating semantically distinct words
- [Phase 02-01]: AnswerResult relocated to nlp/base.py; srs.py re-exports it for backward compatibility
- [Phase 02-01]: NFC normalization applied as first step in check_answer before language-specific normalize() call (research pitfall #1)
- [Phase 02-01]: init_nlp_backends() uses importlib + try/except per backend — missing libraries emit warnings, not crashes
- [Phase 02-03]: normalize() does not map taa marbuta to ha — kept distinct for pedagogical accuracy; soft-match in check_answer returns CORRECT_SLOPPY instead
- [Phase 02-03]: get_aspect_partner() returns None for Arabic — verb aspect handled through verb form detection (WRONG_FORM), not Russian-style pairs
- [Phase 02-03]: Root resolution priority: card_context.morphology.root > camel-tools Analyzer output (curator knowledge is most reliable)
- [Phase 02-03]: Fallback stubs for dediac_ar/normalize_alef_ar allow ArabicNLP to be imported without camel_data installed

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: camel-tools version, exact MSA model name, and Python 3.11+ compatibility need live verification before Phase 2
- [Research]: pymorphy3 maintenance status (community fork) needs checking before Phase 2
- [Research]: Railway memory limits for running 3 NLP models simultaneously need verification before Phase 4 deployment

## Session Continuity

Last session: 2026-03-14T00:00:00Z
Stopped at: Completed 02-03-PLAN.md (ArabicNLP backend with camel-tools)
Resume file: None
