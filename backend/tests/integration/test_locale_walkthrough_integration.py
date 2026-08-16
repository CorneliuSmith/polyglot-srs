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
    pretranslate_upcoming,
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
    # Learning a language through itself: a sentence meaning-line rendered
    # into the course language would restate the drill sentence with the
    # blank filled, so those two kinds deliberately stay on their English
    # source (see auto_translate.self_pair). Everything else localizes.
    is_self = locale_code == code

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
        assert gp2_due["translation"] == (
            "I see it." if is_self else f"{mark} I see it.")

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
        assert cram2["translation"] == (
            "I see it." if is_self else f"{mark} I see it.")
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
        assert lesson["examples"][0]["translation"] == (
            "I see it." if is_self else f"{mark} I see it.")

        # ---- Deck browser: items + vocab item -----------------------------
        gitems = await get_deck_items(conn, c["gdeck"], 50, locale_code)
        assert f"{mark} {tag} second point" in {
            i["item"] for i in gitems["items"]}
        vitems = await get_deck_items(conn, c["vdeck"], 50, locale_code)
        assert f"[{tag}domo]" in {i["detail"] for i in vitems["items"]}
        vocab = await get_vocab_item(conn, c["words"][1], locale_code)
        assert vocab["definition"] == f"[{tag}domo]"

        # ---- Example sentences: translated AND shown ----------------------
        # These used to land reviewed=false like AI-INVENTED content, so the
        # card read filtered them out and a fully translated course still
        # showed every example in English. The source sentence was already
        # human-approved; only its meaning line is re-worded, by the same
        # maker-checker that fills word glosses.
        ex = await conn.fetch(
            "SELECT translation, reviewed FROM example_sentences "
            "WHERE translation_locale = $1 AND language_id = $2", locale_code,
            course)
        if is_self:
            assert ex == [], "self-pair example siblings restate the sentence"
        else:
            assert ex, "locale sibling rows were not created"
            assert all(r["reviewed"] is True for r in ex)
            assert any(r["translation"].startswith(mark) for r in ex)

        # ---- The demand queue holds only what is genuinely missing --------
        # Every kind retries now, so "which kinds are left" no longer says
        # anything useful — the mock rejects the first item of every batch,
        # so any kind can legitimately still be queued. The invariant worth
        # pinning is the other one: nothing that LANDED is still sitting in
        # the queue. A row leaves when its content exists, and only then.
        for row in await conn.fetch(
            "SELECT kind, ref_id FROM translation_demand WHERE locale = $1",
            locale_code,
        ):
            kind, ref = row["kind"], row["ref_id"]
            if kind == "word":
                got = await conn.fetchval(
                    "SELECT count(*) FROM translations "
                    "WHERE vocabulary_id = $1 AND locale = $2", ref, locale_code)
            elif kind == "explanation":
                got = await conn.fetchval(
                    "SELECT count(*) FROM explanation_translations "
                    "WHERE grammar_point_id = $1 AND locale = $2", ref,
                    locale_code)
            elif kind == "grammar_meta":
                got = await conn.fetchval(
                    "SELECT count(*) FROM grammar_point_translations "
                    "WHERE grammar_point_id = $1 AND locale = $2 "
                    "  AND title IS NOT NULL", ref, locale_code)
            else:
                continue  # drill/example are per-field or per-sentence
            assert not got, f"{kind} {ref} landed but is still queued"

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


async def test_portuguese_learning_spanish_fills_without_the_new_migration(
    pool, monkeypatch,
):
    """The owner's live configuration: UI/support Portuguese, course Spanish,
    auto-translate switched on, migration 20260914 NOT applied.

    The three overlays a card actually reads — vocab gloss, drill
    hint/translation, grammar explanation — all predate that migration, so
    a sweep must fill them regardless. This pins that the loop does real
    work in exactly that state (it used to die on the demand-queue query
    before translating anything)."""
    from backend.repositories import cards as cards_repo

    _mock_ai(monkeypatch)
    es = await _lang(pool, "es0", "Spanish0", auto=True)
    await _lang(pool, "pt0", "Portuguese0", auto=False)
    uid = await _learner(pool, "pt@es0", es, "pt0")
    c = await _build_course(pool, es, uid, "es0")

    async with pool.privileged_connection() as conn:
        sp = conn.transaction()
        await sp.start()
        try:
            for t in ("translation_demand", "gym_label_translations",
                      "grammar_point_translations"):
                await conn.execute(f"DROP TABLE {t}")
            cards_repo._TABLE_EXISTS.clear()

            stats = await run_translation_cycle(conn)
            # Words, drills AND explanations each get real work done.
            assert stats["applied"] >= 1, stats
            assert stats["drills"] >= 1, stats
            assert stats["explanations"] >= 1, stats

            # And the learner's cards actually read Portuguese now.
            batch = await add_mixed_learn_batch(conn, uid, es, 10)
            details = await get_card_details_bulk(
                conn, [str(i) for i in batch["items"]], "pt0")
            defs = [d.get("definition") for d in details.values()
                    if d["card_type"] == "vocabulary"]
            assert "[es0domo]" in defs, defs
            gp = [d for d in details.values() if d["card_type"] == "grammar"]
            assert any(d["explanation"].startswith("[Portuguese0]") for d in gp)
        finally:
            await sp.rollback()
            cards_repo._TABLE_EXISTS.clear()
        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1", es)


