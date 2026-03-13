---
plan: 03
phase: 01-schema-auth-and-srs-engine
status: complete
tasks_completed: 3
tasks_total: 3
started: 2026-03-13
completed: 2026-03-13
---

# Plan 01-03: FastAPI App, Auth, Repositories & API Routers

## What was delivered

### Task 1: FastAPI app, JWT dependency, RLS-aware pool
- `backend/main.py` — App factory with lifespan pool management, CORS, router mounts, health endpoint
- `backend/dependencies.py` — JWT validation via PyJWT/HS256 with Supabase tokens
- `backend/repositories/pool.py` — asyncpg pool lifecycle + transaction-scoped RLS context manager
- `backend/routers/__init__.py` — Package init
- `backend/tests/test_auth.py` — 5 JWT unit tests (valid, expired, missing, invalid, wrong audience)

### Task 2: Repository layer and simple routers
- `backend/repositories/languages.py` — Public language queries (no RLS)
- `backend/repositories/cards.py` — Due cards query + SRS update (RLS-filtered)
- `backend/repositories/review.py` — Review log insert (append-only)
- `backend/routers/auth.py` — GET /me, GET/POST /profile (upsert)
- `backend/routers/languages.py` — GET / (public language list)

### Task 3: Review router and integration test stubs
- `backend/routers/review.py` — GET /due (sorted by next_review ASC), POST /submit (SM-2 wiring)
- `backend/tests/test_schema.py` — 6 schema validation stubs (skip without DATABASE_URL)
- `backend/tests/test_rls.py` — 3 RLS isolation stubs (skip without DATABASE_URL)

## Key decisions
- **App factory pattern**: `create_app()` defers settings access so modules import cleanly without env vars
- **CORS in try/except**: Gracefully skips CORS middleware when settings unavailable (test imports)
- **RLS context**: Uses `set_config(..., true)` for transaction-scoped user context (prevents leaking across pooled connections)

## Tests
- 31 passed, 9 skipped (DB integration stubs)
- Auth tests: 5/5 passing

## Commits
- `6a718be`: feat(01-03): FastAPI app with JWT auth, RLS pool, repos, and API routers

## Requirements completed
- AUTH-01: JWT validation with Supabase tokens
- AUTH-02: Protected endpoints require valid JWT
- AUTH-03: User profile management (upsert)
- SRS-04: Review log records all required fields
- SRS-05: Due cards sorted by next_review ASC
