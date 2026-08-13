"""Personal cloze cards: locale renderings, charged to the learner.

user_cloze_cards.translation is a single column with no locale dimension,
so a learner who switched their support language kept reading the language
the card was minted in — forever, with nothing able to fix it.

These are ONE learner's private sentences, so the background loop
deliberately never sweeps them; they're filled on request from that
learner's own allowance. That makes two properties worth pinning: the
learner is told the count and the cost before anything is spent, and a run
that produces nothing never charges them.
"""
from __future__ import annotations

from backend.repositories.cards import get_due_cards
from backend.repositories.personal_decks import (
    list_decks,
    list_personal_cards,
    store_card_translations,
    untranslated_cards,
)

from .conftest import requires_db

pytestmark = requires_db


async def _setup(pool, code: str, locale_code: str):
    async with pool.privileged_connection() as conn:
        lang = await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper())
        await conn.execute(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO NOTHING", locale_code, locale_code.upper())
        uid = await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id",
            f"pc-{code}@t")
        await conn.execute(
            "INSERT INTO user_profiles (id, active_language_id, support_locale) "
            "VALUES ($1, $2, $3) ON CONFLICT (id) DO UPDATE SET "
            "active_language_id = EXCLUDED.active_language_id, "
            "support_locale = EXCLUDED.support_locale",
            uid, lang, locale_code)
        cloze = await conn.fetchval(
            """INSERT INTO user_cloze_cards
                   (user_id, language_id, sentence, answer, translation)
               VALUES ($1, $2, 'Bu şehir çok {{answer}}.', 'büyük',
                       'This city is very big.')
               RETURNING id""",
            uid, lang)
        await conn.execute(
            """INSERT INTO user_cards
                   (user_id, language_id, card_type, card_id, ease_factor,
                    interval, repetitions, streak, lapses, next_review)
               VALUES ($1, $2, 'personal', $3, 2.5, 0, 0, 0, 0, now())""",
            uid, lang, cloze)
    return str(lang), str(uid), str(cloze)


async def test_personal_cards_serve_the_learners_locale_once_filled(pool):
    lang, uid, cloze = await _setup(pool, "pca", "pcb")

    async with pool.privileged_connection() as conn:
        # Before: the card reads in the language it was minted in.
        due = await get_due_cards(conn, lang, 20, "pcb")
        personal = [d for d in due if d["card_type"] == "personal"]
        assert personal, "personal card not served at all"
        assert personal[0]["translation"] == "This city is very big."

        # The learner can be told the count BEFORE anything is spent.
        pending = await untranslated_cards(conn, lang, "pcb")
        assert len(pending) == 1

        stored = await store_card_translations(
            conn, [(cloze, "Esta ciudad es muy grande.")], "pcb")
        assert stored == 1

        # After: the same read serves their language.
        due = await get_due_cards(conn, lang, 20, "pcb")
        personal = [d for d in due if d["card_type"] == "personal"]
        assert personal[0]["translation"] == "Esta ciudad es muy grande."

        # Nothing left to offer, so the learner is never asked to pay twice.
        assert await untranslated_cards(conn, lang, "pcb") == []

        # A different locale still falls back rather than showing Spanish.
        due_other = await get_due_cards(conn, lang, 20, "fr")
        other = [d for d in due_other if d["card_type"] == "personal"]
        assert other[0]["translation"] == "This city is very big."
    del uid


async def test_storing_is_idempotent_so_a_retry_never_double_charges(pool):
    lang, uid, cloze = await _setup(pool, "pcc", "pcd")
    async with pool.privileged_connection() as conn:
        await store_card_translations(conn, [(cloze, "Primera.")], "pcd")
        # A retry after a partial failure must not stack rows or re-bill.
        await store_card_translations(conn, [(cloze, "Segunda.")], "pcd")
        rows = await conn.fetch(
            "SELECT translation FROM user_cloze_card_translations "
            "WHERE cloze_id = $1 AND locale = 'pcd'", cloze)
        assert len(rows) == 1
        assert rows[0]["translation"] == "Primera."
    del uid, lang


