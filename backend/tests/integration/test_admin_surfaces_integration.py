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
    language_release_readiness,
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

        readiness = await language_release_readiness(conn)
        assert any(r["id"] == lang for r in readiness)

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


async def test_grouped_rollups_count_into_the_right_language(pool):
    """The roll-ups were rewritten from per-language correlated subqueries
    (which outran the statement timeout on production corpus sizes and
    500'd the staff bell) to single grouped scans. Grouping bugs are
    silent — a count landing on the wrong language still returns 200 —
    so seed real queue rows and check they surface where they belong."""
    lang, uid = await _seed_account(pool, "rollup-seed@example.com")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO grammar_points (language_id, title, explanation, "
            "reviewed) VALUES ($1, 'Case endings', 'A draft worth reading', "
            "false)",
            lang,
        )
        await conn.execute(
            "INSERT INTO app_feedback (user_id, language_id, category, "
            "message) VALUES ($1, $2, 'bug', 'the keyboard is cut off')",
            uid, lang,
        )

        inbox = await review_inbox_by_language(conn, include_empty=True)
        mine = next(row for row in inbox if row["id"] == lang)
        assert mine["counts"]["grammar_pending"] == 1
        assert mine["counts"]["app_feedback"] == 1
        assert mine["total"] >= 2
        # …and nothing leaked onto other languages' rows.
        for row in inbox:
            if row["id"] != lang:
                assert row["counts"]["grammar_pending"] == 0

        coverage = await generation_coverage(conn)
        cov = next(r for r in coverage if r["language_id"] == lang)
        assert cov["grammar_total"] == 1
        assert cov["grammar_no_drills"] == 1

        # Clean up so the other tests' "empty" expectations hold whatever
        # order the file runs in.
        await conn.execute(
            "DELETE FROM grammar_points WHERE language_id = $1", lang)
        await conn.execute(
            "DELETE FROM app_feedback WHERE user_id = $1", uid)


async def test_personal_card_provenance_round_trip(pool):
    """A hand-made card stores its source and the detail view returns it
    structured (migration 20261005; the write degrades silently without it,
    so this proves the WITH-column path against the real schema)."""
    from backend.repositories.cards import get_card_detail
    from backend.repositories.notes import create_personal_card

    lang, uid = await _seed_account(pool, "provenance@example.com")
    async with pool.privileged_connection() as conn:
        user_card_id = await create_personal_card(
            conn, uid, lang, "Blue is not the best {{answer}} for me.",
            "color", "El azul no es el mejor color para mí.", None,
            source="manual",
        )
        stored = await conn.fetchval(
            "SELECT cc.source FROM user_cards uc"
            " JOIN user_cloze_cards cc ON uc.card_id = cc.id"
            " WHERE uc.id = $1", user_card_id,
        )
        assert stored == "manual"

        detail = await get_card_detail(conn, user_card_id)
        assert detail is not None
        prov = detail["provenance"]
        assert prov["source"] == "manual"
        assert prov["created_at"] is not None
        assert prov["note_title"] is None


async def test_pending_trial_requests_count_on_the_real_table(pool):
    """The bell's access-request signal, against the real schema.

    Counting only 'pending' is the whole contract: an approved request that
    kept ringing the bell would be worse than the silence this replaced.
    """
    from backend.repositories.trials import (
        add_trial_request,
        count_pending_trial_requests,
        list_trial_requests,
        mark_trial_decided,
    )

    _, admin_id = await _seed_account(pool, "trial-count-admin@example.com")
    async with pool.privileged_connection() as conn:
        before = await count_pending_trial_requests(conn)

        assert await add_trial_request(conn, "asker-one@example.com", "One", None)
        assert await add_trial_request(conn, "asker-two@example.com", None, "please")
        # Same email again: deduped, so a stranger cannot inflate the badge.
        assert await add_trial_request(
            conn, "asker-one@example.com", "One", None) is False
        assert await count_pending_trial_requests(conn) == before + 2

        decided = next(
            r for r in await list_trial_requests(conn)
            if r["email"] == "asker-one@example.com"
        )
        await mark_trial_decided(conn, decided["id"], "approved", admin_id)
        assert await count_pending_trial_requests(conn) == before + 1

        await conn.execute(
            "DELETE FROM trial_requests WHERE email = ANY($1::text[])",
            ["asker-one@example.com", "asker-two@example.com"],
        )


async def test_admin_recipients_and_digest_stamp_on_the_real_schema(pool):
    """Who the admin emails go to, resolved from the roles table.

    The env var they replace was never set, so the query that finds these
    accounts is the whole feature — it runs against auth.users, which lives
    behind the shim, and it must not double up on someone holding the role
    for two languages.
    """
    from backend.repositories.admins import (
        admin_recipients,
        admins_due_for_digest,
        mark_digest_sent,
    )

    lang, admin_id = await _seed_account(pool, "digest-admin@example.com")
    _, other_id = await _seed_account(pool, "digest-learner@example.com")
    async with pool.privileged_connection() as conn:
        # The same person, admin on one language and on all of them: a
        # DISTINCT failure here mails them twice per notification.
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, language_id, role) "
            "VALUES ($1, NULL, 'admin'), ($1, $2, 'admin') "
            "ON CONFLICT DO NOTHING",
            admin_id, lang,
        )
        # A contributor is not an admin and must never be mailed as one.
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, language_id, role) "
            "VALUES ($1, $2, 'contributor') ON CONFLICT DO NOTHING",
            other_id, lang,
        )

        emails = [a["email"] for a in await admin_recipients(conn)]
        assert emails.count("digest-admin@example.com") == 1
        assert "digest-learner@example.com" not in emails

        # Never stamped → due. Stamped now → not due for the next 23 hours.
        due = [a["id"] for a in await admins_due_for_digest(conn, 23)]
        assert admin_id in due
        await mark_digest_sent(conn, admin_id)
        due_again = [a["id"] for a in await admins_due_for_digest(conn, 23)]
        assert admin_id not in due_again

        await conn.execute(
            "DELETE FROM contributor_roles WHERE user_id = ANY($1::uuid[])",
            [admin_id, other_id],
        )


async def test_review_prompt_query_executes(pool):
    """The tester-prompt rotation's md5 ORDER BY was once verified only as a
    substring of the SQL text — run the actual query."""
    lang, uid = await _seed_account(pool, "prompted@example.com")
    async with pool.privileged_connection() as conn:
        picked = await pick_review_prompt(
            conn, uid, all_languages=True, language_ids=[lang],
        )
    assert picked is None or "kind" in picked
