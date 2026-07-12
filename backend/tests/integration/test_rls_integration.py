"""Real-Postgres integration tests: RLS tenant isolation + key SQL queries.

These prove the things mocked unit tests can't: that one user cannot read or
write another user's rows, that the privileged connection bypasses RLS as
intended, and that the actual repository SQL runs against the real schema.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta

import asyncpg
import pytest

from backend.repositories.cards import (
    add_grammar_learn_batch,
    add_learn_batch,
    confirm_learn_batch,
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
        # Teach-before-quiz gate: the batch is created suspended and stays out
        # of the review queue until the lesson's first check is passed.
        assert await get_due_cards(conn, lang) == []
        await confirm_learn_batch(conn, user, result["items"])
        due = await get_due_cards(conn, lang)
        assert any(c["correct_answer"] == "casa" for c in due)
        detail = await get_card_detail(conn, due[0]["id"])
    assert detail["definition"] == "house"


async def test_concurrent_learn_calls_are_idempotent(pool):
    """Two learn calls racing (e.g. React StrictMode double-firing the learn
    mutation) must not 500 with UniqueViolationError, and must not duplicate
    cards. The first call holds its transaction open while the second selects
    the same candidate — the second's INSERT then hits the unique index."""
    lang = await _language(pool, "race1")
    user = await _new_user(pool, "race@learn")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO vocabulary (language_id, word, frequency_rank, level) "
            "VALUES ($1, 'agua', 1, 'A1')", lang,
        )
        list_id = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 vocab') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", user, list_id,
        )

    first_inserted = asyncio.Event()

    async def first():
        async with pool.rls_connection(user) as conn:
            res = await add_learn_batch(conn, user, lang, 5)
            first_inserted.set()
            # Hold the transaction open so the second call's SELECT cannot see
            # this insert and it races into the same unique-index slot.
            await asyncio.sleep(0.3)
            return res

    async def second():
        await first_inserted.wait()
        async with pool.rls_connection(user) as conn:
            return await add_learn_batch(conn, user, lang, 5)

    r1, r2 = await asyncio.gather(first(), second())
    assert r1["added"] == 1
    # The loser of the race re-offers the SAME still-unconfirmed card for
    # teaching (abandoned-walkthrough semantics) — never a UniqueViolation,
    # never a duplicate.
    assert r2["added"] <= 1
    if r2["added"]:
        assert r2["items"] == r1["items"]

    async with pool.privileged_connection() as conn:
        n = await conn.fetchval(
            "SELECT count(*) FROM user_cards "
            "WHERE user_id = $1 AND card_type = 'vocabulary'", user,
        )
    assert n == 1


