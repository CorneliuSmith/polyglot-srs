# Architecture Patterns

**Domain:** Multi-language SRS learning platform
**Researched:** 2026-03-12
**Overall confidence:** HIGH (based on detailed product specs + established patterns for FastAPI/asyncpg/NLP systems)

## Recommended Architecture

```
                          +------------------+
                          |   React/Vite     |
                          |   Frontend       |
                          |  (Vercel)        |
                          +--------+---------+
                                   |
                            HTTPS / JSON
                                   |
                          +--------v---------+
                          |   FastAPI         |
                          |   Routers         |
                          |  (Railway)        |
                          +--------+---------+
                                   |
              +--------------------+--------------------+
              |                    |                     |
    +---------v------+  +---------v-------+  +----------v--------+
    | Services Layer |  | NLP Layer       |  | External APIs     |
    | (SRS, Parser,  |  | (BaseNLP +      |  | (Wiktionary,      |
    |  Enrichment)   |  |  Ru/Ar/En)      |  |  Forvo, Tatoeba,  |
    +--------+-------+  +--------+--------+  |  Claude, Stripe)  |
             |                   |            +-------------------+
             |          run_in_executor            |
             |          (sync NLP from             |
             |           async context)            |
             +-------------------+-----------------+
                                 |
                       +---------v----------+
                       | Repository Layer   |
                       | (asyncpg queries)  |
                       +---------+----------+
                                 |
                       +---------v----------+
                       | Supabase PostgreSQL |
                       | (RLS enabled)       |
                       +--------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Sync/Async |
|-----------|---------------|-------------------|------------|
| **Routers** | HTTP request/response, auth extraction, input validation | Services, Repository | Async |
| **Services/SRS** | SM-2 algorithm, session logic, quality mapping | Repository | Pure (sync functions, called from async) |
| **Services/Parser** | Markdown/PDF text extraction, Claude API card extraction | NLP Layer, External APIs, Repository | Async |
| **Services/Enrichment** | Orchestrates Wiktionary/Forvo/Tatoeba lookups, caches results | External APIs, Repository | Async |
| **NLP Layer** | Morphological analysis, lemmatization, answer validation | Nothing external (CPU-bound, in-process) | Sync |
| **Repository Layer** | SQL queries via asyncpg, connection pool management | PostgreSQL | Async |
| **Seeder Scripts** | ETL from external data sources into DB | External files/APIs, Repository | Async (I/O) + Sync (transforms) |
| **External APIs** | Wiktionary, Forvo, Tatoeba, Claude, Stripe | Internet | Async (httpx) |

## The NLP Abstraction Layer

This is the most architecturally significant pattern in the system. It isolates all language-specific behavior behind a uniform interface.

### Pattern: Strategy + Registry

```python
# services/nlp/base.py
from abc import ABC, abstractmethod
from enum import Enum

class AnswerResult(Enum):
    CORRECT = "correct"
    CORRECT_SLOPPY = "sloppy"
    WRONG_FORM = "wrong_form"
    WRONG = "wrong"

class BaseNLP(ABC):
    """All language backends implement this interface."""

    @abstractmethod
    def analyze(self, word: str) -> dict:
        """Full morphological analysis → dict with pos, gender, case, etc."""

    @abstractmethod
    def normalize(self, text: str) -> str:
        """Language-specific normalization (lowercase, strip diacritics, etc.)."""

    @abstractmethod
    def lemmatize(self, word: str) -> str:
        """Return dictionary/canonical form."""

    @abstractmethod
    def get_morphological_family(self, word: str) -> set[str]:
        """All inflected forms sharing the same lemma."""

    @abstractmethod
    def get_aspect_partner(self, verb: str) -> str | None:
        """Aspect partner (Russian-meaningful; others return None)."""

    def check_answer(
        self,
        user_input: str,
        correct_answer: str,
        card_context: dict | None = None,
    ) -> tuple[AnswerResult, str | None]:
        """4-tier validation pipeline. Base implementation handles the
        common flow; subclasses override for language-specific pre-checks
        (e.g., Russian transliteration fallback)."""
        # Layer 1: Exact match
        # Layer 2: Normalized match
        # Layer 3: Lemma match → CORRECT_SLOPPY
        # Layer 4: Morphological family → CORRECT_SLOPPY
        # Layer 5: Aspect partner → WRONG_FORM
        # Layer 6: Explicit alternatives from card_context
        # Layer 7: WRONG
        ...
