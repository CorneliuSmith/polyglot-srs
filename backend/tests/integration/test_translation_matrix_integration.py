"""Every support locale, end to end, on a course nobody has translated.

This exists because the same bug kept coming back wearing a different hat.
Each round found one more reason a particular pair produced nothing —
demand cleared too early, failure recorded as success, the game competing
for the key — and each round was diagnosed from a screenshot, fixed, and
shipped before the next one appeared.

The problem was never the fixes. It was that nothing walked the whole path
for a pair that had never been translated, so a pair-specific blocker only
ever surfaced when a person happened to switch to that language.

So: the real learner journey — profile, readiness (which is what primes the
queue), cycles, readiness again — parameterized over every UI locale, plus
the preconditions that silently produce nothing. A pair that cannot fill
must fail here with the REASON named, not in front of a learner as a bar
stuck at zero.
"""
from __future__ import annotations

import pytest

from backend.repositories.cards import session_readiness
from backend.services.auto_translate import (
    diagnose_pair,
    discover_pairs,
    run_translation_cycle,
)

from .conftest import requires_db

pytestmark = requires_db

# The six the interface ships in. A learner can pick any of these as their
# support language, so every one of them has to fill.
UI_LOCALES = ("es", "fr", "pt", "ru", "ar")


class _MockSettings:
    tutor_dev_mock = True
    anthropic_api_key = ""
    auto_translate_words_per_cycle = 50


@pytest.fixture(autouse=True)
def _mock_ai(monkeypatch):
    s = _MockSettings()
    monkeypatch.setattr("backend.services.translate.get_settings", lambda: s)
    monkeypatch.setattr("backend.services.auto_translate.get_settings", lambda: s)


@pytest.fixture(autouse=True)
async def _quiet_after(pool):
    yield
    async with pool.privileged_connection() as conn:
        await conn.execute("UPDATE languages SET auto_translate_enabled = false")


async def _course_and_learner(
    pool, code: str, locale: str, *, auto: bool = True,
    locale_is_a_language: bool = True,
) -> tuple[str, str]:
    """A course with real content and one learner studying it in *locale*."""
    async with pool.privileged_connection() as conn:
        course = await conn.fetchval(
            "INSERT INTO languages (code, name, rtl, auto_translate_enabled) "
            "VALUES ($1, $2, false, $3) "
            "ON CONFLICT (code) DO UPDATE SET auto_translate_enabled = $3 "
            "RETURNING id", code, f"Course-{code}", auto)
        if locale_is_a_language:
            await conn.execute(
                "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
                "ON CONFLICT (code) DO NOTHING", locale, f"Locale-{locale}")
        uid = await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id",
            f"{code}-{locale}@matrix.test")
        await conn.execute(
            "INSERT INTO user_profiles (id, active_language_id, support_locale, "
            "batch_size) VALUES ($1, $2, $3, 10)", uid, course, locale)

        vdeck = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 Vocabulary') RETURNING id",
            course)
        gdeck = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'grammar', 'A1', 'A1 Grammar') RETURNING id", course)
        for deck in (vdeck, gdeck):
            await conn.execute(
                "INSERT INTO user_content_subscriptions (user_id, "
                "content_list_id) VALUES ($1, $2)", uid, deck)

        # Six words and two points: enough that the mock's reject-the-first
        # behaviour cannot be mistaken for a systemic failure.
        for i in range(6):
            vid = await conn.fetchval(
                "INSERT INTO vocabulary (language_id, word, level, "
                "frequency_rank) VALUES ($1, $2, 'A1', $3) RETURNING id",
                course, f"{code}w{i}", i + 1)
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, 'en', $2)", vid, f"meaning {i}")
            await conn.execute(
                "INSERT INTO example_sentences (language_id, vocabulary_id, "
                "sentence, translation, translation_locale, source, reviewed) "
                "VALUES ($1, $2, $3, $4, 'en', 'human', true)",
                course, vid, f"Sentence {i}.", f"The meaning of {i}.")
        for i in range(2):
            gp = await conn.fetchval(
                "INSERT INTO grammar_points (language_id, title, level, "
                "reviewed, display_order, explanation, culture_note) "
                "VALUES ($1, $2, 'A1', true, $3, 'How it works.', 'An aside.') "
                "RETURNING id", course, f"{code} point {i}", i + 1)
            await conn.execute(
                "INSERT INTO drill_sentences (grammar_point_id, sentence, "
                "answer, source, reviewed, display_order, translation, hint) "
                "VALUES ($1, 'A {{answer}}.', 'x', 'seed', true, 1, "
                "'A thing.', 'the word for thing')", gp)
    return str(course), str(uid)


async def _readiness(pool, uid: str, course: str) -> dict:
    """Readiness exactly as the wait screen asks for it — which is also what
    primes the translation queue, so this is not a passive read."""
    from backend.repositories.cards import pretranslate_upcoming

    async with pool.privileged_connection() as conn:
        state = await session_readiness(conn, uid, course, batch_size=10)
        if not state["learn"]["ready_enough"]:
            await pretranslate_upcoming(conn, uid, course, batch_size=10)
    return state


