#!/usr/bin/env bash
# Build (or repair) the app database end-to-end: migrations → offline seed →
# verification. Safe to re-run at any time — migrations are idempotent
# (IF NOT EXISTS / ON CONFLICT) and every seeder UPSERTs.
#
# Usage:
#   ./scripts/setup_db.sh                    # hosted DB from .env DATABASE_URL
#   ./scripts/setup_db.sh --local            # local Postgres on localhost:5432
#                                            #   (creates db 'polyglot_local',
#                                            #    applies the Supabase auth shim)
#   DATABASE_URL=postgresql://… ./scripts/setup_db.sh   # explicit target
#
# Local mode gives you a full schema + content database for development.
# Note: app sign-in still authenticates against Supabase (the shim only
# provides auth.uid()/roles so migrations and RLS apply) — point the
# backend's DATABASE_URL at the local db but keep the SUPABASE_* env vars.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-.venv/bin/python}
LOCAL_DB_NAME=${LOCAL_DB_NAME:-polyglot_local}
LOCAL=false

if [[ "${1:-}" == "--local" ]]; then
  LOCAL=true
  if ! command -v createdb >/dev/null; then
    echo "ERROR: postgres client tools not found (brew install postgresql@16)" >&2
    exit 1
  fi
  createdb "$LOCAL_DB_NAME" 2>/dev/null && echo "==> Created database $LOCAL_DB_NAME" \
    || echo "==> Database $LOCAL_DB_NAME already exists"
  export DATABASE_URL="postgresql://localhost:5432/$LOCAL_DB_NAME"
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

# --- 1. Supabase auth shim (local Postgres only) ---------------------------
if $LOCAL; then
  echo "==> Applying Supabase auth shim (local Postgres)"
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

echo "==> Seeding vocabulary"
for L in sw tr ar en es fr de it ca mi yo ha xh ro el; do
  $PYTHON -m backend.services.seeder.run --language "$L" \
    || echo "    WARN: $L vocab seeding failed (continuing)"
done
$PYTHON -m backend.services.seeder.run --file data/ru_starter.tsv --language ru \
  || echo "    WARN: ru starter vocab failed (continuing)"

echo "==> Seeding grammar paths"
$PYTHON -m backend.services.seeder.seed_grammar --language all

echo "==> Seeding example sentences"
for L in es fr de it ca mi yo ha xh tr ru sw ro el; do
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
echo "==> Done. Restart the backend if it was running."
