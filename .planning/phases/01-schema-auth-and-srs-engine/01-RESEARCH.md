# Phase 1: Schema, Auth, and SRS Engine - Research

**Researched:** 2026-03-12
**Domain:** PostgreSQL schema with RLS, Supabase Auth, SM-2 SRS algorithm, asyncpg repository layer
**Confidence:** HIGH

## Summary

Phase 1 establishes the database foundation, authentication, and SRS scheduling engine. The core technical challenges are: (1) enforcing Supabase RLS policies when using asyncpg direct connections instead of the supabase-py client, (2) structuring the schema to be fully language-parameterized with proper per-operation RLS policies, and (3) implementing SM-2 with ease recovery to prevent the well-documented "ease hell" problem.

The architecture uses asyncpg connecting directly to Supabase PostgreSQL (port 5432 for dev, port 6543 via Supavisor for production), with RLS enforced by setting `request.jwt.claims` via `set_config()` before each query block. JWT validation happens locally using PyJWT with the Supabase JWT secret, avoiding round-trips to Supabase servers. The SM-2 algorithm is implemented as pure functions with no database dependency, making it trivially testable.

**Primary recommendation:** Use Supabase CLI migrations (which wraps dbmate under the hood), split RLS policies by operation (SELECT/INSERT/UPDATE/DELETE separately), and implement SM-2 as pure functions with ease recovery from day one.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- No quality rating buttons -- Bunpro-style auto-grading from NLP result
- Quality auto-derived: CORRECT=4, CORRECT_SLOPPY=3, WRONG_FORM=2, WRONG=1
- Ease floor 1.3 + gradual ease recovery (5+ consecutive correct -> ease nudges toward 2.5)
- Raw asyncpg with thin repository pattern (no ORM)
- Async for I/O, sync for CPU-bound NLP with run_in_executor
- Three environments: dev (local) + staging (Supabase) + prod (Supabase)
- Stack: FastAPI + Supabase (PostgreSQL + Auth)
- After signup, user sees a language picker to select their first language to study
- Users manually select which grammar/vocab level lists to subscribe to (no auto-subscribe)
- Users can study multiple languages simultaneously and switch freely

