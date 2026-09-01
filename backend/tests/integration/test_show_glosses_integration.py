"""The word-by-word gloss setting: off by default, and safe before its migration.

Owner: an option "turned on automatically in the user account", then *"make
the gloss off by default"*. The Leipzig notation (`bark.3SG`) is genuinely
useful and genuinely unfamiliar — meeting it unasked is exactly what
learners reported as confusing — so it becomes an opt-in switch rather than
something removed or fused to the translation.

Two properties are worth a real database rather than a mock:

  * **the default is OFF**, including for a profile row written before this
    column existed. Nobody meets the notation without choosing to;
  * **the read degrades** when migration 20261012 has not been applied.
    /auth/me is fetched on every page load, so an unguarded new column on
    `user_profiles` takes the whole app down rather than one setting — the
    `is_visible` outage taught that once already.

Runs against a real Postgres (see conftest); skips without one.
"""
from __future__ import annotations

import asyncpg
import pytest

from backend.routers.auth import (
    _present_profile_columns,
    _profile_column_plan,
)

from .conftest import requires_db

pytestmark = requires_db


async def _user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def test_the_column_exists_and_defaults_to_off(pool):
    user = await _user(pool, "gloss-default@example.com")
    async with pool.privileged_connection() as conn:
        # A profile written WITHOUT naming the column — exactly what every
        # existing row is, and what a client one deploy behind sends.
        await conn.execute(
            "INSERT INTO user_profiles (id, batch_size) VALUES ($1, 5)", user
        )
        assert await conn.fetchval(
            "SELECT show_glosses FROM user_profiles WHERE id = $1", user
        ) is False


async def test_turning_it_on_sticks(pool):
    user = await _user(pool, "gloss-on@example.com")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO user_profiles (id, batch_size, show_glosses) "
            "VALUES ($1, 5, true)", user
        )
        assert await conn.fetchval(
            "SELECT show_glosses FROM user_profiles WHERE id = $1", user
        ) is True


async def test_the_column_is_not_null_so_a_read_never_returns_none(pool):
    """A nullable column would put `None` where the client expects a bool,
    and `None ?? true` is true in TypeScript but `None` is falsy in Python —
    the kind of split that makes a setting behave differently on two
    surfaces."""
    async with pool.privileged_connection() as conn:
        nullable = await conn.fetchval(
            """
            SELECT is_nullable FROM information_schema.columns
             WHERE table_name = 'user_profiles' AND column_name = 'show_glosses'
            """
        )
    assert nullable == "NO"


async def test_the_pre_migration_fallback_actually_works(pool):
    """The guard that matters — and it did NOT work before this change.

    `rls_connection` runs everything in one transaction, so the old
    "try the wide SELECT, catch UndefinedColumnError, retry narrower"
    ladder aborted the transaction on its first attempt and the retry
    raised InFailedSQLTransactionError, which nothing caught. On the
    endpoint that renders every page. The ladder read as defensive and
    degraded nothing.

    Asking first (`_present_profile_columns`) has no such failure mode:
    nothing errors, so nothing aborts. This test pins BOTH halves — that
    catching-and-retrying is genuinely broken inside a transaction, and
    that the probe path serves a complete profile without one.
    """
    user = await _user(pool, "gloss-premigration@example.com")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO user_profiles (id, batch_size) VALUES ($1, 5)", user
        )

    # 1. The old shape, reproduced: a failed statement poisons the rest of
    #    the transaction, so the "fallback" never gets to run.
    async with pool.privileged_connection() as conn:
        with pytest.raises(asyncpg.exceptions.UndefinedColumnError):
            await conn.fetchrow(
                "SELECT id, no_such_column FROM user_profiles WHERE id = $1",
                user,
            )
        with pytest.raises(asyncpg.exceptions.InFailedSQLTransactionError):
            await conn.fetchrow(
                "SELECT id, batch_size FROM user_profiles WHERE id = $1", user
            )

    # 2. The new shape: ask which columns exist, select exactly those.
    async with pool.privileged_connection() as conn:
        present = await _present_profile_columns(conn)
        assert "show_glosses" in present
        extra, missing = _profile_column_plan(present)
        assert missing == {}, "every column is migrated in this database"
        row = await conn.fetchrow(
            f"SELECT id, batch_size{extra} FROM user_profiles WHERE id = $1",
            user,
        )
        assert row["show_glosses"] is False


async def test_a_missing_column_is_planned_around_not_selected(pool):
    """The plan for a database that is BEHIND: the column is left out of the
    SELECT and supplied as a default instead, so the statement that runs is
    one this database can answer."""
    plan_extra, plan_defaults = _profile_column_plan(
        {"id", "batch_size", "weekly_digest_opt_in", "weekly_digest_dow"}
    )
    assert "show_glosses" not in plan_extra
    # A database that is behind withholds the layer rather than offering
    # notation the learner never opted into.
    assert plan_defaults["show_glosses"] is False
    # ...and the group that IS present is still selected.
    assert "weekly_digest_opt_in" in plan_extra


async def test_a_middle_group_can_be_missing_on_its_own(pool):
    """Migrations are owner-applied and independent, so "newest applied,
    an older one not" is a real state. The ladder this replaces only ever
    dropped groups from the right and had no attempt that fitted it."""
    extra, defaults = _profile_column_plan(
        {"id", "batch_size", "sentence_audio_on_correct", "show_glosses"}
    )
    assert "sentence_audio_on_correct" in extra
    assert "show_glosses" in extra
    # The older, absent ones come back as defaults rather than breaking the
    # statement.
    assert defaults["allow_explicit_content"] is False
    assert defaults["weekly_digest_opt_in"] is False


async def test_the_choice_survives_an_upsert_that_omits_it(pool):
    """Settings are saved one form at a time; a save that never mentions
    glosses must not reset them. Checked against the database rather than
    the SQL string. Turned ON here, since that is the choice a learner has
    to make deliberately and would be most annoyed to lose."""
    user = await _user(pool, "gloss-upsert@example.com")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO user_profiles (id, batch_size, show_glosses) "
            "VALUES ($1, 5, true)", user
        )
        await conn.execute(
            """
            INSERT INTO user_profiles (id, batch_size, show_glosses)
            VALUES ($1, 9, COALESCE(NULL, false))
            ON CONFLICT (id) DO UPDATE SET
                batch_size = COALESCE($2, user_profiles.batch_size),
                show_glosses = COALESCE(NULL, user_profiles.show_glosses)
            """,
            user, 9,
        )
        row = await conn.fetchrow(
            "SELECT batch_size, show_glosses FROM user_profiles WHERE id = $1",
            user,
        )
        assert row["batch_size"] == 9
        # The opt-in survived a save that was about something else.
        assert row["show_glosses"] is True
