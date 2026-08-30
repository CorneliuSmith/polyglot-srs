#!/usr/bin/env bash
# Snapshot the app database to a timestamped SQL file with pg_dump — a manual
# backup you can take before a risky change or keep as an off-Supabase copy.
#
# This complements, it does not replace, Supabase's automated backups / PITR
# (those are your real disaster recovery for user data). And it's separate from
# scripts/setup_db.sh, which rebuilds the SCHEMA + seeded CONTENT from source —
# this one captures the LIVE DATA (accounts, cards, progress, …) that source
# can't reproduce.
#
# Usage:
#   ./scripts/backup_db.sh                     # full dump from .env DATABASE_URL
#   DATABASE_URL=postgresql://… ./scripts/backup_db.sh
#   ./scripts/backup_db.sh --portable          # VENDOR-NEUTRAL (see below)
#   ./scripts/backup_db.sh --schema-only       # structure only (no rows)
#   ./scripts/backup_db.sh --data-only         # rows only (no structure)
#   ./scripts/backup_db.sh -o /path/to/dir     # write to a different directory
#   ./scripts/backup_db.sh --no-gzip           # keep the plain .sql (default gzips)
#
# Restore a full/plain dump with:
#   gunzip -c backups/polyglot-YYYYMMDD-HHMMSS.sql.gz | psql "$DATABASE_URL"
# (or, uncompressed:  psql "$DATABASE_URL" -f backups/polyglot-….sql)
#
# --portable is the one to use if you might ever leave Supabase.
#
# A plain full dump of a Supabase database also contains Supabase's own
# schemas — storage, realtime, vault, graphql, extensions, supabase_functions —
# and all ~15 of GoTrue's auth tables. None of that restores onto a stock
# Postgres, so the "backup" only restores to another Supabase. Scoping to
# `public` instead loses auth.users, and then every foreign key to it fails.
#
# --portable dumps exactly what this app owns: all of `public`, plus the
# auth.users ROWS (not GoTrue's other tables), ordered so the users load
# first and the foreign keys resolve. Restore it with scripts/restore_db.sh
# onto any Postgres 14+. Round-tripped in CI, not just asserted.
#
# Note: for Supabase, use the DIRECT connection string (port 5432), not the
# pooler (6543) — pg_dump needs a session connection.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="backups"
GZIP=true
PORTABLE=false
SCOPE_FLAGS=()   # --schema-only / --data-only pass straight to pg_dump

while [[ $# -gt 0 ]]; do
  case "$1" in
    --portable)    PORTABLE=true; shift ;;
    --schema-only) SCOPE_FLAGS+=("--schema-only"); shift ;;
    --data-only)   SCOPE_FLAGS+=("--data-only");   shift ;;
    --no-gzip)     GZIP=false; shift ;;
    -o|--out)      OUT_DIR="$2"; shift 2 ;;
    -h|--help)     sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

if ! command -v pg_dump >/dev/null; then
  echo "ERROR: pg_dump not found (install the postgres client tools)." >&2
  exit 1
fi

# Resolve DATABASE_URL from the env or .env, same as setup_db.sh.
if [[ -z "${DATABASE_URL:-}" && -f .env ]]; then
  set -a; source .env; set +a
fi
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL not set (no .env found?). Pass it in the env." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
STAMP=$(date -u +%Y%m%d-%H%M%S)
FILE="$OUT_DIR/polyglot-$STAMP.sql"

echo "==> Target:  $(sed 's|//[^@]*@|//***@|' <<<"$DATABASE_URL")"
echo "==> Writing: $FILE$($GZIP && echo .gz)"

# --no-owner / --no-privileges keep the dump portable across roles (Supabase's
# service role differs from a local postgres user); --if-exists + --clean make
# a restore re-runnable. Scope flags (if any) restrict to schema or data.
DUMP_ARGS=(
  "$DATABASE_URL"
  --no-owner --no-privileges
  --clean --if-exists
  ${SCOPE_FLAGS[@]+"${SCOPE_FLAGS[@]}"}
)

# Emit the dump on stdout so the gzip/plain branch below stays one code path.
emit_dump() {
  if $PORTABLE; then
    # auth.users ROWS first: public's foreign keys point at them, so they have
    # to exist before public's data lands. --data-only because the table
    # itself comes from auth_shim.sql on the target (or already exists on
    # Supabase) — we are deliberately NOT shipping GoTrue's schema.
    echo "-- polyglot portable dump: auth.users rows + all of public."
    echo "-- Restore with scripts/restore_db.sh (applies the shim first)."
    pg_dump "$DATABASE_URL" --no-owner --no-privileges \
      --data-only --table=auth.users
    # All of public, schema + data — deliberately WITHOUT --clean. A portable
    # dump restores into an empty database, so there is nothing to drop, and
    # `--clean` emits DROP SCHEMA public, which FAILS once the auth shim has
    # installed pgcrypto into public. Found by round-tripping this, not by
    # reading it.
    pg_dump "$DATABASE_URL" --no-owner --no-privileges \
      ${SCOPE_FLAGS[@]+"${SCOPE_FLAGS[@]}"} --schema=public
  else
    pg_dump "${DUMP_ARGS[@]}"
  fi
}

if $GZIP; then
  emit_dump | gzip > "$FILE.gz"
  FINAL="$FILE.gz"
else
  emit_dump > "$FILE"
  FINAL="$FILE"
fi

SIZE=$(du -h "$FINAL" | cut -f1)
echo "==> Done. $FINAL ($SIZE)"