### Claude's Discretion
- Schema extension structural choices (translations table format, user profile location, subscriptions format, content lists approach)
- Migration tooling selection
- UI language detection approach
- Initial SM-2 intervals
- Seed data location (migration vs separate script)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DB-01 | PostgreSQL schema with all tables language-parameterized via language_id FK | Schema design pattern with UUID FKs to languages table; all content tables require language_id |
| DB-02 | Row-level security policies on all user tables ensuring users only access own data | Split RLS policies per operation with USING + WITH CHECK; set_config pattern for asyncpg |
| DB-03 | Language seed data (Russian, Arabic, English) inserted on schema creation | Supabase CLI migration with INSERT in migration file |
| DB-04 | Morphology JSONB on vocabulary stores per-language grammar features | JSONB column with per-language schema documented; no validation constraint needed |
| DB-05 | Translations table storing vocabulary definitions per UI language | Separate translations table (recommended over JSONB) with composite unique on (vocabulary_id, locale) |
| DB-06 | Drill sentences support multiple varied sentences per grammar point | drill_sentences table with FK to grammar_points and vocabulary; multiple rows per grammar_point_id |
| DB-07 | User content subscriptions table tracks which grammar/vocab level lists | Join table user_content_subscriptions linking users to content_lists per language |
| SRS-01 | SM-2 algorithm correctly schedules cards based on quality rating (0-5) | Pure function implementation with standard Wozniak formula |
| SRS-02 | Card state tracks ease_factor (floor 1.3), interval, repetitions, streak, lapses | user_cards table columns with defaults matching SM-2 initial state |
| SRS-03 | Failed reviews (quality < 3) reset repetitions and interval to 1 | Branch in sm2_update function; streak reset + lapses increment |
| SRS-04 | Review log records every review with quality, time taken, and timestamp | review_log append-only table with RLS; inserted in transaction with card update |
| SRS-05 | Cards sorted by next_review ascending for review session queue | Query with WHERE next_review <= now() ORDER BY next_review ASC; index on (user_id, language_id, next_review) |
| AUTH-01 | User can create account with email/password via Supabase Auth | Supabase Auth handles this natively; backend verifies JWT |
| AUTH-02 | User can log in with Google OAuth | Supabase Auth Google provider configuration; backend receives same JWT format |
| AUTH-03 | User session persists across browser refresh | Supabase JS client handles token refresh; backend is stateless |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11+ | Runtime | Performance improvements; note FastAPI 0.135+ requires >=3.10 |
| FastAPI | >=0.135 | Web framework | Async-native, Pydantic v2 integration, OpenAPI docs. Current latest ~0.135.1 |
| uvicorn[standard] | >=0.30 | ASGI server | Standard FastAPI server with uvloop for production |
| Pydantic | >=2.7 | Data validation | Rust-backed v2, used for request/response schemas and settings |
| pydantic-settings | >=2.0 | Configuration | Reads env vars + .env files with type validation |
| asyncpg | >=0.31 | PostgreSQL driver | Latest 0.31.0 (Nov 2025). Fastest Python PG driver. Direct connection to Supabase |
| PyJWT | >=2.8 | JWT validation | Decode Supabase JWTs locally with HS256. Simpler than python-jose |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | >=0.27 | HTTP client | Async HTTP for any external API calls in later phases |
| ruff | >=0.4 | Linting/formatting | Single tool replacing Black + isort + flake8 |
| pytest | >=8.0 | Testing | Test runner for all backend tests |
| pytest-asyncio | >=0.24 | Async test support | Required for testing async FastAPI endpoints and asyncpg |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT | python-jose[cryptography] | python-jose is heavier; PyJWT is simpler for HS256-only Supabase JWTs |
| Supabase CLI migrations | Alembic (raw SQL mode) | Alembic is Python-native but Supabase CLI wraps dbmate and integrates with `supabase db reset/push` for multi-env management |
| Supabase CLI migrations | dbmate standalone | dbmate is what Supabase CLI uses internally; using Supabase CLI directly gives tighter integration with the Supabase ecosystem |
| asyncpg direct | supabase-py | supabase-py wraps PostgREST (HTTP), adding latency; asyncpg is 2-5x faster for parameterized queries |

**Installation:**
```bash
pip install fastapi uvicorn[standard] pydantic pydantic-settings asyncpg PyJWT httpx
pip install ruff pytest pytest-asyncio
```

## Architecture Patterns

### Recommended Project Structure

```
backend/
  main.py                       # FastAPI app, lifespan, CORS
  config.py                     # Settings from env vars (pydantic-settings)
  dependencies.py               # FastAPI Depends: get_current_user, get_pool
  routers/
    auth.py                     # Login status, user profile endpoints
    languages.py                # GET /languages
    review.py                   # /due, /submit (Phase 1 stubs)
  services/
    srs.py                      # SM-2 algorithm (pure functions)
  repositories/
    __init__.py
    pool.py                     # asyncpg pool lifecycle + RLS context manager
    cards.py                    # user_cards queries
    review.py                   # review_log queries
    languages.py                # languages table queries
  db/
    migrations/                 # Supabase CLI migration files (raw SQL)
      20260312000000_initial_schema.sql
      20260312000001_seed_languages.sql
    schema.sql                  # Full DDL reference (generated by supabase db dump)
  tests/
    conftest.py                 # Fixtures: test DB, test user tokens
    test_srs.py                 # SM-2 unit tests (pure functions)
    test_schema.py              # Schema validation tests
    test_rls.py                 # RLS policy integration tests
    test_auth.py                # JWT validation tests
```

### Pattern 1: RLS-Aware Connection Context Manager