```

### Registry Pattern (Singleton Backends)

```python
# services/nlp/__init__.py

# Each backend is instantiated ONCE at import time (heavy model loading).
# They are thread-safe for read-only morphological analysis.

NLP_BACKENDS: dict[str, BaseNLP] = {}

def init_nlp_backends():
    """Called once at application startup."""
    from .russian import RussianNLP
    from .arabic import ArabicNLP
    from .english import EnglishNLP

    NLP_BACKENDS["ru"] = RussianNLP()  # loads pymorphy3 (~50ms)
    NLP_BACKENDS["ar"] = ArabicNLP()   # loads camel-tools DB (~2-5s)
    NLP_BACKENDS["en"] = EnglishNLP()  # loads spaCy model (~1s)

def get_nlp(language_code: str) -> BaseNLP:
    if language_code not in NLP_BACKENDS:
        raise ValueError(f"No NLP backend for language: {language_code}")
    return NLP_BACKENDS[language_code]
```

### Calling Sync NLP from Async Context

NLP backends are CPU-bound. Do NOT make them async. Instead, use `run_in_executor` when calling from async router/service code.

```python
import asyncio
from functools import partial

async def validate_answer(
    language_code: str,
    user_input: str,
    correct_answer: str,
    card_context: dict | None = None,
) -> tuple[AnswerResult, str | None]:
    nlp = get_nlp(language_code)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,  # default ThreadPoolExecutor
        partial(nlp.check_answer, user_input, correct_answer, card_context),
    )
```

### Why This Pattern Works

1. **New languages require only one new file.** Implement `BaseNLP`, register in `NLP_BACKENDS`. No changes to routers, services, or schema.
2. **Answer validation is uniform.** The 4-tier pipeline lives in `BaseNLP.check_answer()`. Language backends override only when they need pre-checks (Russian transliteration) or have unique semantics (Arabic verb forms).
3. **Testing is straightforward.** Each NLP backend is a pure class with no I/O. Test with `assert RussianNLP().check_answer("собака", "собаку") == (AnswerResult.CORRECT_SLOPPY, ...)`.
4. **Model loading is controlled.** Heavy models (camel-tools ~1.5GB) load once at startup, not per-request.

## Repository Layer over asyncpg

### Pattern: Thin Repository Functions (NOT Classes)

Use module-level async functions, not repository classes. This avoids unnecessary OOP ceremony while keeping SQL organized.

```
backend/
  repositories/
    __init__.py
    pool.py              # Connection pool lifecycle
    cards.py             # user_cards queries
    vocabulary.py        # vocabulary table queries
    grammar.py           # grammar_points queries
    review.py            # review_log + SRS state queries
    drill.py             # drill_sentences queries
    languages.py         # languages table queries
    subscriptions.py     # user_subscriptions queries
    imports.py           # user_notes_import queries
```

### Connection Pool Lifecycle

```python
# repositories/pool.py
import asyncpg

_pool: asyncpg.Pool | None = None

async def init_pool(dsn: str):
    global _pool
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=5,
        max_size=20,
        command_timeout=30,
    )

async def close_pool():
    if _pool:
        await _pool.close()

def get_pool() -> asyncpg.Pool:
    assert _pool is not None, "Pool not initialized"
    return _pool
```

Wire into FastAPI lifespan:

```python
# main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool(settings.database_url)
    init_nlp_backends()
    yield
    await close_pool()

app = FastAPI(lifespan=lifespan)
```

### Repository Function Pattern

Each repository module exports pure async functions that take a connection (or acquire from pool).

```python
# repositories/vocabulary.py
from .pool import get_pool

