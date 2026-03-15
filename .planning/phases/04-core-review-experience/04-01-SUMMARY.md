---
phase: 04-core-review-experience
plan: "01"
subsystem: backend-api
tags: [review, dashboard, nlp, srs, endpoints, fastapi]
dependency_graph:
  requires: [01-03, 02-01]
  provides: [review-api-contract, dashboard-api-contract]
  affects: [04-02, 04-03]
tech_stack:
  added: []
  patterns: [union-all-query-merge, lru-cache-mock-pattern, asyncmock-testclient]
key_files:
  created:
    - backend/repositories/dashboard.py
    - backend/routers/dashboard.py
    - backend/tests/test_review_endpoints.py
    - backend/tests/test_dashboard_endpoint.py
  modified:
    - backend/repositories/cards.py
    - backend/routers/review.py
    - backend/main.py
decisions:
  - "Two separate queries merged in Python for get_due_cards (vocabulary + grammar UNION)"
  - "Vocabulary cards: sentence=definition, correct_answer=word (type-the-word, no {{answer}})"
  - "Grammar cards: sentence contains {{answer}} marker, correct_answer=grammar_points.title (Phase 4 placeholder)"
  - "ValueError from get_nlp() caught and returned as HTTP 422 not 500"
  - "TestClient mocks: patch backend.main.init_pool/close_pool/get_settings to bypass lifespan DB init"
  - "batch_size defaults to 5 when user has no profile row"
  - "Streak grace period: if no review today but review yesterday, streak counts from yesterday"
metrics:
  duration: "~8 min"
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_created: 4
  files_modified: 3
---

# Phase 4 Plan 01: Core Review API Endpoints Summary

**One-liner:** FastAPI review API extended with NLP validate-answer, vocabulary learn batch, and per-language dashboard — the complete backend contract for the frontend drill UI.

## What Was Built

Four API contracts the frontend drill loop depends on:

1. **`GET /api/review/due`** — extended to return full card content (vocabulary: sentence=definition, correct_answer=word; grammar: sentence with `{{answer}}` marker). Includes `language_code` for NLP dispatch, `morphology`, and `alternatives`.

2. **`POST /api/review/validate-answer`** — dispatches to language-specific NLP backend via `validate_answer_async`. Returns `{"answer_result": "correct|correct_sloppy|wrong_form|wrong", "feedback": str|null}`. Returns HTTP 422 (not 500) for unknown language codes.

3. **`POST /api/review/learn`** — reads `batch_size` from `user_profiles` (default 5), selects unlearned vocabulary from subscribed content lists ordered by `frequency_rank`, inserts into `user_cards` with default SRS values. Returns `{"added": N, "items": [card_id, ...]}`.

4. **`GET /api/dashboard/{language_id}`** — returns `due_count`, `streak_days` (consecutive days with at least one review, grace period for yesterday), and `cefr_progress` dict keyed by A1–C2 with `learned`/`total` fractions.

## Test Coverage

- 17 new tests added (8 review endpoint tests + 9 dashboard tests including pure unit tests for `_compute_streak`)
- All 282 tests pass, 9 skipped (RLS integration tests requiring DATABASE_URL)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Bug Fix] Deprecated FastAPI status constant**
- **Found during:** Task 2 test run
- **Issue:** `status.HTTP_422_UNPROCESSABLE_ENTITY` emits a deprecation warning in current FastAPI version
- **Fix:** Replaced with literal `422` in the validate-answer error handler
- **Files modified:** `backend/routers/review.py`
- **Commit:** bb07d64

**2. [Rule 1 - Bug] TestClient startup failing due to lru_cache settings**
- **Found during:** Task 2 — first test run
- **Issue:** `TestClient` enters lifespan context which calls `get_settings()`. With `lru_cache`, patching `backend.config.get_settings` doesn't intercept the call if called before patch context. Solution: patch the names as imported in `backend.main` (`backend.main.init_pool`, `backend.main.close_pool`, `backend.main.get_settings`) and add all required fields to `FakeSettings` including `database_url`.
- **Fix:** Updated both test fixtures to patch at the `backend.main` namespace and added full `FakeSettings` with all required attributes
- **Files modified:** `backend/tests/test_review_endpoints.py`, `backend/tests/test_dashboard_endpoint.py`
- **Commit:** bb07d64

## Self-Check: PASSED

| Item | Status |
|------|--------|
| backend/repositories/dashboard.py | FOUND |
| backend/routers/dashboard.py | FOUND |
| backend/tests/test_review_endpoints.py | FOUND |
| backend/tests/test_dashboard_endpoint.py | FOUND |
| Commit 87c4ef9 (Task 1) | FOUND |
| Commit bb07d64 (Task 2) | FOUND |
| 282 tests passing | VERIFIED |