async def test_vocab_card_is_cloze_when_example_sentence_exists(pool):
    """A vocab word with an example sentence is taught in context: the due card
    is the sentence with the word blanked, plus its translation as a hint."""
    lang = await _language(pool, "vctx")
    user = await _new_user(pool, "ctx@learn")
    async with pool.privileged_connection() as conn:
        vid = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, frequency_rank, level) "
            "VALUES ($1, 'gato', 1, 'A1') RETURNING id", lang,
        )
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'cat')", vid,
        )
        await conn.execute(
            "INSERT INTO example_sentences (language_id, vocabulary_id, sentence, translation) "
            "VALUES ($1, $2, 'El gato duerme.', 'The cat sleeps.')", lang, vid,
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
        batch = await add_learn_batch(conn, user, lang, 5)
        await confirm_learn_batch(conn, user, batch["items"])
        due = await get_due_cards(conn, lang)
    card = next(c for c in due if c["correct_answer"] == "gato")
    assert card["sentence"] == "El {{answer}} duerme."   # word blanked in context
    assert card["translation"] == "The cat sleeps."       # sentence translation
    assert card["hint"] == "cat"                          # meaning as a hint


async def test_grammar_learn_respects_review_policy(pool):
    lang = await _language(pool, "func2")
    user = await _new_user(pool, "learner@grammar")
    async with pool.privileged_connection() as conn:
        # one human-reviewed point, one only AI-passed (unreviewed)
        reviewed = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Reviewed pt', 'A1', true, 1) RETURNING id", lang,
        )
        ai_only = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, ai_check_status, display_order) "
            "VALUES ($1, 'AI-only pt', 'A1', false, 'pass', 2) RETURNING id", lang,
        )
        # a drill-less point must never be learnable regardless of policy
        await conn.execute(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'No-drills pt', 'A1', true, 3)", lang,
        )
        for gp_id, answer in ((reviewed, 'evde'), (ai_only, 'kitaplar')):
            await conn.execute(
                "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, display_order) "
                "VALUES ($1, 'Ben {{answer}}.', $2, 1)", gp_id, answer,
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
        # confirm the walkthrough so the next batch doesn't re-offer this card
        await confirm_learn_batch(conn, user, res["items"])
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


async def test_grammar_curriculum_path(pool):
    """The browsable grammar path: ordered points with can-do functions, the
    learner's status overlaid, readable point pages, and per-point learning."""
    from backend.repositories.curriculum import (
        get_curriculum,
        get_curriculum_point,
        learn_point,
    )

    lang = await _language(pool, "curr1")
    user = await _new_user(pool, "path@learn")
    async with pool.privileged_connection() as conn:
        first = await conn.fetchval(
            "INSERT INTO grammar_points "
            " (language_id, title, level, function_note, explanation, reviewed, display_order, reference_links) "
            "VALUES ($1, 'Point one', 'A1', 'Say who you are', 'Explained.', true, 1, "
            " '[{\"title\": \"Source\", \"url\": \"https://example.org/one\"}]'::jsonb) RETURNING id",
            lang,
        )
        await conn.execute(
            "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, translation, display_order) "
            "VALUES ($1, 'Yo {{answer}} aquí.', 'estoy', 'I am here.', 1)", first,
        )
        # readable but NOT quizzable (no drills), later in the path
        await conn.execute(
            "INSERT INTO grammar_points (language_id, title, level, function_note, reviewed, display_order) "
            "VALUES ($1, 'Point two', 'A2', 'Describe things', true, 1)", lang,
        )
        # invisible draft (unreviewed, no AI pass) must not appear
        await conn.execute(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Hidden draft', 'A1', false, 2)", lang,
        )

    async with pool.rls_connection(user) as conn:
        path = await get_curriculum(conn, user, lang)
        assert [p["title"] for p in path] == ["Point one", "Point two"]  # ordered, draft hidden
        assert path[0]["function_note"] == "Say who you are"
        assert path[0]["learnable"] is True and path[0]["learned"] is False
        assert path[1]["learnable"] is False  # no drills -> read-only

        # The point page reads like a lesson: completed example + source.
        page = await get_curriculum_point(conn, user, str(first))
        assert page["examples"][0]["sentence"] == "Yo estoy aquí."
        assert page["references"][0]["url"] == "https://example.org/one"

        # Learn THIS point from the path; it becomes due and is idempotent.
        assert (await learn_point(conn, user, str(first)))["added"] is True
        assert (await learn_point(conn, user, str(first))) == {
            "added": False, "reason": "already_learned",
        }
        drill_less = next(p["id"] for p in path if p["title"] == "Point two")
        assert (await learn_point(conn, user, drill_less))["reason"] == "no_drills"

        refreshed = await get_curriculum(conn, user, lang)
        assert refreshed[0]["learned"] is True
        due = await get_due_cards(conn, lang)
    assert any(c["correct_answer"] == "estoy" for c in due)


async def test_item_page_related_reads_and_progress(pool):
    """WP13 item page: authored Related resolves to points + the learner's
    stage, resource read-marks are per-user, and the detail payload carries
    the progress panel."""
    from backend.repositories.cards import get_card_detail
    from backend.repositories.curriculum import (
        get_curriculum_point,
        get_read_ref_keys,
        learn_point,
        set_reference_read,
    )

    lang = await _language(pool, "wp13")
    user = await _new_user(pool, "wp13@item")
    other = await _new_user(pool, "wp13@other")
    async with pool.privileged_connection() as conn:
        main = await conn.fetchval(
            "INSERT INTO grammar_points "
            " (language_id, title, level, reviewed, display_order, reference_links, related) "
            "VALUES ($1, 'Locative', 'A1', true, 1, "
            " '[{\"title\": \"Online src\", \"url\": \"https://example.org/loc\"}, "
            "   {\"title\": \"Chapter 3\", \"book\": \"A Grammar\", \"page\": \"42\"}]'::jsonb, "
            " '[{\"title\": \"Accusative\", \"contrast\": \"WHERE vs WHAT\"}, "
            "   {\"title\": \"Missing point\", \"contrast\": \"never resolves\"}]'::jsonb) "
            "RETURNING id",
            lang,
        )
        await conn.execute(
            "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, display_order) "
            "VALUES ($1, 'Ev{{answer}} kal.', 'de', 1)", main,
        )
        acc = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Accusative', 'A1', true, 2) RETURNING id", lang,
        )

    async with pool.rls_connection(user) as conn:
        # Related resolves the live title (with stage None — not studied) and
        # silently drops the one that doesn't exist.
        page = await get_curriculum_point(conn, user, str(main))
        assert [r["title"] for r in page["related"]] == ["Accusative"]
        assert page["related"][0]["contrast"] == "WHERE vs WHAT"
        assert page["related"][0]["id"] == str(acc)
        assert page["related"][0]["stage"] is None
        # Offline reference survives with book + page.
        assert {"title": "Chapter 3", "book": "A Grammar", "page": "42"} in page["references"]

        # Read-tracking: mark the online source read, toggle it back off.
        await set_reference_read(conn, user, str(main), "https://example.org/loc", True)
        assert await get_read_ref_keys(conn, str(main)) == ["https://example.org/loc"]
        assert (await get_curriculum_point(conn, user, str(main)))["read_refs"] == [
            "https://example.org/loc"
        ]
        await set_reference_read(conn, user, str(main), "https://example.org/loc", False)
        assert await get_read_ref_keys(conn, str(main)) == []
        await set_reference_read(conn, user, str(main), "https://example.org/loc", True)

        # Learn the point; the card detail now carries progress + related.
        card_id = (await learn_point(conn, user, str(main)))["card_id"]
        detail = await get_card_detail(conn, card_id)
        assert detail["point_id"] == str(main)
        assert detail["progress"]["stage"] == "beginner"
        assert detail["progress"]["times_studied"] == 0
        assert detail["progress"]["accuracy"] is None
        assert detail["read_refs"] == ["https://example.org/loc"]
        assert detail["related"][0]["title"] == "Accusative"

    # Another user sees their own empty read state — reads are per-user.
    async with pool.rls_connection(other) as conn:
        assert await get_read_ref_keys(conn, str(main)) == []
        page = await get_curriculum_point(conn, other, str(main))
        assert page["read_refs"] == []