async def test_english_support_is_never_offered_a_translation(pool):
    """Their content already IS English — there is nothing to buy."""
    lang, uid, _ = await _setup(pool, "pce", "pcf")
    async with pool.privileged_connection() as conn:
        assert await untranslated_cards(conn, lang, "en") == []
        assert await untranslated_cards(conn, lang, "") == []
    del uid


async def test_personal_cards_still_list_when_the_deck_migration_is_missing(pool):
    """The decks section reads personal_deck_id. When that migration hasn't
    landed the read used to 500, so the learner saw NO personal cards and no
    reason why — the "I still don't see it" report. Losing the folders is a
    smaller loss than losing every card."""
    lang, uid, _ = await _setup(pool, "pcg", "pch")
    async with pool.privileged_connection() as conn:
        cards = await list_personal_cards(conn, lang)
        assert len(cards) == 1
        assert cards[0]["answer"] == "büyük"
        assert cards[0]["deck_id"] is None
    del uid


async def test_a_learner_can_write_and_delete_their_own_cards(pool):
    """Authoring was deliberately off ("organization only"); the owner has
    since asked for it. Two properties matter: the blank is derived from the
    answer rather than typed by hand, and deleting takes the scheduling row
    with it — user_cards.card_id is polymorphic, so nothing cascades, and a
    stranded row keeps surfacing in reviews as a card with no text."""
    from backend.repositories.notes import create_personal_card
    from backend.repositories.personal_decks import (
        build_cloze,
        delete_personal_card,
    )

    lang, uid, _ = await _setup(pool, "pci", "pcj")

    # The blank is worked out, not typed. Whole words only and
    # case-insensitive, so a sentence-initial capital still matches, and a
    # word that is merely a substring of another does NOT.
    assert build_cloze("Bu ev çok guzel.", "guzel") == "Bu ev çok {{answer}}."
    assert build_cloze("Guzel bir ev.", "guzel") == "{{answer}} bir ev."
    assert build_cloze("Bu ev buyukbaba.", "buyuk") is None
    assert build_cloze("Bu ev güzel.", "kitap") is None

    async with pool.privileged_connection() as conn:
        sentence = build_cloze("Bu ev çok guzel.", "guzel")
        card_row = await create_personal_card(
            conn, uid, lang, sentence, "guzel", "This house is very nice.",
            None, None)
        assert card_row

        cards = await list_personal_cards(conn, lang)
        assert any(c["answer"] == "guzel" for c in cards)

        cloze_id = next(c["id"] for c in cards if c["answer"] == "guzel")
        due_before = await get_due_cards(conn, lang, 20, "pcj")
        assert any(str(d["card_id"]) == cloze_id for d in due_before)

        assert await delete_personal_card(conn, cloze_id) is True

        # Gone from the listing AND from the review queue — no orphan row.
        assert not any(c["id"] == cloze_id
                       for c in await list_personal_cards(conn, lang))
        assert not any(str(d["card_id"]) == cloze_id
                       for d in await get_due_cards(conn, lang, 20, "pcj"))
        assert await conn.fetchval(
            "SELECT count(*) FROM user_cards "
            "WHERE card_type = 'personal' AND card_id = $1", cloze_id) == 0

        # Deleting something already gone is reported, not crashed.
        assert await delete_personal_card(conn, cloze_id) is False


async def test_deleting_a_card_takes_its_locale_translations_with_it(pool):
    """The overlay is ON DELETE CASCADE — a deleted card must not leave
    private translated text behind."""
    from backend.repositories.personal_decks import delete_personal_card

    lang, uid, cloze = await _setup(pool, "pck", "pcl")
    async with pool.privileged_connection() as conn:
        await store_card_translations(conn, [(cloze, "Muy grande.")], "pcl")
        assert await conn.fetchval(
            "SELECT count(*) FROM user_cloze_card_translations "
            "WHERE cloze_id = $1", cloze) == 1

        await delete_personal_card(conn, cloze)
        assert await conn.fetchval(
            "SELECT count(*) FROM user_cloze_card_translations "
            "WHERE cloze_id = $1", cloze) == 0
    del uid, lang


