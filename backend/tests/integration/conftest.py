"""Integration test harness — runs against a REAL Postgres.

Set INTEGRATION_DATABASE_URL to a throwaway Postgres (local or a CI service);
the whole module skips when it's absent, so the normal unit suite is unaffected.

The session fixture wipes the schema, installs the Supabase auth shim, applies
every migration in order, and grants the `authenticated` role — i.e. it
reproduces the production schema (including RLS) on a vanilla Postgres, so the
multi-tenant isolation that unit tests can only mock is exercised for real.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
_MIGRATIONS = sorted((_REPO / "supabase" / "migrations").glob("*.sql"))
_SHIM = _HERE / "auth_shim.sql"

INTEGRATION_DSN = os.environ.get("INTEGRATION_DATABASE_URL")

requires_db = pytest.mark.skipif(
    not INTEGRATION_DSN,
    reason="set INTEGRATION_DATABASE_URL to a throwaway Postgres to run integration tests",
)

# Settings() needs these to construct; dummy values are fine for integration.
os.environ.setdefault("SUPABASE_URL", "https://test.local")
os.environ.setdefault("SUPABASE_ANON_KEY", "test")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("ENVIRONMENT", "test")
if INTEGRATION_DSN:
    os.environ.setdefault("DATABASE_URL", INTEGRATION_DSN)


def _psql(sql_file: Path) -> None:
    subprocess.run(
        ["psql", INTEGRATION_DSN, "-v", "ON_ERROR_STOP=1", "-q", "-f", str(sql_file)],
        check=True, capture_output=True, text=True,
    )


def _psql_cmd(sql: str) -> None:
    subprocess.run(
        ["psql", INTEGRATION_DSN, "-v", "ON_ERROR_STOP=1", "-q", "-c", sql],
        check=True, capture_output=True, text=True,
    )


@pytest.fixture(scope="session")
def schema():
    """Reset the DB and apply shim + all migrations once per session."""
    if not INTEGRATION_DSN:
        pytest.skip("no INTEGRATION_DATABASE_URL")
    _psql_cmd(
        "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; "
        "DROP SCHEMA IF EXISTS auth CASCADE;"
    )
    _psql(_SHIM)
    for migration in _MIGRATIONS:
        _psql(migration)
    # Supabase grants table privileges to authenticated; RLS does the gating.
    _psql_cmd(
        "GRANT USAGE ON SCHEMA public TO authenticated; "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
        "TO authenticated;"
    )
    yield


@pytest.fixture
async def pool(schema):
    """Initialize the app's asyncpg pool against the integration DB."""
    from backend.repositories import pool as pool_mod

    await pool_mod.init_pool(INTEGRATION_DSN)
    try:
        yield pool_mod
    finally:
        await pool_mod.close_pool()
