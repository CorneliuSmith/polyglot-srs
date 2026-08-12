"""Every submission channel, end to end: a NON-admin files something and the
admin sees it — through the exact query the admin's panel runs.

This is the regression suite for the owner's complaint: *"testers submit
reviews, the admin never sees them."* Nothing was lost on the way in; the
rows were there the whole time. What was missing was the path OUT — a queue
the admin's panel didn't read, a language the selector wasn't pointed at, a
count that stayed zero. So each test here writes with the same repository
call the submitting endpoint uses, and reads with the same one the admin's
panel uses, and asserts the roll-up tile the admin actually looks at moves.

Two failure shapes are covered beyond the plain round trip:

  * cross-language — a submission carries the language its author was
    STUDYING, while every review surface is scoped to the admin's working
    language. This is the exact scenario that hid the testers' reviews, so
    it gets a test where EVERY channel is filed against language A and the
    admin sits on B;
  * missing schema — migrations are owner-applied, so a deploy runs ahead of
    the schema routinely. An inbox that 500s is an inbox that shows nothing,
    which is the same outage from the admin's chair.

Runs against a real Postgres (see conftest); skips without one.
"""
from __future__ import annotations

from backend.repositories.change_requests import create_request, list_requests
from backend.repositories.contributor import (
    add_example_sentence,
    add_recommendation,
    add_review_note,
    add_vocab_review_note,
    list_feedback,
    list_pending_examples,
    list_review_notes,
    list_suggestions,
    list_tester_recommendations,
    list_vocab_items,
    recommendations_for_targets,
    review_inbox_counts,
    review_inbox_other_languages,
    submit_suggestion,
)
from backend.repositories.review import add_card_feedback

from .conftest import requires_db

pytestmark = requires_db


# ── fixtures-by-hand (same shape as the other contributor integration tests) ─

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


async def _grant(pool, user_id: str, language_id: str | None, role: str) -> None:
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, language_id, role) "
            "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            user_id, language_id, role,
        )


async def _point(pool, language_id: str, title: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, reviewed, display_order) "
            "VALUES ($1, $2, true, 1) RETURNING id",
            language_id, title,
        ))


async def _word(pool, language_id: str, word: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level) "
            "VALUES ($1, $2, 'A1') RETURNING id",
            language_id, word,
        ))


async def _card(pool, user_id: str, language_id: str, card_type: str, card_id: str) -> str:
    """A learner's own card — what "Report an issue" is filed against."""
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            user_id, language_id, card_type, card_id,
        ))


# ── one test per submission channel ─────────────────────────────────────────

async def test_card_feedback_from_a_learner_reaches_the_admin_queue(pool):
    """Channel 1: "Report an issue" on a card, filed by a plain learner with
    no roles at all, through their OWN RLS connection — the least privileged
    writer in the system. It has to land in the contributor feedback queue
    and be counted by the inbox."""
    lang = await _lang(pool, "sv1")
    learner = await _user(pool, "learner@sv1")
    point = await _point(pool, lang, "Locative")
    card = await _card(pool, learner, lang, "grammar", point)

    # Submitted exactly as the endpoint does it: the learner's own connection,
    # RLS on, no contributor role anywhere.
    async with pool.rls_connection(learner) as conn:
        assert await add_card_feedback(
            conn, learner, card, "the translation says the opposite"
        ) is True

    async with pool.privileged_connection() as conn:
        queue = await list_feedback(conn, lang)
        assert [f["message"] for f in queue] == [
            "the translation says the opposite"
        ]
        # The panel identifies the card by title, not a bare uuid.
        assert queue[0]["card_title"] == "Locative"
        assert queue[0]["card_type"] == "grammar"
        assert (await review_inbox_counts(conn, lang))["feedback"] == 1