async def test_sentences_change_every_appearance(pool):
    """Each appearance of a card shows a sentence at random but NEVER the one
    shown immediately before (tracked via review_log.prompt_sentence) — the
    learner practices the word/pattern, not one memorized string."""
    lang = await _language(pool, "rot1")
    user = await _new_user(pool, "rotate@learn")
    async with pool.privileged_connection() as conn:
        vid = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, frequency_rank, level) "
            "VALUES ($1, 'agua', 1, 'A1') RETURNING id", lang,
        )
        for i, (s, t) in enumerate([
            ("El agua está fría.", "The water is cold."),
            ("Quiero agua, por favor.", "I want water, please."),
        ]):
            await conn.execute(
                "INSERT INTO example_sentences "
                "(language_id, vocabulary_id, sentence, translation, difficulty_rank) "
                "VALUES ($1, $2, $3, $4, $5)", lang, vid, s, t, i + 1,
            )
        card_id = await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
            "VALUES ($1, $2, 'vocabulary', $3) RETURNING id", user, lang, vid,
        )
        gp = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Rotating pt', 'A1', true, 1) RETURNING id", lang,
        )
        for i, (s, a) in enumerate([("Drill {{answer}} uno.", "a1"),
                                    ("Drill {{answer}} dos.", "a2")]):
            await conn.execute(
                "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, display_order) "
                "VALUES ($1, $2, $3, $4)", gp, s, a, i + 1,
            )
        g_card = await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
            "VALUES ($1, $2, 'grammar', $3) RETURNING id", user, lang, gp,
        )

    async def _log_shown(cid, prompt):
        async with pool.privileged_connection() as conn:
            await conn.execute(
                "INSERT INTO review_log (user_id, card_id, quality, answer_result, "
                " interval_before, interval_after, prompt_sentence) "
                "VALUES ($1, $2, 4, 'correct', 0, 1, $3)", user, cid, prompt,
            )

    prev_v = prev_g = None
    seen_v, seen_g = set(), set()
    for _ in range(4):
        async with pool.rls_connection(user) as conn:
            due = {c["id"]: c for c in await get_due_cards(conn, lang)}
        v_shown = due[card_id]["sentence"]
        g_shown = due[g_card]["sentence"]
        assert "{{answer}}" in v_shown and "{{answer}}" in g_shown
        if prev_v is not None:
            assert v_shown != prev_v   # never repeats the last-shown sentence
            assert g_shown != prev_g
        await _log_shown(card_id, v_shown)
        await _log_shown(g_card, g_shown)
        prev_v, prev_g = v_shown, g_shown
        seen_v.add(v_shown)
        seen_g.add(g_shown)
    assert len(seen_v) == 2 and len(seen_g) == 2  # both contexts get exposure


