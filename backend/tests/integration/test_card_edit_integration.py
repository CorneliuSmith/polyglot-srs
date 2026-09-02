"""Editing the card a review queue row is about, one kind at a time.

Owner: *"In the reviews i need to be able to view and edit the cards
referenced easily to actually decide if the student is right or wrong about
their feedback."* Seeing the card was the previous round; this is the other
half — the verdict on a learner report is usually "yes, and here is the
correction", and there was nowhere to make it without leaving the queue.

One endpoint serves four kinds, and each one lands in a different table with
different consequences: a drill edit de-certifies its point, an explanation
edit re-enters the review pool, a word's English definition is the source
every locale is translated from. That fan-out is what these tests pin, along
with the two rules that keep the editor from doing damage on the way past —
only the fields actually sent are written, and a word's own text is never
rewritten in place.

Runs against a real Postgres (see conftest); skips without one.
"""
from __future__ import annotations

from backend.repositories.contributor import card_language_id, edit_reviewed_card

from .conftest import requires_db

pytestmark = requires_db

EDITOR = "editor-cards@example.com"


async def _lang(pool, code: str) -> str:
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


async def _point(pool, language_id: str, title: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, explanation, level, "
            "display_order, reviewed) VALUES ($1, $2, 'Used for habits.', 'A2', "
            "1, true) RETURNING id",
            language_id, title,
        ))


async def _drill(pool, point_id: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, "
            "hint, translation) VALUES ($1, 'Casi no {{answer}} vino.', 'queda', "
            "'almost none is left', 'There is almost no wine left.') RETURNING id",
            point_id,
        ))


async def _word(pool, language_id: str, word: str) -> str:
    async with pool.privileged_connection() as conn:
        vocab_id = str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level, part_of_speech, "
            "reading) VALUES ($1, $2, 'A1', 'adj', 'peh-KEH-nya') RETURNING id",
            language_id, word,
        ))
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'small; little; of a young person, short') "
            "ON CONFLICT DO NOTHING",
            vocab_id,
        )
        return vocab_id


async def _edit(pool, target_type: str, target_id: str, fields: dict,
                editor: str) -> str:
    async with pool.privileged_connection() as conn:
        return await edit_reviewed_card(
            conn, target_type, target_id, fields, editor
        )


async def test_a_word_definition_is_corrected_where_the_report_is_read(pool):
    """The commonest row on the queue: "too much info" on a gloss.

    English is what gets edited because English is what every support locale
    is translated FROM — correcting only the locale rendering leaves the next
    locale to inherit the same sentence.
    """
    lang = await _lang(pool, "ce1")
    editor = await _user(pool, EDITOR)
    word = await _word(pool, lang, "pequeña")

    assert await _edit(pool, "vocabulary", word,
                       {"translation": "small"}, editor) == "ok"

    async with pool.privileged_connection() as conn:
        assert await conn.fetchval(
            "SELECT definition FROM translations WHERE vocabulary_id = $1 "
            "AND locale = 'en'", word) == "small"
        # The reading was not in the payload, so it is untouched — an editor
        # that offers two boxes must not blank the one it didn't show.
        assert await conn.fetchval(
            "SELECT reading FROM vocabulary WHERE id = $1", word) == "peh-KEH-nya"
        # And the edit is in the audit log, which is what makes it revertible.
        assert await conn.fetchval(
            "SELECT count(*) FROM content_change_log WHERE entity_id = $1 "
            "AND field = 'definition'", word) == 1


async def test_a_words_own_text_is_never_rewritten_in_place(pool):
    """The word IS the card's identity: user_cards, audio and every example
    point at that row. A rename here would silently re-target all of them,
    so `sentence` is not in the vocabulary editor's field list and is
    dropped rather than obeyed."""
    lang = await _lang(pool, "ce2")
    editor = await _user(pool, EDITOR)
    word = await _word(pool, lang, "cama")

    assert await _edit(pool, "vocabulary", word,
                       {"sentence": "camaX", "translation": "bed"},
                       editor) == "ok"

    async with pool.privileged_connection() as conn:
        assert await conn.fetchval(
            "SELECT word FROM vocabulary WHERE id = $1", word) == "cama"
        assert await conn.fetchval(
            "SELECT definition FROM translations WHERE vocabulary_id = $1 "
            "AND locale = 'en'", word) == "bed"


async def test_a_drill_edit_sends_its_point_back_for_re_approval(pool):
    """Editing from a queue must mean exactly what editing from the content
    editor means. For drills that includes de-certification: a second
    reviewer re-approves before learners see the change."""
    lang = await _lang(pool, "ce3")
    editor = await _user(pool, EDITOR)
    point = await _point(pool, lang, "Present tense · ce3")
    drill = await _drill(pool, point)

    assert await _edit(pool, "drill", drill,
                       {"hint": "there is hardly any left"}, editor) == "ok"

    async with pool.privileged_connection() as conn:
        row = await conn.fetchrow(
            "SELECT sentence, answer, hint, translation, is_modified "
            "FROM drill_sentences WHERE id = $1", drill)
        assert row["hint"] == "there is hardly any left"
        # Everything not sent survives the merge.
        assert row["sentence"] == "Casi no {{answer}} vino."
        assert row["answer"] == "queda"
        assert row["translation"] == "There is almost no wine left."
        assert row["is_modified"] is True
        assert await conn.fetchval(
            "SELECT reviewed FROM grammar_points WHERE id = $1", point) is False


async def test_a_grammar_title_and_explanation_are_both_reachable(pool):
    """The title is the first thing on a grammar card and had no editor at
    all outside the content workspace. The explanation goes through
    `save_explanation`, so it re-enters the review pool as it always has."""
    lang = await _lang(pool, "ce4")
    editor = await _user(pool, EDITOR)
    point = await _point(pool, lang, "Gender and number of nouns")

    assert await _edit(pool, "grammar_point", point,
                       {"sentence": "Gender and number",
                        "translation": "Nouns carry gender and number."},
                       editor) == "ok"

    async with pool.privileged_connection() as conn:
        row = await conn.fetchrow(
            "SELECT title, explanation, reviewed FROM grammar_points WHERE id = $1",
            point)
        assert row["title"] == "Gender and number"
        assert row["explanation"] == "Nouns carry gender and number."
        assert row["reviewed"] is False


async def test_a_card_that_is_gone_reports_itself_rather_than_erroring(pool):
    """A queue row outlives the card it names — the board already says so
    for the read; the write has to agree rather than raise."""
    lang = await _lang(pool, "ce5")
    editor = await _user(pool, EDITOR)
    word = await _word(pool, lang, "ya")
    async with pool.privileged_connection() as conn:
        await conn.execute("DELETE FROM translations WHERE vocabulary_id = $1", word)
        await conn.execute("DELETE FROM vocabulary WHERE id = $1", word)

    assert await _edit(pool, "vocabulary", word, {"translation": "x"},
                       editor) == "not_found"
    async with pool.privileged_connection() as conn:
        assert await card_language_id(conn, "vocabulary", word) is None
        # A malformed id comes off an old row too, and is the same answer.
        assert await card_language_id(conn, "vocabulary", "not-a-uuid") is None


async def test_a_kind_with_no_editable_card_is_refused_not_guessed_at(pool):
    """tutor_message and reading are generated per learner and never stored;
    'other' names nothing. There is no row to write, and inventing one is
    worse than saying so."""
    lang = await _lang(pool, "ce6")
    editor = await _user(pool, EDITOR)
    word = await _word(pool, lang, "queda")
    assert await _edit(pool, "tutor_message", word, {"translation": "x"},
                       editor) == "unsupported"