async def test_grammar_review_note_from_a_tester_reaches_the_admin_queue(pool):
    """Channel 2: a written note on a grammar point. A tester's judgement in
    prose is the highest-value thing they produce, and the notes board is
    where an admin reads it."""
    lang = await _lang(pool, "sv2")
    tester = await _user(pool, "tester@sv2")
    await _grant(pool, tester, lang, "trial_reviewer")
    point = await _point(pool, lang, "Aspect pairs")

    async with pool.privileged_connection() as conn:
        await add_review_note(conn, point, tester, "the perfective gloss is reversed")

        notes = await list_review_notes(conn, lang)
        assert len(notes) == 1
        assert notes[0]["entity_type"] == "grammar"
        assert notes[0]["entity_label"] == "Aspect pairs"
        assert notes[0]["note"] == "the perfective gloss is reversed"
        # Attributed, so the admin can go back to whoever filed it.
        assert notes[0]["author_email"] == "tester@sv2"
        assert (await review_inbox_counts(conn, lang))["notes"] == 1


async def test_vocab_review_note_from_a_tester_reaches_the_admin_queue(pool):
    """Channel 3: the same note box, on a word instead of a point. It shares
    a table with grammar notes and a queue with them, and the language it
    resolves through is the WORD's — a join that has no test above."""
    lang = await _lang(pool, "sv3")
    tester = await _user(pool, "tester@sv3")
    await _grant(pool, tester, lang, "trial_reviewer")
    word = await _word(pool, lang, "chai")

    async with pool.privileged_connection() as conn:
        await add_vocab_review_note(conn, word, tester, "this gloss is regional")

        notes = await list_review_notes(conn, lang)
        assert len(notes) == 1
        assert notes[0]["entity_type"] == "vocab"
        assert notes[0]["entity_label"] == "chai"
        assert notes[0]["vocabulary_id"] == word
        assert (await review_inbox_counts(conn, lang))["notes"] == 1


async def test_change_request_from_a_tester_reaches_the_board_as_advisory(pool):
    """Channel 4: the votable board. Testers may raise here now, so their
    row must reach the admin's board — and be distinguishable from a full
    contributor's, since it carries no publishing standing."""
    lang = await _lang(pool, "sv4")
    tester = await _user(pool, "tester@sv4")
    contributor = await _user(pool, "contributor@sv4")
    admin = await _user(pool, "admin@sv4")
    await _grant(pool, tester, lang, "trial_reviewer")
    await _grant(pool, contributor, lang, "contributor")
    await _grant(pool, admin, None, "admin")

    async with pool.privileged_connection() as conn:
        await create_request(
            conn, tester, lang, "vocabulary", None, "chai",
            "translation", "the gender agreement is wrong", None,
        )
        await create_request(
            conn, contributor, lang, "vocabulary", None, "chai",
            "explanation", "same word, staff view", None,
        )

        # Read as the ADMIN — the viewer whose board this is.
        board = {r["issue"]: r for r in await list_requests(conn, lang, admin)}
        assert set(board) == {
            "the gender agreement is wrong", "same word, staff view",
        }
        assert board["the gender agreement is wrong"]["is_advisory"] is True
        assert board["the gender agreement is wrong"]["author_email"] == "tester@sv4"
        # A contributor's request is a peer's, not advice.
        assert board["same word, staff view"]["is_advisory"] is False
        assert (await review_inbox_counts(conn, lang))["change_requests"] == 2


async def test_content_suggestion_from_a_contributor_reaches_the_admin_queue(pool):
    """Channel 5: a proposed edit to a live card. Nothing goes live until a
    reviewer approves it, which makes the approval queue the only place it
    can be seen at all."""
    lang = await _lang(pool, "sv5")
    author = await _user(pool, "contributor@sv5")
    await _grant(pool, author, lang, "contributor")
    word = await _word(pool, lang, "silla")

    async with pool.privileged_connection() as conn:
        await submit_suggestion(
            conn, lang, "vocabulary", word, author,
            {"definition": "chair (seat with a back)"}, "the current gloss is a stub",
        )

        pending = await list_suggestions(conn, lang)
        assert len(pending) == 1
        assert pending[0]["entity_type"] == "vocabulary"
        assert pending[0]["card_title"] == "silla"
        assert pending[0]["proposed"] == {"definition": "chair (seat with a back)"}
        assert pending[0]["note"] == "the current gloss is a stub"
        assert (await review_inbox_counts(conn, lang))["suggestions"] == 1


