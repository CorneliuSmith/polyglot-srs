"""Real-Postgres integration tests: RLS tenant isolation + key SQL queries.

These prove the things mocked unit tests can't: that one user cannot read or
write another user's rows, that the privileged connection bypasses RLS as
intended, and that the actual repository SQL runs against the real schema.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import asyncpg
import pytest

from backend.repositories.cards import (
    add_grammar_learn_batch,
    add_learn_batch,
    get_card_detail,
    get_due_cards,
    update_card_srs,
)
from backend.repositories.review import insert_review_log
from backend.repositories.tutor import get_user_profile, upsert_user_profile
from backend.services.fsrs import CardState, Rating, fsrs_review

from .conftest import requires_db

pytestmark = requires_db


# ── helpers ──────────────────────────────────────────────────────────────────

async def _new_user(pool_mod, email: str) -> str:
    async with pool_mod.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def _language(pool_mod, code: str) -> str:
    async with pool_mod.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _insert_card(pool_mod, user_id: str, language_id: str) -> str:
    async with pool_mod.privileged_connection() as conn:
        return str(await conn.fetchval(
            """
            INSERT INTO user_cards (user_id, language_id, card_type, card_id)
            VALUES ($1, $2, 'vocabulary', gen_random_uuid()) RETURNING id
            """,
            user_id, language_id,
        ))


# ── schema sanity ────────────────────────────────────────────────────────────

async def test_all_migrations_applied(pool):
    async with pool.privileged_connection() as conn:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
    names = {r["table_name"] for r in rows}
    assert len(names) >= 12  # vocabulary, user_cards, tutor_*, contributor_roles, ...
    # personal-text + FSRS-weights feature tables must be present
    assert {"user_notes", "user_cloze_cards", "fsrs_weights"} <= names


# ── RLS isolation: the #1 risk ───────────────────────────────────────────────

async def test_user_cards_are_isolated(pool):
    lang = await _language(pool, "rls1")
    a = await _new_user(pool, "a@isolation")
    b = await _new_user(pool, "b@isolation")
    a_card = await _insert_card(pool, a, lang)
    await _insert_card(pool, b, lang)

    async with pool.rls_connection(a) as conn:
        rows = await conn.fetch("SELECT id, user_id FROM user_cards")
    ids = {str(r["id"]) for r in rows}
    assert a_card in ids
    assert all(str(r["user_id"]) == a for r in rows)  # never sees B's rows


async def test_cannot_insert_card_for_another_user(pool):
    lang = await _language(pool, "rls2")
    a = await _new_user(pool, "a@check")
    b = await _new_user(pool, "b@check")
    # A, acting as themselves, must not be able to create a card owned by B.
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with pool.rls_connection(a) as conn:
            await conn.execute(
                "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
                "VALUES ($1, $2, 'vocabulary', gen_random_uuid())",
                b, lang,
            )


async def test_tutor_profile_isolated(pool):
    a = await _new_user(pool, "a@mem")
    b = await _new_user(pool, "b@mem")
    async with pool.rls_connection(a) as conn:
        await upsert_user_profile(conn, a, {"native_language": "English"})
    async with pool.rls_connection(b) as conn:
        await upsert_user_profile(conn, b, {"native_language": "Spanish"})
        b_view = await get_user_profile(conn, b)
        # B cannot read A's profile even by id.
        a_view_from_b = await get_user_profile(conn, a)
    assert b_view == {"native_language": "Spanish"}
    assert a_view_from_b == {}  # RLS hides A's row from B


async def test_card_feedback_isolated(pool):
    lang = await _language(pool, "rls3")
    a = await _new_user(pool, "a@fb")
    b = await _new_user(pool, "b@fb")
    content = uuid.uuid4()
    async with pool.privileged_connection() as conn:
        for uid in (a, b):
            await conn.execute(
                "INSERT INTO card_feedback (user_id, language_id, card_type, content_id, message) "
                "VALUES ($1, $2, 'grammar', $3, 'issue')",
                uid, lang, content,
            )
    async with pool.rls_connection(a) as conn:
        rows = await conn.fetch("SELECT user_id FROM card_feedback")
    assert rows and all(str(r["user_id"]) == a for r in rows)


async def test_contributor_role_read_own_only(pool):
    a = await _new_user(pool, "a@role")
    b = await _new_user(pool, "b@role")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, role) VALUES ($1, 'admin')", a
        )
    async with pool.rls_connection(b) as conn:
        rows = await conn.fetch("SELECT user_id FROM contributor_roles")
    assert rows == []  # B sees none of A's roles


# ── privileged connection bypasses RLS (the contributor write path) ───────────

async def test_privileged_write_grammar_point(pool):
    lang = await _language(pool, "rls4")
    async with pool.privileged_connection() as conn:
        pid = await conn.fetchval(
            """
            INSERT INTO grammar_points (language_id, title, explanation_source, reviewed)
            VALUES ($1, 'Test point', 'contributor', false) RETURNING id
            """,
            lang,
        )
    assert pid is not None


async def test_authenticated_cannot_write_grammar_content(pool):
    """Defense-in-depth: even with a role, the DB blocks content writes via RLS."""
    lang = await _language(pool, "rls5")
    user = await _new_user(pool, "contrib@hardening")
    # Reads are allowed (world-readable)...
    async with pool.rls_connection(user) as conn:
        await conn.fetch("SELECT id FROM grammar_points LIMIT 1")
    # ...but a direct write as the authenticated role is denied by RLS.
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with pool.rls_connection(user) as conn:
            await conn.execute(
                "INSERT INTO grammar_points (language_id, title) VALUES ($1, 'sneaky')",
                lang,
            )


# ── functional: real repository SQL against real data ────────────────────────

async def test_vocab_learn_and_due_flow(pool):
    lang = await _language(pool, "func1")
    user = await _new_user(pool, "learner@func")
    async with pool.privileged_connection() as conn:
        vocab_id = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, frequency_rank, level) "
            "VALUES ($1, 'casa', 1, 'A1') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'house')", vocab_id,
        )
        list_id = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 vocab') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", user, list_id,
        )

    async with pool.rls_connection(user) as conn:
        result = await add_learn_batch(conn, user, lang, 5)
        assert result["added"] == 1
        due = await get_due_cards(conn, lang)
        assert any(c["correct_answer"] == "casa" for c in due)
        detail = await get_card_detail(conn, due[0]["id"])
    assert detail["definition"] == "house"


async def test_grammar_learn_respects_review_policy(pool):
    lang = await _language(pool, "func2")
    user = await _new_user(pool, "learner@grammar")
    async with pool.privileged_connection() as conn:
        # one human-reviewed point, one only AI-passed (unreviewed)
        reviewed = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Reviewed pt', 'A1', true, 1) RETURNING id", lang,
        )
        await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, ai_check_status, display_order) "
            "VALUES ($1, 'AI-only pt', 'A1', false, 'pass', 2) RETURNING id", lang,
        )
        list_id = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'grammar', 'A1', 'A1 grammar') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", user, list_id,
        )

    # strict (default): only the reviewed point is learnable
    async with pool.rls_connection(user) as conn:
        res = await add_grammar_learn_batch(conn, user, lang, 10)
        learned = {r async for r in _card_ids(conn, user)}
    assert res["added"] == 1
    assert str(reviewed) in learned

    # switch to ai_ok: the AI-passed point becomes learnable too
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE languages SET grammar_review_policy = 'ai_ok' WHERE id = $1", lang
        )
    async with pool.rls_connection(user) as conn:
        res2 = await add_grammar_learn_batch(conn, user, lang, 10)
    assert res2["added"] == 1  # the previously-hidden AI-passed point


async def test_personal_cloze_card_flow_and_isolation(pool):
    from backend.repositories.notes import create_note, create_personal_card

    lang = await _language(pool, "func3")
    a = await _new_user(pool, "a@notes")
    b = await _new_user(pool, "b@notes")

    async with pool.rls_connection(a) as conn:
        note = await create_note(conn, a, lang, "My text", "El gato duerme.")
        await create_personal_card(
            conn, a, lang, "El {{answer}} duerme.", "gato", "The cat sleeps.", note,
        )
        # A's personal card shows up as due, in cloze form
        due = await get_due_cards(conn, lang)
        personal = [c for c in due if c["card_type"] == "personal"]
        assert personal and personal[0]["correct_answer"] == "gato"
        assert "{{answer}}" in personal[0]["sentence"]
        detail = await get_card_detail(conn, personal[0]["id"])
    assert detail["card_type"] == "personal"
    assert detail["definition"] == "The cat sleeps."
    # the detail surfaces the word back in its original sentence, and the
    # source note it came from
    assert detail["examples"] == [
        {"sentence": "El gato duerme.", "translation": "The cat sleeps.", "hint": None}
    ]
    assert detail["usage_note"] == "From your note: My text"

    # B sees none of A's notes or personal cards (RLS)
    async with pool.rls_connection(b) as conn:
        notes = await conn.fetch("SELECT id FROM user_notes")
        clozes = await conn.fetch("SELECT id FROM user_cloze_cards")
        b_due = await get_due_cards(conn, lang)
    assert notes == [] and clozes == []
    assert [c for c in b_due if c["card_type"] == "personal"] == []


async def test_fsrs_submit_persists_state_and_logs(pool):
    """The FSRS submit path writes stability/difficulty/state and a review_log row."""
    lang = await _language(pool, "fsrs1")
    user = await _new_user(pool, "learner@fsrs")
    card_id = await _insert_card(pool, user, lang)

    async with pool.rls_connection(user) as conn:
        # A brand-new card has no FSRS state yet.
        before = await conn.fetchrow(
            "SELECT stability, difficulty, state, interval FROM user_cards WHERE id = $1",
            card_id,
        )
        assert before["stability"] is None and before["state"] == "new"

        result = fsrs_review(CardState(), Rating.GOOD, 0.0, enable_fuzz=False)
        await update_card_srs(conn, card_id, {
            "stability": result.stability,
            "difficulty": result.difficulty,
            "state": result.state,
            "interval": result.interval,
            "repetitions": result.repetitions,
            "streak": result.streak,
            "lapses": result.lapses,
            "next_review": result.next_review,
        })
        await insert_review_log(
            conn,
            user_id=user,
            card_id=card_id,
            quality=4,
            answer_result="correct",
            interval_before=before["interval"],
            interval_after=result.interval,
            stability_before=None,
            stability_after=result.stability,
            difficulty_before=None,
            difficulty_after=result.difficulty,
            time_taken_ms=1500,
        )

        after = await conn.fetchrow(
            "SELECT stability, difficulty, state, interval, repetitions "
            "FROM user_cards WHERE id = $1",
            card_id,
        )
        log = await conn.fetchrow(
            "SELECT stability_after, difficulty_after, ease_factor_before, quality "
            "FROM review_log WHERE card_id = $1",
            card_id,
        )

    assert after["stability"] == pytest.approx(result.stability)
    assert after["state"] == "review" and after["repetitions"] == 1
    assert log["stability_after"] == pytest.approx(result.stability)
    assert log["ease_factor_before"] is None  # legacy column now optional
    assert log["quality"] == 4


async def test_fsrs_weight_fit_resolve_and_isolation(pool):
    """The fit job stores per-language weights the scheduler resolves; per-user
    rows stay private to their owner."""
    from backend.jobs.fit_fsrs_weights import fit_languages
    from backend.repositories.fsrs_weights import get_effective_params

    lang = await _language(pool, "fsrsw")
    a = await _new_user(pool, "a@weights")
    b = await _new_user(pool, "b@weights")
    card = await _insert_card(pool, a, lang)

    # Lay down a short review history for user A's card.
    async with pool.privileged_connection() as conn:
        base = await conn.fetchval("SELECT now()")
        grades = [("correct", 4), ("correct", 4), ("wrong", 1), ("correct", 4)]
        for i, (answer, quality) in enumerate(grades):
            await conn.execute(
                """
                INSERT INTO review_log
                    (user_id, card_id, quality, answer_result,
                     interval_before, interval_after, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                a, card, quality, answer, i, i + 1,
                base + timedelta(days=i * 2),
            )
        # Fit per-language weights with a low threshold for the test.
        fitted = await fit_languages(conn, min_reviews=2)
        assert fitted == 1
        stored = await conn.fetchval(
            "SELECT params FROM fsrs_weights WHERE language_id = $1 AND scope = 'language'",
            lang,
        )
    assert stored is not None and len(stored) == 19

    # The scheduler resolves the per-language fit for any user of that language.
    async with pool.rls_connection(b) as conn:
        resolved = await get_effective_params(conn, b, lang)
    assert resolved == tuple(stored)

    # A per-user row is private: B never resolves A's personal weights.
    async with pool.privileged_connection() as conn:
        await conn.execute(
            """
            INSERT INTO fsrs_weights (scope, language_id, user_id, params, review_count)
            VALUES ('user_language', $1, $2, $3, 1500)
            """,
            lang, a, [0.9] * 19,
        )
    async with pool.rls_connection(b) as conn:
        rows = await conn.fetch("SELECT scope FROM fsrs_weights")
        b_resolved = await get_effective_params(conn, b, lang)
    # B sees only the shared language row, not A's user_language row.
    assert {r["scope"] for r in rows} == {"language"}
    assert b_resolved == tuple(stored)
    assert b_resolved != (0.9,) * 19

    async with pool.rls_connection(a) as conn:
        a_resolved = await get_effective_params(conn, a, lang)
    assert a_resolved == (0.9,) * 19  # A gets their own per-user weights


