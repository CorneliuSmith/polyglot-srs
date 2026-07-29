"""The schema must build on plain Postgres, not just on Supabase.

Owner: "make sure db is easily migratable... I don't want to be stuck with
supabase." Portability that isn't tested is portability you find out you
don't have on the day you need it. These run against the integration
database, which is vanilla Postgres + auth_shim.sql — so if they pass, the
schema demonstrably stands up without Supabase.

What they guard is narrow and deliberate: the migrations must not reach for
anything only Supabase provides. They say nothing about GoTrue sign-in,
which is a separate (and still Supabase-coupled) concern documented in
docs/database.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.services.schema_check import find_schema_drift

from .conftest import requires_db

pytestmark = requires_db

MIGRATIONS = sorted(
    (Path(__file__).resolve().parents[3] / "supabase" / "migrations").glob("*.sql")
)

# Schemas that exist ONLY on Supabase. `auth` is the deliberate exception —
# auth_shim.sql recreates it, which is what makes the rest portable.
_SUPABASE_ONLY = re.compile(
    r"\b(storage|realtime|supabase_functions|vault|graphql|graphql_public)\s*\.",
    re.IGNORECASE,
)
# pgcrypto lives in `extensions` on Supabase and `public` everywhere else, so
# a hard-coded `extensions.` prefix does not resolve off-platform.
_EXTENSIONS_SCHEMA = re.compile(r"\bextensions\s*\.", re.IGNORECASE)


def test_there_are_migrations_to_check():
    # A glob that silently matches nothing would make every test below pass
    # while proving nothing at all.
    assert len(MIGRATIONS) > 30


def test_no_migration_uses_a_supabase_only_schema():
    offenders = [
        f"{m.name}: {_SUPABASE_ONLY.search(m.read_text()).group(0)}"
        for m in MIGRATIONS
        if _SUPABASE_ONLY.search(m.read_text())
    ]
    assert not offenders, (
        "These migrations reference a Supabase-only schema and will not apply "
        f"to plain Postgres: {offenders}"
    )


def test_no_migration_hard_codes_the_extensions_schema():
    offenders = [m.name for m in MIGRATIONS if _EXTENSIONS_SCHEMA.search(m.read_text())]
    assert not offenders, (
        "`extensions.` resolves on Supabase but not on a stock Postgres where "
        f"pgcrypto installs into public: {offenders}"
    )


@pytest.mark.asyncio
async def test_the_whole_schema_applies_to_plain_postgres(pool):
    """The integration database is vanilla Postgres + the auth shim. If the
    expected objects are all present there, the schema is portable."""
    async with pool.privileged_connection() as conn:
        drift = await find_schema_drift(conn)
    assert drift["initialized"], "migrations did not apply to plain Postgres"
    assert drift["ok"], f"missing on plain Postgres: {drift['missing'][:10]}"


@pytest.mark.asyncio
async def test_row_level_security_is_actually_enforced_here(pool):
    """RLS is the security model, and it depends on auth.uid(). If the shim
    ever stopped resolving, policies would silently pass everything — so
    assert the enforcement, not merely that the policies exist."""
    async with pool.privileged_connection() as conn:
        policies = await conn.fetchval("SELECT count(*) FROM pg_policies")
        assert policies > 50, f"only {policies} RLS policies present"

        # auth.uid() must exist and read the JWT claim the app sets.
        uid = await conn.fetchval("SELECT auth.uid()")
        assert uid is None, "auth.uid() should be NULL with no claims set"

    user_id = "11111111-1111-1111-1111-111111111111"
    async with pool.rls_connection(user_id) as conn:
        seen = await conn.fetchval("SELECT auth.uid()")
    assert str(seen) == user_id, (
        "auth.uid() did not reflect the connection's JWT claims — RLS would "
        "not isolate users on this database"
    )
