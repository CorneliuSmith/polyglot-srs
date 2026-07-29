#!/usr/bin/env bash
# Build (or repair) the app database end-to-end: migrations → offline seed →
# verification. Safe to re-run at any time — migrations are idempotent
# (IF NOT EXISTS / ON CONFLICT) and every seeder UPSERTs.
#
# Works against ANY Postgres 14+ — Supabase, RDS, Neon, Fly, a container, a
# laptop. Nothing here shells out to the `supabase` CLI: migrations are plain
# SQL applied with psql, tracked in _setup_migrations so re-runs are cheap.
# See docs/database.md for what a move off Supabase actually involves.
#
# Usage:
#   ./scripts/setup_db.sh                    # target from .env DATABASE_URL
#   ./scripts/setup_db.sh --local            # local Postgres, creates a db
#   ./scripts/setup_db.sh --schema-only      # migrations, no content seeding
#   DATABASE_URL=postgresql://… ./scripts/setup_db.sh   # explicit target
#
# Env:
#   LOCAL_DB_NAME   database name for --local (default polyglot_local)
#   LOCAL_PG_URL    server to create it on (default postgresql://localhost:5432)
#
# --local applies backend/tests/integration/auth_shim.sql, which recreates the
# bit of Supabase the migrations lean on (auth.users, auth.uid(), the
# `authenticated` role). That shim is what makes the schema portable; it is
# NOT test-only scaffolding.
#
# Sign-in is the one piece still tied to Supabase (GoTrue). A local DB gives
# you the full schema and content; keep the SUPABASE_* env vars for auth, or
# see docs/database.md for replacing it.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-.venv/bin/python}
LOCAL_DB_NAME=${LOCAL_DB_NAME:-polyglot_local}
LOCAL_PG_URL=${LOCAL_PG_URL:-postgresql://localhost:5432}
LOCAL=false
SCHEMA_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --local)       LOCAL=true ;;
    --schema-only) SCHEMA_ONLY=true ;;
    *) echo "ERROR: unknown flag $arg (--local, --schema-only)" >&2; exit 64 ;;
  esac
done

if $LOCAL; then
  if ! command -v psql >/dev/null; then
    echo "ERROR: postgres client tools not found (psql)." >&2
    echo "  macOS: brew install postgresql@16" >&2
    echo "  Debian/Ubuntu: apt install postgresql-client" >&2
    exit 1
  fi
  # createdb via psql rather than the createdb binary: works the same whether
  # the server is local, in Docker, or on another host in LOCAL_PG_URL.
  if psql "$LOCAL_PG_URL/postgres" -tAc \
       "SELECT 1 FROM pg_database WHERE datname = '$LOCAL_DB_NAME'" | grep -q 1; then
    echo "==> Database $LOCAL_DB_NAME already exists"
  else
    psql "$LOCAL_PG_URL/postgres" -q -c "CREATE DATABASE $LOCAL_DB_NAME"
    echo "==> Created database $LOCAL_DB_NAME"
  fi
  export DATABASE_URL="$LOCAL_PG_URL/$LOCAL_DB_NAME"
elif [[ -z "${DATABASE_URL:-}" ]]; then
  if [[ -f .env ]]; then
    set -a; source .env; set +a
  fi
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL not set (no .env found?). Pass it or use --local." >&2
  exit 1
fi

echo "==> Target: $(sed 's|//[^@]*@|//***@|' <<<"$DATABASE_URL")"

# --- 1. Auth shim (any Postgres that isn't already Supabase) ---------------
# Detected, not assumed: --local is not the only non-Supabase target. Anyone
# pointing this at RDS/Neon/a container needs the shim just as much, and on
# real Supabase auth.uid() already exists so this is a no-op.
if psql "$DATABASE_URL" -tAc \
     "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname = 'auth' AND p.proname = 'uid'" | grep -q 1; then
  echo "==> auth.uid() present — skipping shim"
else
  echo "==> Applying auth compatibility shim (auth.users, auth.uid(), roles)"
  psql "$DATABASE_URL" -q -v ON_ERROR_STOP=1 -f backend/tests/integration/auth_shim.sql
fi

# --- 2. Migrations, in filename (= chronological) order --------------------
# A tracking table makes re-runs skip what's already applied. On a database
# that predates the tracking table (e.g. one migrated by hand), a migration
# whose objects already exist rolls back cleanly (--single-transaction) and is
# recorded as baselined instead of failing the run.
echo "==> Applying migrations"
psql "$DATABASE_URL" -q -v ON_ERROR_STOP=1 -c \
  "CREATE TABLE IF NOT EXISTS _setup_migrations (
     filename   TEXT PRIMARY KEY,
     applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );
   ALTER TABLE _setup_migrations ENABLE ROW LEVEL SECURITY"

