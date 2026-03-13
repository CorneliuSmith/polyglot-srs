---
phase: 01-schema-auth-and-srs-engine
plan: "02"
subsystem: srs
tags: [sm2, spaced-repetition, pytest, python, pure-functions]

requires: []
provides:
  - "SM-2 algorithm as pure functions in backend/services/srs.py"
  - "AnswerResult enum with locked quality mapping (CORRECT=4, SLOPPY=3, WRONG_FORM=2, WRONG=1)"
  - "CardState and SRSUpdate dataclasses"
  - "Ease recovery: nudges toward 2.5 after 5+ consecutive correct answers"
  - "Interval fuzzing: +/-5% for intervals > 2 to prevent review clustering"
  - "26 passing unit tests covering all SM-2 behaviors"
affects:
  - "02-review-session-api (uses sm2_update in review endpoints)"
  - "04-nlp-backends (answer validation returns AnswerResult, fed into sm2_update)"
  - "Any phase using scheduling or review logic"

tech-stack:
  added: [pytest]
  patterns:
    - "Pure functions for SRS — no DB dependency, trivially testable"
    - "TDD: RED (failing tests) -> GREEN (implementation) -> REFACTOR"
    - "Ease recovery uses INCOMING streak to determine threshold, not post-increment"

key-files:
  created:
    - backend/services/__init__.py
    - backend/services/srs.py
    - backend/tests/__init__.py
    - backend/tests/conftest.py
    - backend/tests/test_srs.py
  modified: []

key-decisions:
  - "LOCKED: AnswerResult quality map is CORRECT=4, CORRECT_SLOPPY=3, WRONG_FORM=2, WRONG=1"
  - "Ease recovery threshold check uses incoming streak (not post-increment) — streak=4 does not trigger, streak=5 does"
  - "Interval fuzzing applies only to intervals > 2 days to avoid distorting short-interval learning"
  - "Use datetime.now(timezone.utc) not deprecated datetime.utcnow()"

patterns-established:
  - "Pure functions: sm2_update(CardState, int) -> SRSUpdate — no side effects, no DB calls"
  - "Dataclasses for state: CardState (input) and SRSUpdate (output) are separate types"
  - "Constants at module level with type annotations and docstrings"

requirements-completed: [SRS-01, SRS-02, SRS-03, SRS-04, SRS-05]

duration: 8min
completed: 2026-03-13
---

# Phase 1 Plan 02: SM-2 SRS Algorithm Summary

**Pure SM-2 spaced repetition engine with ease recovery, quality auto-mapping from AnswerResult enum, interval fuzzing, and 26 passing unit tests — no database dependency**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-13T10:37:20Z
- **Completed:** 2026-03-13T10:45:17Z
- **Tasks:** 1 (TDD feature with 3 commits: RED/GREEN/REFACTOR)
- **Files modified:** 5 created

## Accomplishments
- Implemented full SM-2 algorithm as pure functions in `backend/services/srs.py`
- `AnswerResult` enum with locked quality mapping (CORRECT=4, CORRECT_SLOPPY=3, WRONG_FORM=2, WRONG=1) established as project-wide constant
- Ease recovery: after 5 consecutive correct answers (incoming streak), ease nudges +0.05 toward target 2.5
- Interval fuzzing: ±5% randomization for intervals > 2 days to prevent review clustering
- 26 unit tests covering all specified behaviors pass cleanly

## Task Commits

TDD task with three commits:

1. **RED phase: failing SM-2 tests** - `c08122e` (test)
2. **GREEN phase: SM-2 implementation** - `b520826` (feat)
3. **REFACTOR: remove unused import** - `fbc8041` (refactor)

_Note: TDD tasks have multiple commits (test → feat → refactor)_

## Files Created/Modified
- `backend/services/__init__.py` - Package init (empty)
- `backend/services/srs.py` - SM-2 algorithm: AnswerResult, QUALITY_MAP, CardState, SRSUpdate, sm2_update, map_answer_to_quality (190 lines)
- `backend/tests/__init__.py` - Package init (empty)
- `backend/tests/conftest.py` - `fixed_seed` pytest fixture for deterministic fuzz tests
- `backend/tests/test_srs.py` - 26 unit tests across 8 test classes (282 lines)

## Decisions Made
- **Locked quality map:** CORRECT=4, CORRECT_SLOPPY=3, WRONG_FORM=2, WRONG=1. This is a named locked decision referenced in the code and tests.
- **Ease recovery uses incoming streak:** The threshold check (`streak >= 5`) evaluates the streak BEFORE the current review increments it. This means a card needs 5 consecutive correct answers already recorded before recovery triggers on the next review.
- **Interval fuzzing threshold = 2:** Intervals of 1-2 days are not fuzzed (first and second reviews are deterministic). Fuzzing begins at interval=3+ to avoid distorting early learning.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ease recovery threshold semantics**
- **Found during:** GREEN phase (test run revealed `test_no_recovery_below_threshold` failing)
- **Issue:** Initial implementation checked `new_streak >= EASE_RECOVERY_THRESHOLD` (post-increment), but the test spec requires that incoming streak=4 does NOT trigger recovery while incoming streak=5 DOES
- **Fix:** Changed check from `new_streak` to `streak` (incoming value) in the ease recovery block
- **Files modified:** `backend/services/srs.py`
- **Verification:** All 26 tests pass including `test_no_recovery_below_threshold` and `test_recovery_at_threshold`
- **Committed in:** b520826 (GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug fix during GREEN phase)
**Impact on plan:** Fix clarified ambiguous spec semantics. No scope creep.

## Issues Encountered
- `pytest` not installed in system Python — installed with `pip3 install pytest --break-system-packages` (Python 3.14.2 on macOS with PEP 668 restrictions). One-time setup; not a recurring issue.

## User Setup Required
None - no external service configuration required. Pure Python, no dependencies beyond pytest.

## Next Phase Readiness
- `sm2_update` is ready to be called from review session endpoints (Plan 03)
- `AnswerResult` enum is ready to receive output from NLP answer validators (Phase 2)
- All SRS-01 through SRS-05 requirements met
- No blockers for next plan in this phase

---
*Phase: 01-schema-auth-and-srs-engine*
*Completed: 2026-03-13*
