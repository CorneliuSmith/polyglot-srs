"""Trial (advisory) reviewers: gating, recommendations, and activity."""
from __future__ import annotations

from backend.repositories.contributor import (
    add_recommendation,
    add_review_note,
    add_vocab_review_note,
    can_review,
    can_trial_review,
    get_note_language,
    list_review_notes,
    recommendations_for_targets,
    resolve_review_note,
    trial_reviewer_activity,
)

from .conftest import requires_db

pytestmark = requires_db


async def _language(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def _grant(pool, user_id: str, language_id: str, role: str) -> None:
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, language_id, role) "
            "VALUES ($1, $2, $3)",
            user_id, language_id, role,
        )


def _roles(language_id: str, role: str) -> list[dict]:
    return [{"role": role, "language_id": language_id}]


def test_trial_reviewer_can_review_but_not_publish():
    lang = "11111111-1111-1111-1111-111111111111"
    trial = _roles(lang, "trial_reviewer")
    assert can_trial_review(trial, lang) is True
    assert can_review(trial, lang) is False  # advisory only, no publish
    full = _roles(lang, "reviewer")
    assert can_trial_review(full, lang) is True
    assert can_review(full, lang) is True


async def test_recommendations_tally_and_activity(pool):
    lang = await _language(pool, "trv")
    alice = await _user(pool, "alice-trial@t")
    bob = await _user(pool, "bob-trial@t")
    await _grant(pool, alice, lang, "trial_reviewer")
    await _grant(pool, bob, lang, "trial_reviewer")

    # A pending drill to recommend on.
    async with pool.privileged_connection() as conn:
        point = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, display_order) "
            "VALUES ($1, 'P', true, 1) RETURNING id", lang,
        )
        drill = str(await conn.fetchval(
            "INSERT INTO drill_sentences "
            "(grammar_point_id, sentence, answer, source, reviewed, display_order) "
            "VALUES ($1, 'a {{answer}} b', 'x', 'ai', false, 1) RETURNING id", point,
        ))

        await add_recommendation(conn, alice, lang, "drill", drill, "approve", "reads well")
        await add_recommendation(conn, bob, lang, "drill", drill, "reject", "unnatural")
        # Alice changes her mind — upsert, not a second row.
        await add_recommendation(conn, alice, lang, "drill", drill, "reject", "on reflection, no")

        tally = await recommendations_for_targets(conn, "drill", [drill])
        assert tally[drill]["approve"] == 0
        assert tally[drill]["reject"] == 2
        assert len(tally[drill]["notes"]) == 2

        activity = await trial_reviewer_activity(conn, lang)
        by_email = {a["email"]: a for a in activity}
        assert by_email["alice-trial@t"]["recommendations"] == 1
        assert by_email["bob-trial@t"]["recommendations"] == 1


async def test_review_notes_cover_grammar_and_vocab(pool):
    lang = await _language(pool, "nvo")
    author = await _user(pool, "note-author@t")
    async with pool.privileged_connection() as conn:
        point = str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, display_order) "
            "VALUES ($1, 'Cases', true, 1) RETURNING id", lang,
        ))
        word = str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level) "
            "VALUES ($1, 'chai', 'A1') RETURNING id", lang,
        ))

        g_note = await add_review_note(conn, point, author, "tone marks look off")
        v_note = await add_vocab_review_note(conn, word, author, "gloss is regional")

        # Both surface in one language-scoped list, tagged by entity.
        notes = await list_review_notes(conn, lang)
        by_type = {n["entity_type"]: n for n in notes}
        assert by_type["grammar"]["entity_label"] == "Cases"
        assert by_type["vocab"]["entity_label"] == "chai"

        # A vocab note resolves through the vocab word's language.
        assert await get_note_language(conn, v_note) == lang
        assert await resolve_review_note(conn, v_note, author) is True
        assert g_note != v_note

        # Resolved note drops from the default (open-only) list.
        open_notes = await list_review_notes(conn, lang)
        assert {n["entity_type"] for n in open_notes} == {"grammar"}