async def test_the_self_pair_never_translates_the_answer_away(pool, monkeypatch):
    """Spanish course, Spanish support: the drill's meaning-line must stay on
    its English source.

    Rendering "I see it." into the course language reproduces the drill
    sentence with the blank filled — printing the answer directly under the
    question. Hints and glosses have no such problem and still localize."""
    from backend.services.auto_translate import self_pair

    _mock_ai(monkeypatch)
    course = await _lang(pool, "sp7", "Selfish7", auto=True)
    uid = await _learner(pool, "self@sp7", course, "sp7")
    c = await _build_course(pool, course, uid, "sp7")

    assert self_pair({"locale": "sp7", "language_code": "sp7"}) is True
    assert self_pair({"locale": "pt", "language_code": "sp7"}) is False

    await _cycle(pool)

    async with pool.privileged_connection() as conn:
        rows = await conn.fetch(
            """SELECT dht.hint, dht.translation
                 FROM drill_hint_translations dht
                 JOIN drill_sentences ds ON ds.id = dht.drill_id
                 JOIN grammar_points gp ON gp.id = ds.grammar_point_id
                WHERE gp.language_id = $1 AND dht.locale = 'sp7'""",
            course)
        assert rows, "drills were not attempted at all"
        # No meaning-line was ever rendered into the course language…
        assert all(r["translation"] is None for r in rows), [
            r["translation"] for r in rows]
        # …but the hint was (the second of the batch; the mock rejects #0).
        assert any((r["hint"] or "").startswith("[Selfish7]") for r in rows)

        # The card therefore still shows the authored English meaning-line.
        due_batch = await add_mixed_learn_batch(conn, uid, course, 10)
        await confirm_learn_batch(conn, uid, [str(i) for i in due_batch["items"]])
        due = await get_due_cards(conn, course, 20, "sp7")
        grammar = [d for d in due if d["card_type"] == "grammar"]
        assert grammar and all(d["translation"] == "I see it." for d in grammar)

        # And no self-locale example sibling was written either.
        n = await conn.fetchval(
            "SELECT count(*) FROM example_sentences WHERE language_id = $1 "
            "AND translation_locale = 'sp7'", course)
        assert n == 0

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_readiness_drives_the_wait_and_smart_loading_looks_ahead(
    pool, monkeypatch,
):
    """The "you're first here" screen's inputs.

    Readiness reports how much of the NEXT session already reads in the
    learner's language, so the UI can start at 60% rather than holding out
    for a perfect session. And the lookahead is tiered: a pair with nothing
    translated queues a whole level's worth (that first session is the one
    that would otherwise stall), and a nearly-spent queue pulls in the level
    above so moving up doesn't land on a fresh wall of English."""
    from backend.repositories.cards import (
        READY_ENOUGH,
        pretranslate_upcoming,
        session_readiness,
    )

    _mock_ai(monkeypatch)
    course = await _lang(pool, "rd1", "Readyish", auto=True)
    await _lang(pool, "rd2", "Readylocale", auto=False)
    uid = await _learner(pool, "ready@rd1", course, "rd2")
    c = await _build_course(pool, course, uid, "rd1")

    async with pool.privileged_connection() as conn:
        # Nothing translated yet → not ready, and the UI offers the wait.
        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["locale"] == "rd2"
        assert st["threshold"] == READY_ENOUGH
        # 2 words scored twice (gloss + example meaning lines) + 2 points.
        assert st["learn"]["total"] == 6
        assert st["learn"]["ready"] == 0
        assert st["learn"]["ready_enough"] is False

        # First run on an untranslated pair queues far more than one session.
        await conn.execute("DELETE FROM translation_demand WHERE locale = 'rd2'")
        await pretranslate_upcoming(conn, uid, course, batch_size=1)
        # batch_size=1, yet the whole course is queued — the first-run span
        # is a level's worth, not one session's.
        words = await conn.fetchval(
            "SELECT count(*) FROM translation_demand "
            "WHERE locale = 'rd2' AND kind = 'word'")
        points = await conn.fetchval(
            "SELECT count(*) FROM translation_demand "
            "WHERE locale = 'rd2' AND kind = 'explanation'")
        assert words == 2, words
        assert points == 2, points

    # Translate, then readiness should clear the bar.
    await _cycle(pool)
    async with pool.privileged_connection() as conn:
        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["learn"]["ready"] >= 1
        assert st["learn"]["pct"] > 0

        # An English-support learner never waits: their content IS English.
        await conn.execute(
            "UPDATE user_profiles SET support_locale = NULL WHERE id = $1", uid)
        st_en = await session_readiness(conn, uid, course, batch_size=10)
        assert st_en["learn"]["ready_enough"] is True
        assert st_en["review"]["ready_enough"] is True

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_the_level_above_is_queued_when_the_queue_runs_low(pool, monkeypatch):
    """Approaching a level boundary pulls the next level in — deliberately
    ignoring subscriptions, since the whole point is content they have not
    reached yet. Queuing only reorders the loop's work; the per-cycle budget
    still caps what any of it costs."""
    from backend.repositories.cards import pretranslate_upcoming

    _mock_ai(monkeypatch)
    course = await _lang(pool, "lv1", "Levelish", auto=True)
    await _lang(pool, "lv2", "Levellocale", auto=False)
    uid = await _learner(pool, "level@lv1", course, "lv2")

    async with pool.privileged_connection() as conn:
        deck = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 Vocabulary') RETURNING id",
            course)
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", uid, deck)
        # One A1 word (their queue is nearly spent) and A2 words they have
        # not subscribed to and cannot yet reach.
        a1 = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level, frequency_rank) "
            "VALUES ($1, 'lv1uno', 'A1', 1) RETURNING id", course)
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'one')", a1)
        a2_ids = []
        for i in range(3):
            vid = await conn.fetchval(
                "INSERT INTO vocabulary (language_id, word, level, "
                "frequency_rank) VALUES ($1, $2, 'A2', $3) RETURNING id",
                course, f"lv1next{i}", i + 10)
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, 'en', 'next')", vid)
            a2_ids.append(vid)

        await pretranslate_upcoming(conn, uid, course, batch_size=5)

        queued = {r["ref_id"] for r in await conn.fetch(
            "SELECT ref_id FROM translation_demand "
            "WHERE locale = 'lv2' AND kind = 'word'")}
        assert a1 in queued, "their own A1 word was not queued"
        assert queued & set(a2_ids), "the level above was not pulled in"

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)


