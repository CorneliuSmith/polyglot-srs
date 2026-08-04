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

    assert stats["applied"] == 1
    assert stats["queued"] == 1
    # Batch item 0 is the mock's designated reject → queued, never applied.
    assert await _queued(pool, w1, "pt")
    assert await _gloss(pool, w1, "pt") is None
    # Item 1 is approved → the pt overlay row exists (mock echoes "[word]").
    assert await _gloss(pool, w2, "pt") == "[gunwale]"
    # The English course has a real Gym manifest (data/gym/en.json), so the
    # same sweep also fills the pt picker labels — the "El Gimnasio shows
    # 'Present -ar'" gap.
    assert stats["gym_labels"] >= 1
    async with pool.privileged_connection() as conn:
        n = await conn.fetchval(
            "SELECT count(*) FROM gym_label_translations "
            "WHERE language_code = 'en' AND locale = 'pt'")
    # Every manifest entry got a row; the mock-rejected first entry stores
    # NULLs (attempted, English fallback) and isn't counted as applied.
    assert n >= stats["gym_labels"]


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


async def test_demand_lane_beats_the_sweep_and_clears_itself(pool, monkeypatch):
    """A card read that served English records demand; the next cycle
    translates exactly those rows FIRST (any level — no waiting for the
    A1-first ordering) and deletes the queue rows, approved or not."""
    from backend.services.auto_translate import note_missing_content

    _mock_ai(monkeypatch)
    course = await _lang(pool, "at8", "Demandish", auto=True)
    await _lang(pool, "fr2", "French2", auto=False)
    await _learner(pool, "fr@at8", course, "fr2")

    async with pool.privileged_connection() as conn:
        # A C2 point: the breadth-first sweep would reach it LAST, so its
        # translation appearing proves the demand lane ran.
        gp = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, "
            "display_order, explanation, culture_note) "
            "VALUES ($1, 'The aorist optative', 'C2', true, 99, "
            "'Rare but real.', 'Poets love it.') RETURNING id", course)
        # Filler the sweep would otherwise spend the whole cycle on.
        for i in range(3):
            await conn.execute(
                "INSERT INTO vocabulary (language_id, word, level, "
                "frequency_rank) VALUES ($1, $2, 'A1', $3)",
                course, f"word{i}", i + 1)
        await note_missing_content(conn, "fr2", grammar_ids=[gp])
        pending = await conn.fetch(
            "SELECT kind FROM translation_demand WHERE locale = 'fr2'")
        # The detector mirrors pending_*: explanation + title/notes are
        # missing (no drills exist for the point, so no drill demand).
        assert sorted(r["kind"] for r in pending) == [
            "explanation", "grammar_meta"]

    stats = await _cycle(pool)
    assert stats["demand"] >= 1

    async with pool.privileged_connection() as conn:
        gpt = await conn.fetchrow(
            "SELECT title, culture_note FROM grammar_point_translations "
            "WHERE grammar_point_id = $1 AND locale = 'fr2'", gp)
        # Title was batch item 0 → mock-rejected → NULL (English fallback);
        # the culture note is item 0 of ITS batch too. Both fields attempted,
        # the row itself proves grammar_meta ran through the demand lane.
        assert gpt is not None
        et = await conn.fetchval(
            "SELECT count(*) FROM explanation_translations "
            "WHERE grammar_point_id = $1 AND locale = 'fr2'", gp)
        assert et in (0, 1)  # rejected-or-stored; either way it was attempted
        left = await conn.fetchval(
            "SELECT count(*) FROM translation_demand WHERE locale = 'fr2'")
        assert left == 0


async def test_demand_for_a_switched_off_course_is_ignored(pool, monkeypatch):
    """Demand is a priority lane, not a bypass: rows for a course whose
    auto-translate toggle is off are never picked up (and cost nothing)."""
    from backend.services.auto_translate import note_missing_content

    _mock_ai(monkeypatch)
    course = await _lang(pool, "at9", "Offish", auto=False)
    await _lang(pool, "ru2", "Russian2", auto=False)

    async with pool.privileged_connection() as conn:
        gp = await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed, "
            "display_order, explanation) VALUES ($1, 'Point', 'A1', true, 1, "
            "'Text.') RETURNING id", course)
        await note_missing_content(conn, "ru2", grammar_ids=[gp])

    stats = await _cycle(pool)
    assert stats["demand"] == 0

    async with pool.privileged_connection() as conn:
        n = await conn.fetchval(
            "SELECT count(*) FROM grammar_point_translations "
            "WHERE grammar_point_id = $1", gp)
        assert n == 0