async def get_vocabulary_by_language(
    language_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT id, word, lemma, pos, definition, morphology,
               frequency_rank, audio_url
        FROM vocabulary
        WHERE language_id = $1
        ORDER BY frequency_rank ASC NULLS LAST
        LIMIT $2 OFFSET $3
        """,
        language_id, limit, offset,
    )
    return [dict(r) for r in rows]

async def upsert_vocabulary(language_id: str, word: str, **fields) -> str:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO vocabulary (language_id, word, lemma, pos, definition, morphology)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (language_id, lemma) DO UPDATE SET
            definition = EXCLUDED.definition,
            morphology = EXCLUDED.morphology
        RETURNING id
        """,
        language_id, word,
        fields.get("lemma"), fields.get("pos"),
        fields.get("definition"), fields.get("morphology"),
    )
    return str(row["id"])
```

### Why Functions, Not Classes

- **No state to manage.** The connection pool is the shared resource; repositories are stateless.
- **Easier to test.** Pass a test connection directly; no mocking class constructors.
- **Matches asyncpg idiom.** asyncpg is already functional (`pool.fetch()`), wrapping in classes adds nothing.
- **Avoids "repository per entity" bloat.** Some queries naturally span tables (e.g., fetching due cards with vocabulary data). Functions group by domain, not by table.

### Transaction Pattern

For multi-table writes (e.g., submitting a review updates `user_cards` AND inserts into `review_log`):

```python
# repositories/review.py
async def submit_review(
    user_id: str,
    card_id: str,
    card_type: str,
    language_id: str,
    quality: int,
    time_taken_ms: int,
    srs_updates: dict,  # pre-computed by SM-2 service
):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE user_cards
                SET ease_factor = $1, interval = $2, repetitions = $3,
                    next_review = $4, last_review = $5, streak = $6, lapses = $7
                WHERE user_id = $8 AND card_id = $9
                """,
                srs_updates["ease_factor"], srs_updates["interval"],
                srs_updates["repetitions"], srs_updates["next_review"],
                srs_updates["last_review"], srs_updates["streak"],
                srs_updates["lapses"], user_id, card_id,
            )
            await conn.execute(
                """
                INSERT INTO review_log (user_id, language_id, card_id, card_type, quality, time_taken_ms)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_id, language_id, card_id, card_type, quality, time_taken_ms,
            )
```

## Review Session Flow

This is the core user-facing loop. Architecture must support both self-graded and type-to-answer modes.

### Data Flow

```
1. Client: GET /api/review/due?language_code=ru&limit=20
   ↓
2. Router extracts user_id from Supabase JWT, passes to service
   ↓
3. Repository: SELECT from user_cards
   WHERE user_id = $1 AND language_id = $2
     AND next_review <= now() AND NOT is_suspended
   ORDER BY next_review ASC LIMIT $3
   ↓
4. Repository: JOIN to vocabulary/grammar_points to hydrate card content
   ↓
5. Response: list of card objects with:
   - card metadata (id, type, language_id)
   - content (word, definition, examples, audio_url, morphology)
   - drill_sentence (if type-to-answer mode)
   - SRS state is NOT sent to client (server-authoritative)
   ↓
6. Client renders card queue. For each card:
   a. Show front (prompt + sentence with blank)
   b. User types answer OR flips card
   ↓
7. If type-to-answer:
   POST /api/review/check
   { card_id, user_input, drill_sentence_id }
   ↓
8. Router → NLP layer (via run_in_executor):
   nlp.check_answer(user_input, correct_answer, card_context)
   → returns AnswerResult + explanation
   ↓
9. Client shows result + explanation. User rates quality (or auto-mapped).
   ↓
10. POST /api/review/submit
    { card_id, card_type, quality, time_taken_ms }
    ↓
11. Service: sm2_update(card_state, quality) → new SRS state
    ↓
12. Repository: UPDATE user_cards + INSERT review_log (in transaction)
    ↓
13. Response: { next_review, streak, session_progress }
    ↓
14. Client advances to next card in queue. Repeat from step 6.
    ↓
15. Session complete:
    GET /api/review/session-summary?language_code=ru
    → { cards_reviewed, accuracy_pct, time_spent, streak }
