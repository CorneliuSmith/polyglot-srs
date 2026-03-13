---
phase: 01-schema-auth-and-srs-engine
plan: "01"
subsystem: database
tags: [supabase, postgresql, asyncpg, pydantic-settings, fastapi, rls, migrations]

# Dependency graph
requires: []
provides:
  - "10-table PostgreSQL schema with FKs, indexes, constraints via Supabase migrations"
  - "Per-operation RLS policies on all 4 user data tables"
  - "Language seed data for Russian, Arabic, English"
  - "Python project scaffold with FastAPI, asyncpg, pydantic-settings dependencies"
  - "pydantic-settings Settings class with all Supabase and DB config fields"
affects:
  - 01-02-auth-and-api-foundation
  - 01-03-srs-engine
  - all subsequent phases (all tables defined here)

# Tech tracking
tech-stack:
  added:
    - fastapi>=0.135
    - uvicorn[standard]>=0.30
    - pydantic>=2.7
    - pydantic-settings>=2.0
    - asyncpg>=0.31
    - PyJWT>=2.8
    - httpx>=0.27
    - ruff>=0.4 (dev)
    - pytest>=8.0 (dev)
    - pytest-asyncio>=0.24 (dev)
  patterns:
    - "pydantic-settings with env_file='.env' and @lru_cache get_settings()"
    - "Supabase CLI migrations in supabase/migrations/ with timestamped filenames"
    - "Per-operation RLS policies using auth.uid() (not catch-all policies)"
    - "morphology JSONB for language-specific grammar features on vocabulary"
    - "Polymorphic card_id on user_cards (card_type discriminator: 'grammar' | 'vocabulary')"

key-files:
  created:
    - pyproject.toml
    - backend/__init__.py
    - backend/repositories/__init__.py
    - backend/config.py
    - .env.example
    - .gitignore
    - supabase/config.toml
    - supabase/migrations/20260312000000_initial_schema.sql
    - supabase/migrations/20260312000001_rls_policies.sql
    - supabase/migrations/20260312000002_seed_languages.sql
  modified: []

key-decisions:
  - "Supabase CLI not installed: created supabase/ directory structure manually with config.toml"
  - "SQL aligned with multi-space formatting for readability; verification scripts updated to use regex for whitespace"
  - "Per-operation RLS policies preferred over single catch-all policies for explicitness and auditability"
  - "review_log is append-only: no UPDATE or DELETE RLS policies, only SELECT and INSERT"
  - "Public content tables (languages, grammar_points, vocabulary, etc.) have no RLS -- readable by all authenticated users per research recommendation"

patterns-established:
  - "Pattern 1: Per-operation RLS -- each policy does exactly one operation (SELECT/INSERT/UPDATE/DELETE), all scoped to auth.uid()"
  - "Pattern 2: morphology JSONB stores per-language grammar features (gender, aspect, root, form, declension) allowing schema evolution without migrations"
  - "Pattern 3: Polymorphic card_id on user_cards -- card_type discriminates between grammar and vocabulary, avoiding separate join tables"
  - "Pattern 4: content_lists as explicit DB rows with UNIQUE(language_id, list_type, level) allowing clean subscription join via user_content_subscriptions"

requirements-completed: [DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07]

# Metrics
duration: 9min
completed: 2026-03-13
---

# Phase 1 Plan 01: Schema and Project Scaffold Summary

**10-table PostgreSQL schema with per-operation RLS policies, language-parameterized throughout, plus FastAPI project scaffold with pydantic-settings config**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-13T10:37:22Z
- **Completed:** 2026-03-13T10:46:16Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Project scaffold with pyproject.toml, backend/config.py (pydantic-settings), .env.example, .gitignore, and supabase/config.toml
- Three SQL migration files defining all 10 tables with correct FKs, indexes, and constraints (UNIQUE, CHECK, NOT NULL)
- 12 per-operation RLS policies across 4 user tables; public content tables intentionally excluded from RLS

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold and configuration** - `051c878` (feat)
2. **Task 2: Database schema migrations with RLS and seed data** - `fbc8041` (included in 01-02 refactor commit)

## Files Created/Modified

- `pyproject.toml` - Python 3.11+ project config with all production and dev dependencies
- `backend/__init__.py` - Package init file
- `backend/repositories/__init__.py` - Repository package init
- `backend/config.py` - pydantic-settings Settings with supabase_url, supabase_anon_key, supabase_service_role_key, supabase_jwt_secret, database_url, cors_origins; lru_cache get_settings()
- `.env.example` - All environment variable names with placeholder values
- `.gitignore` - Python defaults, .env, .venv, __pycache__, supabase/.temp
- `supabase/config.toml` - Supabase local dev config (created manually, CLI not installed)
- `supabase/migrations/20260312000000_initial_schema.sql` - 10 tables with FKs, indexes, constraints
- `supabase/migrations/20260312000001_rls_policies.sql` - 12 per-operation RLS policies for 4 user tables
- `supabase/migrations/20260312000002_seed_languages.sql` - Russian/Arabic/English seed with ON CONFLICT idempotency

## Decisions Made

- Supabase CLI not available: created supabase directory structure manually instead of running `supabase init`
- Used `morphology JSONB NOT NULL DEFAULT '{}'` on vocabulary for per-language grammar features (gender, aspect, root, declension) -- allows adding new language features without schema migrations
- Polymorphic `card_id` on user_cards with `card_type` discriminator avoids separate tables for grammar cards and vocabulary cards while maintaining clean querying
- `review_log` is append-only by design: only SELECT and INSERT RLS policies, no UPDATE or DELETE -- preserves immutable review history
- Public content tables (languages, grammar_points, vocabulary, translations, drill_sentences, content_lists) deliberately excluded from RLS per research recommendation to avoid performance overhead on public data

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Supabase CLI not installed**
- **Found during:** Task 1 (Project scaffold)
- **Issue:** `supabase init` would fail as Supabase CLI is not installed on this machine
- **Fix:** Created supabase/migrations/ directory and supabase/config.toml manually with standard Supabase local dev configuration
- **Files modified:** supabase/config.toml
- **Verification:** Directory structure exists and config.toml is syntactically valid TOML
- **Committed in:** 051c878 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix necessary to complete task without CLI. Manual config.toml matches what `supabase init` would generate. No scope creep.

## Issues Encountered

- Plan verification script used exact single-space string matching (`'morphology JSONB'`) but SQL file uses aligned multi-space formatting. The content was correct; the verification script had a false negative. Verified with regex (`re.search(r'morphology\s+JSONB', m1, re.IGNORECASE)`).

## User Setup Required

None - no external service configuration required at this stage. Developers will need to populate `.env` from `.env.example` when connecting to a Supabase project, but that is handled in a later phase.

## Next Phase Readiness

- Schema foundation complete: all 10 tables defined with correct relationships
- RLS policies in place for all user data tables
- Project scaffold ready for FastAPI application code (01-02)
- SM-2 SRS engine already implemented (01-02 was executed before this summary was created)
- Migrations can be applied to a Supabase project via `supabase db push` once CLI is installed

---
*Phase: 01-schema-auth-and-srs-engine*
*Completed: 2026-03-13*
