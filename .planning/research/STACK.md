# Technology Stack

**Project:** PolyglotSRS
**Researched:** 2026-03-12
**Overall Confidence:** MEDIUM -- versions are from training data (cutoff May 2025); verify with `pip index versions <pkg>` before pinning in requirements.txt

> **IMPORTANT:** WebSearch, WebFetch, and Bash were unavailable during this research session. All version numbers below are from training data knowledge (May 2025 cutoff). Before starting development, run `pip install <package>` without a version pin to get the latest, then pin whatever installs. Versions listed here are the last known stable releases and should be treated as minimum floors, not exact targets.

---

## Recommended Stack

### Backend Core

| Technology | Min Version | Purpose | Why | Confidence |
|------------|-------------|---------|-----|------------|
| **Python** | 3.11+ | Runtime | 3.11 has significant performance improvements (10-60% faster). 3.12+ adds more optimizations. PROJECT.md specifies 3.11+ which is correct -- do NOT use 3.10 or below, you lose TaskGroup and ExceptionGroup support | HIGH |
| **FastAPI** | >=0.115 | Web framework | Async-native, automatic OpenAPI docs, Pydantic v2 integration. The standard for modern Python APIs. No serious competitor in the async Python space | HIGH |
| **Uvicorn** | >=0.30 | ASGI server | Standard FastAPI server. Use `uvicorn[standard]` to get uvloop and httptools for production performance | HIGH |
| **Pydantic** | >=2.7 | Data validation | FastAPI's backbone. V2 is Rust-backed, 5-50x faster than V1. Ensure you use V2 -- V1 API is deprecated | HIGH |

### Database

| Technology | Min Version | Purpose | Why | Confidence |
|------------|-------------|---------|-----|------------|
| **Supabase** | (managed) | PostgreSQL + Auth + Storage | Managed Postgres with built-in auth, RLS policies, and realtime subscriptions. Eliminates building auth from scratch. Free tier is generous for development | HIGH |
| **asyncpg** | >=0.29 | PostgreSQL driver | Fastest Python PostgreSQL driver (C extension). 2-5x faster than psycopg3 async for typical workloads. Raw SQL means full control over queries, no ORM translation overhead | HIGH |
| **PostgreSQL** | 15+ | Database (via Supabase) | Supabase runs PG 15. JSONB for morphology fields, full-text search for dictionary lookups, array types for tags. All features this project needs are mature | HIGH |

### NLP Libraries

| Technology | Min Version | Purpose | Why | Confidence |
|------------|-------------|---------|-----|------------|
| **pymorphy3** | >=2.0 | Russian morphology | Fork of pymorphy2 with Python 3.11+ support. Provides lemmatization, POS tagging, morphological analysis, and inflection. Runs locally, no API quota. Small memory footprint (~30MB) | MEDIUM |
| **camel-tools** | >=1.5 | Arabic NLP | CAMeL Lab's toolkit for Arabic. Morphological analysis, disambiguation, transliteration, dialect ID. The most comprehensive open-source Arabic NLP toolkit. Models are ~1.5GB -- must bake into Docker image | MEDIUM |
| **spaCy** | >=3.7 | English NLP | Industry standard. `en_core_web_sm` model is ~12MB, sufficient for lemmatization and POS tagging. Do NOT use the large model -- you only need lemma and POS, not NER or vectors | HIGH |

### Frontend

| Technology | Min Version | Purpose | Why | Confidence |
|------------|-------------|---------|-----|------------|
| **React** | 18+ | UI framework | Standard choice. Hooks-based architecture. React 19 may be available -- check but 18 is stable and well-supported | HIGH |
| **Vite** | >=5.0 | Build tool | Fast HMR, native ESM. Replaced webpack/CRA as the standard React build tool. Sub-second cold starts | HIGH |
| **Tailwind CSS** | >=3.4 | Styling | Utility-first CSS. Tailwind v4 released early 2025 with significant changes (CSS-first config, no more tailwind.config.js). Evaluate v4 but v3.4 is proven stable | MEDIUM |
| **TypeScript** | >=5.4 | Type safety | Non-negotiable for a project this complex. Catches NLP response shape mismatches, API contract drift | HIGH |

### Authentication and Payments

| Technology | Min Version | Purpose | Why | Confidence |
|------------|-------------|---------|-----|------------|
| **Supabase Auth** | (managed) | Authentication | Email + Google OAuth out of the box. JWT tokens verified on backend. Eliminates custom auth code entirely | HIGH |
| **stripe** (Python) | >=8.0 | Payments SDK | Official Stripe Python SDK. Handles subscriptions, webhooks, customer portal. Per-language pricing maps cleanly to Stripe Products/Prices | HIGH |

