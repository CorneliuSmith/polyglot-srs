"""The auto-translate loop against real Postgres: demand-driven, gated, capped.

Real DB because the whole feature is three predicates — "an admin switched
the course on", "a live account uses this pair", "this word still lacks the
gloss" — and each one failing open means silent API spend (or a re-translated
word). Mock mode (tutor_dev_mock) drives the maker–checker: it approves every
item except the FIRST of each batch, which it rejects — exercising both the
apply path and the review-queue path in one sweep.
"""
from __future__ import annotations

from backend.services.auto_translate import run_translation_cycle

from .conftest import requires_db

pytestmark = requires_db


class _MockSettings:
    tutor_dev_mock = True
    anthropic_api_key = ""
    auto_translate_words_per_cycle = 50


def _mock_ai(monkeypatch, **overrides):
    s = _MockSettings()
    for k, v in overrides.items():
        setattr(s, k, v)
    monkeypatch.setattr(
        "backend.services.translate.get_settings", lambda: s
    )
    monkeypatch.setattr(
        "backend.services.auto_translate.get_settings", lambda: s
    )


async def _lang(pool, code: str, name: str, *, auto: bool) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl, auto_translate_enabled) "
            "VALUES ($1, $2, false, $3) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, "
            "auto_translate_enabled = EXCLUDED.auto_translate_enabled "
            "RETURNING id",
            code, name, auto,
        ))


async def _learner(pool, email: str, lang: str, support_locale: str) -> str:
    async with pool.privileged_connection() as conn:
        uid = str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))
        await conn.execute(
            "INSERT INTO user_profiles (id, active_language_id, support_locale) "
            "VALUES ($1, $2, $3)",
            uid, lang, support_locale,
        )
    return uid


async def _word(pool, lang: str, word: str, rank: int,
                en_gloss: str | None = None) -> str:
    async with pool.privileged_connection() as conn:
        vid = str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level, frequency_rank) "
            "VALUES ($1, $2, 'A1', $3) RETURNING id",
            lang, word, rank,
        ))
        if en_gloss is not None:
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, 'en', $2)", vid, en_gloss,
            )
    return vid


async def _gloss(pool, vid: str, locale: str) -> str | None:
    async with pool.privileged_connection() as conn:
        return await conn.fetchval(
            "SELECT definition FROM translations "
            "WHERE vocabulary_id = $1 AND locale = $2", vid, locale,
        )


async def _queued(pool, vid: str, locale: str) -> bool:
    async with pool.privileged_connection() as conn:
        return bool(await conn.fetchval(
            "SELECT 1 FROM translation_reviews "
            "WHERE vocabulary_id = $1 AND locale = $2", vid, locale,
        ))


async def _cycle(pool):
    async with pool.privileged_connection() as conn:
        return await run_translation_cycle(conn)


async def test_english_course_fills_a_live_support_locale(pool, monkeypatch):
    """The owner's test path: English course switched on, one account learning
    English from Portuguese → the sweep fills pt glosses. The mock rejects the
    first (most frequent) word, so it lands in the review queue instead."""
    _mock_ai(monkeypatch)
    en = await _lang(pool, "en", "English", auto=True)
    await _lang(pool, "pt", "Portuguese", auto=False)
    await _learner(pool, "tester@at1", en, "pt")
    w1 = await _word(pool, en, "binnacle", 1, "the housing of a ship's compass")
    w2 = await _word(pool, en, "gunwale", 2, "the upper edge of a boat's side")

    stats = await _cycle(pool)

    assert stats["processed"] == 2
    # Batch item 0 is the mock's designated reject → queued, never applied.
    assert await _queued(pool, w1, "pt")
    assert await _gloss(pool, w1, "pt") is None
    # Item 1 is approved → the pt overlay row exists (mock echoes "[word]").
    assert await _gloss(pool, w2, "pt") == "[gunwale]"


async def test_nothing_happens_while_the_switch_is_off(pool, monkeypatch):
    """A live pair with the course toggled OFF spends nothing — the switch is
    the admin's cost control, and off is the default."""
    _mock_ai(monkeypatch)
    es = await _lang(pool, "at2", "Spanishish", auto=False)
    await _lang(pool, "fr", "French", auto=False)
    await _learner(pool, "off@at2", es, "fr")
    w = await _word(pool, es, "casa", 1, "house")

    stats = await _cycle(pool)

    assert stats["processed"] == 0
    assert await _gloss(pool, w, "fr") is None
    assert not await _queued(pool, w, "fr")


async def test_a_pair_with_no_learners_costs_nothing(pool, monkeypatch):
    """Switched on but nobody learning it from anywhere: demand-driven means
    the loop doesn't touch it."""
    _mock_ai(monkeypatch)
    lang = await _lang(pool, "at3", "Lonely", auto=True)
    w = await _word(pool, lang, "solus", 1, "alone")

    stats = await _cycle(pool)

    assert stats["processed"] == 0
    assert await _gloss(pool, w, "pt") is None


