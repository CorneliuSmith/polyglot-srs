"""The full learner walkthrough, localized: every page's read path, before
and after the loop runs.

This is the owner's "cycle through each page" guarantee as a test. One
learner story per pair: set the profile → start a learn session → every
surface serves English (and records demand) → one translation cycle → the
SAME reads now serve the locale. Surfaces covered: learn details, due
cards, card detail (vocab + grammar), Gym cram cards, the grammar path,
the lesson page, deck items (grammar + vocab), and the vocab item view.

Two pairs run: a normal one (course ≠ locale) and the SELF-pair (learning
Spanish with Spanish support) — the configuration the owner actually tests
with, which the loop used to exclude entirely.
"""
from __future__ import annotations

from backend.repositories.cards import (
    add_mixed_learn_batch,
    confirm_learn_batch,
    get_card_detail,
    get_card_details_bulk,
    get_cram_cards,
    get_deck_items,
    get_due_cards,
    get_vocab_item,
)
from backend.repositories.curriculum import get_curriculum, get_curriculum_point
from backend.services.auto_translate import run_translation_cycle

from .conftest import requires_db
from .test_auto_translate_integration import _lang, _learner, _mock_ai

pytestmark = requires_db


async def _cycle(pool):
    async with pool.privileged_connection() as conn:
        return await run_translation_cycle(conn)


async def _build_course(pool, lang: str, uid: str, tag: str) -> dict:
    """A minimal but complete course: two subscribed decks (vocab + grammar),
    two words with English glosses and a reviewed English example sentence,
    two grammar points with explanation/culture/function notes and a
    reviewed drill each. Two of everything, because the mock checker
    rejects the FIRST item of every batch — assertions target the second."""
    async with pool.privileged_connection() as conn:
        vdeck = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 Vocabulary') RETURNING id", lang)
        gdeck = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'grammar', 'A1', 'A1 Grammar') RETURNING id", lang)
        for deck in (vdeck, gdeck):
            await conn.execute(
                "INSERT INTO user_content_subscriptions "
                "(user_id, content_list_id) VALUES ($1, $2)", uid, deck)
        words = []
        for i, (w, gloss) in enumerate(
            [(f"{tag}akvo", "water"), (f"{tag}domo", "house")]
        ):
            vid = await conn.fetchval(
                "INSERT INTO vocabulary (language_id, word, level, "
                "frequency_rank) VALUES ($1, $2, 'A1', $3) RETURNING id",
                lang, w, i + 1)
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, 'en', $2)", vid, gloss)
            await conn.execute(
                "INSERT INTO example_sentences (language_id, vocabulary_id, "
                "sentence, translation, translation_locale, reviewed) "
                "VALUES ($1, $2, $3, $4, 'en', true)",
                lang, vid, f"La {w} estas.", f"The {gloss} is here.")
            words.append(str(vid))
        points, drills = [], []
        for i, title in enumerate([f"{tag} first point", f"{tag} second point"]):
            gp = await conn.fetchval(
                "INSERT INTO grammar_points (language_id, title, level, "
                "reviewed, display_order, explanation, culture_note, "
                "function_note) VALUES ($1, $2, 'A1', true, $3, "
                "'How it works.', 'A cultural aside.', 'What it does.') "
                "RETURNING id", lang, title, i + 1)
            d = await conn.fetchval(
                "INSERT INTO drill_sentences (grammar_point_id, sentence, "
                "answer, source, reviewed, display_order, translation, hint) "
                "VALUES ($1, 'Mi {{answer}}.', 'vidas', 'seed', true, 1, "
                "'I see it.', 'the verb to see') RETURNING id", gp)
            points.append(str(gp))
            drills.append(str(d))
    return {"words": words, "points": points, "drills": drills,
            "vdeck": str(vdeck), "gdeck": str(gdeck)}