async def test_learn_session_start_pretranslates_the_upcoming_queue(pool, monkeypatch):
    """Starting a learn session queues demand for MORE than the session:
    the next few sessions' worth of upcoming content goes in too, so by the
    time those cards are learned — and long before they're reviewed — the
    overlays already exist."""
    from backend.repositories.cards import (
        LEARN_LOOKAHEAD_SESSIONS,
        add_learn_batch,
    )

    _mock_ai(monkeypatch)
    course = await _lang(pool, "at10", "Aheadish", auto=True)
    await _lang(pool, "es3", "Spanish3", auto=False)
    uid = await _learner(pool, "ahead@at10", course, "es3")

    async with pool.privileged_connection() as conn:
        cl = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 Vocabulary') RETURNING id",
            course)
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", uid, cl)
        for i in range(8):
            await conn.execute(
                "INSERT INTO vocabulary (language_id, word, level, "
                "frequency_rank) VALUES ($1, $2, 'A1', $3)",
                course, f"ahead{i}", i + 1)

        batch = await add_learn_batch(conn, uid, course, batch_size=2)
        assert batch["added"] == 2

        # Demand covers the batch AND the lookahead — capped by content:
        # min(8 available, 2 * (1 + LEARN_LOOKAHEAD_SESSIONS)).
        expected = min(8, 2 * (1 + LEARN_LOOKAHEAD_SESSIONS))
        n = await conn.fetchval(
            "SELECT count(*) FROM translation_demand "
            "WHERE kind = 'word' AND locale = 'es3'")
        assert n == expected


async def test_translation_status_names_the_actual_blocker(pool, monkeypatch):
    """The admin readout: switched-off courses, migration state, provider,
    and the real backlog per live pair."""
    from backend.services.auto_translate import translation_status

    _mock_ai(monkeypatch)
    on = await _lang(pool, "ts1", "Onish", auto=True)
    off = await _lang(pool, "ts2", "Offish", auto=False)
    await _lang(pool, "ts3", "Localish", auto=False)
    await _learner(pool, "on@ts1", on, "ts3")
    await _learner(pool, "off@ts2", off, "ts3")
    await _word(pool, on, "unum", 1, "one")
    await _word(pool, on, "duo", 2, "two")

    async with pool.privileged_connection() as conn:
        st = await translation_status(conn)

    assert st["provider_ready"] is True
    assert st["migrations"]["translation_demand"] is True
    # The switched-ON pair reports its real backlog…
    pair = next(p for p in st["pairs"] if p["code"] == "ts1")
    assert pair["locale"] == "ts3"
    assert pair["learners"] == 1
    assert pair["pending"]["words"] == 2
    assert pair["filled"]["words"] == 0
    # …and the switched-OFF course is named rather than silently absent.
    assert any(o["code"] == "ts2" for o in st["switched_off"])
    assert not any(p["code"] == "ts2" for p in st["pairs"])

    # After a sweep the backlog moves and the filled count rises.
    await _cycle(pool)
    async with pool.privileged_connection() as conn:
        st2 = await translation_status(conn)
    pair2 = next(p for p in st2["pairs"] if p["code"] == "ts1")
    assert pair2["pending"]["words"] < pair["pending"]["words"]
    assert pair2["filled"]["words"] >= 1

    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1", on)


async def test_status_counts_match_the_queues(pool, monkeypatch):
    """The readout's backlog numbers must equal what the sweep would
    actually pick up. They come from separate COUNT queries (a limited
    fetch reports its own cap — a real 5,000-word backlog showed as a
    frozen '1000'), so this pins the two against each other and fails if
    the predicates ever drift apart."""
    from backend.services.auto_translate import (
        count_pending,
        pending_drills,
        pending_explanations,
        pending_grammar_meta,
        pending_words,
        translation_status,
    )

    _mock_ai(monkeypatch)
    course = await _lang(pool, "cnt", "Countish", auto=True)
    await _lang(pool, "cn2", "Countlocale", auto=False)
    uid = await _learner(pool, "cnt@cnt", course, "cn2")
    for i in range(7):
        await _word(pool, course, f"cntword{i}", i + 1, f"gloss {i}")

    async with pool.privileged_connection() as conn:
        for i in range(3):
            gp = await conn.fetchval(
                "INSERT INTO grammar_points (language_id, title, level, "
                "reviewed, display_order, explanation) VALUES "
                "($1, $2, 'A1', true, $3, 'How it works.') RETURNING id",
                course, f"cnt point {i}", i)
            await conn.execute(
                "INSERT INTO drill_sentences (grammar_point_id, sentence, "
                "answer, source, reviewed, display_order, translation, hint) "
                "VALUES ($1, 'Mi {{answer}}.', 'x', 'seed', true, 1, "
                "'I see it.', 'the verb') ", gp)

        for kind, fn in (
            ("words", pending_words), ("drills", pending_drills),
            ("explanations", pending_explanations),
            ("grammar_meta", pending_grammar_meta),
        ):
            queued = len(await fn(conn, course, "cn2", 10_000))
            counted = await count_pending(conn, kind, course, "cn2")
            assert counted == queued, f"{kind}: {counted} != {queued}"

        st = await translation_status(conn)
        pair = next(p for p in st["pairs"] if p["code"] == "cnt")
        # Real counts, not a cap: 7 words and 3 of each grammar kind.
        assert pair["pending"]["words"] == 7
        assert pair["pending"]["drills"] == 3
        assert pair["pending"]["explanations"] == 3

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del uid