async def test_tester_recommendation_reaches_both_admin_surfaces(pool):
    """Channel 6: the advisory approve/reject a trial reviewer leaves on a
    pending item — for most testers the ONLY thing they produce.

    It has to be readable in two places, because either one alone loses it:
    the standalone queue (which survives), and the generation panel that
    lists the item itself (where the bulk-approve button is — approving
    DELETES the pending row and takes the note with it).
    """
    lang = await _lang(pool, "sv6")
    tester = await _user(pool, "tester@sv6")
    await _grant(pool, tester, lang, "trial_reviewer")
    word = await _word(pool, lang, "libro")

    async with pool.privileged_connection() as conn:
        example = await add_example_sentence(
            conn, word, lang, "Leo un libro.", "I read a book.", source="ai"
        )
        await add_recommendation(
            conn, tester, lang, "example", example, "reject",
            note="'Leo' reads as the name Leo here.",
        )

        # Surface A — the standalone queue.
        listed = await list_tester_recommendations(conn, lang)
        assert len(listed) == 1
        assert listed[0]["recommendation"] == "reject"
        assert listed[0]["note"] == "'Leo' reads as the name Leo here."
        assert listed[0]["recommender_email"] == "tester@sv6"

        # Surface B — the pending row itself, as the generation panel builds
        # it (list + tally, the same pair the endpoint calls).
        pending = await list_pending_examples(conn, lang)
        tally = await recommendations_for_targets(
            conn, "example", [e["id"] for e in pending]
        )
        assert tally[example]["reject"] == 1
        assert tally[example]["notes"] == ["'Leo' reads as the name Leo here."]

        assert (await review_inbox_counts(conn, lang))["tester_recommendations"] == 1


# ── the cross-language failure, with every channel at once ──────────────────

async def _file_one_of_everything(pool, lang: str, suffix: str) -> dict:
    """One submission per channel against *lang*, all from non-admins."""
    learner = await _user(pool, f"learner@{suffix}")
    tester = await _user(pool, f"tester@{suffix}")
    contributor = await _user(pool, f"contributor@{suffix}")
    await _grant(pool, tester, lang, "trial_reviewer")
    await _grant(pool, contributor, lang, "contributor")

    point = await _point(pool, lang, "Word order")
    word = await _word(pool, lang, f"palabra-{suffix}")
    card = await _card(pool, learner, lang, "grammar", point)

    async with pool.rls_connection(learner) as conn:
        await add_card_feedback(conn, learner, card, "this card looks wrong")

    async with pool.privileged_connection() as conn:
        await add_review_note(conn, point, tester, "the example contradicts the rule")
        await add_vocab_review_note(conn, word, tester, "the gloss is too narrow")
        await create_request(
            conn, tester, lang, "vocabulary", word, f"palabra-{suffix}",
            "translation", "wrong register", None,
        )
        await submit_suggestion(
            conn, lang, "vocabulary", word, contributor,
            {"definition": "word (unit of language)"}, None,
        )
        example = await add_example_sentence(
            conn, word, lang, f"Una palabra {suffix}.", "A word.", source="ai"
        )
        await add_recommendation(
            conn, tester, lang, "example", example, "reject", note="not idiomatic",
        )
    return {"tester": tester, "word": word, "example": example}