### Supporting Backend Libraries

| Library | Min Version | Purpose | When to Use | Confidence |
|---------|-------------|---------|-------------|------------|
| **httpx** | >=0.27 | HTTP client | Async HTTP for Wiktionary, Forvo, Tatoeba API calls. Drop-in replacement for requests but async-native | HIGH |
| **python-jose[cryptography]** | >=3.3 | JWT validation | Validating Supabase JWTs on FastAPI side. Use the `cryptography` backend, NOT the default `python-ecdsa` | HIGH |
| **python-multipart** | >=0.0.9 | Form parsing | Required by FastAPI for file uploads (PDF/Markdown import) | HIGH |
| **PyMuPDF (fitz)** | >=1.24 | PDF parsing | Extract text from uploaded PDFs. Faster and more reliable than pdfplumber for text extraction. Handles multi-column layouts | MEDIUM |
| **anthropic** | >=0.30 | Claude API | Card extraction from imported notes. Use the official SDK, not raw HTTP | HIGH |
| **redis / valkey** | >=5.0 | Caching | Cache Wiktionary definitions, Forvo audio URLs, NLP analysis results. Optional for MVP but critical for performance at scale | MEDIUM |

### Supporting Frontend Libraries

| Library | Min Version | Purpose | When to Use | Confidence |
|---------|-------------|---------|-------------|------------|
| **@supabase/supabase-js** | >=2.43 | Supabase client | Auth, realtime subscriptions, direct DB queries where RLS permits | HIGH |
| **@tanstack/react-query** | >=5.0 | Server state | Cache SRS session data, prefetch next cards. Handles stale-while-revalidate pattern needed for SRS queue | HIGH |
| **zustand** | >=4.5 | Client state | Lightweight store for review session state (current card, queue, timer). NOT Redux -- too much boilerplate for this scope | HIGH |
| **react-router** | >=6.20 | Routing | Standard. v7 may be available (merged with Remix) -- evaluate but v6 is battle-tested | MEDIUM |
| **sonner** | latest | Notifications | Answer feedback toasts (correct/wrong/close). Newer and better animated than react-hot-toast | LOW |
| **framer-motion** | >=11.0 | Animations | Card flip animations, slide transitions for SRS queue. Lightweight for what you need | MEDIUM |
| **recharts** | >=2.12 | Charts | Dashboard heatmap, streak charts, CEFR progress visualization | MEDIUM |

### DevOps and Tooling

| Technology | Min Version | Purpose | Why | Confidence |
|------------|-------------|---------|-----|------------|
| **Docker** | latest | Containerization | Required for Railway deployment. Bake camel-tools models into image | HIGH |
| **Ruff** | >=0.4 | Python linting/formatting | Replaced Black + isort + flake8. Single tool, 10-100x faster. The new standard | HIGH |
| **pytest** | >=8.0 | Testing | With pytest-asyncio for async test support | HIGH |
| **pytest-asyncio** | >=0.23 | Async test support | Required for testing async FastAPI endpoints and asyncpg queries | HIGH |
| **Vitest** | >=1.0 | Frontend testing | Native Vite integration. Faster than Jest for Vite projects | HIGH |
| **Playwright** | >=1.42 | E2E testing | Cross-browser E2E tests. Better than Cypress for modern async apps | MEDIUM |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Python DB driver | asyncpg | psycopg3 (async) | asyncpg is 2-5x faster for parameterized queries. psycopg3 is catching up but asyncpg remains the performance king for PostgreSQL |
| Python DB driver | asyncpg | supabase-py | supabase-py wraps PostgREST (HTTP), adding latency. asyncpg connects directly to Postgres -- critical for high-frequency SRS review sessions |
| ORM | None (raw SQL) | SQLAlchemy 2.0 | ORM adds abstraction overhead. This project has complex language-specific queries (JSONB morphology fields, array operations) that are cleaner in raw SQL. Repository pattern gives structure without ORM cost |
| ORM | None (raw SQL) | Tortoise ORM | Less mature than SQLAlchemy, smaller community. Same objection -- raw SQL is better for this domain |
| Russian NLP | pymorphy3 | Natasha (NLP lib) | Natasha is higher-level (NER, extraction). pymorphy3 is lower-level morphological analysis which is exactly what answer validation needs |
| Arabic NLP | camel-tools | Farasa | camel-tools has better morphological disambiguation and is actively maintained by CAMeL Lab at NYU Abu Dhabi. More comprehensive for MSA |
| Arabic NLP | camel-tools | Stanza (Arabic) | Stanza's Arabic support is thinner -- no root extraction, weaker morphological analysis. camel-tools is purpose-built |
| English NLP | spaCy | NLTK | NLTK is academic/pedagogical. spaCy is production-grade, faster, better API. No contest for production use |
| State management | zustand | Redux Toolkit | Redux is overkill. SRS review session state is simple (current card, queue position, score). Zustand does this in ~20 lines vs Redux's boilerplate |
| State management | zustand | Jotai | Jotai is atomic (bottom-up). Zustand is store-based (top-down). SRS session is naturally a single store with related state -- zustand fits better |
| CSS | Tailwind | CSS Modules | Tailwind's utility approach is faster for building UIs. RTL support via `rtl:` variant is essential for Arabic layout |
| Build tool | Vite | Next.js | This is an SPA with a separate FastAPI backend. Next.js adds SSR complexity that provides no value here -- SRS review is entirely client-driven |
| Charting | recharts | Chart.js | recharts is React-native (declarative components). Chart.js requires imperative DOM manipulation via refs. For a React app, recharts integrates more naturally |
| PDF parsing | PyMuPDF | pdfplumber | PyMuPDF is faster, handles more edge cases (scanned PDFs with OCR, multi-column), and has a smaller dependency footprint |
| HTTP client | httpx | aiohttp | httpx has a cleaner API, supports both sync and async, and is the modern standard. aiohttp is older and more verbose |

