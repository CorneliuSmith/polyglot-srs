# PolyglotSRS

A spaced-repetition language-learning platform with language-aware answer
validation and AI tutors — Bunpro-style grammar + vocabulary review, extended
to many languages and a paid AI coaching layer.

**Languages (14):** Russian, Arabic, English, Turkish, Swahili, Yoruba, Hausa,
Xhosa, Spanish, Italian, French, German, Catalan, Māori.

## What's here

- **SRS review** — type-the-answer drills graded per language by a dedicated
  NLP backend (morphology-aware; diacritics coach rather than fail). SM-2
  scheduling.
- **Grammar** — grammar points with explanations, culture notes, references,
  and fill-in-the-blank drills. An optional "Show grammar" panel in review.
- **AI tutors** — per-language tutoring agents (Claude API) grounded in the
  learner's SRS failure data + durable cross-session memory.
- **Content pipeline** — seed vocabulary/grammar from open data; AI-generate
  grammar with NLP-validated drills; a contributor/admin authoring + review
  workflow (AI semantic check + required human linguist sign-off, gated by a
  per-language policy).
- **Student feedback** on cards → contributor triage queue.

## Stack

FastAPI + asyncpg + Supabase (Postgres, Auth, RLS) backend; Vite + React +
TypeScript + Zustand frontend; Claude API for tutoring and content generation.

## Run

```bash
# Backend (needs a .env — see .env.example)
pip install -e ".[dev]"
uvicorn backend.main:create_app --factory --reload

# Frontend
cd frontend && npm install && npm run dev
```

`TUTOR_DEV_MOCK=true` exercises the tutor and content generation with no API
key (canned responses). See `.env.example`.

## Tests

```bash
ruff check backend
python -m pytest backend/tests -q          # ~500 unit tests
cd frontend && npx tsc -b && npx vitest run # ~95 tests
```

Real-Postgres **integration / RLS** tests (tenant isolation, migrations,
repository SQL) run when a throwaway database is provided:

```bash
export INTEGRATION_DATABASE_URL="postgresql://user:pass@localhost:5432/polyglot_test"
python -m pytest backend/tests/integration -q
```

CI (`.github/workflows/ci.yml`) runs all of the above on every push, with a
Postgres service for the integration tests.

## Content & data

Seeding is documented in [`data/README.md`](data/README.md) (sources,
licensing, the `scripts/refresh_seed_data.sh` pipeline, AI generation, and the
contributor workflow). Nothing is pre-seeded — the schema and pipeline are in
place; run the seeders/generators against your database to populate content.

## Scheduling

Reviews are scheduled with FSRS-5 (stability + difficulty per card). The
scheduler uses per-language weights fit from pooled review history, falling
back to built-in defaults, with an optional per-user-per-language override.
Refresh the fitted weights periodically (e.g. nightly cron) once enough
reviews have accumulated:

    python -m backend.jobs.fit_fsrs_weights --db-url "$DATABASE_URL"

## Billing (tutor add-on)

The AI tutor is gated by `tutor_entitlements`, driven by Stripe. Set
`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and `STRIPE_PRICE_ID`, point a
Stripe webhook at `POST /api/billing/webhook`, and set `TUTOR_FREE_ACCESS=false`
so entitlements actually govern access. A completed checkout grants the
(user, language) entitlement; a canceled/unpaid subscription revokes it. For
local testing without Stripe, set `STRIPE_DEV_MOCK=true` — the subscribe button
then grants access directly so you can exercise the gated → unlocked flow.

## Docs

- [`data/README.md`](data/README.md) — data sourcing, licensing, grammar pipeline
- [`docs/claude-db-access.md`](docs/claude-db-access.md) — giving this environment DB access (staging only)