```

### Key Design Decisions

**Server-authoritative SRS state.** The client never computes intervals or ease factors. It only sends quality ratings. This prevents cheating and ensures consistency.

**Separate check and submit endpoints.** `/check` validates the answer and returns feedback. `/submit` records the quality rating. This separation allows the user to see the explanation and then decide their quality rating (especially for WRONG_FORM results where the user can override).

**Card queue is fetched once per session.** The client gets up to N due cards at session start. Cards that become due mid-session (unlikely given SRS intervals) are not added dynamically. Keeps the session predictable.

**Drill sentences are pre-selected per card.** When hydrating the card queue, the backend picks a drill sentence for each card. This avoids the client needing to make per-card requests.

### Session State

Session state lives entirely on the client (React state via `useReviewSession` hook). The server is stateless between requests. This simplifies the backend and allows users to close the browser mid-session without data loss (each card submission is immediately persisted).

## Seed Data Pipeline

### Pattern: Download, Transform, Load (DTL)

Each language has its own seeder script that follows a three-phase pattern. Seeders are CLI scripts, NOT API endpoints.

```
backend/
  services/
    seeder/
      __init__.py
      base.py              # Shared utilities
      seed_russian.py      # OpenRussian TSV → vocabulary + grammar
      seed_arabic.py       # Arabic Wordnet + frequency → vocabulary
      seed_english.py      # COCA + WordNet → vocabulary
      seed_drill.py        # Tatoeba → drill_sentences (shared)
```

### Pipeline Flow

```
Phase 1: DOWNLOAD
  seed_russian.py:
    wget openrussian.org/ru/words.tsv → data/raw/ru/words.tsv
    wget openrussian.org/ru/translations.tsv → data/raw/ru/translations.tsv

  seed_arabic.py:
    Download Arabic Wordnet XML → data/raw/ar/wordnet.xml
    Download OpenSubtitles freq list → data/raw/ar/frequency.tsv

  seed_english.py:
    NLTK WordNet (programmatic) → in-memory
    COCA frequency list → data/raw/en/coca.tsv

Phase 2: TRANSFORM (sync, CPU-bound)
  For each raw record:
    1. Parse source format (TSV, XML, NLTK objects)
    2. Map to our vocabulary schema fields
    3. Run through NLP backend:
       - nlp.analyze(word) → morphology JSONB
       - nlp.lemmatize(word) → lemma field
    4. Assign frequency_rank from corpus data
    5. Yield normalized dict ready for INSERT

  This is where language-specific logic lives:
    Russian: extract gender, aspect, animacy from pymorphy3
    Arabic: extract root, pattern, verb form from camel-tools
    English: extract POS, irregular forms from spaCy

Phase 3: LOAD (async, batched)
  1. Connect to Supabase PostgreSQL via asyncpg
  2. Look up language_id for the target language
  3. Batch INSERT using COPY or executemany (not individual INSERTs)
  4. Use ON CONFLICT (language_id, lemma) DO UPDATE for idempotency
  5. Log: inserted N, updated M, skipped K
```

### Seeder Base Pattern

```python
# services/seeder/base.py
from abc import ABC, abstractmethod

class BaseSeeder(ABC):
    """Each language seeder implements this."""

    @abstractmethod
    def download(self, data_dir: str) -> list[str]:
        """Download raw data files. Return list of file paths."""

    @abstractmethod
    def transform(self, raw_files: list[str]) -> Iterator[dict]:
        """Yield vocabulary dicts ready for DB insert."""

    async def load(self, records: Iterator[dict], language_code: str):
        """Batch insert into vocabulary table. Shared implementation."""
        pool = get_pool()
        language_id = await get_language_id(pool, language_code)
        batch = []
        inserted = 0
        for record in records:
            record["language_id"] = language_id
            batch.append(record)
            if len(batch) >= 500:
                await bulk_upsert_vocabulary(pool, batch)
                inserted += len(batch)
                batch = []
        if batch:
            await bulk_upsert_vocabulary(pool, batch)
            inserted += len(batch)
        return inserted

    async def run(self, data_dir: str, language_code: str):
        """Full pipeline: download → transform → load."""
        files = self.download(data_dir)
        records = self.transform(files)
        count = await self.load(records, language_code)
        print(f"Seeded {count} vocabulary items for {language_code}")