async def _run_until_ready(pool, uid: str, course: str, max_cycles: int = 8):
    """Cycle until the session opens, the way a learner waiting would."""
    state = await _readiness(pool, uid, course)
    for _ in range(max_cycles):
        if state["learn"]["ready_enough"]:
            return state, True
        async with pool.privileged_connection() as conn:
            await run_translation_cycle(conn)
            # A failure sets a retry window; the learner's clock is the only
            # thing that passes it, so pass it here too.
            await conn.execute(
                "UPDATE translation_attempts SET last_attempt_at = "
                "now() - interval '2 days'")
        state = await _readiness(pool, uid, course)
    return state, state["learn"]["ready_enough"]


@pytest.mark.parametrize("locale", UI_LOCALES)
async def test_every_support_locale_fills_from_nothing(pool, locale):
    """A learner picking any interface language must be able to start.

    This is the screenshot, reproduced per locale: "0 cards of 3 ready" on a
    course nobody has studied in that language. If a pair cannot get there,
    the assertion names which one rather than leaving it to a bug report.
    """
    course, uid = await _course_and_learner(pool, f"mx{locale}", locale)

    before = await _readiness(pool, uid, course)
    assert before["locale"] == locale
    assert not before["learn"]["ready_enough"], "fixture is already translated"

    state, ready = await _run_until_ready(pool, uid, course)

    if not ready:
        async with pool.privileged_connection() as conn:
            why = await diagnose_pair(conn, course, locale)
        pytest.fail(
            f"{locale}: never became startable — "
            f"{state['learn']['cards_ready']}/{state['learn']['start_cards']} "
            f"cards, {round(state['learn']['pct'] * 100)}% of the batch. "
            f"Blockers: {why}"
        )


@pytest.mark.parametrize("locale", UI_LOCALES)
async def test_every_support_locale_is_a_live_pair(pool, locale):
    """The loop must SEE the pair at all.

    discover_pairs joins the support locale back to `languages`, so a locale
    the interface offers but the languages table doesn't hold is invisible
    to the loop — no error, no log line, just nothing happening forever.
    """
    course, _ = await _course_and_learner(pool, f"pr{locale}", locale)
    async with pool.privileged_connection() as conn:
        pairs = await discover_pairs(conn)
    assert any(str(p["language_id"]) == course and p["locale"] == locale
               for p in pairs), f"{locale} is not a live pair"


async def test_a_switched_off_course_says_so(pool):
    """The most common cause of "I turned it on and nothing happened" is
    that it was turned on for a DIFFERENT course. That must be reportable,
    not guessable."""
    course, _ = await _course_and_learner(pool, "mxoff", "es", auto=False)
    async with pool.privileged_connection() as conn:
        why = await diagnose_pair(conn, course, "es")
    assert "switched_off" in why["blockers"], why


async def test_a_locale_missing_from_languages_says_so(pool):
    """A support locale with no `languages` row can never be a pair. It is
    silent today; it must be named."""
    course, _ = await _course_and_learner(
        pool, "mxghost", "zz", locale_is_a_language=False)
    async with pool.privileged_connection() as conn:
        why = await diagnose_pair(conn, course, "zz")
    assert "locale_not_a_language" in why["blockers"], why


async def test_a_healthy_pair_reports_no_blockers(pool):
    """The diagnosis has to be able to say "nothing is wrong" too, or it is
    just a list of scary words."""
    course, _ = await _course_and_learner(pool, "mxok", "pt")
    async with pool.privileged_connection() as conn:
        why = await diagnose_pair(conn, course, "pt")
    assert why["blockers"] == [], why


# ---------------------------------------------------------------------------
# The clean-database cases above all pass. A live database is not clean: it
# carries rows written by the code that had the bug. These are the shapes
# that old code left behind, and each one has to heal on its own.
# ---------------------------------------------------------------------------


async def test_it_recovers_from_glosses_the_old_code_rejected(pool):
    """Words parked in translation_reviews used to be skipped forever.

    A live course has a pile of them from before the retry ledger existed.
    If they stay excluded, a learner who arrives now sees exactly what the
    report showed: zero cards, no movement, no explanation.
    """
    course, uid = await _course_and_learner(pool, "lgw", "es")
    async with pool.privileged_connection() as conn:
        # Every word already "attempted" the way the old code recorded it.
        await conn.execute(
            """INSERT INTO translation_reviews (vocabulary_id, locale, proposed, reason)
               SELECT id, 'es', '', 'rejected by the old checker'
                 FROM vocabulary WHERE language_id = $1""", course)

    _, ready = await _run_until_ready(pool, uid, course)
    if not ready:
        async with pool.privileged_connection() as conn:
            why = await diagnose_pair(conn, course, "es")
        pytest.fail(f"legacy rejects never retried: {why}")