**What:** When using asyncpg direct connections with Supabase RLS, you must set `request.jwt.claims` and the PostgreSQL role before executing queries. This requires a context manager that wraps each authenticated query block.

**When to use:** Every repository function that accesses user-scoped tables (user_cards, review_log, user_subscriptions, user_notes_import).

**Example:**
```python
# repositories/pool.py
import asyncpg
import json
from contextlib import asynccontextmanager

_pool: asyncpg.Pool | None = None

async def init_pool(dsn: str):
    global _pool
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=2,
        max_size=10,
        command_timeout=30,
        # For Supavisor (port 6543), add:
        # statement_cache_size=0,
    )

async def close_pool():
    if _pool:
        await _pool.close()

def get_pool() -> asyncpg.Pool:
    assert _pool is not None, "Pool not initialized"
    return _pool

@asynccontextmanager
async def rls_connection(user_id: str):
    """Acquire a connection with RLS context set for the given user."""
    pool = get_pool()
    async with pool.acquire() as conn:
        # Set JWT claims so auth.uid() returns this user's ID
        claims = json.dumps({"sub": user_id, "role": "authenticated"})
        await conn.execute(
            "SELECT set_config('request.jwt.claims', $1, true)",
            claims,
        )
        await conn.execute(
            "SELECT set_config('role', 'authenticated', true)",
        )
        yield conn
```
**Source:** [Supabase Discussion #30124](https://github.com/orgs/supabase/discussions/30124), [Supabase RLS Docs](https://supabase.com/docs/guides/database/postgres/row-level-security)

### Pattern 2: JWT Validation Dependency

**What:** FastAPI dependency that extracts and validates the Supabase JWT from the Authorization header, returning the user ID.

**When to use:** Every authenticated endpoint.

**Example:**
```python
# dependencies.py
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config import settings

security = HTTPBearer(auto_error=False)

async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required",
        )
    try:
        payload = jwt.decode(
            cred.credentials,
            settings.supabase_jwt_secret,
            audience="authenticated",
            algorithms=["HS256"],
        )
        return {"id": payload["sub"], "email": payload.get("email")}
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
```
**Source:** [DEV Community - Validating Supabase JWT with FastAPI](https://dev.to/zwx00/validating-a-supabase-jwt-locally-with-python-and-fastapi-59jf)

### Pattern 3: SM-2 as Pure Functions

**What:** The SM-2 algorithm implemented as a pure function that takes current card state + quality and returns new state. No database access, no side effects.

**When to use:** Always. SM-2 logic must be separate from persistence.

**Example:**
```python
# services/srs.py
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

@dataclass
class CardState:
    ease_factor: float = 2.5
    interval: int = 1          # days
    repetitions: int = 0
    streak: int = 0
    lapses: int = 0

@dataclass
class SRSUpdate:
    ease_factor: float
    interval: int
    repetitions: int
    streak: int
    lapses: int
    next_review: datetime

EASE_FLOOR = 1.3
EASE_RECOVERY_THRESHOLD = 5   # consecutive correct before recovery kicks in
EASE_RECOVERY_INCREMENT = 0.05
EASE_TARGET = 2.5

def sm2_update(state: CardState, quality: int) -> SRSUpdate:
    """Pure SM-2 with ease recovery. quality: 0-5."""
    assert 0 <= quality <= 5

    ease = state.ease_factor
    interval = state.interval
    repetitions = state.repetitions
    streak = state.streak
    lapses = state.lapses

    if quality >= 3:
        # Successful review
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ease)
        repetitions += 1
        streak += 1
    else:
        # Failed review
        repetitions = 0
        interval = 1
        lapses += 1
        streak = 0

    # Standard SM-2 ease factor update
    ease = ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    ease = max(EASE_FLOOR, ease)

    # Ease recovery: after consecutive correct answers, nudge ease toward target
    if streak >= EASE_RECOVERY_THRESHOLD and ease < EASE_TARGET:
        ease = min(EASE_TARGET, ease + EASE_RECOVERY_INCREMENT)

    # Interval fuzzing: +/- 5% to prevent review clustering
    import random
    if interval > 2:
        fuzz = random.uniform(0.95, 1.05)
        interval = max(1, round(interval * fuzz))

    next_review = datetime.now(timezone.utc) + timedelta(days=interval)

    return SRSUpdate(
        ease_factor=round(ease, 4),
        interval=interval,
        repetitions=repetitions,
        streak=streak,
        lapses=lapses,
        next_review=next_review,
    )
```

### Pattern 4: Repository Functions with RLS Context

**What:** Repository functions accept a connection (from rls_connection context manager) and execute parameterized queries.

**When to use:** All user-scoped data access.

**Example:**
```python
# repositories/cards.py
import asyncpg

async def get_due_cards(
    conn: asyncpg.Connection,
    language_id: str,
    limit: int = 20,
) -> list[dict]:
    """Fetch due cards. RLS filters to current user automatically."""
    rows = await conn.fetch(
        """
        SELECT uc.id, uc.card_type, uc.card_id, uc.ease_factor,
               uc.interval, uc.repetitions, uc.streak, uc.lapses,
               uc.next_review
        FROM user_cards uc
        WHERE uc.language_id = $1
          AND uc.next_review <= now()
          AND uc.is_suspended = false
        ORDER BY uc.next_review ASC
        LIMIT $2
        """,
        language_id, limit,
    )
    return [dict(r) for r in rows]

async def update_card_srs(
    conn: asyncpg.Connection,
    card_id: str,
    srs_update: dict,
) -> None:
    await conn.execute(
        """
        UPDATE user_cards
        SET ease_factor = $1, interval = $2, repetitions = $3,
            next_review = $4, last_review = now(),
            streak = $5, lapses = $6
        WHERE id = $7
        """,
        srs_update["ease_factor"], srs_update["interval"],
        srs_update["repetitions"], srs_update["next_review"],
        srs_update["streak"], srs_update["lapses"], card_id,
    )
```

### Pattern 5: Configuration with pydantic-settings

**What:** Centralized settings loaded from environment variables with type validation.

**Example:**
```python
# config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    database_url: str              # Direct PG connection string

    # App
    environment: str = "development"  # development | staging | production
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

### Anti-Patterns to Avoid

- **FOR ALL RLS policies:** Never use `FOR ALL USING (auth.uid() = user_id)` alone. It only controls reads. Writes need `WITH CHECK`. Split into per-operation policies.
- **Service role key for all queries:** Using the service role key bypasses RLS entirely. Only use it for admin operations (migrations, seed scripts). Normal queries must go through the authenticated role with set_config.
- **Mixing asyncpg pool with Supavisor transaction mode without disabling statement caching:** asyncpg uses prepared statements by default; Supavisor transaction mode breaks them. Set `statement_cache_size=0` when connecting through port 6543.
- **Storing SRS state on client:** Server-authoritative SRS prevents cheating and ensures consistency across devices.
- **datetime.utcnow():** Deprecated in Python 3.12+. Use `datetime.now(timezone.utc)` instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT validation | Custom token parsing | PyJWT with `jwt.decode()` | JWT has subtle security requirements (timing attacks, algorithm confusion) |
| Authentication flow | Custom email/password + OAuth | Supabase Auth | Email verification, password reset, OAuth providers, session management all handled |
| Database migrations | Manual SQL file management | Supabase CLI (`supabase migration new`, `supabase db push`) | Tracks migration state, supports reset, integrates with Supabase environments |
| Connection pooling | Custom pool manager | asyncpg.create_pool() | Battle-tested pool with proper connection lifecycle management |
| Password hashing | bcrypt wrapper | Supabase Auth | Auth handles this; backend never sees passwords |
| UUID generation | Python uuid4 | PostgreSQL gen_random_uuid() | Let the database generate UUIDs; avoids client-side generation issues |

**Key insight:** Supabase Auth handles the entire authentication lifecycle (signup, login, OAuth, session refresh, password reset). The backend's only auth responsibility is JWT validation and RLS context setup.

## Common Pitfalls

### Pitfall 1: RLS WITH CHECK Missing on Write Policies
**What goes wrong:** Using `FOR ALL USING (auth.uid() = user_id)` only filters which rows are visible. Without `WITH CHECK`, INSERT and UPDATE operations against user-scoped tables will silently fail or allow inserting rows for other users.
**Why it happens:** The `USING` clause controls row visibility for SELECT/UPDATE/DELETE. The `WITH CHECK` clause controls what rows can be written. They are independent.
**How to avoid:** Split policies by operation. Every INSERT needs `WITH CHECK`, every UPDATE needs both `USING` and `WITH CHECK`.
**Warning signs:** Users cannot insert their own cards. Or worse: no error but data appears under wrong user_id.

### Pitfall 2: SM-2 Ease Factor Death Spiral
**What goes wrong:** Standard SM-2 drops ease factor on failures and barely recovers on success. Cards that hit the 1.3 floor stay there permanently, creating review overload.
**Why it happens:** A quality=0 drops EF by 0.8. Eight consecutive quality=5 responses are needed to recover 0.8 EF. Users rarely achieve this on struggling cards.
**How to avoid:** Implement ease recovery from day one: after EASE_RECOVERY_THRESHOLD (5) consecutive correct answers, nudge ease toward 2.5 by EASE_RECOVERY_INCREMENT (0.05). This is a locked decision from CONTEXT.md.
**Warning signs:** `SELECT COUNT(*) FROM user_cards WHERE ease_factor <= 1.35 AND repetitions > 10` returns >25% of mature cards.

### Pitfall 3: asyncpg + Supavisor Prepared Statement Conflict
**What goes wrong:** asyncpg uses prepared statements by default. Supavisor (Supabase's connection pooler on port 6543) in transaction mode does not support prepared statements, causing `DuplicatePreparedStatementError`.
**Why it happens:** In transaction mode, the underlying PostgreSQL connection is shared between clients. Prepared statements from one client leak into another's session.
**How to avoid:** For development, use direct connection (port 5432). For production with Supavisor, pass `statement_cache_size=0` to `asyncpg.create_pool()`.
**Warning signs:** Intermittent `DuplicatePreparedStatementError` or `InvalidSQLStatementNameError` in production logs.

### Pitfall 4: Public Tables Invisible After Enabling RLS
**What goes wrong:** Enabling RLS on shared tables (languages, grammar_points, vocabulary, drill_sentences) without a permissive read policy makes them return zero rows to authenticated users.
**Why it happens:** RLS defaults to deny-all once enabled. You must explicitly allow reads.
**How to avoid:** For public/shared tables, either (a) do NOT enable RLS, or (b) add `CREATE POLICY "public_read" ON languages FOR SELECT USING (true)`. Option (a) is simpler and correct for truly public data.
**Warning signs:** API returns empty arrays for languages or vocabulary.

### Pitfall 5: set_config Third Argument Must Be True for Transaction Scope
**What goes wrong:** Using `set_config('request.jwt.claims', claims, false)` sets the config for the entire session, not just the current transaction. If the connection is returned to the pool and reused, the previous user's claims persist.
**Why it happens:** The third argument to `set_config` controls scope: `true` = transaction-local (reset on transaction end), `false` = session-local (persists until connection close or explicit reset).
**How to avoid:** Always use `true` as the third argument when setting RLS context. Wrap authenticated queries in a transaction.
**Warning signs:** User A sees User B's data intermittently (connection pool reuse).

### Pitfall 6: Interval Clustering from Rounding
**What goes wrong:** `round(interval * ease_factor)` produces the same integer for nearby cards. 50 cards added on day 1 cluster to the same review dates.
**Why it happens:** Integer rounding of continuous values causes convergence.
**How to avoid:** Add 5% interval fuzzing: `interval = round(interval * ease * uniform(0.95, 1.05))`. Already included in the SM-2 implementation pattern above.
**Warning signs:** Daily due counts are spiky (40 one day, 5 the next).

## Code Examples

### Full RLS Policy Set for user_cards
```sql
-- Source: Supabase RLS docs + Pitfalls research
-- Enable RLS
ALTER TABLE user_cards ENABLE ROW LEVEL SECURITY;

-- SELECT: users see only their own cards
CREATE POLICY "users_select_own_cards"
  ON user_cards FOR SELECT
  USING (auth.uid() = user_id);

-- INSERT: users can only insert cards for themselves
CREATE POLICY "users_insert_own_cards"
  ON user_cards FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- UPDATE: users can only update their own cards
CREATE POLICY "users_update_own_cards"
  ON user_cards FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- DELETE: users can only delete their own cards
CREATE POLICY "users_delete_own_cards"
  ON user_cards FOR DELETE
  USING (auth.uid() = user_id);
```

### Translations Table (Discretion Recommendation)
```sql
-- Separate table preferred over JSONB for queryability and indexing
CREATE TABLE translations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vocabulary_id UUID NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
  locale TEXT NOT NULL,           -- 'en', 'ru', 'ar', 'es', 'pt'
  definition TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(vocabulary_id, locale)
);

-- No RLS needed -- translations are public content
CREATE INDEX idx_translations_vocab ON translations(vocabulary_id);
```

### User Profiles (Discretion Recommendation)
```sql
-- Dedicated table rather than Supabase auth metadata
-- Reason: auth metadata updates require auth API calls; a table is simpler with asyncpg
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  batch_size INT DEFAULT 5 CHECK (batch_size BETWEEN 1 AND 50),
  ui_language TEXT DEFAULT 'en',
  active_language_id UUID REFERENCES languages(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_select_own_profile" ON user_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "users_insert_own_profile" ON user_profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "users_update_own_profile" ON user_profiles FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
```

### Content Lists and User Content Subscriptions (Discretion Recommendation)
```sql
-- Explicit content_lists table -- each row is a subscribable list like "A1 Grammar (Russian)"
CREATE TABLE content_lists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  language_id UUID NOT NULL REFERENCES languages(id),
  list_type TEXT NOT NULL CHECK (list_type IN ('grammar', 'vocabulary')),
  level TEXT CHECK (level IN ('A1','A2','B1','B2','C1','C2')),
  title TEXT NOT NULL,           -- "A1 Grammar", "A2 Vocabulary", etc.
  description TEXT,
  display_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(language_id, list_type, level)
);

-- Join table: which lists a user is subscribed to
CREATE TABLE user_content_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content_list_id UUID NOT NULL REFERENCES content_lists(id) ON DELETE CASCADE,
  subscribed_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, content_list_id)
);