```

### Enrichment After Seeding

After base vocabulary is seeded, a second pass enriches records:

```
For each vocabulary record missing wiktionary_data or audio_url:
  1. Fetch Wiktionary definition + inflection table → cache in wiktionary_data JSONB
  2. Fetch Forvo audio URL → store in audio_url
  3. Fetch Tatoeba example sentences → store in examples JSONB
  4. Rate-limit: 1 req/sec for Wiktionary, respect Forvo 500/day limit
```

This is a separate script (`enrich.py`), not part of seeding, because:
- External API calls are slow and rate-limited
- Seeding should be fast and repeatable
- Enrichment can run incrementally (only enrich records with NULL fields)

## Complete Directory Structure

```
backend/
  main.py                       # FastAPI app, lifespan, CORS
  config.py                     # Settings from env vars (pydantic-settings)
  routers/
    auth.py                     # Supabase JWT verification
    languages.py                # GET /languages
    cards.py                    # CRUD for grammar_points + vocabulary
    review.py                   # /due, /check, /submit, /session-summary
    drill.py                    # Standalone drill mode (outside SRS)
    import_.py                  # Note/PDF upload + Claude extraction
    subscriptions.py            # Stripe webhooks + status
    integrations.py             # Wiktionary/Forvo/Tatoeba proxies
  services/
    srs.py                      # SM-2 algorithm (pure functions)
    parser.py                   # MD/PDF → text → Claude → cards
    enrichment.py               # Wiktionary + Forvo + Tatoeba orchestrator
    nlp/
      __init__.py               # NLP_BACKENDS registry + get_nlp()
      base.py                   # BaseNLP ABC + AnswerResult enum
      russian.py                # RussianNLP (pymorphy3)
      arabic.py                 # ArabicNLP (camel-tools)
      english.py                # EnglishNLP (spaCy)
    seeder/
      __init__.py
      base.py                   # BaseSeeder ABC
      seed_russian.py           # OpenRussian ETL
      seed_arabic.py            # Arabic Wordnet + freq ETL
      seed_english.py           # COCA + WordNet ETL
      seed_drills.py            # Tatoeba sentence import
      enrich.py                 # Post-seed enrichment (Wiktionary, Forvo)
  repositories/
    __init__.py
    pool.py                     # asyncpg pool lifecycle
    languages.py
    vocabulary.py
    grammar.py
    cards.py                    # user_cards (SRS state)
    review.py                   # review_log
    drill.py                    # drill_sentences
    subscriptions.py
    imports.py
  models/
    schemas.py                  # Pydantic models for request/response
  db/
    schema.sql                  # Full DDL + RLS policies
    migrations/                 # Manual SQL migration files
  data/
    raw/                        # Downloaded seed data (gitignored)
      ru/
      ar/
      en/