async def test_rotation_hunts_unseen_then_missed_cells(pool):
    """A paradigm point is really N questions in one card: every drill gets
    shown before any repeats, and once all are seen the rotation keeps
    returning to the one the learner misses until it sticks."""
    lang = await _language(pool, "hunt1")
    user = await _new_user(pool, "hunt@learn")
    async with pool.privileged_connection() as conn:
        gp = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Pronoun paradigm', 'A1', true, 1) RETURNING id", lang,
        )
        drills = [
            ("{{answer}} soy yo-cell.", "Yo"),
            ("{{answer}} eres tú-cell.", "Tú"),
            ("{{answer}} es usted-cell.", "Usted"),
        ]
        for i, (s, a) in enumerate(drills):
            await conn.execute(
                "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, display_order) "
                "VALUES ($1, $2, $3, $4)", gp, s, a, i + 1,
            )
        card = await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
            "VALUES ($1, $2, 'grammar', $3) RETURNING id", user, lang, gp,
        )

    async def _log(prompt, result):
        async with pool.privileged_connection() as conn:
            await conn.execute(
                "INSERT INTO review_log (user_id, card_id, quality, answer_result, "
                " interval_before, interval_after, prompt_sentence) "
                "VALUES ($1, $2, 3, $3, 0, 1, $4)", user, card, result, prompt,
            )

    async def _shown():
        async with pool.rls_connection(user) as conn:
            due = {c["id"]: c for c in await get_due_cards(conn, lang)}
        return due[card]["sentence"]

    # Phase 1 — full coverage: all three cells appear before any repeat.
    # The usted drill gets answered WRONG; the others right.
    shown = []
    for _ in range(3):
        s = await _shown()
        shown.append(s)
        await _log(s, "wrong" if "usted-cell" in s else "correct")
    assert sorted(shown) == sorted(d[0] for d in drills)

    # Phase 2 — gap-hunting: everything's been seen, usted was missed, and
    # (unless it was just shown) the card goes straight back to it.
    if "usted-cell" not in shown[-1]:
        s = await _shown()
        assert "usted-cell" in s
        await _log(s, "correct")
    # After the miss is answered (and is now last-shown), rotation moves on…
    s = await _shown()
    assert "usted-cell" not in s
    await _log(s, "correct")
    # …and the miss STILL comes back next, until its record cleans up.
    assert "usted-cell" in await _shown()


async def test_review_log_records_prompt_sentence(pool):
    """The exact sentence shown is logged per review (per-sentence analysis)."""
    lang = await _language(pool, "plog")
    user = await _new_user(pool, "plog@learn")
    card = await _insert_card(pool, user, lang)
    async with pool.rls_connection(user) as conn:
        result = fsrs_review(CardState(), Rating.GOOD, 0.0, enable_fuzz=False)
        await insert_review_log(
            conn, user_id=user, card_id=card, quality=4, answer_result="correct",
            interval_before=0, interval_after=result.interval,
            stability_before=None, stability_after=result.stability,
            difficulty_before=None, difficulty_after=result.difficulty,
            time_taken_ms=900, prompt_sentence="El {{answer}} duerme.",
        )
        logged = await conn.fetchval(
            "SELECT prompt_sentence FROM review_log WHERE card_id = $1", card
        )
    assert logged == "El {{answer}} duerme."