for f in supabase/migrations/*.sql; do
  base=$(basename "$f")
  done_already=$(psql "$DATABASE_URL" -tAc \
    "SELECT 1 FROM _setup_migrations WHERE filename = '$base'")
  if [[ "$done_already" == "1" ]]; then
    echo "    skip    $base (recorded)"
    continue
  fi
  if err=$(psql "$DATABASE_URL" -q -v ON_ERROR_STOP=1 --single-transaction -f "$f" 2>&1 >/dev/null); then
    echo "    applied $base"
  elif grep -qiE "already exists|duplicate" <<<"$err"; then
    echo "    skip    $base (objects already exist — baselined)"
  else
    echo "ERROR applying $base:" >&2
    echo "$err" >&2
    exit 1
  fi
  psql "$DATABASE_URL" -q -v ON_ERROR_STOP=1 -c \
    "INSERT INTO _setup_migrations (filename) VALUES ('$base') ON CONFLICT DO NOTHING"
done

if $SCHEMA_ONLY; then
  echo "==> --schema-only: migrations applied, skipping content seed."
  exit 0
fi

# --- 3. Offline seed (no API key / internet needed) -------------------------
# Per-language vocab failures warn and continue: a missing optional dependency
# (e.g. nltk for English) shouldn't kill the whole rebuild.

# English enrichment wants spaCy's small model; without it seeding still works
# (WordNet-only POS) but logs a warning. Fetch it once if we're online.
if ! $PYTHON -c "import spacy; spacy.load('en_core_web_sm')" >/dev/null 2>&1; then
  echo "==> spaCy model en_core_web_sm missing — attempting one-time download"
  $PYTHON -m spacy download en_core_web_sm >/dev/null 2>&1 \
    || echo "    WARN: download failed (offline?) — English seeds with WordNet-only POS"
fi

# Languages come from what's on disk, not a hand-kept list — the previous
# literal had gone stale and silently skipped the five newest languages.
VOCAB_LANGS=$(ls data/*_frequency.tsv 2>/dev/null \
  | sed 's|data/||; s|_frequency.tsv||' | tr '\n' ' ')
echo "==> Seeding vocabulary [$VOCAB_LANGS]"
for L in $VOCAB_LANGS; do
  $PYTHON -m backend.services.seeder.run --language "$L" \
    || echo "    WARN: $L vocab seeding failed (continuing)"
done
$PYTHON -m backend.services.seeder.run --file data/ru_starter.tsv --language ru \
  || echo "    WARN: ru starter vocab failed (continuing)"

echo "==> Seeding grammar paths"
$PYTHON -m backend.services.seeder.seed_grammar --language all

SENTENCE_LANGS=$(ls data/sentences/*_sentences.tsv 2>/dev/null \
  | sed 's|data/sentences/||; s|_sentences.tsv||' | tr '\n' ' ')
echo "==> Seeding example sentences [$SENTENCE_LANGS]"
for L in $SENTENCE_LANGS; do
  $PYTHON -m backend.services.seeder.seed_sentences --language "$L" \
    || echo "    WARN: $L sentences failed (continuing)"
done

# --- 4. Verify ---------------------------------------------------------------
echo "==> Verifying"
psql "$DATABASE_URL" -tA -v ON_ERROR_STOP=1 <<'SQL'
SELECT 'vocabulary:        ' || COUNT(*) FROM vocabulary;
SELECT 'grammar_points:    ' || COUNT(*) FROM grammar_points;
SELECT 'drill_sentences:   ' || COUNT(*) FROM drill_sentences;
SELECT 'example_sentences: ' || COUNT(*) FROM example_sentences;
SELECT 'content_lists:     ' || COUNT(*) FROM content_lists;
SQL

LISTS=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM content_lists")
if [[ "$LISTS" -eq 0 ]]; then
  echo "ERROR: content_lists is empty — onboarding/Learn will have nothing." >&2
  exit 1
fi

# Seeded is not the same as VISIBLE. Under an 'ai_ok' publish policy a point
# also needs an AI-check verdict before a learner sees it, and nothing in the
# seed pipeline sets one — a language could look perfectly seeded here and
# still render an empty grammar path. Say so rather than let it be found in
# the app.
HIDDEN=$(psql "$DATABASE_URL" -tAc "
  SELECT COALESCE(string_agg(code || ' (' || n || ')', ', ' ORDER BY code), '')
  FROM (
    SELECT l.code, count(*) AS n
    FROM grammar_points gp JOIN languages l ON l.id = gp.language_id
    WHERE l.grammar_review_policy = 'ai_ok'
      AND gp.reviewed = false
      AND gp.ai_check_status IS DISTINCT FROM 'pass'
    GROUP BY l.code
  ) t")
if [[ -n "$HIDDEN" ]]; then
  echo
  echo "NOTE: grammar points seeded but NOT yet visible to learners:"
  echo "        $HIDDEN"
  echo "      They need an AI-check verdict as well as the 'ai_ok' policy:"
  echo "        python -m backend.services.seeder.generate_grammar --language <code> --ai-check"
  echo "      (or the 'Check all now' button in Account -> Admin)"
fi

echo "==> Done. Restart the backend if it was running."
