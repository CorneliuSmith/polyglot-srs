"""The admin console's read surfaces and the assign-by-email flow, against a
REAL schema.

Every admin endpoint's unit test patches its repository call, which means an
invalid query — or a router reading a shape the repository doesn't return —
passes every test and 500s only in production. That is exactly what happened
with experiment assignment: `find_user_by_email` returns a bare id string,
the router indexed into it like a dict, the test mocked the lookup as a dict,
and the owner's very first assignment failed with "Could not assign that."

These tests EXECUTE the real repository functions on the migrated schema.
They assert shapes loosely on purpose: the point is that the SQL runs and
returns what its callers index into, not the specific numbers.
"""
from __future__ import annotations

from backend.repositories.contributor import (
    admin_cohorts,
    admin_engagement,
    admin_engagement_user_detail,
    admin_engagement_users,
    admin_feature_popularity,
    admin_timeseries,
    find_user_by_email,
    generation_coverage,
    pick_review_prompt,
    review_inbox_by_language,
)
from backend.repositories.experiments import (
    assign_variant,
    clear_assignment,
    get_experiment,
)
from backend.repositories.feedback import open_feedback_by_language

from .conftest import requires_db

pytestmark = requires_db


async def _seed_account(pool, email: str) -> tuple[str, str]:
    """A language and an account studying it — the minimum every admin
    surface reads over."""
    async with pool.privileged_connection() as conn:
        lang = str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ('qq', 'Quenya', false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        ))
        uid = str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))
        await conn.execute(
            "INSERT INTO user_profiles (id, active_language_id) VALUES ($1, $2) "
            "ON CONFLICT (id) DO NOTHING",
            uid, lang,
        )
    return lang, uid


async def test_assign_by_email_runs_the_real_seam(pool):
    """The exact sequence the experiment-assign endpoint runs after auth:
    email → id string → pin → release. The dict-shaped TypeError that 500'd
    production dies here forever."""
    _, uid = await _seed_account(pool, "pinme@example.com")
    async with pool.privileged_connection() as conn:
        # ui_skin is seeded by migration 20260930 — the same row production has.
        experiment = await get_experiment(conn, "ui_skin")
        assert experiment is not None
        variant = next(
            v["key"] for v in experiment["variants"]
            if v["key"] != experiment["default_variant"]
        )

        target_id = await find_user_by_email(conn, "  PinMe@Example.com ")
        assert target_id == uid  # a bare string, trimmed and case-blind

        assert await assign_variant(conn, target_id, "ui_skin", variant,
                                    source="admin", note="beta group")
        stored = await conn.fetchrow(
            "SELECT variant, source, note FROM experiment_assignments "
            "WHERE user_id = $1 AND experiment_key = 'ui_skin'", uid,
        )
        assert dict(stored) == {"variant": variant, "source": "admin",
                                "note": "beta group"}

        await clear_assignment(conn, target_id, "ui_skin")
        assert await conn.fetchval(
            "SELECT count(*) FROM experiment_assignments "
            "WHERE user_id = $1 AND experiment_key = 'ui_skin'", uid,
        ) == 0


async def test_every_admin_read_surface_executes(pool):
    """Run each admin read the console fires, on the real schema, and index
    into the results the way the routers do."""
    lang, uid = await _seed_account(pool, "admin-reads@example.com")
    async with pool.privileged_connection() as conn:
        inbox = await review_inbox_by_language(conn, include_empty=True)
        assert any(row["id"] == lang for row in inbox)
        assert all("counts" in row and "total" in row for row in inbox)

        assert isinstance(await open_feedback_by_language(conn), list)

        coverage = await generation_coverage(conn)
        # The router reads these exact keys to attach model overrides.
        assert all("language_id" in r and "language_code" in r for r in coverage)

        snapshot = await admin_engagement(conn, 30)
        assert snapshot["total_users"] >= 1
        assert "speak" in snapshot["feature_users"]

        users = await admin_engagement_users(conn, 30)
        me = next(u for u in users if u["id"] == uid)
        assert me["speak_sessions"] == 0

        assert isinstance(await admin_engagement_user_detail(conn, uid, 30), list)
        assert len(await admin_timeseries(conn, 7)) == 7
        assert isinstance(await admin_cohorts(conn, 8), list)

        popularity = await admin_feature_popularity(conn, 30)
        assert {f["key"] for f in popularity} >= {"review", "speak", "gym"}


async def test_review_prompt_query_executes(pool):
    """The tester-prompt rotation's md5 ORDER BY was once verified only as a
    substring of the SQL text — run the actual query."""
    lang, uid = await _seed_account(pool, "prompted@example.com")
    async with pool.privileged_connection() as conn:
        picked = await pick_review_prompt(
            conn, uid, all_languages=True, language_ids=[lang],
        )
    assert picked is None or "kind" in picked