async def test_weak_areas_include_grammar_failures(pool):
    """Grammar failures reach the tutor's weak-area analysis, not just vocab."""
    from backend.repositories.tutor import get_weak_areas

    lang = await _language(pool, "weakg")
    user = await _new_user(pool, "weak@grammar")
    async with pool.privileged_connection() as conn:
        gp = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Weak pattern', 'A2', true, 1) RETURNING id", lang,
        )
        card = await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, lapses) "
            "VALUES ($1, $2, 'grammar', $3, 2) RETURNING id", user, lang, gp,
        )
        await conn.execute(
            "INSERT INTO review_log (user_id, card_id, quality, answer_result, "
            " interval_before, interval_after) "
            "VALUES ($1, $2, 1, 'wrong', 1, 1)", user, card,
        )
    async with pool.rls_connection(user) as conn:
        weak = await get_weak_areas(conn, user, lang)
    grammar_items = [w for w in weak if w["kind"] == "grammar"]
    assert grammar_items and grammar_items[0]["word"] == "Weak pattern"
    assert grammar_items[0]["level"] == "A2"
    assert int(grammar_items[0]["recent_failures"]) == 1


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
        # The fit job runs the WP8 held-out gate: a 4-review toy history is
        # (rightly) rejected rather than adopted, and rejection stores
        # nothing. Adoption mechanics are unit-tested; here we only need the
        # job to run cleanly, then seed a language row the way an ADOPTED
        # fit would be stored, to exercise resolution + RLS.
        await fit_languages(conn, min_reviews=2)
        from backend.repositories.fsrs_weights import upsert_language_weights

        fitted_params = [round(0.1 + i * 0.01, 2) for i in range(19)]
        await upsert_language_weights(
            conn, lang, fitted_params, review_count=4,
            log_loss=0.5, holdout_log_loss=0.45, defaults_holdout_log_loss=0.5,
        )
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


async def test_placement_includes_grammar_cloze(pool):
    """Placement mixes vocabulary and reviewed grammar cloze drills."""
    from backend.repositories.onboarding import (
        get_placement_answers,
        sample_placement_items,
    )

    lang = await _language(pool, "gplace")
    async with pool.privileged_connection() as conn:
        gp = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, display_order) "
            "VALUES ($1, 'Adjective agreement', 'A2', true, 1) RETURNING id", lang,
        )
        drill = await conn.fetchval(
            """
            INSERT INTO drill_sentences
                (grammar_point_id, sentence, answer, translation, display_order)
            VALUES ($1, 'la casa {{answer}}', 'roja', 'the red house', 1)
            RETURNING id
            """,
            gp,
        )

    async with pool.rls_connection(await _new_user(pool, "g@place")) as conn:
        items = await sample_placement_items(conn, lang)
        grammar_items = [i for i in items if i["kind"] == "grammar"]
        answers = await get_placement_answers(conn, lang, [str(drill)])

    assert grammar_items, "expected a grammar placement item"
    item = grammar_items[0]
    assert item["prompt"] == "la casa ____"  # the {{answer}} marker is blanked
    assert item["translation"] == "the red house"
    assert answers[str(drill)] == {"answer": "roja", "level": "A2"}


async def test_vocab_seeder_creates_content_lists(pool):
    """Seeding vocabulary also creates a content_list per level, so the words
    are immediately subscribable (otherwise 'Learn Vocabulary' stays empty)."""
    from backend.services.seeder.base import BaseSeeder

    from .conftest import INTEGRATION_DSN

    class _Seeder(BaseSeeder):
        language_code = "mi"

        async def download(self):  # pragma: no cover - not used
            pass

        async def transform(self):  # pragma: no cover - not used
            return []

    seeder = _Seeder(INTEGRATION_DSN)
    n = await seeder.load([
        {"word": "aroha", "level": "A1", "frequency_rank": 1,
         "translations": {"en": "love"}},
        {"word": "whenua", "level": "A2", "frequency_rank": 600,
         "translations": {"en": "land"}},
    ])
    assert n == 2

    async with pool.privileged_connection() as conn:
        rows = await conn.fetch(
            "SELECT level FROM content_lists "
            "WHERE list_type = 'vocabulary' "
            "AND language_id = (SELECT id FROM languages WHERE code = 'mi') "
            "ORDER BY level"
        )
    assert [r["level"] for r in rows] == ["A1", "A2"]