async def test_the_review_session_survives_a_missing_overlay_migration(pool):
    """The whole review session must not die because ONE new table is absent.

    This is the trap the codebase documents and I walked into anyway: the
    pooled connection runs a single transaction, so a query naming a missing
    table doesn't just fail itself — it aborts the transaction, and every
    later query in the request dies too, INCLUDING the fallback meant to
    rescue it. try/except reads as safe and isn't. Probing with to_regclass
    never raises, so nothing is poisoned.

    Symptom when this regresses: get_due_cards 500s and the review page sits
    on "Loading cards…" forever.
    """
    lang, uid, _ = await _setup(pool, "pcm", "pcn")

    async with pool.privileged_connection() as conn:
        await conn.execute(
            "ALTER TABLE user_cloze_card_translations RENAME TO ucct_hidden")
        try:
            # Vocabulary, grammar AND personal cards all still come back.
            due = await get_due_cards(conn, lang, 20, "pcn")
            assert any(d["card_type"] == "personal" for d in due)
            # The card falls back to its minted-language translation.
            personal = next(d for d in due if d["card_type"] == "personal")
            assert personal["translation"] == "This city is very big."

            # The transaction is still usable — the real tell. Under the old
            # try/except this raised "current transaction is aborted".
            assert await conn.fetchval("SELECT 1") == 1

            # And the deck listing degrades rather than exploding.
            assert await untranslated_cards(conn, lang, "pcn") == []
            assert len(await list_personal_cards(conn, lang)) == 1
            assert await conn.fetchval("SELECT 1") == 1
        finally:
            await conn.execute(
                "ALTER TABLE ucct_hidden RENAME TO user_cloze_card_translations")
    del uid


async def test_personal_decks_survive_a_missing_deck_migration(pool):
    """Same discipline for the older personal_decks migration."""
    lang, uid, _ = await _setup(pool, "pco", "pcp")

    async with pool.privileged_connection() as conn:
        await conn.execute("ALTER TABLE personal_decks RENAME TO pd_hidden")
        try:
            assert await list_decks(conn, lang) == []
            assert await conn.fetchval("SELECT 1") == 1
        finally:
            await conn.execute("ALTER TABLE pd_hidden RENAME TO personal_decks")
    del uid


async def test_an_untranslated_card_is_flagged_before_it_reaches_the_learner(pool):
    """The reported screen, reproduced through the real query.

    A learner studying Turkish with Arabic support saw
    "This city is very big and millions of people live there." under the
    heading الترجمة. Nothing failed: the personal card was minted in
    English, no Arabic rendering existed, and the payload carried no way
    for the UI to know which language it had been handed.
    """
    lang, uid, cloze = await _setup(pool, "lgt", "ar")

    async with pool.privileged_connection() as conn:
        due = await get_due_cards(conn, lang, 20, "ar")
        card = next(d for d in due if d["card_type"] == "personal")

        # Served, because a cloze with no cue at all is worse than one in
        # the wrong language — but no longer served as if it were Arabic.
        assert card["translation"] == "This city is very big."
        assert card["locale_mismatch"] == ["translation"]

        # The hint is the learner's own Turkish answer. Flagging it would
        # mark every personal card of every non-Latin learner.
        assert "hint" not in card["locale_mismatch"]

        # Once their language lands, the flag goes away entirely.
        await store_card_translations(
            conn, [(cloze, "هذه المدينة كبيرة جداً.")], "ar")
        due = await get_due_cards(conn, lang, 20, "ar")
        card = next(d for d in due if d["card_type"] == "personal")
        assert card["translation"] == "هذه المدينة كبيرة جداً."
        assert "locale_mismatch" not in card
    del uid


async def test_a_latin_script_learner_sees_no_change(pool):
    """Script cannot separate English from Spanish, so the guard says
    nothing rather than guessing — and must not start stamping every card
    of every Latin-script learner."""
    lang, uid, _ = await _setup(pool, "lgs", "es")

    async with pool.privileged_connection() as conn:
        due = await get_due_cards(conn, lang, 20, "es")
        card = next(d for d in due if d["card_type"] == "personal")
        assert card["translation"] == "This city is very big."
        assert "locale_mismatch" not in card
    del uid