async def test_pivot_courses_translate_via_the_english_gloss(pool, monkeypatch):
    """A non-English course: the word's ENGLISH gloss is the pivot the maker
    disambiguates with, so a word without one is skipped rather than
    translated blind."""
    _mock_ai(monkeypatch)
    course = await _lang(pool, "at4", "Pivotish", auto=True)
    await _lang(pool, "ru", "Russian", auto=False)
    await _learner(pool, "ru@at4", course, "ru")
    # Rank 1 has no English gloss → skipped. Ranks 2 and 3 both process;
    # the mock rejects the first item of the batch (rank 2) and approves
    # the second (rank 3).
    bare = await _word(pool, course, "senzo", 1)
    first = await _word(pool, course, "akvo", 2, "water")
    second = await _word(pool, course, "domo", 3, "house")

    stats = await _cycle(pool)

    assert stats["processed"] == 2
    assert await _gloss(pool, bare, "ru") is None
    assert not await _queued(pool, bare, "ru")
    assert await _queued(pool, first, "ru")
    assert await _gloss(pool, second, "ru") == "[domo]"

    # A second sweep re-processes nothing: applied and queued words are both
    # excluded from "pending", so the loop converges instead of re-spending.
    stats2 = await _cycle(pool)
    assert stats2["processed"] == 0


async def test_the_cycle_budget_caps_spend(pool, monkeypatch):
    """words_per_cycle is the hourly cost ceiling: with a budget of 1, one
    word processes this sweep and the rest wait for the next."""
    _mock_ai(monkeypatch, auto_translate_words_per_cycle=1)
    course = await _lang(pool, "at5", "Budgetish", auto=True)
    await _lang(pool, "de", "German", auto=False)
    await _learner(pool, "de@at5", course, "de")
    for i, w in enumerate(["unu", "du", "tri"], start=1):
        await _word(pool, course, w, i, f"number {i}")

    stats = await _cycle(pool)
    assert stats["processed"] == 1

    # Drain the two leftovers: the session DB is shared, and another test's
    # global "processed" assertion must not inherit this pair's backlog.
    _mock_ai(monkeypatch)  # restore the default budget
    for _ in range(5):
        if not (await _cycle(pool))["processed"]:
            break
    else:  # pragma: no cover - loop failed to converge
        raise AssertionError("auto-translate cycle never drained")


async def test_drills_and_explanations_fill_after_the_glosses(pool, monkeypatch):
    """The strings a grammar card actually shows — the drill translation and
    hint under the cloze, and the point's explanation — fill from the same
    budget once glosses are done. The mock rejects the FIRST item of every
    batch: a rejected drill rendering is recorded as a NULL row (attempted,
    card keeps its English fallback, no re-spend), a rejected explanation is
    simply retried later because that table requires non-null text."""
    _mock_ai(monkeypatch)
    course = await _lang(pool, "at6", "Drillish", auto=True)
    await _lang(pool, "es2", "Spanish2", auto=False)
    await _learner(pool, "es@at6", course, "es2")

    async with pool.privileged_connection() as conn:
        gp1 = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, "
            "display_order, explanation) VALUES ($1, 'P1', 'A1', true, 1, "
            "'How the first point works.') RETURNING id", course)
        gp2 = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, "
            "display_order, explanation) VALUES ($1, 'P2', 'A1', true, 2, "
            "'How the second point works.') RETURNING id", course)
        d1 = await conn.fetchval(
            "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, "
            "source, reviewed, display_order, translation, hint) "
            "VALUES ($1, 'Bu {{answer}}.', 'ev', 'ai', true, 1, "
            "'This is a house.', 'the word for house') RETURNING id", gp1)
        d2 = await conn.fetchval(
            "INSERT INTO drill_sentences (grammar_point_id, sentence, answer, "
            "source, reviewed, display_order, translation, hint) "
            "VALUES ($1, 'O {{answer}}.', 'su', 'ai', true, 2, "
            "'That is water.', 'the word for water') RETURNING id", gp2)

    stats = await _cycle(pool)
    assert stats["drills"] >= 1
    assert stats["explanations"] == 1  # first of the batch rejected, retried later

    async with pool.privileged_connection() as conn:
        rows = {str(r["drill_id"]): r for r in await conn.fetch(
            "SELECT drill_id, translation, hint, reviewed "
            "FROM drill_hint_translations WHERE locale = 'es2'")}
        # Both drills got a row — attempted is recorded either way.
        assert set(rows) == {str(d1), str(d2)}
        # Batch item 0 (d1) was rejected for both fields → NULL fallback row.
        assert rows[str(d1)]["translation"] is None
        # Item 1 (d2) carries the mock's rendering, stored as a live draft.
        assert rows[str(d2)]["translation"] == "[Spanish2] That is water."
        assert rows[str(d2)]["reviewed"] is False
        ets = await conn.fetch(
            "SELECT grammar_point_id, explanation FROM explanation_translations "
            "WHERE locale = 'es2'")
        # One of the two explanations stored (the batch's second item).
        assert len(ets) == 1
        assert str(ets[0]["grammar_point_id"]) in {str(gp1), str(gp2)}
        assert ets[0]["explanation"].startswith("[Spanish2]")

    # A second sweep re-touches only the rejected explanation — every drill
    # already has its attempted row.
    stats2 = await _cycle(pool)
    assert stats2["drills"] == 0
    assert stats2["processed"] == 1
