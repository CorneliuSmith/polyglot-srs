#!/usr/bin/env bash
# Bootstrap (or add) an admin: grants the global 'admin' role to an account
# by email. This is the only role that can't be granted from inside the app
# the first time — every later grant can go through the Contributor page.
#
# Usage:
#   DATABASE_URL=postgres://... ./scripts/grant_admin.sh you@example.com
#   ./scripts/grant_admin.sh you@example.com          # DATABASE_URL from env/.env
#
# The account must exist first (sign up in the app, confirm the email).
set -euo pipefail

EMAIL="${1:?usage: grant_admin.sh <account-email>}"

if [[ -z "${DATABASE_URL:-}" && -f .env ]]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi
: "${DATABASE_URL:?DATABASE_URL not set (pass it or put it in .env)}"

RESULT=$(psql "$DATABASE_URL" -tA -v ON_ERROR_STOP=1 <<SQL
WITH target AS (
    SELECT id FROM auth.users WHERE lower(email) = lower('${EMAIL}')
), grant_row AS (
    INSERT INTO contributor_roles (user_id, language_id, role)
    SELECT id, NULL, 'admin' FROM target
    ON CONFLICT (user_id, language_id, role) DO NOTHING
    RETURNING user_id
)
SELECT
  CASE
    WHEN NOT EXISTS (SELECT 1 FROM target) THEN 'NO_ACCOUNT'
    WHEN EXISTS (SELECT 1 FROM grant_row) THEN 'GRANTED'
    ELSE 'ALREADY_ADMIN'
  END;
SQL
)

case "$RESULT" in
  GRANTED)       echo "OK: ${EMAIL} is now an admin." ;;
  ALREADY_ADMIN) echo "OK: ${EMAIL} was already an admin." ;;
  NO_ACCOUNT)    echo "ERROR: no account with email ${EMAIL} — sign up in the app first." >&2; exit 1 ;;
  *)             echo "Unexpected result: ${RESULT}" >&2; exit 1 ;;
esac