async def test_the_wait_game_plays_the_session_being_waited_for(pool, monkeypatch):
    """The game's pool is the upcoming batch's already-translated words —
    not the learner's review history. That's what makes it work for someone
    with no cards at all, which is precisely who sees this screen: a brand
    new learner on a brand new pair. The pool also grows as the loop fills,
    so the longer the wait the richer the game."""
    from backend.repositories.cards import session_readiness

    _mock_ai(monkeypatch)
    course = await _lang(pool, "gm1", "Gameish", auto=True)
    await _lang(pool, "gm2", "Gamelocale", auto=False)
    uid = await _learner(pool, "game@gm1", course, "gm2")
    c = await _build_course(pool, course, uid, "gm1")

    async with pool.privileged_connection() as conn:
        # Nothing translated: no pool, so the screen shows progress only —
        # anything it could offer would be English, which is what the
        # learner chose to wait out.
        before = await session_readiness(conn, uid, course, batch_size=10)
        assert before["pairs"] == []
        # This learner has NO cards; the pool must not depend on having any.
        assert await conn.fetchval(
            "SELECT count(*) FROM user_cards WHERE user_id = $1", uid) == 0

    await _cycle(pool)

    async with pool.privileged_connection() as conn:
        after = await session_readiness(conn, uid, course, batch_size=10)
        assert after["pairs"], "no game pool after a translation cycle"
        # Every pair is playable: a word AND a meaning, both non-empty.
        for pair in after["pairs"]:
            assert pair["word"] and pair["gloss"]
        # The pool is drawn from the batch they are about to meet, so the
        # words played are the words taught minutes later.
        words = {p["word"] for p in after["pairs"]}
        assert words <= {"gm1akvo", "gm1domo"}, words

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_demand_beyond_the_cycle_cap_survives_to_the_next_pass(
    pool, monkeypatch,
):
    """Demand the cycle couldn't pay for must stay QUEUED.

    It used to be deleted wholesale after each pass: the lane attempted at
    most BATCH_SIZE rows but cleared every ref_id in the batch, dropping the
    rest onto the breadth-first sweep. That sweep runs orders of magnitude
    slower and reaches the low-priority kinds last, which is how a single
    lesson ended up with some example sentences in the learner's language
    and the others stuck in English for good.
    """
    from backend.services.auto_translate import process_demand

    _mock_ai(monkeypatch)
    course = await _lang(pool, "cp1", "Capish", auto=True)
    await _lang(pool, "cp2", "Caplocale", auto=False)
    uid = await _learner(pool, "cap@cp1", course, "cp2")

    async with pool.privileged_connection() as conn:
        ids = []
        for i in range(6):
            vid = await conn.fetchval(
                "INSERT INTO vocabulary (language_id, word, level, "
                "frequency_rank) VALUES ($1, $2, 'A1', $3) RETURNING id",
                course, f"cp1w{i}", i + 1)
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, 'en', 'thing')", vid)
            await conn.execute(
                "INSERT INTO translation_demand (kind, ref_id, locale) "
                "VALUES ('word', $1, 'cp2')", vid)
            ids.append(vid)

        # A budget that covers only part of the queue.
        stats = {"applied": 0, "queued": 0, "processed": 0, "demand": 0}
        left = await process_demand(conn, 2, stats)

        remaining = await conn.fetchval(
            "SELECT count(*) FROM translation_demand "
            "WHERE locale = 'cp2' AND kind = 'word'")
        # Four never got paid for, and the one the mock rejected keeps its
        # place too — demand is released by content landing, not by having
        # been looked at once.
        assert remaining == 5, f"unpaid or failed demand was dropped: {remaining}"
        assert left == 0, left

        # The next pass clears everything it can. What stays behind is
        # exactly what did not land, each carrying an attempt to pace it.
        await process_demand(conn, 50, stats)
        stuck = await conn.fetch(
            "SELECT ref_id FROM translation_demand "
            "WHERE locale = 'cp2' AND kind = 'word'")
        for r in stuck:
            assert not await conn.fetchval(
                "SELECT count(*) FROM translations "
                "WHERE vocabulary_id = $1 AND locale = 'cp2'", r["ref_id"]), \
                "a glossed word is still queued"
            assert await conn.fetchval(
                "SELECT attempts FROM translation_attempts "
                "WHERE kind = 'word' AND ref_id = $1 AND locale = 'cp2'",
                r["ref_id"]), "a stuck word with no attempt would never be paced"

        # Age the ledger and the stragglers come back rather than being
        # abandoned — the property this whole mechanism exists for.
        await conn.execute(
            "UPDATE translation_attempts SET last_attempt_at = "
            "now() - interval '2 days' WHERE locale = 'cp2'")
        await process_demand(conn, 50, stats)

        # Every word ends up resolved — glossed, or parked for a human.
        settled = await conn.fetchval(
            """SELECT count(*) FROM vocabulary v
                WHERE v.id = ANY($1::uuid[])
                  AND (EXISTS (SELECT 1 FROM translations t
                                WHERE t.vocabulary_id = v.id AND t.locale = 'cp2')
                    OR EXISTS (SELECT 1 FROM translation_reviews r
                                WHERE r.vocabulary_id = v.id AND r.locale = 'cp2'))""",
            ids)
        assert settled == 6, settled

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del uid