async def test_billing_grant_revoke_and_entitlement_rls(pool):
    """Stripe-driven grant/revoke toggles the tutor entitlement; users can read
    their own billing customer but cannot grant themselves entitlements."""
    from backend.repositories.billing import (
        get_customer_id,
        grant_entitlement,
        revoke_by_subscription,
        save_customer_id,
    )
    from backend.repositories.tutor import has_tutor_entitlement

    lang = await _language(pool, "bill")
    user = await _new_user(pool, "buyer@bill")
    other = await _new_user(pool, "other@bill")

    async with pool.privileged_connection() as conn:
        await grant_entitlement(
            conn, user, lang, subscription_id="sub_x", customer_id="cus_x"
        )
        assert await has_tutor_entitlement(conn, user, lang) is True

        # A canceled subscription webhook deactivates the entitlement.
        assert await revoke_by_subscription(conn, "sub_x") == 1
        assert await has_tutor_entitlement(conn, user, lang) is False

        await save_customer_id(conn, user, "cus_x")

    async with pool.rls_connection(user) as conn:
        # The user can read their own Stripe customer mapping.
        assert await get_customer_id(conn, user) == "cus_x"
        # ...but cannot grant themselves an entitlement (writes are service-role).
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
            await conn.execute(
                "INSERT INTO tutor_entitlements (user_id, language_id) VALUES ($1, $2)",
                user, lang,
            )

    async with pool.rls_connection(other) as conn:
        # Another user can't see the buyer's customer mapping.
        assert await get_customer_id(conn, other) is None


async def _card_ids(conn, user_id):
    rows = await conn.fetch(
        "SELECT card_id FROM user_cards WHERE user_id = $1 AND card_type = 'grammar'",
        user_id,
    )
    for r in rows:
        yield str(r["card_id"])


async def test_tutor_usage_kinds_and_cost_aggregation(pool):
    """WP9b: summary rows never count against allowances, token sums roll up
    per (language, model, kind), and one user can't read another's usage."""
    from datetime import UTC, datetime

    from backend.repositories.tutor import (
        aggregate_tutor_usage,
        count_tutor_messages,
        log_tutor_usage,
    )

    lang = await _language(pool, "cost")
    user = await _new_user(pool, "learner@cost")
    other = await _new_user(pool, "other@cost")
    epoch = datetime(2000, 1, 1, tzinfo=UTC)

    chat_usage = {"input_tokens": 100, "output_tokens": 40,
                  "cache_write_tokens": 10, "cache_read_tokens": 500}
    async with pool.rls_connection(user) as conn:
        await log_tutor_usage(conn, user, lang, "claude-sonnet-5",
                              usage=chat_usage)
        await log_tutor_usage(conn, user, lang, "claude-sonnet-5",
                              usage=chat_usage)
        await log_tutor_usage(conn, user, lang, "claude-sonnet-4-6",
                              usage={"input_tokens": 300, "output_tokens": 50},
                              kind="summary")

    async with pool.rls_connection(user) as conn:
        # The summarizer row is operator cost, not a spent message.
        assert await count_tutor_messages(conn, user, epoch) == 2
        # RLS: another user's window is untouched by these rows.
    async with pool.rls_connection(other) as conn:
        assert await count_tutor_messages(conn, other, epoch) == 0
        rows = await conn.fetch("SELECT 1 FROM tutor_usage")
        assert rows == []  # select-own policy holds

    async with pool.privileged_connection() as conn:
        rollup = {
            (r["model"], r["kind"]): r
            for r in await aggregate_tutor_usage(conn, epoch)
            if str(r["language_id"]) == lang
        }
    chat = rollup[("claude-sonnet-5", "chat")]
    assert chat["messages"] == 2
    assert chat["input_tokens"] == 200
    assert chat["output_tokens"] == 80
    assert chat["cache_write_tokens"] == 20
    assert chat["cache_read_tokens"] == 1000
    summary = rollup[("claude-sonnet-4-6", "summary")]
    assert summary["messages"] == 1
    assert summary["cache_read_tokens"] == 0  # NULL columns sum to 0