async def test_onboarding_subscribes_and_unlocks_learning(pool):
    """Completing onboarding subscribes the user to content at/below their level,
    which is what makes 'Learn' actually return cards."""
    from backend.repositories.onboarding import (
        complete_onboarding,
        get_status,
        sample_placement_items,
    )

    lang = await _language(pool, "onbrd")
    user = await _new_user(pool, "newbie@onboard")

    async with pool.privileged_connection() as conn:
        # Content lists across three levels (grammar + vocab each).
        for level in ("A1", "A2", "B1"):
            for list_type in ("grammar", "vocabulary"):
                await conn.execute(
                    "INSERT INTO content_lists (language_id, list_type, level, title) "
                    "VALUES ($1, $2, $3, $4)",
                    lang, list_type, level, f"{level} {list_type}",
                )
        # A graded word (A1) with a definition so it becomes learnable + placeable.
        vid = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, frequency_rank, level) "
            "VALUES ($1, 'hola', 1, 'A1') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'hello')", vid,
        )

    async with pool.rls_connection(user) as conn:
        # Before: not onboarded, no subscriptions, nothing to learn.
        assert (await get_status(conn, user))["onboarded"] is False
        assert (await add_learn_batch(conn, user, lang, 5))["added"] == 0

        result = await complete_onboarding(conn, user, lang, "A2")
        # A1 + A2 lists only (B1 is above the chosen level): 2 levels × 2 types.
        assert result["subscribed"] == 4

        status = await get_status(conn, user)
        assert status["onboarded"] is True
        assert status["active_language_id"] == lang
        assert status["has_subscriptions"] is True

        # The payoff: subscribed content is now learnable.
        learned = await add_learn_batch(conn, user, lang, 5)
        assert learned["added"] == 1

        # Idempotent: completing again creates no duplicate subscriptions.
        assert (await complete_onboarding(conn, user, lang, "A2"))["subscribed"] == 0

        items = await sample_placement_items(conn, lang)
    assert any(i["prompt"] == "hello" and i["level"] == "A1" for i in items)


async def _card_ids(conn, user_id):
    rows = await conn.fetch(
        "SELECT card_id FROM user_cards WHERE user_id = $1 AND card_type = 'grammar'",
        user_id,
    )
    for r in rows:
        yield str(r["card_id"])