```

## Patterns to Follow

### Pattern 1: Language-Parameterized Everything

Every query, every endpoint, every service call takes a `language_code` or `language_id` parameter. Nothing is hardcoded to a specific language.

**Why:** Adding a 4th language (e.g., Japanese) should require only: a new NLP backend, a new seeder script, and a new row in the `languages` table. Zero changes to routers, services, or frontend components.

**Enforce via:** All user-facing tables have `language_id` as a required FK. All repository functions accept `language_id` as a parameter. All API endpoints accept `language_code` as a query/path parameter.

### Pattern 2: Sync Compute, Async I/O

NLP operations (morphological analysis, lemmatization, answer checking) are CPU-bound. They run synchronously. Database queries, HTTP calls, and file I/O are async.

**Bridge:** When an async endpoint needs NLP, use `asyncio.get_event_loop().run_in_executor(None, sync_fn)`. This offloads to the default ThreadPoolExecutor without blocking the event loop.

**Do NOT:** Make NLP backends async. Do not use `asyncio.to_thread()` unless on Python 3.9+ (it is equivalent but slightly cleaner syntax than `run_in_executor`). Actually, since the constraint is Python 3.11+, `asyncio.to_thread()` is the preferred syntax.

### Pattern 3: Pydantic for API Boundaries, Dicts Internally

Use Pydantic models for request/response validation at the router level. Internally (services, repositories), pass plain dicts. asyncpg returns `Record` objects that convert cleanly to dicts.

**Why:** Pydantic at the boundary catches bad input early. Internally, dicts avoid the overhead of constructing model instances for every DB row, and the JSONB morphology field is naturally a dict.

### Pattern 4: Idempotent Seeding

All seeder scripts use `ON CONFLICT ... DO UPDATE`. Running a seeder twice produces the same result. This enables safe re-runs when source data updates.

## Anti-Patterns to Avoid

### Anti-Pattern 1: ORM Abstraction over asyncpg

**What:** Wrapping asyncpg in SQLAlchemy async or a custom ORM layer.
**Why bad:** Adds complexity without benefit. The morphology JSONB field and language-parameterized queries are easier to express in raw SQL. ORM mapping of polymorphic card types (grammar vs vocabulary) is awkward.
**Instead:** Thin repository functions with raw SQL. Use `$1, $2` parameterized queries (asyncpg syntax).

### Anti-Pattern 2: Async NLP Backends

**What:** Making `analyze()`, `lemmatize()`, `check_answer()` async.
**Why bad:** pymorphy3, camel-tools, and spaCy are all synchronous CPU-bound libraries. Wrapping them in `async def` with `await` is misleading and gains nothing. It can even deadlock if the event loop tries to run sync code that itself tries to use the event loop.
**Instead:** Keep NLP sync. Use `asyncio.to_thread()` at the call site.

### Anti-Pattern 3: Per-Request NLP Model Loading

**What:** Loading `pymorphy3.MorphAnalyzer()` or `spacy.load()` inside each request handler.
**Why bad:** Model loading takes 50ms-5s depending on the library. On every request, this destroys response times.
**Instead:** Load once at application startup in `lifespan()`. Store in `NLP_BACKENDS` singleton dict.

### Anti-Pattern 4: Client-Side SRS Computation

**What:** Sending SRS state to the client and letting JavaScript compute the next interval.
**Why bad:** Users can manipulate review timing. State can desync between tabs/devices. SM-2 edge cases are easier to test server-side.
**Instead:** Server-authoritative. Client sends only quality rating; server computes and persists new state.

### Anti-Pattern 5: Mixing Seed Data with Enrichment

**What:** Calling Wiktionary/Forvo during the seeding pipeline.
**Why bad:** External APIs are rate-limited and flaky. A seeder that depends on 100k Wiktionary calls will fail partway through and leave the DB in a partial state. It also takes hours.
**Instead:** Seed base data (from offline dumps) first. Enrich incrementally in a separate script that can resume where it left off.

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| DB connections | asyncpg pool (5-20) | asyncpg pool (20-50) | Connection pooler (PgBouncer) |
| NLP latency | run_in_executor, default thread pool | Increase thread pool size | Dedicated NLP worker service |
| camel-tools memory | ~1.5GB in single process | Same (shared across threads) | Separate NLP microservice |
| Review queue query | Simple index on (user_id, next_review) | Composite index, EXPLAIN ANALYZE | Materialized view of due counts |
| Seed data volume | 100k vocabulary rows total | Same (data grows slowly) | Partitioning by language_id |
| Session concurrency | No issues | No issues | Redis for session rate limiting |

## Suggested Build Order (Dependencies)

The architecture has clear dependency chains that dictate build order:

```
Layer 0: Foundation (no dependencies)
  ├── schema.sql (DDL + RLS policies)
  ├── asyncpg pool lifecycle (pool.py)
  └── config.py (pydantic-settings)

Layer 1: Data Access (depends on Layer 0)
  ├── Repository functions (all modules)
  └── Pydantic request/response schemas

