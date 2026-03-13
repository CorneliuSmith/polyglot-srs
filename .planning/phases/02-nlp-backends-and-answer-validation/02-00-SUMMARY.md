---
phase: 02-nlp-backends-and-answer-validation
plan: "00"
subsystem: testing
tags: [pytest, tdd, nlp, pymorphy3, camel-tools, spacy, lemminflect, cyrtranslit, russian, arabic, english]

# Dependency graph
requires:
  - phase: 01-schema-auth-and-srs-engine
    provides: AnswerResult enum in srs.py (to be relocated to nlp.base in 02-01)

provides:
  - Failing test contracts for BaseNLP abstract interface and registry (RED)
  - Failing test contracts for RussianNLP backend: normalize, lemmatize, morphological family, transliteration, aspect partners (RED)
  - Failing test contracts for ArabicNLP backend: tashkeel stripping, alef normalization, diacritic invariance, verb form detection (RED)
  - Failing test contracts for EnglishNLP backend: article stripping, irregular lemmatization, morphological family via lemminflect (RED)

affects:
  - 02-01-base-nlp (must turn test_nlp_base.py GREEN)
  - 02-02-english-nlp (must turn test_nlp_english.py GREEN)
  - 02-03-russian-nlp (must turn test_nlp_russian.py GREEN)
  - 02-04-arabic-nlp (must turn test_nlp_arabic.py GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED phase: test files define behavioral contracts before any implementation"
    - "pytest.importorskip() used for tests requiring optional NLP libraries (camel_tools, spacy)"
    - "Standardized get_aspect_partner(verb, card_context=None) signature across all backends"

key-files:
  created:
    - backend/tests/test_nlp_base.py
    - backend/tests/test_nlp_russian.py
    - backend/tests/test_nlp_arabic.py
    - backend/tests/test_nlp_english.py
  modified: []

key-decisions:
  - "get_aspect_partner(verb, card_context=None) is the standardized two-parameter signature across all NLP backends — Layer 5 in check_answer calls self.get_aspect_partner(correct, card_context)"
  - "Arabic tests use pytest.importorskip('camel_tools') to skip gracefully when camel-tools data is not installed — allows CI to run without 300MB+ Arabic data"
  - "English tests use pytest.importorskip('spacy') pattern for same reason"
  - "Taa marbuta (ة) vs ha (ه) tested as CORRECT_SLOPPY — not CORRECT or WRONG — per research pitfall 6"
  - "Aspect partner for Russian reads from card_context['morphology']['aspect_partner'] — pymorphy3 does not have aspect pair data"

patterns-established:
  - "RED phase separation: 02-00 writes all tests; 02-01 through 02-04 turn them GREEN"
  - "StubNLP in test_nlp_base.py implements all abstract methods locally — no real NLP library needed for base tests"
  - "card_context dict pattern: backends receive card_context for accessing morphology JSONB field data"

requirements-completed: [NLP-01, NLP-02, NLP-03, NLP-04, NLP-05, NLP-06, NLP-07, NLP-08, NLP-09, NLP-10]

# Metrics
duration: 4min
completed: 2026-03-13
---

# Phase 2 Plan 00: NLP TDD Red Phase Summary

**Four failing test files establishing behavioral contracts for BaseNLP pipeline, Russian/Arabic/English backends, and NLP registry using pytest with importorskip for optional library dependencies**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-13T20:47:38Z
- **Completed:** 2026-03-13T20:51:01Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `test_nlp_base.py` with 28 test functions covering BaseNLP ABC, 4-tier check_answer pipeline (all 6 layers), NLP registry, and AnswerResult relocation — all failing RED
- Created `test_nlp_russian.py` with 24 test functions covering normalization, lemmatization, morphological family, Latin transliteration (NLP-04), and aspect partner detection (NLP-05) — all failing RED
- Created `test_nlp_arabic.py` with 20 test functions covering tashkeel stripping, alef normalization, tatweel, diacritic invariance (NLP-07), taa marbuta, and verb form detection (NLP-08) — all failing RED
- Created `test_nlp_english.py` with 20 test functions covering article stripping, irregular verb/noun lemmatization, morphological family via lemminflect, and full pipeline (NLP-09) — all failing RED
- Standardized `get_aspect_partner(verb, card_context=None)` signature enforced across all test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing test files for BaseNLP and NLP registry (RED)** - `f8cf40b` (test)
2. **Task 2: Write failing test files for Russian, Arabic, and English backends (RED)** - `e2c8e15` (test)

## Files Created/Modified

- `backend/tests/test_nlp_base.py` - BaseNLP abstract interface, 4-tier pipeline, registry, AnswerResult tests (RED)
- `backend/tests/test_nlp_russian.py` - RussianNLP normalization, lemmatization, transliteration, aspect partner tests (RED)
- `backend/tests/test_nlp_arabic.py` - ArabicNLP tashkeel, alef, diacritic invariance, verb form detection tests (RED)
- `backend/tests/test_nlp_english.py` - EnglishNLP article stripping, irregular lemmatization, morphological family tests (RED)

## Decisions Made

- Standardized `get_aspect_partner(verb, card_context=None)` two-parameter signature across all backends — Layer 5 in `check_answer` calls `self.get_aspect_partner(correct, card_context)` so all backends must accept both parameters even if they ignore `card_context`
- `pytest.importorskip("camel_tools")` and `pytest.importorskip("spacy")` used for Arabic and English tests respectively — allows test suite to run in environments without the heavy NLP libraries installed
- Taa marbuta vs ha difference tested as `CORRECT_SLOPPY` not `CORRECT` — per research pitfall 6 (blanket normalization conflates semantically different words)
- Russian aspect partner reads from `card_context["morphology"]["aspect_partner"]` — pymorphy3 does not provide aspect pair data (research pitfall 2)
- `AnswerResult` relocation tests included in `test_nlp_base.py` — verifies that importing from `nlp.base` works and values match the LOCKED QUALITY_MAP from plan 01-02

## Deviations from Plan

None — plan executed exactly as written. All four test files created, all exit non-zero (RED).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four test files are in place and define the full behavioral contracts
- Plans 02-01 through 02-04 can now be executed to turn tests GREEN
- 02-01 (BaseNLP + registry) should run first as it provides the imports the other three depend on
- NLP library dependencies must be installed before GREEN phases: `pip install pymorphy3 camel-tools spacy lemminflect cyrtranslit && python -m spacy download en_core_web_sm && camel_data -i light`

---
*Phase: 02-nlp-backends-and-answer-validation*
*Completed: 2026-03-13*