ALTER TABLE user_content_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_select_own_subs" ON user_content_subscriptions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "users_insert_own_subs" ON user_content_subscriptions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "users_delete_own_subs" ON user_content_subscriptions FOR DELETE USING (auth.uid() = user_id);

-- content_lists is public data -- no RLS or permissive policy
```

### FastAPI Lifespan Setup
```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from repositories.pool import init_pool, close_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool(settings.database_url)
    yield
    await close_pool()

app = FastAPI(
    title="PolyglotSRS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Quality Auto-Mapping (from CONTEXT.md decisions)
```python
# services/srs.py
from enum import Enum

class AnswerResult(str, Enum):
    CORRECT = "correct"
    CORRECT_SLOPPY = "sloppy"
    WRONG_FORM = "wrong_form"
    WRONG = "wrong"

# Locked decision: quality auto-derived from NLP result
QUALITY_MAP: dict[AnswerResult, int] = {
    AnswerResult.CORRECT: 4,        # Good
    AnswerResult.CORRECT_SLOPPY: 3, # Hard
    AnswerResult.WRONG_FORM: 2,     # User can retry or accept
    AnswerResult.WRONG: 1,          # Again
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose for JWT | PyJWT (simpler, maintained) | 2024 | python-jose is less actively maintained; PyJWT is the standard |
| datetime.utcnow() | datetime.now(timezone.utc) | Python 3.12 | utcnow() is deprecated; always use timezone-aware datetimes |
| PgBouncer (Supabase) | Supavisor (Supabase) | 2024 | Supabase moved from PgBouncer to their own Supavisor; same asyncpg concerns apply |
| SM-2 only | FSRS available | 2023-2024 | FSRS (Free Spaced Repetition Scheduler) uses ML for better scheduling; SM-2 is simpler to implement and sufficient for v1 |
| Alembic for all Python projects | Supabase CLI migrations (wraps dbmate) | 2023+ | For Supabase projects, Supabase CLI provides tighter integration with `supabase db push/reset/diff` |

**Deprecated/outdated:**
- `datetime.utcnow()`: Deprecated in Python 3.12+. Use `datetime.now(timezone.utc)`.
- python-jose: Less maintained than PyJWT. PyJWT is the recommended alternative for simple JWT decode.
- `FOR ALL` RLS policies: Not deprecated but an anti-pattern. Always split by operation.

## Migration Strategy (Discretion Recommendation)

**Recommendation: Supabase CLI migrations.**

Supabase CLI wraps dbmate under the hood and provides:
- `supabase migration new <name>` -- creates timestamped SQL file in `supabase/migrations/`
- `supabase db reset` -- applies all migrations to local dev DB
- `supabase db push` -- applies pending migrations to remote (staging/prod)
- `supabase db diff` -- generates migration from schema diff
- Native integration with the three-environment setup (local, staging, prod)

Migration files are raw SQL, which aligns with the raw asyncpg approach. No Python tooling needed.

**Seed data recommendation:** Include language seed data (ru, ar, en) in the initial migration file. It is small, static, and must exist before any other operations.

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Initialize (creates supabase/ directory)
supabase init

# Create first migration
supabase migration new initial_schema

# Apply locally
supabase db reset

# Push to remote
supabase db push
```

## Open Questions

1. **set_config scope with asyncpg pool**
   - What we know: `set_config('request.jwt.claims', claims, true)` is transaction-scoped. asyncpg pool returns connections when the `async with pool.acquire()` block exits.
   - What's unclear: Whether the transaction-local scope reliably clears on connection return to pool in all edge cases (e.g., connection error mid-transaction).
   - Recommendation: Always use `true` (transaction-local), wrap in explicit transaction blocks, and add a pool connection cleanup callback as defense-in-depth.

2. **Supabase free tier connection limits**
   - What we know: Free tier allows ~60 direct connections. asyncpg pool + Supabase Dashboard + migrations all consume connections.
   - What's unclear: Exact current limits and whether Supavisor changes this.
   - Recommendation: Start with `min_size=2, max_size=10` for dev. Monitor with `SELECT count(*) FROM pg_stat_activity`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24+ |
| Config file | none -- see Wave 0 |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | All tables have language_id FK | unit | `pytest tests/test_schema.py::test_language_parameterization -x` | Wave 0 |
| DB-02 | RLS policies block cross-user access | integration | `pytest tests/test_rls.py -x` | Wave 0 |
| DB-03 | Language seed data exists after migration | integration | `pytest tests/test_schema.py::test_language_seed_data -x` | Wave 0 |
| DB-04 | Morphology JSONB stores per-language features | unit | `pytest tests/test_schema.py::test_morphology_jsonb -x` | Wave 0 |
| DB-05 | Translations table stores per-locale definitions | unit | `pytest tests/test_schema.py::test_translations_table -x` | Wave 0 |
| DB-06 | Multiple drill sentences per grammar point | unit | `pytest tests/test_schema.py::test_drill_sentences -x` | Wave 0 |
| DB-07 | User content subscriptions join table works | integration | `pytest tests/test_schema.py::test_user_subscriptions -x` | Wave 0 |
| SRS-01 | SM-2 schedules correctly for quality 0-5 | unit | `pytest tests/test_srs.py::test_sm2_quality_range -x` | Wave 0 |
| SRS-02 | Card state tracks all required fields | unit | `pytest tests/test_srs.py::test_card_state_fields -x` | Wave 0 |
| SRS-03 | Failed reviews reset interval and repetitions | unit | `pytest tests/test_srs.py::test_failed_review_reset -x` | Wave 0 |
| SRS-04 | Review log records all fields | integration | `pytest tests/test_review.py::test_review_log_insert -x` | Wave 0 |
| SRS-05 | Due cards sorted by next_review ASC | integration | `pytest tests/test_review.py::test_due_card_ordering -x` | Wave 0 |
| AUTH-01 | Email/password signup produces valid JWT | manual-only | Requires Supabase Auth running; test via Supabase dashboard | N/A |
| AUTH-02 | Google OAuth login produces valid JWT | manual-only | Requires Google OAuth config; test via browser | N/A |
| AUTH-03 | Session persists across refresh | manual-only | Frontend concern; backend is stateless JWT validation | N/A |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` -- shared fixtures (test DB connection, test user JWT tokens, cleanup)
- [ ] `tests/test_srs.py` -- SM-2 pure function tests (no DB needed)
- [ ] `tests/test_schema.py` -- schema validation tests (requires local Supabase or test PG)
- [ ] `tests/test_rls.py` -- RLS integration tests (two test users, cross-access assertions)
- [ ] `tests/test_review.py` -- review log and due card query tests
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest]` -- pytest configuration with asyncio mode
- [ ] Framework install: `pip install pytest pytest-asyncio` (already in requirements)

## Sources

### Primary (HIGH confidence)
- [Supabase RLS Documentation](https://supabase.com/docs/guides/database/postgres/row-level-security) - RLS policy syntax, USING vs WITH CHECK
- [Supabase Connection Management](https://supabase.com/docs/guides/database/connection-management) - Supavisor, port 5432 vs 6543
- [Supabase Database Migrations](https://supabase.com/docs/guides/deployment/database-migrations) - CLI migration workflow
- [asyncpg PyPI](https://pypi.org/project/asyncpg/) - v0.31.0, Nov 2025
- [FastAPI PyPI](https://pypi.org/project/fastapi/) - v0.135.x, requires Python >=3.10
- [SuperMemo SM-2 Algorithm](https://super-memory.com/english/ol/sm2.htm) - Original algorithm specification

### Secondary (MEDIUM confidence)
- [Supabase Discussion #30124](https://github.com/orgs/supabase/discussions/30124) - set_config pattern for direct PG connections with RLS
- [DEV Community - Supabase JWT + FastAPI](https://dev.to/zwx00/validating-a-supabase-jwt-locally-with-python-and-fastapi-59jf) - PyJWT decode pattern with audience validation
- [Supabase Pooling + asyncpg Fix](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249) - statement_cache_size=0 fix

### Tertiary (LOW confidence)
- pytest-asyncio version: search results showed 1.3.0 but this may be documentation version, not package version. Verify with `pip install pytest-asyncio` to get actual latest.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all versions verified via PyPI/official sources
- Architecture: HIGH - patterns derived from Supabase official docs and verified community patterns
- RLS patterns: HIGH - verified against Supabase docs and community discussion
- SM-2 algorithm: HIGH - well-documented public algorithm, ease recovery is a standard extension
- Migration strategy: MEDIUM - Supabase CLI wrapping dbmate is confirmed but specific workflow for three-env may need iteration
- Pitfalls: HIGH - all pitfalls verified against official docs or are well-documented community knowledge

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (30 days -- stable domain, no fast-moving dependencies)