async def test_it_recovers_from_hollow_grammar_rows(pool):
    """grammar_point_translations rows with every field NULL.

    The old code wrote one whenever a rendering failed, and the pending
    query read any row as done — so the point kept its English title
    forever. Those rows are still in the database.
    """
    course, uid = await _course_and_learner(pool, "lgg", "fr")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            """INSERT INTO grammar_point_translations
                   (grammar_point_id, locale, title, culture_note,
                    function_note, reviewed)
               SELECT id, 'fr', NULL, NULL, NULL, false
                 FROM grammar_points WHERE language_id = $1""", course)

    async with pool.privileged_connection() as conn:
        await run_translation_cycle(conn)
        filled = await conn.fetchval(
            """SELECT count(*) FROM grammar_point_translations g
                JOIN grammar_points p ON p.id = g.grammar_point_id
               WHERE p.language_id = $1 AND g.locale = 'fr'
                 AND g.title IS NOT NULL""", course)
    assert filled >= 1, "a hollow row must not count as a finished point"


async def test_it_recovers_from_hollow_drill_rows(pool):
    """Same shape, same fix, different table."""
    course, uid = await _course_and_learner(pool, "lgd", "ru")
    async with pool.privileged_connection() as conn:
        await conn.execute(
            """INSERT INTO drill_hint_translations
                   (drill_id, locale, hint, translation, reviewed)
               SELECT d.id, 'ru', NULL, NULL, false
                 FROM drill_sentences d
                 JOIN grammar_points p ON p.id = d.grammar_point_id
                WHERE p.language_id = $1""", course)

    async with pool.privileged_connection() as conn:
        await run_translation_cycle(conn)
        filled = await conn.fetchval(
            """SELECT count(*) FROM drill_hint_translations t
                JOIN drill_sentences d ON d.id = t.drill_id
                JOIN grammar_points p ON p.id = d.grammar_point_id
               WHERE p.language_id = $1 AND t.locale = 'ru'
                 AND (t.translation IS NOT NULL OR t.hint IS NOT NULL)""",
            course)
    assert filled >= 1, "a hollow row must not count as a finished drill"


async def test_a_big_backlog_still_serves_the_learner_in_front_of_it(pool):
    """The A1-first sweep is not the learner's session.

    A real course has thousands of untranslated words. If the learner's own
    batch only fills when the breadth-first sweep happens to reach it, the
    wait screen is at the mercy of alphabetical luck — which is what "it
    just sits there" looks like on a large course.
    """
    course, uid = await _course_and_learner(pool, "lgbig", "pt")
    async with pool.privileged_connection() as conn:
        # 300 words the learner will not see for months, ranked ahead of
        # nothing — they simply swamp any budget.
        await conn.execute(
            """INSERT INTO vocabulary (language_id, word, level, frequency_rank)
               SELECT $1, 'filler' || g, 'C2', 1000 + g
                 FROM generate_series(1, 300) g""", course)
        await conn.execute(
            """INSERT INTO translations (vocabulary_id, locale, definition)
               SELECT id, 'en', 'filler meaning' FROM vocabulary
                WHERE language_id = $1 AND word LIKE 'filler%'""", course)

    _, ready = await _run_until_ready(pool, uid, course, max_cycles=4)
    if not ready:
        async with pool.privileged_connection() as conn:
            why = await diagnose_pair(conn, course, "pt")
        pytest.fail(f"the learner's own batch lost to the backlog: {why}")


async def test_the_readout_answers_is_it_running(pool):
    """The question every one of these rounds started with.

    The status readout could say the course was on, the provider was ready
    and the backlog was N — and still not answer "is the sweep running at
    all?". A loop that never started, a task that died, and a worker that
    simply isn't the one running it all look identical to a learner, and
    each has a different fix.
    """
    from backend.services.auto_translate import heartbeat, translation_status

    await _course_and_learner(pool, "mxbeat", "es")
    async with pool.privileged_connection() as conn:
        status = await translation_status(conn)

    assert "loop_enabled" in status, "cannot tell if the sweep is switched on"
    assert "loop" in status, "cannot tell if the sweep has ever run"
    # Nothing has run in this test process, and the readout says so plainly
    # rather than implying health by omission.
    assert status["loop"]["started"] is False
    assert status["loop"]["last_cycle_at"] is None

    # After a cycle the process can prove it did something.
    async with pool.privileged_connection() as conn:
        await run_translation_cycle(conn)
    beat = heartbeat()
    assert beat["last_cycle_at"] is None, (
        "run_translation_cycle is the unit of work; the HEARTBEAT belongs to "
        "the loop that schedules it, so calling the unit directly must not "
        "fake proof that the loop is alive"
    )


async def test_the_readout_covers_every_table_the_loop_depends_on(pool):
    """A green "Migrations applied" that skips a table is a false negative
    with a light on it.

    translation_attempts is the one most likely to be missed: nothing
    crashes without it, the loop just quietly stops pacing its retries. The
    admin panel reduces this dict to a single dot, so anything absent here
    is invisible in production.
    """
    from backend.services.auto_translate import translation_status

    async with pool.privileged_connection() as conn:
        status = await translation_status(conn)

    for table in ("translation_demand", "translation_attempts",
                  "grammar_point_translations", "gym_label_translations"):
        assert table in status["migrations"], (
            f"{table} is never probed, so its migration being unapplied "
            f"cannot be seen from the admin readout"
        )