async def test_example_meaning_lines_reach_the_learner_not_just_the_database(
    pool, monkeypatch,
):
    """Sentence meaning lines must actually DISPLAY in the learner's language.

    The loop translated them all along, but stored them like AI-invented
    content: reviewed=false, which the card read filters out. So a learner
    whose course was otherwise fully localized still read every example in
    English, with nothing on screen saying anything was pending.

    pending_examples only picks English sentences a human already approved,
    so the sentence and its meaning are signed off — only the wording of the
    meaning line is new, and it comes through the same maker-checker that
    produces word glosses, which display immediately.

    This language is on the STRICT review policy: the fix must not depend on
    an admin loosening it.
    """
    _mock_ai(monkeypatch)
    course = await _lang(pool, "xmp1", "Exampleish", auto=True)
    await _lang(pool, "xmp2", "Examplelocale", auto=False)
    uid = await _learner(pool, "xmp@xmp1", course, "xmp2")
    c = await _build_course(pool, course, uid, "xmp1")

    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE languages SET grammar_review_policy = 'strict' WHERE id = $1",
            course)
        batch = await add_mixed_learn_batch(conn, uid, course, 10)
        card_ids = [str(i) for i in batch["items"]]
        await get_card_details_bulk(conn, card_ids, "xmp2")

    await _cycle(pool)

    async with pool.privileged_connection() as conn:
        # Stored AND visible: the locale sibling is reviewed, so the read
        # path's learner-facing filter keeps it.
        sib = await conn.fetchrow(
            """SELECT translation, reviewed FROM example_sentences
                WHERE language_id = $1 AND translation_locale = 'xmp2'
                LIMIT 1""", course)
        assert sib is not None, "no locale sibling written"
        assert sib["reviewed"] is True, "translation hidden behind the AI gate"
        assert sib["translation"].startswith("[Examplelocale]")

        # What the learner actually reads on the card.
        await confirm_learn_batch(conn, uid, card_ids)
        due = await get_due_cards(conn, course, 20, "xmp2")
        vocab = [d for d in due if d["card_type"] == "vocabulary"]
        shown = [d["translation"] for d in vocab if d.get("translation")]
        assert shown, "no example meaning line served at all"
        assert any(t.startswith("[Examplelocale]") for t in shown), shown

        # The gate still holds for sentences the AI INVENTS.
        from backend.repositories.contributor import add_example_sentence
        invented = await add_example_sentence(
            conn, c["words"][0], course, "xmp1 nova frazo", "A new sentence.",
            source="ai", origin_detail="generate:test")
        assert await conn.fetchval(
            "SELECT reviewed FROM example_sentences WHERE id = $1", invented
        ) is False

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)