async def _walkthrough(pool, code: str, locale_code: str, locale_name: str,
                       tag: str):
    """The shared story, parameterized so the normal pair and the self-pair
    run the identical page cycle."""
    course = await _lang(pool, code, code.capitalize() + "ish", auto=True)
    if locale_code != code:
        await _lang(pool, locale_code, locale_name, auto=False)
    uid = await _learner(pool, f"walk@{code}", course, locale_code)
    c = await _build_course(pool, course, uid, tag)
    mark = f"[{locale_name}]"

    async with pool.privileged_connection() as conn:
        # ---- Learn session start: batch + details, English first ----------
        batch = await add_mixed_learn_batch(conn, uid, course, 10)
        assert batch["added"] == 4
        card_ids = [str(i) for i in batch["items"]]
        details = await get_card_details_bulk(conn, card_ids, locale_code)
        titles = {d["title"] for d in details.values()}
        assert f"{tag} second point" in titles  # authored English served
        # Demand was recorded for every kind the learn session touched.
        kinds = {r["kind"] for r in await conn.fetch(
            "SELECT DISTINCT kind FROM translation_demand WHERE locale = $1",
            locale_code)}
        assert {"word", "drill", "explanation", "grammar_meta",
                "example"} <= kinds

    # ---- One loop cycle ---------------------------------------------------
    stats = await _cycle(pool)
    assert stats["demand"] >= 1

    async with pool.privileged_connection() as conn:
        # ---- Learn details, reloaded: localized ---------------------------
        details = await get_card_details_bulk(conn, card_ids, locale_code)
        by_title = {d["title"]: d for d in details.values()}
        gp2 = by_title.get(f"{mark} {tag} second point")
        assert gp2 is not None, f"localized title missing in {by_title.keys()}"
        assert gp2["explanation"].startswith(mark)
        assert gp2["culture_note"].startswith(mark)
        # The second word's gloss (first is the mock's designated reject).
        defs = [d.get("definition") for d in details.values()
                if d["card_type"] == "vocabulary"]
        # The gloss mock echoes the headword; the first word is the mock's
        # designated reject and keeps its English gloss.
        assert f"[{tag}domo]" in defs

        # ---- Review session: due cards ------------------------------------
        # A due review card shows the drill (hint + translation), not the
        # point name — those are the strings that must have switched.
        await confirm_learn_batch(conn, uid, card_ids)
        due = await get_due_cards(conn, course, 20, locale_code)
        gp2_due = next(
            d for d in due
            if d["card_type"] == "grammar"
            and str(d["card_id"]) == c["points"][1])
        assert gp2_due["hint"] == f"{mark} the verb to see"
        assert gp2_due["translation"] == f"{mark} I see it."

        # ---- Card detail (the ⓘ view) -------------------------------------
        detail = await get_card_detail(conn, str(gp2_due["id"]), locale_code)
        assert detail["title"] == f"{mark} {tag} second point"
        assert detail["explanation"].startswith(mark)
        assert detail["culture_note"].startswith(mark)

        # ---- Gym cram cards -----------------------------------------------
        cram = await get_cram_cards(conn, c["points"], per_point=1,
                                    support_locale=locale_code, user_id=uid)
        cram2 = next(x for x in cram
                     if str(x["card_id"]) == c["points"][1])
        assert cram2["title"] == f"{mark} {tag} second point"
        assert cram2["translation"] == f"{mark} I see it."
        # Owner's rule: the Gym HINT stays the authored baseline.
        assert cram2["hint"] == "the verb to see"

        # ---- Grammar path + lesson page -----------------------------------
        path = await get_curriculum(conn, uid, course, locale_code)
        path_titles = {p["title"] for p in path}
        assert f"{mark} {tag} second point" in path_titles
        lesson = await get_curriculum_point(conn, uid, c["points"][1],
                                            locale_code)
        assert lesson["title"] == f"{mark} {tag} second point"
        assert lesson["explanation"].startswith(mark)
        assert lesson["culture_note"].startswith(mark)
        assert lesson["examples"][0]["translation"] == f"{mark} I see it."

        # ---- Deck browser: items + vocab item -----------------------------
        gitems = await get_deck_items(conn, c["gdeck"], 50, locale_code)
        assert f"{mark} {tag} second point" in {
            i["item"] for i in gitems["items"]}
        vitems = await get_deck_items(conn, c["vdeck"], 50, locale_code)
        assert f"[{tag}domo]" in {i["detail"] for i in vitems["items"]}
        vocab = await get_vocab_item(conn, c["words"][1], locale_code)
        assert vocab["definition"] == f"[{tag}domo]"

        # ---- Example sentences: translated but PENDING (the review gate) --
        ex = await conn.fetch(
            "SELECT translation, reviewed FROM example_sentences "
            "WHERE translation_locale = $1 AND language_id = $2", locale_code,
            course)
        assert ex, "locale sibling rows were not created"
        assert all(r["reviewed"] is False for r in ex)
        assert any(r["translation"].startswith(mark) for r in ex)

        # ---- The demand queue drained -------------------------------------
        # Everything translated stays quiet; only kinds whose first-of-batch
        # rendering the mock REJECTED (and which retry by design — an
        # explanation stores nothing on reject, an example gets no sibling
        # row) may have been re-noted by the reloads above.
        left = {r["kind"] for r in await conn.fetch(
            "SELECT kind FROM translation_demand WHERE locale = $1",
            locale_code)}
        assert left <= {"explanation", "example"}, left

        # Leave nothing running: retryable rejects on an auto-enabled course
        # would leak into other tests' cycle counts in the same session.
        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
        await conn.execute(
            "DELETE FROM translation_demand WHERE locale = $1", locale_code)