---

## Critical Integration Notes

### asyncpg + Supabase: Connection Pooling

Supabase exposes both a direct PostgreSQL connection and a connection pooler (PgBouncer on port 6543). For asyncpg:

- **Use the pooler URL (port 6543) in production** -- asyncpg creates its own connection pool, but Railway -> Supabase needs the pooler to handle connection limits
- **Use direct URL (port 5432) for migrations** -- pooler doesn't support prepared statements in transaction mode
- asyncpg's built-in pool (`asyncpg.create_pool()`) handles connection lifecycle. Set `min_size=5, max_size=20` as starting point
- **IMPORTANT:** Supabase free tier allows 60 connections. With asyncpg pool + Supabase dashboard + migrations, you can hit this. Monitor connection count

### camel-tools: Docker Image Strategy

camel-tools models are ~1.5GB. Strategy:

```dockerfile
# Multi-stage build
FROM python:3.11-slim AS builder
RUN pip install camel-tools
RUN camel_data -i disambig-mle-calima-msa-r13

FROM python:3.11-slim AS runtime
COPY --from=builder /root/.camel_tools /root/.camel_tools
# ... rest of app
```

- Bake models into Docker image, do NOT download at startup (cold start would be 3-5 minutes on Railway)
- Railway has a ~8GB image size limit -- with camel-tools models + spaCy model + app, expect ~2-3GB total. Well within limits
- Use `.dockerignore` to exclude test data, docs, etc.

### Sync NLP in Async Context

pymorphy3 and camel-tools are synchronous (CPU-bound). In FastAPI async endpoints:

```python
import asyncio
from functools import partial

async def validate_answer(text: str, language: str):
    loop = asyncio.get_event_loop()
    # Run CPU-bound NLP in thread pool
    result = await loop.run_in_executor(
        None,  # default ThreadPoolExecutor
        partial(nlp_backends[language].analyze, text)
    )
    return result
```

- Default ThreadPoolExecutor has `min(32, os.cpu_count() + 4)` workers
- Railway's smallest plan has 1 vCPU -- expect 5 concurrent NLP operations max
- If NLP becomes a bottleneck, consider a dedicated NLP worker process with a task queue

### Tailwind RTL Support

For Arabic layout, Tailwind's `rtl:` variant is essential:

```html
<div dir="rtl" class="text-right rtl:text-left">
  <!-- Arabic content with proper RTL layout -->
</div>
```

- Requires the `rtl:` variant which is built into Tailwind v3.3+
- Noto Naskh Arabic font: load from Google Fonts, specify in Tailwind theme extend

---

## Version Pinning Strategy

Use **compatible release** pins in `requirements.txt`:

