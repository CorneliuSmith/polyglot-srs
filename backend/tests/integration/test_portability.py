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

import os
import re
import subprocess
import tempfile
import uuid
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


# ── data portability: dump → restore onto a virgin database ────────────────
# The schema tests above prove the STRUCTURE is portable. These prove the DATA
# is: that `backup_db.sh --portable` produces something `restore_db.sh` can
# land on a Postgres that has never seen Supabase, with learner rows and their
# foreign keys intact. Written after a manual round-trip found two real bugs
# (a DROP SCHEMA public that failed on a pgcrypto dependency, and a colliding
# CREATE SCHEMA public) — neither visible by reading the scripts.

REPO = Path(__file__).resolve().parents[3]
_DSN = os.environ.get("INTEGRATION_DATABASE_URL", "")


def _admin_dsn(dbname: str) -> str:
    """The integration DSN pointed at a different database on the same server."""
    return _DSN.rsplit("/", 1)[0] + "/" + dbname


def _psql(dsn: str, sql: str) -> str:
    out = subprocess.run(
        ["psql", dsn, "-tAc", sql],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


@pytest.fixture()
def scratch_dbs():
    """Two throwaway databases, dropped afterwards whatever happens."""
    suffix = uuid.uuid4().hex[:8]
    src, dst = f"pt_src_{suffix}", f"pt_dst_{suffix}"
    admin = _admin_dsn("postgres")
    _psql(admin, f"CREATE DATABASE {src}")
    try:
        yield _admin_dsn(src), _admin_dsn(dst), dst
    finally:
        for name in (src, dst):
            subprocess.run(
                ["psql", admin, "-q", "-c", f"DROP DATABASE IF EXISTS {name}"],
                capture_output=True, text=True,
            )


@pytest.mark.skipif(not _DSN, reason="needs INTEGRATION_DATABASE_URL")
def test_a_portable_dump_restores_onto_a_database_that_never_had_supabase(
    scratch_dbs,
):
    src_dsn, dst_dsn, _ = scratch_dbs
    env = {**os.environ, "DATABASE_URL": src_dsn}

    # Build the source: schema only (fast — content isn't what's under test).
    subprocess.run(
        ["./scripts/setup_db.sh", "--schema-only"],
        cwd=REPO, env=env, capture_output=True, text=True, check=True,
    )

    # A learner with a card and a review — the rows whose foreign keys to
    # auth.users are exactly what a naive public-only dump breaks.
    user_id = str(uuid.uuid4())
    _psql(src_dsn, f"""
        INSERT INTO auth.users (id, email) VALUES ('{user_id}', 'rt@example.com');
        INSERT INTO user_profiles (id, batch_size) VALUES ('{user_id}', 9);
        INSERT INTO vocabulary (language_id, word)
          SELECT id, 'roundtrip' FROM languages WHERE code = 'es';
        INSERT INTO user_cards (user_id, language_id, card_type, card_id, repetitions)
          SELECT '{user_id}', v.language_id, 'vocabulary', v.id, 4
          FROM vocabulary v WHERE v.word = 'roundtrip';
    """)

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["./scripts/backup_db.sh", "--portable", "--no-gzip", "-o", tmp],
            cwd=REPO, env=env, capture_output=True, text=True, check=True,
        )
        dumps = list(Path(tmp).glob("polyglot-*.sql"))
        assert len(dumps) == 1, f"expected one dump, got {dumps}"

        restore = subprocess.run(
            ["./scripts/restore_db.sh", str(dumps[0]),
             "--into", dst_dsn, "--create"],
            cwd=REPO, capture_output=True, text=True,
        )
    assert restore.returncode == 0, (
        f"restore failed:\n{restore.stdout[-3000:]}\n{restore.stderr[-3000:]}"
    )

    # The data actually arrived, and the FK survived.
    assert _psql(dst_dsn, "SELECT count(*) FROM auth.users") == "1"
    assert _psql(dst_dsn, f"SELECT batch_size FROM user_profiles WHERE id='{user_id}'") == "9"
    assert _psql(dst_dsn, "SELECT repetitions FROM user_cards") == "4"
    assert _psql(
        dst_dsn,
        "SELECT count(*) FROM user_cards uc WHERE NOT EXISTS "
        "(SELECT 1 FROM auth.users u WHERE u.id = uc.user_id)",
    ) == "0", "restored cards point at a missing user — dump ordering is wrong"
    # And the restored database is a working one, not just rows in tables.
    assert int(_psql(dst_dsn, "SELECT count(*) FROM pg_policies")) > 50