async def test_every_page_localizes_after_one_cycle(pool, monkeypatch):
    """Normal pair: a course studied FROM another language."""
    _mock_ai(monkeypatch)
    await _walkthrough(pool, "wk1", "es9", "Spanish9", "wk1")


async def test_the_self_pair_localizes_too(pool, monkeypatch):
    """The owner's own configuration: Spanish UI, Spanish course. The
    support locale IS the course language, and every surface still renders
    in it — hints, titles, explanations are English text ABOUT the course,
    not self-translations."""
    _mock_ai(monkeypatch)
    await _walkthrough(pool, "zz8", "zz8", "Zz8ish", "zz8")


async def test_everything_degrades_when_the_migration_is_missing(pool, monkeypatch):
    """The state production was actually in: migration 20260914 not applied.

    Every connection here runs inside ONE transaction (pool.py), so a query
    against a missing table doesn't just fail — it aborts the transaction
    and every later query in the same request dies with it. That's how the
    Gym vanished for locale-set learners and how whole sweeps died without
    translating anything. This drops the three new tables (inside a rolled-
    back savepoint) and drives every touched path: reads serve English, the
    sweep still translates the old kinds, the Gym overlay yields {}, and —
    the actual regression — the connection stays usable afterwards."""
    from backend.repositories import cards as cards_repo
    from backend.repositories.cards import pretranslate_upcoming
    from backend.routers.gym import label_overlay
    from backend.services.auto_translate import note_missing_content

    _mock_ai(monkeypatch)
    course = await _lang(pool, "dg1", "Degradish", auto=True)
    await _lang(pool, "fr9", "French9", auto=False)
    uid = await _learner(pool, "degrade@dg1", course, "fr9")
    c = await _build_course(pool, course, uid, "dg1")

    async with pool.privileged_connection() as conn:
        sp = conn.transaction()
        await sp.start()
        try:
            for t in ("translation_demand", "gym_label_translations",
                      "grammar_point_translations"):
                await conn.execute(f"DROP TABLE {t}")
            # The positive cache would happily join a table we just dropped.
            cards_repo._TABLE_EXISTS.clear()

            # Learn start (incl. the pre-translate lookahead) must not blow up.
            batch = await add_mixed_learn_batch(conn, uid, course, 4)
            assert batch["added"] == 4
            await pretranslate_upcoming(conn, uid, course, 4)

            # Every read path serves the authored English, no exception.
            details = await get_card_details_bulk(
                conn, [str(i) for i in batch["items"]], "fr9")
            assert "dg1 second point" in {d["title"] for d in details.values()}
            await confirm_learn_batch(conn, uid,
                                      [str(i) for i in batch["items"]])
            due = await get_due_cards(conn, course, 20, "fr9")
            gp2 = next(d for d in due if d["card_type"] == "grammar"
                       and str(d["card_id"]) == c["points"][1])
            assert gp2["hint"] == "the verb to see"
            lesson = await get_curriculum_point(conn, uid, c["points"][1],
                                               "fr9")
            assert lesson["title"] == "dg1 second point"
            cram = await get_cram_cards(conn, c["points"], per_point=1,
                                        support_locale="fr9", user_id=uid)
            assert cram

            # Demand recording is a silent no-op, not a transaction poison.
            await note_missing_content(conn, "fr9", vocab_ids=c["words"],
                                       grammar_ids=c["points"])

            # The Gym overlay degrades to English labels, not a 500.
            manifest = {"columns": [{"entries": [{"point": "dg1 first point",
                                                  "label": "P1"}]}]}
            assert await label_overlay(conn, "dg1", "fr9", manifest,
                                       course) == {}

            # The sweep still translates the kinds whose tables exist.
            stats = await run_translation_cycle(conn)
            assert stats["applied"] >= 1 or stats["drills"] >= 1
            assert stats["demand"] == 0
            assert stats["grammar_meta"] == 0
            assert stats["gym_labels"] == 0

            # THE regression: the transaction survived all of the above.
            assert await conn.fetchval("SELECT 1") == 1
        finally:
            await sp.rollback()
            cards_repo._TABLE_EXISTS.clear()
        # Tables are back and the outer transaction is healthy.
        assert await conn.fetchval(
            "SELECT to_regclass('translation_demand') IS NOT NULL")
        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