async def test_every_channel_is_visible_while_the_admin_works_in_another_language(pool):
    """THE scenario. Testers exercise language A; the admin's selector sits on
    language B, where everything is genuinely quiet. The per-language tiles
    are therefore all zero and always were — correctly. What must not happen
    is that being the whole story.

    The cross-language roll-up names A and breaks its total down by queue, so
    "All clear" is only ever reachable when nothing arrived anywhere.
    """
    studied = await _lang(pool, "sva")   # what the testers were using
    working = await _lang(pool, "svb")   # where the admin's selector sits
    await _file_one_of_everything(pool, studied, "sva")

    async with pool.privileged_connection() as conn:
        # The admin's own language really is empty — the tiles are not lying.
        assert all(v == 0 for v in (await review_inbox_counts(conn, working)).values())

        strip = {r["id"]: r for r in await review_inbox_other_languages(conn, working)}
        assert studied in strip, "the language the testers used is not named"
        elsewhere = strip[studied]
        assert elsewhere["code"] == "sva"

        # Every channel is counted, not just the ones that happen to share a
        # table with something the admin already watches.
        counts = elsewhere["counts"]
        assert counts["feedback"] == 1
        assert counts["notes"] == 2                  # grammar + vocab notes
        assert counts["change_requests"] == 1
        assert counts["suggestions"] == 1
        assert counts["tester_recommendations"] == 1
        assert counts["pending_examples"] == 1
        # …and the badge total is the sum, so a glance is enough.
        assert elsewhere["total"] == sum(counts.values())

        # Switching to that language shows the same numbers in the tiles —
        # the strip and the inbox count the same things by construction.
        tiles = await review_inbox_counts(conn, studied)
        assert {k: tiles[k] for k in counts} == counts


async def test_a_language_never_reports_itself_in_the_strip(pool):
    """The strip is "what you are NOT looking at". If a language listed
    itself, the admin would be told to switch to where they already are."""
    lang = await _lang(pool, "svs")
    await _file_one_of_everything(pool, lang, "svs")

    async with pool.privileged_connection() as conn:
        assert (await review_inbox_counts(conn, lang))["notes"] == 2
        assert lang not in {
            r["id"] for r in await review_inbox_other_languages(conn, lang)
        }


# ── degrading rather than disappearing when the schema is behind ────────────

async def test_the_inbox_still_answers_when_an_optional_table_is_missing(pool):
    """Migrations are owner-applied, so a deploy routinely runs ahead of the
    schema. A raised UndefinedTableError would abort the whole pooled
    transaction — not just its own query — so the Review workspace would go
    blank, which from the admin's chair is indistinguishable from "the
    testers sent nothing".

    The missing queue reads zero; every other queue still counts.
    """
    lang = await _lang(pool, "svm")
    await _file_one_of_everything(pool, lang, "svm")

    async with pool.privileged_connection() as conn:
        await conn.execute(
            "ALTER TABLE review_recommendations RENAME TO rr_hidden")
        try:
            counts = await review_inbox_counts(conn, lang)
            assert counts["tester_recommendations"] == 0   # the missing one
            assert counts["notes"] == 2                    # the rest survive
            assert counts["feedback"] == 1
            assert counts["change_requests"] == 1
            assert await list_tester_recommendations(conn, lang) == []
            # The cross-language strip degrades the same way rather than
            # taking the whole roll-up down with it.
            other = await review_inbox_other_languages(conn, lang)
            assert all(o["counts"]["tester_recommendations"] == 0 for o in other)
            # The transaction is still usable — the real tell that nothing
            # was poisoned on the way through.
            assert await conn.fetchval("SELECT 1") == 1
        finally:
            await conn.execute(
                "ALTER TABLE rr_hidden RENAME TO review_recommendations")


async def test_the_inbox_still_answers_when_an_optional_column_is_missing(pool):
    """Same failure one level down: the table is there but a column added by
    a later migration is not. The probe is per-column for exactly this, and
    the vocab list — where a reviewer goes to FIND the flagged rows — has to
    survive it too."""
    lang = await _lang(pool, "svc")
    await _file_one_of_everything(pool, lang, "svc")

    async with pool.privileged_connection() as conn:
        await conn.execute(
            "ALTER TABLE example_sentences RENAME COLUMN flagged TO flagged_hidden")
        try:
            counts = await review_inbox_counts(conn, lang)
            assert counts["flagged_examples"] == 0        # the missing one
            assert counts["pending_examples"] == 1        # neighbours survive
            assert counts["notes"] == 2

            items = {i["word"]: i for i in await list_vocab_items(conn, lang)}
            assert items["palabra-svc"]["flagged_count"] == 0
            assert await conn.fetchval("SELECT 1") == 1
        finally:
            await conn.execute(
                "ALTER TABLE example_sentences "
                "RENAME COLUMN flagged_hidden TO flagged")