```
# Pin to major.minor, allow patch updates
fastapi~=0.115
uvicorn[standard]~=0.30
pydantic~=2.7
asyncpg~=0.29
httpx~=0.27
stripe~=8.0
python-jose[cryptography]~=3.3
python-multipart~=0.0.9
PyMuPDF~=1.24
anthropic~=0.30

# NLP -- pin more tightly, these have model compatibility concerns
spacy~=3.7
pymorphy3~=2.0
camel-tools~=1.5

# Dev
ruff~=0.4
pytest~=8.0
pytest-asyncio~=0.23
```

For frontend, use `package.json` with caret ranges (default npm behavior):

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@supabase/supabase-js": "^2.43.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.5.0",
    "react-router-dom": "^6.20.0",
    "framer-motion": "^11.0.0",
    "recharts": "^2.12.0",
    "sonner": "^1.0.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "tailwindcss": "^3.4.0",
    "vitest": "^1.0.0",
    "@playwright/test": "^1.42.0"
  }
}
```

---

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| **supabase-py** for data queries | Wraps PostgREST (HTTP layer on top of Postgres). Adds latency. asyncpg connects directly. Use supabase-py only if you need Supabase-specific features (storage, realtime) from Python |
| **SQLAlchemy** | ORM abstraction hides the SQL you need to understand for JSONB morphology queries, array operations, and complex joins. Raw asyncpg + repository pattern is cleaner |
| **Django** | Monolithic, synchronous by default. FastAPI is async-native and better suited for an SPA backend with NLP processing |
| **Next.js** | SSR adds no value here. SRS review is entirely client-side interactive. Vite SPA is simpler, faster to build, and deploys to Vercel trivially |
| **MongoDB** | Relational data (users -> cards -> reviews -> progress) is a perfect fit for PostgreSQL. JSONB handles the semi-structured morphology data. No reason for a document store |
| **Celery** | Overkill for v1. `run_in_executor` handles NLP offloading. If you need background jobs later (bulk import processing), consider `arq` (Redis-based, async-native) over Celery |
| **Redux** | Excessive boilerplate for SRS session state. Zustand or Jotai are better fits |
| **Material UI / Chakra UI** | Component libraries add weight and fight Tailwind. Use headless components (Radix UI) if you need accessible primitives, style with Tailwind |
| **Large spaCy models** (en_core_web_md/lg) | You only need lemmatization and POS tagging. `en_core_web_sm` (12MB) handles this. The medium (40MB) and large (560MB) models add NER and word vectors you will not use |
| **NLTK** | Academic library. Slower, worse API, less maintained than spaCy for production use |

---

## Installation Commands

### Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Core
pip install fastapi uvicorn[standard] pydantic asyncpg httpx

# Auth + Payments
pip install python-jose[cryptography] python-multipart stripe

# NLP
pip install spacy pymorphy3 camel-tools
python -m spacy download en_core_web_sm
camel_data -i disambig-mle-calima-msa-r13

# File processing
pip install PyMuPDF anthropic

# Dev tools
pip install ruff pytest pytest-asyncio httpx  # httpx needed for FastAPI TestClient async
```

### Frontend

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install @supabase/supabase-js @tanstack/react-query zustand react-router-dom framer-motion recharts sonner
npm install -D tailwindcss postcss autoprefixer @playwright/test vitest @testing-library/react
npx tailwindcss init -p
```

---

## Sources and Confidence Notes

| Claim | Source | Confidence |
|-------|--------|------------|
| FastAPI >=0.115 is current | Training data (May 2025) | MEDIUM -- verify on PyPI |
| asyncpg >=0.29 is current | Training data | MEDIUM -- verify on PyPI |
| pymorphy3 >=2.0 exists and works with Python 3.11+ | Training data | MEDIUM -- pymorphy3 is a community fork, verify it's maintained |
| camel-tools >=1.5 is current | Training data | LOW -- less mainstream library, verify version and Python compatibility |
| spaCy >=3.7 is current | Training data | MEDIUM -- spaCy releases frequently, may be 3.8+ by now |
| Supabase PgBouncer on port 6543 | Training data | MEDIUM -- Supabase may have changed their pooler setup |
| Railway ~8GB image limit | Training data | LOW -- verify current Railway limits |
| camel-tools model size ~1.5GB | Training data | MEDIUM -- model sizes change between versions |
| Tailwind v4 released early 2025 | Training data | MEDIUM -- if v4 is stable, consider it; if not, stick with v3.4 |

**Action required before development:** Run `pip install <package>` for each library without version pins to determine current latest versions, then pin accordingly. Pay special attention to camel-tools and pymorphy3 as they are less mainstream and may have compatibility issues with newer Python versions.