async def test_sentences_already_written_hidden_get_un_hidden(pool, monkeypatch):
    """Translations produced BEFORE they were stored visibly must be repaired.

    Those rows aren't merely hidden, they're stuck: pending_examples skips
    any sentence that already has a locale sibling, so the loop believes the
    work is done and never retries. A forward-only fix leaves a learner
    staring at English no matter how many times they reload. The sweep
    repairs them, so this does not wait on the backfill migration.
    """
    _mock_ai(monkeypatch)
    course = await _lang(pool, "hid1", "Hiddenish", auto=True)
    await _lang(pool, "hid2", "Hiddenlocale", auto=False)
    uid = await _learner(pool, "hid@hid1", course, "hid2")
    c = await _build_course(pool, course, uid, "hid1")

    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE languages SET grammar_review_policy = 'strict' WHERE id = $1",
            course)
        # Exactly the old state: a translation that exists but is invisible.
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale, source, origin_detail, reviewed)
               SELECT $1, es.vocabulary_id, es.sentence, '[Hiddenlocale] old',
                      'hid2', 'ai', 'auto_translate:hid2', false
                 FROM example_sentences es
                WHERE es.language_id = $1 AND es.translation_locale = 'en'""",
            course)
        hidden = await conn.fetchval(
            "SELECT count(*) FROM example_sentences "
            "WHERE language_id = $1 AND translation_locale = 'hid2' "
            "AND reviewed = false", course)
        assert hidden > 0, "test did not reproduce the stuck state"

        # Stuck: the loop won't re-translate what already has a sibling.
        from backend.services.auto_translate import pending_examples
        assert await pending_examples(conn, course, "hid2", 50) == []

    await _cycle(pool)

    async with pool.privileged_connection() as conn:
        assert await conn.fetchval(
            "SELECT count(*) FROM example_sentences "
            "WHERE language_id = $1 AND translation_locale = 'hid2' "
            "AND reviewed = false", course) == 0

        # And it reaches the card, on a strict-policy language.
        batch = await add_mixed_learn_batch(conn, uid, course, 10)
        card_ids = [str(i) for i in batch["items"]]
        await confirm_learn_batch(conn, uid, card_ids)
        due = await get_due_cards(conn, course, 20, "hid2")
        shown = [d["translation"] for d in due
                 if d["card_type"] == "vocabulary" and d.get("translation")]
        assert any(t.startswith("[Hiddenlocale]") for t in shown), shown

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_the_self_pair_is_not_scored_on_work_that_never_happens(pool, monkeypatch):
    """Learning a language THROUGH itself must still be able to reach ready.

    The loop deliberately never renders example sentences for a self-pair —
    translating one reproduces the drill sentence with the blank filled in,
    handing over the answer (auto_translate.self_pair). Readiness scored a
    word on its gloss AND its examples regardless, so those points could
    never be earned: the score was capped below the start threshold forever
    and the wait screen could never advance on its own.
    """
    from backend.repositories.cards import READY_ENOUGH, session_readiness

    _mock_ai(monkeypatch)
    course = await _lang(pool, "sp1", "Selfish", auto=True)
    uid = await _learner(pool, "self@sp1", course, "sp1")   # course == locale
    c = await _build_course(pool, course, uid, "sp1")

    async with pool.privileged_connection() as conn:
        st = await session_readiness(conn, uid, course, batch_size=10)
        # 2 words + 2 grammar points. Words score ONCE here, not twice.
        assert st["learn"]["total"] == 4, st["learn"]

    await _cycle(pool)

    async with pool.privileged_connection() as conn:
        # Glosses and explanations are all this pair can ever have, so with
        # those filled it must reach 100% — under the old scoring it was
        # capped at half regardless, permanently short of the threshold.
        for vid in c["words"]:
            await conn.execute(
                """INSERT INTO translations (vocabulary_id, locale, definition)
                   VALUES ($1, 'sp1', 'definición')
                   ON CONFLICT (vocabulary_id, locale) DO NOTHING""", vid)
        for gp in c["points"]:
            await conn.execute(
                """INSERT INTO explanation_translations
                       (grammar_point_id, locale, explanation)
                   VALUES ($1, 'sp1', 'explicación')
                   ON CONFLICT DO NOTHING""", gp)

        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["learn"]["pct"] == 1.0, st["learn"]
        assert st["learn"]["ready_enough"] is True
        assert st["learn"]["pct"] >= READY_ENOUGH

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_a_normal_pair_still_scores_its_example_lines(pool, monkeypatch):
    """The self-pair exemption must not quietly disable the check that made
    readiness honest for everyone else."""
    from backend.repositories.cards import session_readiness

    _mock_ai(monkeypatch)
    course = await _lang(pool, "np1", "Normalish", auto=True)
    await _lang(pool, "np2", "Normallocale", auto=False)
    uid = await _learner(pool, "norm@np1", course, "np2")
    c = await _build_course(pool, course, uid, "np1")

    async with pool.privileged_connection() as conn:
        st = await session_readiness(conn, uid, course, batch_size=10)
        # 2 words counted TWICE (gloss + examples) + 2 grammar points.
        assert st["learn"]["total"] == 6, st["learn"]
        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_a_few_ready_cards_open_the_gate_at_a_low_percentage(
    pool, monkeypatch,
):
    """The gate a learner actually feels: enough CARDS to start on.

    The percentage measures the whole batch, glosses and example sentences
    together, and sentences are translated last — so it climbs slowly and
    stays low long after there is real work available. Gating on it alone
    left someone sitting at 5% with usable cards already waiting and no way
    in, which is the shape of every "it got stuck" report.

    Cards ready is the other way in. Sentences still drive the percentage
    and still fill during the session (the learn loop re-serves its lessons
    on every advance), but they no longer keep anyone out.
    """
    from backend.repositories.cards import (
        READY_ENOUGH,
        START_CARDS,
        session_readiness,
    )

    _mock_ai(monkeypatch)
    course = await _lang(pool, "gate1", "Gateish", auto=True)
    await _lang(pool, "gate2", "Gatelocale", auto=False)
    uid = await _learner(pool, "gate@gate1", course, "gate2")
    c = await _build_course(pool, course, uid, "gate1")

    async with pool.privileged_connection() as conn:
        # Four cards: two words, two grammar points. Nothing translated.
        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["learn"]["cards"] == 4
        assert st["learn"]["cards_ready"] == 0
        assert st["learn"]["start_cards"] == START_CARDS
        assert st["learn"]["ready_enough"] is False

        # Two glosses and one explanation land — nothing else. Every example
        # sentence is still English, so the percentage stays under the bar.
        for vid in c["words"]:
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, 'gate2', 'rendered')", vid)
        await conn.execute(
            "INSERT INTO explanation_translations (grammar_point_id, locale, "
            "explanation) VALUES ($1, 'gate2', 'rendered')", c["points"][0])

        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["learn"]["cards_ready"] == START_CARDS
        # The old gate would still be shut: 3 of 6 points is under 0.6.
        assert st["learn"]["pct"] < READY_ENOUGH
        # The new one is open.
        assert st["learn"]["ready_enough"] is True

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_the_review_queue_is_reachable_by_the_fill_that_gates_it(
    pool, monkeypatch,
):
    """A stalled REVIEW session must be able to name the cards it is stuck on.

    Every selector feeding the inline fill returned work the learner had
    NOT started — which is, by definition, everything the review queue is
    not. So a review session gated on its own half asked for a fill and
    got the learn batch: words the learner wasn't waiting on, paid for out
    of the same per-(user, language) cooldown that the review half needed.
    The owner watched "0 of 3" on a Hindi review session while the match
    game beside it filled up with freshly French-glossed words from the
    learn batch — the fill working perfectly, aimed at the wrong half.
    """
    from backend.repositories.cards import (
        due_batch_ids,
        session_readiness,
        start_batch_ids,
    )

    _mock_ai(monkeypatch)
    course = await _lang(pool, "revq1", "Reviewish", auto=True)
    await _lang(pool, "revq2", "Reviewlocale", auto=False)
    uid = await _learner(pool, "due@revq1", course, "revq2")
    c = await _build_course(pool, course, uid, "revq")

    async with pool.privileged_connection() as conn:
        batch = await add_mixed_learn_batch(conn, uid, course, 10)
        assert batch["added"] == 4
        # They finished the lesson: the cards are live and come round again.
        await conn.execute(
            "UPDATE user_cards SET is_suspended = false, next_review = now() "
            "WHERE user_id = $1 AND language_id = $2", uid, course)

        # Nothing left to learn, four cards to review — the exact split the
        # fill used to get backwards.
        learn_v, learn_g = await start_batch_ids(conn, uid, course, 10)
        due_v, due_g = await due_batch_ids(conn, uid, course, 10)
        assert (learn_v, learn_g) == ([], [])
        assert sorted(str(i) for i in due_v) == sorted(c["words"])
        assert sorted(str(i) for i in due_g) == sorted(c["points"])

        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["learn"]["ready_enough"] is True   # nothing to wait for
        assert st["review"]["cards"] == 4
        assert st["review"]["cards_ready"] == 0
        assert st["review"]["ready_enough"] is False

        # Translate what the review gate is actually scoring, and it opens.
        for vid in c["words"]:
            await conn.execute(
                "INSERT INTO translations (vocabulary_id, locale, definition) "
                "VALUES ($1, 'revq2', 'rendered')", vid)
        await conn.execute(
            "INSERT INTO explanation_translations (grammar_point_id, locale, "
            "explanation) VALUES ($1, 'revq2', 'rendered')", c["points"][0])

        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["review"]["cards_ready"] == 3
        assert st["review"]["ready_enough"] is True

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)


async def test_the_due_queue_is_queued_for_the_loop_as_well(pool, monkeypatch):
    """...and the background loop hears about it too.

    pretranslate_upcoming is what stocks the demand table between sessions.
    It looked ahead over unstarted vocabulary only, so on a support locale
    nobody had used before, a returning learner's due queue — the half they
    actually open — had no demand recorded against it at all.
    """
    from backend.repositories.cards import pretranslate_upcoming

    _mock_ai(monkeypatch)
    course = await _lang(pool, "revq3", "Duelandish", auto=True)
    await _lang(pool, "revq4", "Duelocale", auto=False)
    uid = await _learner(pool, "loop@revq3", course, "revq4")
    c = await _build_course(pool, course, uid, "revd")

    async with pool.privileged_connection() as conn:
        await add_mixed_learn_batch(conn, uid, course, 10)
        await conn.execute(
            "UPDATE user_cards SET is_suspended = false, next_review = now() "
            "WHERE user_id = $1 AND language_id = $2", uid, course)
        await conn.execute("DELETE FROM translation_demand WHERE locale = $1",
                           "revq4")

        await pretranslate_upcoming(conn, uid, course, batch_size=10)

        queued = {str(r["ref_id"]) for r in await conn.fetch(
            "SELECT ref_id FROM translation_demand "
            " WHERE locale = 'revq4' AND kind = 'word'")}
        assert set(c["words"]) <= queued

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)


async def test_the_gate_scales_down_to_a_batch_smaller_than_the_threshold(
    pool, monkeypatch,
):
    """A two-card batch must not need three ready cards to start."""
    from backend.repositories.cards import session_readiness

    _mock_ai(monkeypatch)
    course = await _lang(pool, "gate3", "Smallish", auto=True)
    await _lang(pool, "gate4", "Smalllocale", auto=False)
    uid = await _learner(pool, "small@gate3", course, "gate4")

    async with pool.privileged_connection() as conn:
        deck = await conn.fetchval(
            "INSERT INTO content_lists (language_id, list_type, level, title) "
            "VALUES ($1, 'vocabulary', 'A1', 'A1 Vocabulary') RETURNING id",
            course)
        await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2)", uid, deck)
        vid = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level, frequency_rank) "
            "VALUES ($1, 'lone', 'A1', 1) RETURNING id", course)
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', 'only')", vid)

        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["learn"]["cards"] == 1
        assert st["learn"]["start_cards"] == 1
        assert st["learn"]["ready_enough"] is False

        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'gate4', 'rendered')", vid)
        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["learn"]["ready_enough"] is True

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)


async def test_the_automatic_help_language_follows_the_interface(
    pool, monkeypatch,
):
    """The state machine the owner asked for, end to end.

    Automatic (support_locale NULL) means the help language IS the
    interface language, resolved at read time — nothing chosen, nothing
    stored, nothing to go stale. Before this rule, "automatic" was
    materialized by the globe writing support_locale, which converted it
    into a frozen choice: the observed result was an English interface
    whose Speak coach wrote French, because every backend reader treated
    the raw column as the truth and NULL as English.

    Here: an automatic learner's readiness, demand queue and rendered
    cards all speak the interface language — and when the interface
    changes, they all move together, instantly, with no write to
    support_locale at all.
    """
    from backend.repositories.cards import session_readiness

    _mock_ai(monkeypatch)
    course = await _lang(pool, "aut1", "Autoish", auto=True)
    await _lang(pool, "aut2", "Autolocale", auto=False)
    uid = await _learner(pool, "auto@aut1", course, None)
    c = await _build_course(pool, course, uid, "aut")

    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE user_profiles SET ui_language = 'aut2' WHERE id = $1", uid)

        # Readiness scores the INTERFACE language, not English.
        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["locale"] == "aut2"
        assert st["learn"]["ready_enough"] is False

        # The demand the wait screen records is for that language too.
        await pretranslate_upcoming(conn, uid, course, batch_size=10)
        queued = {r["locale"] for r in await conn.fetch(
            "SELECT DISTINCT locale FROM translation_demand")}
        assert "aut2" in queued

    # One loop cycle — the sweep's profile scan must FIND the automatic
    # learner (it used to filter on the raw column and skip them).
    stats = await _cycle(pool)
    assert stats["demand"] >= 1

    async with pool.privileged_connection() as conn:
        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["learn"]["cards_ready"] >= 1

        # The globe flips the interface to English → the help language
        # follows in the SAME read. No stored state, so nothing can lag or
        # freeze: this is the "stable once they decide" property.
        await conn.execute(
            "UPDATE user_profiles SET ui_language = 'en' WHERE id = $1", uid)
        st = await session_readiness(conn, uid, course, batch_size=10)
        assert st["locale"] is None or st["locale"] == "en"
        assert st["learn"]["ready_enough"] is True  # English needs no wait

        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_an_explicit_choice_survives_interface_flips(pool, monkeypatch):
    """The other half of the rule: a decision, once made, never moves.

    A learner who chose their help language in Settings keeps it through
    any number of interface changes — the exact opposite of the freeze
    bug, where a language nobody chose kept overriding. Decided = stable;
    undecided = follows. Never a third state.
    """
    from backend.repositories.cards import session_readiness

    _mock_ai(monkeypatch)
    course = await _lang(pool, "exp1", "Explicitish", auto=True)
    await _lang(pool, "exp2", "Explocale", auto=False)
    await _lang(pool, "exp3", "Otherlocale", auto=False)
    uid = await _learner(pool, "explicit@exp1", course, "exp2")
    c = await _build_course(pool, course, uid, "exp")

    async with pool.privileged_connection() as conn:
        for ui in ("en", "exp3", "en"):
            await conn.execute(
                "UPDATE user_profiles SET ui_language = $2 WHERE id = $1",
                uid, ui)
            st = await session_readiness(conn, uid, course, batch_size=10)
            assert st["locale"] == "exp2", (
                f"explicit choice moved under ui_language={ui!r}"
            )
        await conn.execute(
            "UPDATE languages SET auto_translate_enabled = false WHERE id = $1",
            course)
    del c


async def test_the_settings_level_reaches_every_prompt(pool, monkeypatch):
    """Stage 1 of adaptive-sessions, end to end against a real database.

    Before: Settings → Your level re-seated deck subscriptions and stored
    nothing; get_assessment_summary derived level from card history
    (fallback A1), so the choice never reached a single AI prompt. Now
    set_learner_level persists chosen_level and the assessment applies it
    as a floor — the same summary object Tutor, Read and Speak all read.
    """
    from backend.repositories.assessment import get_assessment_summary
    from backend.repositories.onboarding import set_learner_level

    _mock_ai(monkeypatch)
    course = await _lang(pool, "lvl1", "Levelish", auto=False)
    uid = await _learner(pool, "level@lvl1", course, None)
    c = await _build_course(pool, course, uid, "lvl")

    async with pool.privileged_connection() as conn:
        # A young account: card evidence is thin, so the derived level is
        # the A1 default.
        before = await get_assessment_summary(conn, uid, course)
        assert before["level"] == "A1"

        # The user sets B2 in Settings. Decks re-seat AND the choice is
        # stored — the half that was missing.
        result = await set_learner_level(conn, uid, course, "B2")
        assert result["level"] == "B2"

        after = await get_assessment_summary(conn, uid, course)
        assert after["level"] == "B2"
        assert after["chosen_level"] == "B2"

        # Changed again, it follows again — no freeze, no cache.
        await set_learner_level(conn, uid, course, "A2")
        again = await get_assessment_summary(conn, uid, course)
        assert again["level"] == "A2"
    del c
