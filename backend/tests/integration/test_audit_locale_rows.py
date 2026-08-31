"""Would a brand-new user get another language's translations?

The report: an English speaker, a NEW account, studying Spanish, shown
Arabic. A new profile has support_locale NULL, which cards.py maps to
English — so the profile cannot be the cause, and reading the query layer
found nothing either. That leaves one candidate the code cannot rule out:
a row STORED under the wrong language label, which is then served to
everybody as English.

These prove the detector actually detects that, against the real schema —
including the one case that matters, a Spanish row whose 'en' translation
is Arabic.
"""
from __future__ import annotations

import uuid

import asyncpg
import pytest

from backend.services.quality import audit_locale_rows as alr

from .conftest import INTEGRATION_DSN, requires_db

pytestmark = requires_db


@pytest.fixture
async def conn(schema):
    c = await asyncpg.connect(INTEGRATION_DSN)
    try:
        yield c
    finally:
        await c.close()


async def _spanish_course(conn) -> dict:
    # Full hex, never a slice — see test_seed_sentences_locale: these
    # codes share one session-scoped schema all run, and a truncated
    # tail collided in CI.
    code = f"zz{uuid.uuid4().hex}"
    lang_id = await conn.fetchval(
        "INSERT INTO languages (code, name) VALUES ($1, 'Spanish') RETURNING id",
        code)
    vocab_id = await conn.fetchval(
        "INSERT INTO vocabulary (language_id, word, level) "
        "VALUES ($1, 'libro', 'A1') RETURNING id", lang_id)
    point_id = await conn.fetchval(
        "INSERT INTO grammar_points (language_id, title, level, display_order) "
        "VALUES ($1, 'Present tense', 'A1', 1) RETURNING id", lang_id)
    return {"code": code, "lang_id": lang_id, "vocab_id": vocab_id,
            "point_id": point_id}


class TestTheReportedShape:
    async def test_arabic_filed_as_english_on_a_spanish_course_is_caught(
            self, conn):
        # THE case. translation_locale='en' means every learner reads this,
        # whatever their profile says — a new user included.
        fx = await _spanish_course(conn)
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'Leo un libro.', 'أقرأ كتابًا.', 'en')""",
            fx["lang_id"], fx["vocab_id"])

        found = await alr.scan_content(conn, fx["code"], 100)
        assert found == 1

    async def test_a_correct_course_is_silent(self, conn):
        fx = await _spanish_course(conn)
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'Leo un libro.', 'I read a book.', 'en')""",
            fx["lang_id"], fx["vocab_id"])
        await conn.execute(
            """INSERT INTO drill_sentences
                   (grammar_point_id, sentence, answer, translation,
                    display_order)
               VALUES ($1, 'Yo {{answer}} un libro.', 'leo',
                       'I read a book.', 1)""",
            fx["point_id"])

        assert await alr.scan_content(conn, fx["code"], 100) == 0

    async def test_a_properly_filed_arabic_rendering_is_not_a_finding(
            self, conn):
        # The whole point of multi-locale rows: Arabic under 'ar' is correct
        # and must not be reported, or the signal drowns in its own noise.
        fx = await _spanish_course(conn)
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'Leo un libro.', 'أقرأ كتابًا.', 'ar')""",
            fx["lang_id"], fx["vocab_id"])

        assert await alr.scan_content(conn, fx["code"], 100) == 0

    async def test_a_drill_translation_in_arabic_is_caught(self, conn):
        # drill_sentences.translation has no locale column — it IS the
        # English, so anything non-Latin there reaches every learner.
        fx = await _spanish_course(conn)
        await conn.execute(
            """INSERT INTO drill_sentences
                   (grammar_point_id, sentence, answer, translation,
                    display_order)
               VALUES ($1, 'Yo {{answer}} un libro.', 'leo',
                       'أقرأ كتابًا.', 1)""",
            fx["point_id"])

        assert await alr.scan_content(conn, fx["code"], 100) == 1

    async def test_a_vocabulary_definition_in_the_wrong_script_is_caught(
            self, conn):
        fx = await _spanish_course(conn)
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'كتاب')", fx["vocab_id"])

        assert await alr.scan_content(conn, fx["code"], 100) == 1


class TestNotCryingWolf:
    async def test_numbers_and_punctuation_are_not_a_language(self, conn):
        fx = await _spanish_course(conn)
        for text in ("1991", "—", "3.14 %"):
            await conn.execute(
                """INSERT INTO example_sentences
                       (language_id, vocabulary_id, sentence, translation,
                        translation_locale)
                   VALUES ($1, $2, $3, $4, 'en')""",
                fx["lang_id"], fx["vocab_id"], f"s-{text}", text)

        assert await alr.scan_content(conn, fx["code"], 100) == 0

    async def test_one_latin_language_is_never_accused_of_being_another(
            self, conn):
        # We can prove "this is Arabic". We cannot prove "this is Spanish
        # rather than Italian", and a checker that guessed would produce
        # findings nobody could act on.
        fx = await _spanish_course(conn)
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'Leo un libro.', 'Leggo un libro.', 'en')""",
            fx["lang_id"], fx["vocab_id"])

        assert await alr.scan_content(conn, fx["code"], 100) == 0


class TestTheAccountReport:
    async def test_an_unknown_address_says_so_instead_of_crashing(
            self, conn, capsys):
        await alr.check_user(conn, "nobody@example.invalid")
        assert "no such account" in capsys.readouterr().out
