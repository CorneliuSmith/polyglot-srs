"""The card a change request is ABOUT, resolved for the review board.

Owner: *"it is hard to decide when you don't see the full card."* The board
showed a bare label and a one-line complaint, which is not enough to judge
anything — whether a hint gives the answer away is a question about the
hint AND the sentence AND the answer, and only one of the three was on
screen.

`load_cards` resolves `target_type` + `target_id` into the live row. What is
worth testing is less the happy path than the four ways it is asked for
something that isn't there, because every one of them is a real state of the
board: a target kind that never had a row, a card deleted since the request
was raised, a request filed against nothing at all, and a mix of kinds in
one call (which must not turn into one query per row).

Runs against a real Postgres (see conftest); skips without one.
"""
from __future__ import annotations

from backend.repositories.change_requests import create_request, list_requests, load_cards

from .conftest import requires_db

pytestmark = requires_db


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
            "display_order) VALUES ($1, $2, 'Used for habitual actions.', 'A2', 1) "
            "RETURNING id",
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
            "reading) VALUES ($1, $2, 'A1', 'noun', 'peh-KEH-nya') RETURNING id",
            language_id, word,
        ))
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'small') ON CONFLICT DO NOTHING",
            vocab_id,
        )
        return vocab_id


async def _example(pool, language_id: str, vocab_id: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO example_sentences (language_id, vocabulary_id, sentence, "
            "translation) VALUES ($1, $2, 'La casa es pequeña.', "
            "'The house is small.') RETURNING id",
            language_id, vocab_id,
        ))


async def _raise(pool, author: str, language_id: str, target_type: str,
                 target_id: str | None, field: str, issue: str) -> str:
    async with pool.privileged_connection() as conn:
        return await create_request(
            conn, author, language_id, target_type, target_id,
            "a label", field, issue, None,
        )


async def _board(pool, language_id: str, viewer: str) -> list[dict]:
    async with pool.privileged_connection() as conn:
        requests = await list_requests(conn, language_id, viewer)
        await load_cards(conn, requests)
    return requests


async def test_a_drill_request_carries_the_sentence_answer_and_hint(pool):
    """The exact case from the report: "the hint doesn't fit with the
    sentence", where neither the hint nor the sentence was on screen."""
    lang = await _lang(pool, "cr1")
    author = await _user(pool, "tester-cr1@example.com")
    point = await _point(pool, lang, "Present tense · cr1")
    drill = await _drill(pool, point)
    await _raise(pool, author, lang, "drill", drill, "hint",
                 "The hint doesn't fit with the sentence")

    [req] = await _board(pool, lang, author)
    card = req["card"]
    assert card is not None
    assert card["sentence"] == "Casi no {{answer}} vino."
    # The answer is the half that makes "gives the answer away" decidable.
    assert card["answer"] == "queda"
    assert card["hint"] == "almost none is left"
    assert card["translation"] == "There is almost no wine left."
    # And what situates it — which point this drill is teaching.
    assert card["context"] == "Present tense · cr1"
    assert card["level"] == "A2"


async def test_a_vocabulary_request_carries_the_word_reading_and_definition(pool):
    lang = await _lang(pool, "cr2")
    author = await _user(pool, "tester-cr2@example.com")
    word = await _word(pool, lang, "pequeña")
    await _raise(pool, author, lang, "vocabulary", word, "translation",
                 "Too much info")

    [req] = await _board(pool, lang, author)
    assert req["card"]["sentence"] == "pequeña"
    assert req["card"]["hint"] == "peh-KEH-nya"
    assert req["card"]["translation"] == "small"
    assert req["card"]["context"] == "noun"


async def test_an_example_request_carries_the_word_it_illustrates(pool):
    lang = await _lang(pool, "cr3")
    author = await _user(pool, "tester-cr3@example.com")
    word = await _word(pool, lang, "casa")
    example = await _example(pool, lang, word)
    await _raise(pool, author, lang, "example_sentence", example, "sentence",
                 "Makes no sense")

    [req] = await _board(pool, lang, author)
    assert req["card"]["sentence"] == "La casa es pequeña."
    assert req["card"]["translation"] == "The house is small."
    assert req["card"]["context"] == "casa"


async def test_a_grammar_point_request_carries_its_explanation(pool):
    lang = await _lang(pool, "cr4")
    author = await _user(pool, "tester-cr4@example.com")
    point = await _point(pool, lang, "Subjunctive · cr4")
    await _raise(pool, author, lang, "grammar_point", point, "explanation",
                 "Explanation is circular")

    [req] = await _board(pool, lang, author)
    assert req["card"]["sentence"] == "Subjunctive · cr4"
    assert req["card"]["translation"] == "Used for habitual actions."


async def test_a_tutor_message_has_no_card_and_that_is_not_an_error(pool):
    """A tutor reply is generated per learner and never stored — the quote
    captured at flag time IS the record. Asking for a row would be asking
    for something that was never written."""
    lang = await _lang(pool, "cr5")
    author = await _user(pool, "tester-cr5@example.com")
    await _raise(pool, author, lang, "tutor_message", None, "other",
                 "The tutor said something wrong")

    [req] = await _board(pool, lang, author)
    assert req["card"] is None


async def test_a_deleted_card_leaves_the_request_readable(pool):
    """A request outlives the row it was raised against. The board has to
    survive that — it is the normal end state of "reject deletes the drill"
    followed by someone opening the request that asked for the rejection."""
    lang = await _lang(pool, "cr6")
    author = await _user(pool, "tester-cr6@example.com")
    point = await _point(pool, lang, "Present tense · cr6")
    drill = await _drill(pool, point)
    await _raise(pool, author, lang, "drill", drill, "sentence", "Remove it")

    async with pool.privileged_connection() as conn:
        await conn.execute("DELETE FROM drill_sentences WHERE id = $1", drill)

    [req] = await _board(pool, lang, author)
    assert req["card"] is None
    # The request itself is intact — the complaint still reads.
    assert req["issue"] == "Remove it"


async def test_mixed_kinds_resolve_together(pool):
    """One query per KIND present, not per request. The assertion that
    matters is that every row gets its own card and none get another's."""
    lang = await _lang(pool, "cr7")
    author = await _user(pool, "tester-cr7@example.com")
    point = await _point(pool, lang, "Present tense · cr7")
    drill = await _drill(pool, point)
    word = await _word(pool, lang, "vino")

    await _raise(pool, author, lang, "drill", drill, "hint", "Gives answer away")
    await _raise(pool, author, lang, "vocabulary", word, "translation", "Confusion")
    await _raise(pool, author, lang, "reading", None, "other", "Odd text")

    board = await _board(pool, lang, author)
    by_issue = {r["issue"]: r for r in board}
    assert by_issue["Gives answer away"]["card"]["answer"] == "queda"
    assert by_issue["Confusion"]["card"]["sentence"] == "vino"
    assert by_issue["Odd text"]["card"] is None
