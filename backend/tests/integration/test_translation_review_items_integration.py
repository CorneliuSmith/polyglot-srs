"""Non-vocabulary translation rejects, on a real database: the writer's
queue row → the admin list (typed, labelled, counted in the inbox) →
approve lands in the row's own layer, reviewed. Generator never called."""
from __future__ import annotations

import uuid

from backend.repositories.contributor import (
    list_translation_review_items,
    resolve_translation_review_item,
    review_inbox_counts,
)
from backend.services.auto_translate import _queue_review_item

from .conftest import requires_db

pytestmark = requires_db


async def _course(conn) -> dict:
    code = f"tr{uuid.uuid4().hex[:8]}"
    lang = await conn.fetchval(
        "INSERT INTO languages (code, name) VALUES ($1, 'Spanish') RETURNING id",
        code)
    point = await conn.fetchval(
        "INSERT INTO grammar_points (language_id, title, level, display_order, "
        "reviewed) VALUES ($1, 'Present tense', 'A1', 1, true) RETURNING id", lang)
    drill = await conn.fetchval(
        """INSERT INTO drill_sentences
               (grammar_point_id, sentence, answer, hint, translation,
                display_order, reviewed)
           VALUES ($1, 'Yo {{answer}} un libro.', 'leo', 'a verb',
                   'I read a book.', 1, true) RETURNING id""", point)
    vocab = await conn.fetchval(
        "INSERT INTO vocabulary (language_id, word, level) "
        "VALUES ($1, 'libro', 'A1') RETURNING id", lang)
    example = await conn.fetchval(
        """INSERT INTO example_sentences
               (language_id, vocabulary_id, sentence, translation,
                translation_locale, reviewed)
           VALUES ($1, $2, 'Leo un libro.', 'I read a book.', 'en', true)
           RETURNING id""", lang, vocab)
    pair = {"language_id": lang, "locale": "fr", "locale_name": "French",
            "language_code": code}
    return {"lang": lang, "point": point, "drill": drill, "vocab": vocab,
            "example": example, "pair": pair}


def _reject(proposed, note="unsure"):
    return {"verdict": "reject", "translation": "", "proposed": proposed,
            "note": note}


async def test_a_rejected_drill_hint_is_listed_counted_and_approved(pool):
    async with pool.privileged_connection() as conn:
        fx = await _course(conn)
        await _queue_review_item(conn, fx["pair"], "drill", "hint", fx["drill"],
                                 "a verb", _reject("un verbe"))
        # Queuing the same field twice is a no-op, not a duplicate row.
        await _queue_review_item(conn, fx["pair"], "drill", "hint", fx["drill"],
                                 "a verb", _reject("un autre verbe"))

        items = await list_translation_review_items(conn, language_id=str(fx["lang"]))
        assert len(items) == 1
        item = items[0]
        assert item["kind"] == "drill" and item["field"] == "hint"
        assert item["label"] == "Yo {{answer}} un libro."
        assert item["proposed"] == "un verbe"
        assert item["target_type"] == "drill"
        assert item["target_id"] == str(fx["drill"])

        # The inbox counts it under the gloss queue's key — one panel, one tile.
        counts = await review_inbox_counts(conn, str(fx["lang"]))
        assert counts["ai_translations"] == 1
        assert "ai_translation_items" not in counts

        assert await resolve_translation_review_item(conn, item["id"], True) == "ok"
        row = await conn.fetchrow(
            "SELECT hint, translation, reviewed FROM drill_hint_translations "
            "WHERE drill_id = $1 AND locale = 'fr'", fx["drill"])
        assert (row["hint"], row["translation"], row["reviewed"]) == ("un verbe", None, True)
        assert await list_translation_review_items(conn, language_id=str(fx["lang"])) == []
        assert (await review_inbox_counts(conn, str(fx["lang"])))["ai_translations"] == 0


async def test_grammar_meta_and_explanation_write_their_own_layers(pool):
    async with pool.privileged_connection() as conn:
        fx = await _course(conn)
        await _queue_review_item(conn, fx["pair"], "grammar_meta", "title",
                                 fx["point"], "Present tense", _reject("Le présent"))
        await _queue_review_item(conn, fx["pair"], "explanation", "explanation",
                                 fx["point"], "Use it for now.",
                                 _reject("Utilisez-le pour maintenant."))
        items = await list_translation_review_items(conn, language_id=str(fx["lang"]))
        assert sorted(i["kind"] for i in items) == ["explanation", "grammar_meta"]
        assert all(i["label"] == "Present tense" for i in items)
        assert all(i["target_type"] == "grammar_point" for i in items)
        for i in items:
            assert await resolve_translation_review_item(conn, i["id"], True) == "ok"
        assert await conn.fetchval(
            "SELECT title FROM grammar_point_translations "
            "WHERE grammar_point_id = $1 AND locale = 'fr'", fx["point"]) == "Le présent"
        assert await conn.fetchval(
            "SELECT explanation FROM explanation_translations "
            "WHERE grammar_point_id = $1 AND locale = 'fr'",
            fx["point"]) == "Utilisez-le pour maintenant."


async def test_an_approved_example_meaning_becomes_a_locale_row(pool):
    async with pool.privileged_connection() as conn:
        fx = await _course(conn)
        await _queue_review_item(conn, fx["pair"], "example", "translation",
                                 fx["example"], "I read a book.",
                                 _reject("Je lis un livre."))
        [item] = await list_translation_review_items(conn, language_id=str(fx["lang"]))
        assert item["label"] == "Leo un libro."
        assert item["target_type"] == "example_sentence"
        assert await resolve_translation_review_item(conn, item["id"], True) == "ok"
        row = await conn.fetchrow(
            "SELECT translation, reviewed, source FROM example_sentences "
            "WHERE vocabulary_id = $1 AND translation_locale = 'fr'", fx["vocab"])
        assert (row["translation"], row["reviewed"], row["source"]) == (
            "Je lis un livre.", True, "ai")


async def test_reject_clears_the_row_and_touches_no_layer(pool):
    async with pool.privileged_connection() as conn:
        fx = await _course(conn)
        await _queue_review_item(conn, fx["pair"], "drill", "translation",
                                 fx["drill"], "I read a book.", _reject(""))
        [item] = await list_translation_review_items(conn, language_id=str(fx["lang"]))
        assert item["proposed"] is None
        assert await resolve_translation_review_item(conn, item["id"], True) == "empty"
        assert await resolve_translation_review_item(conn, item["id"], False) == "ok"
        assert await conn.fetchval(
            "SELECT count(*) FROM drill_hint_translations WHERE drill_id = $1",
            fx["drill"]) == 0
        assert await resolve_translation_review_item(conn, item["id"], False) == "not_pending"