Layer 2: Core Logic (depends on Layer 1)
  ├── NLP backends (base.py + russian.py + arabic.py + english.py)
  │   └── No DB dependency — pure computation
  ├── SM-2 algorithm (srs.py)
  │   └── No DB dependency — pure functions
  └── Seeder scripts (depend on repositories + NLP)

Layer 3: API Endpoints (depends on Layer 2)
  ├── Review endpoints (/due, /check, /submit)
  │   └── Depends on: repositories, NLP, SRS
  ├── Drill endpoints
  │   └── Depends on: repositories, NLP
  ├── Card CRUD endpoints
  │   └── Depends on: repositories
  └── Language endpoints
      └── Depends on: repositories

Layer 4: Integration Features (depends on Layer 3)
  ├── Enrichment service (Wiktionary, Forvo, Tatoeba)
  ├── Note import pipeline (parser + Claude API)
  ├── Stripe subscriptions
  └── Auth middleware (Supabase JWT)

Layer 5: Frontend (depends on Layer 3 API being stable)
  ├── Review session UI
  ├── Dashboard
  ├── RTL support
  └── On-screen keyboards
```

**Phase ordering rationale:**
1. Schema + pool + NLP + SM-2 have zero cross-dependencies and can be built in parallel (or any order).
2. Repositories depend only on pool.
3. Seeders depend on repositories + NLP (need both to transform and load data).
4. Review endpoints are the core product loop and need repositories + NLP + SM-2.
5. External integrations (Wiktionary, Forvo, Stripe) are additive and can be deferred.
6. Frontend can start as soon as review API endpoints exist.

## Data Flow Summary

### Happy Path: User Reviews a Russian Vocabulary Card

```
User opens Dashboard → clicks "Review Now"
  → GET /api/review/due?language_code=ru&limit=20
  → Repository: fetch due user_cards JOIN vocabulary
  → Response: 20 cards with content + drill sentences

User sees card: "Я вижу {{___}}" (hint: accusative of "собака")
User types: "собаку"
  → POST /api/review/check { card_id, user_input: "собаку", drill_id }
  → Router extracts correct_answer "собаку" from drill_sentence
  → asyncio.to_thread(russian_nlp.check_answer, "собаку", "собаку", context)
  → Layer 1: exact match → AnswerResult.CORRECT
  → Response: { result: "correct", explanation: null }

User clicks "Good" (quality = 4)
  → POST /api/review/submit { card_id, quality: 4, time_taken_ms: 3200 }
  → Service: sm2_update(card_state, quality=4)
    → interval: 1 → 6, repetitions: 0 → 1, ease: 2.5 → 2.5
  → Repository: UPDATE user_cards + INSERT review_log (transaction)
  → Response: { next_review: "2026-03-18", streak: 5 }
```

### Error Path: User Types Wrong Aspect

```
Card expects: "написать" (perfective)
User types: "писать" (imperfective)
  → POST /api/review/check
  → russian_nlp.check_answer("писать", "написать", context)
  → Layer 1: no exact match
  → Layer 2: normalized no match
  → Layer 3: lemmatize("писать") = "писать", lemmatize("написать") = "написать" → no match
  → Layer 4: morphological family of "написать" does not contain "писать"
  → Layer 5: get_aspect_partner("написать") → "писать" → MATCH
  → Response: { result: "wrong_form", explanation: "писать is imperfective..." }

User sees explanation, clicks "Mark wrong" → quality = 1
  → POST /api/review/submit { card_id, quality: 1 }
  → SM-2 resets repetitions to 0, interval to 1 day
```

## Sources

- PolyglotSRS product spec (`polyglot-srs-spec.md`) — schema, backend structure, API integrations
- Answer validation spec (`answer-validation-spec.md`) — 4-tier validation pipeline, per-language edge cases
- PROJECT.md — constraints and key decisions
- SM-2 algorithm: well-documented public algorithm (SuperMemo, Anki implementations)
- asyncpg documentation: connection pool management, transaction patterns
- FastAPI documentation: lifespan events, dependency injection
- Confidence: HIGH for all patterns (derived from detailed specs + established library idioms)