async def test_cram_and_search_respect_review_policy(pool):
    """WP13(f,g): cram cards and search hits only surface visible grammar
    (reviewed, or AI-passed under an 'ai_ok' policy), and search marks
    what's already in the caller's reviews."""
    from backend.repositories.cards import get_cram_cards
    from backend.repositories.curriculum import search_content

    lang = await _language(pool, "wp13fg")
    user = await _new_user(pool, "crammer@wp13")

    async with pool.privileged_connection() as conn:
        approved = str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, level) "
            "VALUES ($1, 'Locative case', true, 'A1') RETURNING id", lang,
        ))
        draft = str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, level) "
            "VALUES ($1, 'Locative draft', false, 'A1') RETURNING id", lang,
        ))
        for i in range(5):
            await conn.execute(
                "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, "
                "translation, display_order) VALUES ($1, $2, 'de', 'at home', $3)",
                approved, f"Ev{{{{answer}}}} kal {i}.", i,
            )
        await conn.execute(
            "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, display_order) "
            "VALUES ($1, 'Draft {{answer}}.', 'x', 0)", draft,
        )
        word = str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level) "
            "VALUES ($1, 'evde', 'A1') RETURNING id", lang,
        ))
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'at home')", word,
        )

    async with pool.rls_connection(user) as conn:
        # Cram: the draft point contributes nothing under the default
        # 'strict' policy; the approved point is capped at 3 drills.
        cards = await get_cram_cards(conn, [approved, draft])
        assert {c["card_id"] for c in cards} == {approved}
        assert len(cards) == 3

        results = await search_content(conn, user, lang, "locative")
        assert [g["title"] for g in results["grammar"]] == ["Locative case"]
        assert results["grammar"][0]["learned"] is False

        # ILIKE wildcards from user input match literally, not as wildcards.
        assert (await search_content(conn, user, lang, "%"))["grammar"] == []

        vocab_hits = await search_content(conn, user, lang, "at home")
        assert [v["word"] for v in vocab_hits["vocabulary"]] == ["evde"]

    # Once the point is in the user's reviews, search says so.
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
            "VALUES ($1, $2, 'grammar', $3)", user, lang, approved,
        )
    async with pool.rls_connection(user) as conn:
        results = await search_content(conn, user, lang, "locative")
        assert results["grammar"][0]["learned"] is True


async def test_english_support_locale_localizes_cards(pool):
    """'Learning English from Spanish': definitions prefer the support locale
    (falling back to the English definition) and example sentences are the
    ones whose translation is in that locale."""
    from backend.repositories.cards import get_card_detail, get_due_cards

    async with pool.privileged_connection() as conn:
        lang = str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ('en', 'English', false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
        ))
        word = str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level, frequency_rank) "
            "VALUES ($1, 'water', 'A1', 3) RETURNING id", lang,
        ))
        for locale, definition in (("en", "a clear liquid"), ("es", "agua")):
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, $2, $3) ON CONFLICT (vocabulary_id, locale) "
                "DO UPDATE SET definition = EXCLUDED.definition", word, locale, definition,
            )
        for locale, translation in (("es", "Bebo agua."), ("de", "Ich trinke Wasser.")):
            await conn.execute(
                "INSERT INTO example_sentences (language_id, vocabulary_id, sentence, "
                "translation, difficulty_rank, translation_locale) "
                "VALUES ($1, $2, 'I drink water.', $3, 3, $4) "
                "ON CONFLICT (vocabulary_id, sentence, translation_locale) DO NOTHING",
                lang, word, translation, locale,
            )

    user = await _new_user(pool, "learner@supploc")
    async with pool.privileged_connection() as conn:
        card = str(await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id, "
            "next_review) VALUES ($1, $2, 'vocabulary', $3, now() - interval '1h') "
            "RETURNING id", user, lang, word,
        ))

    async with pool.rls_connection(user) as conn:
        # Spanish support: the card clozes the Spanish-translated sentence,
        # the hint is the Spanish definition.
        cards = await get_due_cards(conn, lang, support_locale="es")
        c = next(x for x in cards if str(x["id"]) == card)
        assert "{{answer}}" in c["sentence"]
        assert c["translation"] == "Bebo agua."
        assert c["hint"] == "agua"

        detail = await get_card_detail(conn, card, support_locale="es")
        assert detail["definition"] == "agua"
        assert [e["translation"] for e in detail["examples"]] == ["Bebo agua."]

        # A locale with no content of its own: no sentences in that locale,
        # and the definition falls back to English.
        cards = await get_due_cards(conn, lang, support_locale="sw")
        c = next(x for x in cards if str(x["id"]) == card)
        assert c["sentence"] == "a clear liquid"  # definition-mode prompt
        assert c["translation"] is None

        # No support locale = today's behavior (English definitions).
        cards = await get_due_cards(conn, lang)
        c = next(x for x in cards if str(x["id"]) == card)
        assert c["sentence"] == "a clear liquid"


