#!/usr/bin/env bash
# Restore a --portable backup onto ANY Postgres 14+ — Supabase, RDS, Neon,
# Fly, a container, a laptop.
#
# This is the other half of `backup_db.sh --portable`. A portable dump carries
# auth.users ROWS but not GoTrue's schema, so the target needs the auth shim
# in place before the rows can land; that is the one step people get wrong,
# so this script does it for them.
#
# Usage:
#   ./scripts/restore_db.sh backups/polyglot-20260729-221521.sql.gz
#   ./scripts/restore_db.sh dump.sql --into postgresql://localhost:5432/newdb
#   ./scripts/restore_db.sh dump.sql --create   # create the database first
#
# Reads .gz or plain .sql. Target comes from --into, else DATABASE_URL, else
# .env — the same resolution order as the other scripts.
#
# NOT idempotent, deliberately: it restores into an EMPTY database. Pointed at
# one that already holds data you would get primary-key conflicts on
# auth.users, which is a confusing half-restore. Use --create, or drop and
# recreate the target yourself.
set -euo pipefail
cd "$(dirname "$0")/.."

DUMP=""
INTO=""
CREATE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --into)    INTO="$2"; shift 2 ;;
    --create)  CREATE=true; shift ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    -*)        echo "Unknown option: $1" >&2; exit 2 ;;
    *)         DUMP="$1"; shift ;;
  esac
done

if [[ -z "$DUMP" ]]; then
  echo "ERROR: no dump file given. Usage: $0 <dump.sql[.gz]> [--into URL]" >&2
  exit 64
fi
if [[ ! -f "$DUMP" ]]; then
  echo "ERROR: no such file: $DUMP" >&2
  exit 66
fi
if ! command -v psql >/dev/null; then
  echo "ERROR: psql not found (install the postgres client tools)." >&2
  exit 1
fi

if [[ -n "$INTO" ]]; then
  TARGET="$INTO"
else
  if [[ -z "${DATABASE_URL:-}" && -f .env ]]; then
    set -a; source .env; set +a
  fi
  TARGET="${DATABASE_URL:-}"
fi
if [[ -z "$TARGET" ]]; then
  echo "ERROR: no target. Pass --into URL or set DATABASE_URL." >&2
  exit 78
fi

echo "==> Dump:   $DUMP"
echo "==> Target: $(sed 's|//[^@]*@|//***@|' <<<"$TARGET")"

# --create: split "postgres://host:port/dbname" so we can CREATE DATABASE from
# the server's default database first.
if $CREATE; then
  DBNAME="${TARGET##*/}"
  DBNAME="${DBNAME%%\?*}"
  SERVER="${TARGET%/*}"
  if psql "$SERVER/postgres" -tAc \
       "SELECT 1 FROM pg_database WHERE datname = '$DBNAME'" | grep -q 1; then
    echo "==> Database $DBNAME already exists"
  else
    psql "$SERVER/postgres" -q -c "CREATE DATABASE \"$DBNAME\""
    echo "==> Created database $DBNAME"
  fi
fi

# The shim, unless the target already provides auth.uid() (i.e. is Supabase).
# A portable dump's very first COPY writes auth.users, so the table has to be
# there or the restore dies on line one.
if psql "$TARGET" -tAc \
     "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname = 'auth' AND p.proname = 'uid'" | grep -q 1; then
  echo "==> auth.uid() present — skipping shim"
else
  echo "==> Applying auth compatibility shim"
  psql "$TARGET" -q -v ON_ERROR_STOP=1 -f backend/tests/integration/auth_shim.sql
fi

# The dump recreates `public` wholesale, so clear it first — otherwise its
# CREATE SCHEMA collides with the one every Postgres ships with. Safe because
# the shim keeps pgcrypto in `extensions`, so nothing we need lives in public.
echo "==> Clearing target public schema"
psql "$TARGET" -q -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS public CASCADE"

echo "==> Restoring"
# ON_ERROR_STOP so a broken restore fails loudly instead of leaving a database
# that is silently missing half its rows.
if [[ "$DUMP" == *.gz ]]; then
  gunzip -c "$DUMP" | psql "$TARGET" -q -v ON_ERROR_STOP=1
else
  psql "$TARGET" -q -v ON_ERROR_STOP=1 -f "$DUMP"
fi

echo "==> Verifying"
psql "$TARGET" -tA -v ON_ERROR_STOP=1 <<'SQL'
SELECT 'auth.users:        ' || COUNT(*) FROM auth.users;
SELECT 'user_profiles:     ' || COUNT(*) FROM user_profiles;
SELECT 'user_cards:        ' || COUNT(*) FROM user_cards;
SELECT 'review_log:        ' || COUNT(*) FROM review_log;
SELECT 'languages:         ' || COUNT(*) FROM languages;
SELECT 'vocabulary:        ' || COUNT(*) FROM vocabulary;
SELECT 'grammar_points:    ' || COUNT(*) FROM grammar_points;
SQL

# An orphaned card means a user row failed to load — the exact failure the
# ordering in --portable exists to prevent, so check rather than assume.
ORPHANS=$(psql "$TARGET" -tAc "
  SELECT count(*) FROM user_cards uc
  WHERE NOT EXISTS (SELECT 1 FROM auth.users u WHERE u.id = uc.user_id)")
if [[ "$ORPHANS" != "0" ]]; then
  echo "ERROR: $ORPHANS user_cards rows reference a missing auth.users row." >&2
  echo "       The dump was probably scoped to public only." >&2
  exit 1
fi

echo "==> Done. Point DATABASE_URL at this database and restart the backend."