async def test_reset_progress_deck_and_language(pool):
    """Reset studies: per-deck and per-language wipes delete the caller's
    cards AND their review history (FK cascade), never touch another user,
    and leave deck subscriptions and content intact."""
    from backend.repositories.cards import (
        reset_deck_progress,
        reset_language_progress,
    )

    lang = await _language(pool, "rst")
    user = await _new_user(pool, "resetter@rst")
    other = await _new_user(pool, "bystander@rst")

    async with pool.privileged_connection() as conn:
        deck = str(await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'grammar', 'A1', 'RST A1 Grammar') RETURNING id", lang,
        ))
        point_a1 = str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, level) "
            "VALUES ($1, 'Reset point', true, 'A1') RETURNING id", lang,
        ))
        point_b1 = str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, level) "
            "VALUES ($1, 'Survivor point', true, 'B1') RETURNING id", lang,
        ))
        cards = {}
        for owner in (user, other):
            for point in (point_a1, point_b1):
                cards[(owner, point)] = str(await conn.fetchval(
                    "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
                    "VALUES ($1, $2, 'grammar', $3) RETURNING id", owner, lang, point,
                ))
                await conn.execute(
                    "INSERT INTO review_log (user_id, card_id, quality, "
                    "ease_factor_before, ease_factor_after, interval_before, "
                    "interval_after) VALUES ($1, $2, 4, 2.5, 2.6, 1, 3)",
                    owner, cards[(owner, point)],
                )
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", user, deck,
        )

    # Per-deck: only the caller's A1 card goes; B1 card and history survive.
    async with pool.rls_connection(user) as conn:
        result = await reset_deck_progress(conn, user, deck)
        assert result == {"cards_deleted": 1}
        assert await reset_deck_progress(conn, user, str(uuid.uuid4())) is None

    async with pool.privileged_connection() as conn:
        remaining = {
            str(r["card_id"]) for r in await conn.fetch(
                "SELECT card_id FROM user_cards WHERE user_id = $1", user)
        }
        assert remaining == {point_b1}
        # review_log cascade removed exactly the deleted card's history
        assert await conn.fetchval(
            "SELECT count(*) FROM review_log WHERE user_id = $1", user) == 1
        # the bystander is untouched, subscription survives
        assert await conn.fetchval(
            "SELECT count(*) FROM user_cards WHERE user_id = $1", other) == 2
        assert await conn.fetchval(
            "SELECT count(*) FROM user_content_subscriptions "
            "WHERE user_id = $1 AND content_list_id = $2", user, deck) == 1

    # Per-language: everything of the caller's in that language goes.
    async with pool.rls_connection(user) as conn:
        result = await reset_language_progress(conn, user, lang)
        assert result == {"cards_deleted": 1}

    async with pool.privileged_connection() as conn:
        assert await conn.fetchval(
            "SELECT count(*) FROM user_cards WHERE user_id = $1", user) == 0
        assert await conn.fetchval(
            "SELECT count(*) FROM review_log WHERE user_id = $1", user) == 0
        assert await conn.fetchval(
            "SELECT count(*) FROM user_cards WHERE user_id = $1", other) == 2
