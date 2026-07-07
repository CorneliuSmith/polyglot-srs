"""User cards repository — RLS-protected queries."""

from __future__ import annotations

import hashlib
import json

import asyncpg

from backend.repositories.curriculum import get_read_ref_keys, resolve_related
from backend.services.extract import ANSWER_MARKER, make_cloze
from backend.services.references import clean_references
from backend.services.srs_stages import stage_for


async def get_due_cards(
    conn: asyncpg.Connection, language_id: str, limit: int = 20
) -> list[dict]:
    """Return due cards for the authenticated user with full card content.

    Performs two queries (one for vocabulary, one for grammar) merged in Python
    and sorted by next_review ASC.  RLS automatically filters to the
    connection's user context.

    Vocabulary cards — type-the-word mode:
      sentence = definition text (no {{answer}} marker)
      correct_answer = vocabulary.word

    Grammar cards — fill-in-the-blank mode:
      sentence = drill sentence with {{answer}} marker
      correct_answer = grammar_points.title (placeholder for Phase 4)
    """
    # -- Vocabulary cards ---------------------------------------------------
    # Teach the word in context: a real example sentence with the word blanked
    # out (cloze), with its translation as a hint. All of the word's sentences
    # are fetched and each APPEARANCE shows one at random — never the sentence
    # shown last time (review_log.prompt_sentence) — so the learner practices
    # the word, not one memorized string. Falls back to the plain
    # definition -> type-the-word prompt when no sentence works.
    vocab_rows = await conn.fetch(
        """
        SELECT
            uc.id,
            uc.user_id,
            uc.language_id,
            uc.card_type,
            uc.card_id,
            v.word                          AS word,
            t.definition                    AS definition,
            ex.sentences                    AS example_sentences,
            ex.translations                 AS example_translations,
            ex.glosses                      AS example_glosses,
            ex.transliterations             AS example_transliterations,
            lp.prompt_sentence              AS last_prompt,
            v.morphology                    AS morphology,
            v.alternatives                  AS alternatives,
            l.code                          AS language_code,
            uc.ease_factor,
            uc.interval,
            uc.repetitions,
            uc.streak,
            uc.lapses,
            uc.next_review
        FROM user_cards uc
        JOIN vocabulary v       ON uc.card_id = v.id
        JOIN languages l        ON uc.language_id = l.id
        LEFT JOIN translations t
               ON v.id = t.vocabulary_id AND t.locale = 'en'
        LEFT JOIN LATERAL (
            SELECT
                array_agg(es.sentence
                          ORDER BY es.difficulty_rank ASC NULLS LAST, es.id) AS sentences,
                array_agg(es.translation
                          ORDER BY es.difficulty_rank ASC NULLS LAST, es.id) AS translations,
                array_agg(es.gloss
                          ORDER BY es.difficulty_rank ASC NULLS LAST, es.id) AS glosses,
                array_agg(es.transliteration
                          ORDER BY es.difficulty_rank ASC NULLS LAST, es.id) AS transliterations
            FROM example_sentences es
            WHERE es.vocabulary_id = v.id
        ) ex ON true
        LEFT JOIN LATERAL (
            SELECT rl.prompt_sentence
            FROM review_log rl
            WHERE rl.card_id = uc.id AND rl.prompt_sentence IS NOT NULL
            ORDER BY rl.created_at DESC
            LIMIT 1
        ) lp ON true
        WHERE uc.language_id = $1
          AND uc.card_type = 'vocabulary'
          AND uc.next_review <= now()
          AND uc.is_suspended = false
        ORDER BY uc.next_review ASC
        LIMIT $2
        """,
        language_id,
        limit,
    )

    # -- Grammar cards -------------------------------------------------------
    # Fill-in-the-blank drills. All of a point's drills are fetched and each
    # appearance shows one at random, never the last-shown (same as vocab).
    grammar_rows = await conn.fetch(
        """
        SELECT
            uc.id,
            uc.user_id,
            uc.language_id,
            uc.card_type,
            uc.card_id,
            gp.title                        AS title,
            d.sentences                     AS drill_sentences,
            d.answers                       AS drill_answers,
            d.hints                         AS drill_hints,
            d.translations                  AS drill_translations,
            d.glosses                       AS drill_glosses,
            d.transliterations              AS drill_transliterations,
            lp.prompt_sentence              AS last_prompt,
            l.code                          AS language_code,
            uc.ease_factor,
            uc.interval,
            uc.repetitions,
            uc.streak,
            uc.lapses,
            uc.next_review
        FROM user_cards uc
        JOIN grammar_points gp  ON uc.card_id = gp.id
        JOIN languages l        ON uc.language_id = l.id
        LEFT JOIN LATERAL (
            SELECT
                array_agg(ds.sentence    ORDER BY ds.display_order, ds.id) AS sentences,
                array_agg(ds.answer      ORDER BY ds.display_order, ds.id) AS answers,
                array_agg(ds.hint        ORDER BY ds.display_order, ds.id) AS hints,
                array_agg(ds.translation ORDER BY ds.display_order, ds.id) AS translations,
                array_agg(ds.gloss       ORDER BY ds.display_order, ds.id) AS glosses,
                array_agg(ds.transliteration ORDER BY ds.display_order, ds.id) AS transliterations
            FROM drill_sentences ds
            WHERE ds.grammar_point_id = gp.id
        ) d ON true
        LEFT JOIN LATERAL (
            SELECT rl.prompt_sentence
            FROM review_log rl
            WHERE rl.card_id = uc.id AND rl.prompt_sentence IS NOT NULL
            ORDER BY rl.created_at DESC
            LIMIT 1
        ) lp ON true
        WHERE uc.language_id = $1
          AND uc.card_type = 'grammar'
          AND uc.next_review <= now()
          AND uc.is_suspended = false
        ORDER BY uc.next_review ASC
        LIMIT $2
        """,
        language_id,
        limit,
    )

    # -- Personal cloze cards (learner's own text) --------------------------
    personal_rows = await conn.fetch(
        """
        SELECT
            uc.id,
            uc.user_id,
            uc.language_id,
            uc.card_type,
            uc.card_id,
            cc.sentence                     AS sentence,
            cc.answer                       AS correct_answer,
            NULL::text                      AS hint,
            cc.translation                  AS translation,
            NULL::jsonb                     AS morphology,
            NULL::text[]                    AS alternatives,
            l.code                          AS language_code,
            uc.ease_factor,
            uc.interval,
            uc.repetitions,
            uc.streak,
            uc.lapses,
            uc.next_review
        FROM user_cards uc
        JOIN user_cloze_cards cc ON uc.card_id = cc.id
        JOIN languages l         ON uc.language_id = l.id
        WHERE uc.language_id = $1
          AND uc.card_type = 'personal'
          AND uc.next_review <= now()
          AND uc.is_suspended = false
        ORDER BY uc.next_review ASC
        LIMIT $2
        """,
        language_id,
        limit,
    )

    # Per-sentence history for the gap-hunting rotation (one query for the
    # whole batch).
    stats = await _sentence_stats(
        conn, [str(r["id"]) for r in [*vocab_rows, *grammar_rows]]
    )

    # Merge and sort by next_review
    combined = (
        [_vocab_card(r, stats.get(str(r["id"]), {})) for r in vocab_rows]
        + [_grammar_card(r, stats.get(str(r["id"]), {})) for r in grammar_rows]
        + [dict(r) for r in personal_rows]
    )
    combined.sort(key=lambda r: r["next_review"])
    return combined[:limit]


def _srs_fields(r: asyncpg.Record) -> dict:
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "language_id": r["language_id"],
        "card_type": r["card_type"],
        "card_id": r["card_id"],
        "language_code": r["language_code"],
        "ease_factor": r["ease_factor"],
        "interval": r["interval"],
        "repetitions": r["repetitions"],
        "streak": r["streak"],
        "lapses": r["lapses"],
        "next_review": r["next_review"],
    }


def _stable_pick(n: int, key: str) -> int:
    """Deterministic index in [0, n): same card state -> same pick.

    Sentences rotate per APPEARANCE, not per page load: the key folds in the
    card's review counters and the last-shown prompt, so a reload mid-review
    shows the same sentence, while an actual recorded review advances the
    rotation (counters and last_prompt change).
    """
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % n


def _rotation_key(r: asyncpg.Record) -> str:
    return f"{r['id']}:{r['repetitions']}:{r['lapses']}:{r['last_prompt'] or ''}"


async def _sentence_stats(
    conn: asyncpg.Connection, card_ids: list[str]
) -> dict[str, dict[str, tuple[int, int]]]:
    """Per-sentence (times shown, times missed) for each card, from the log.

    This is what makes a paradigm point behave like N questions instead of
    one: the rotation below uses it to hunt the sentences — and therefore the
    paradigm cells — the learner hasn't seen or keeps missing.
    """
    if not card_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT card_id, prompt_sentence,
               count(*) AS seen,
               count(*) FILTER (WHERE answer_result IN ('wrong', 'wrong_form'))
                   AS misses
        FROM review_log
        WHERE card_id = ANY($1::uuid[]) AND prompt_sentence IS NOT NULL
        GROUP BY card_id, prompt_sentence
        """,
        card_ids,
    )
    out: dict[str, dict[str, tuple[int, int]]] = {}
    for r in rows:
        out.setdefault(str(r["card_id"]), {})[r["prompt_sentence"]] = (
            int(r["seen"]), int(r["misses"]),
        )
    return out


def _pick_index(
    prompts: list[str],
    last_prompt: str | None,
    stats: dict[str, tuple[int, int]],
    key: str,
) -> int:
    """Gap-hunting rotation: unseen first, then most-missed, else uniform.

    Never repeats the last-shown prompt (when there's a choice), and every
    branch resolves via the same deterministic hash, so reloads mid-review
    stay stable and the pick only advances when a review is recorded.
    """
    idxs = [i for i, p in enumerate(prompts) if p != last_prompt] or list(
        range(len(prompts))
    )
    unseen = [i for i in idxs if prompts[i] not in stats]
    if unseen:
        pool = unseen
    else:
        missed = [i for i in idxs if stats[prompts[i]][1] > 0]
        if missed:
            def miss_rate(i: int) -> float:
                seen, misses = stats[prompts[i]]
                return misses / seen

            worst = max(miss_rate(i) for i in missed)
            pool = [i for i in missed if miss_rate(i) == worst]
        else:
            pool = idxs
    return pool[_stable_pick(len(pool), key)]


def _vocab_card(r: asyncpg.Record, stats: dict[str, tuple[int, int]]) -> dict:
    """Shape a vocabulary row into a card, preferring a cloze example sentence.

    The sentence changes on every APPEARANCE of the card (Bunpro-style): a
    deterministic, gap-hunting pick among the word's sentences — stable
    across page reloads — that prefers sentences never shown, then the ones
    the learner keeps missing, and never repeats the one shown last time
    (review_log.prompt_sentence). Sentences where the word is inflected
    beyond a whole-word match are skipped by make_cloze. Falls back to the
    definition -> type-the-word prompt when nothing clozes.
    """
    word = r["word"]
    sentences = r["example_sentences"] or []
    translations = r["example_translations"] or []
    glosses = r["example_glosses"] or []
    translits = r["example_transliterations"] or []
    candidates = []
    for i, raw in enumerate(sentences):
        cloze = make_cloze(raw, word)
        if cloze:
            candidates.append((
                cloze,
                translations[i] if i < len(translations) else None,
                glosses[i] if i < len(glosses) else None,
                translits[i] if i < len(translits) else None,
            ))
    sentence, translation, hint = (r["definition"] or word), None, None
    gloss, transliteration = None, None
    if candidates:
        idx = _pick_index(
            [c[0] for c in candidates], r["last_prompt"], stats, _rotation_key(r)
        )
        sentence, translation, gloss, transliteration = candidates[idx]
        hint = r["definition"]
    return {
        **_srs_fields(r),
        "sentence": sentence,
        "correct_answer": word,
        "hint": hint,
        "translation": translation,
        "gloss": gloss,
        "transliteration": transliteration,
        "morphology": r["morphology"],
        "alternatives": r["alternatives"],
    }


def _grammar_card(r: asyncpg.Record, stats: dict[str, tuple[int, int]]) -> dict:
    """Shape a grammar row into a fill-in-the-blank card, rotating drills.

    The drill changes on every APPEARANCE (deterministic, stable across page
    reloads, never the last-shown), gap-hunting across the point's drills:
    a paradigm point (subject pronouns, a conjugation table) is really N
    questions wearing one card, so unseen cells come first and missed cells
    come back until they stick. Points without drills fall back to a
    type-the-title card for legacy rows only — new learns are gated on having
    drills, so this shouldn't be reachable for fresh content.
    """
    drills = r["drill_sentences"] or []
    gloss, transliteration = None, None
    if drills:
        idx = _pick_index(list(drills), r["last_prompt"], stats, _rotation_key(r))
        sentence = drills[idx]
        answer = (r["drill_answers"] or [None])[idx]
        hint = (r["drill_hints"] or [None] * len(drills))[idx]
        translation = (r["drill_translations"] or [None] * len(drills))[idx]
        gloss = (r["drill_glosses"] or [None] * len(drills))[idx]
        transliteration = (r["drill_transliterations"] or [None] * len(drills))[idx]
    else:
        sentence, answer, hint, translation = r["title"], r["title"], None, None
    return {
        **_srs_fields(r),
        "sentence": sentence,
        "correct_answer": answer,
        "hint": hint,
        "translation": translation,
        "gloss": gloss,
        "transliteration": transliteration,
        "morphology": None,
        "alternatives": None,
    }


async def add_learn_batch(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
    level: str | None = None,
) -> dict:
    """Add a batch of new vocabulary cards to user_cards from subscribed lists.

    Selects vocabulary the user has not yet learned, ordered by frequency_rank
    ASC (most frequent first), limited to batch_size.  Cards are inserted with
    default SRS values and next_review = now() so they are immediately due.
    When *level* is given, the batch draws only from that CEFR level (a
    specific deck) instead of everything subscribed.

    Returns:
        {"added": int, "items": list[str]}  — count and list of new user_card IDs
    """
    # Select candidate vocabulary IDs the user hasn't started yet.
    # Content lists are level-based: a NULL-level list covers the whole
    # language; otherwise membership means vocabulary.level = list.level.
    # DISTINCT guards against duplicates when multiple subscribed lists
    # match the same word (would violate user_cards' unique constraint).
    vocab_rows = await conn.fetch(
        """
        SELECT DISTINCT v.id, v.frequency_rank
        FROM vocabulary v
        JOIN content_lists cl
               ON v.language_id = cl.language_id
              AND cl.list_type = 'vocabulary'
              AND (cl.level IS NULL OR cl.level = v.level)
        JOIN user_content_subscriptions ucs
               ON cl.id = ucs.content_list_id
              AND ucs.user_id = $1
        WHERE v.language_id = $2
          AND ($4::text IS NULL OR v.level = $4)
          -- exclude items already in the deck, EXCEPT suspended never-reviewed
          -- ones: those are abandoned walkthroughs waiting to be re-taught
          AND v.id NOT IN (
              SELECT card_id FROM user_cards
              WHERE user_id = $1 AND card_type = 'vocabulary'
                AND NOT (is_suspended AND repetitions = 0)
          )
        ORDER BY v.frequency_rank ASC NULLS LAST
        LIMIT $3
        """,
        user_id,
        language_id,
        batch_size,
        level,
    )

    if not vocab_rows:
        return {"added": 0, "items": []}

    vocab_ids = [r["id"] for r in vocab_rows]

    # Insert new user_cards SUSPENDED: they enter the review queue only when
    # the learner finishes the lesson walkthrough (confirm_learn_batch). If
    # the page never loads, nothing leaks into reviews.
    # ON CONFLICT: two concurrent learn calls (e.g. React StrictMode
    # double-firing the mutation) can both select the same candidates; the
    # WHERE keeps the update to re-teachable rows so an active card is never
    # re-suspended.
    inserted_ids = []
    for vocab_id in vocab_ids:
        row = await conn.fetchrow(
            """
            INSERT INTO user_cards
                (user_id, language_id, card_type, card_id,
                 ease_factor, interval, repetitions, streak, lapses,
                 next_review, is_suspended)
            VALUES
                ($1, $2, 'vocabulary', $3,
                 2.5, 0, 0, 0, 0,
                 now(), true)
            ON CONFLICT (user_id, card_type, card_id) DO UPDATE
                SET is_suspended = true
                WHERE user_cards.is_suspended AND user_cards.repetitions = 0
            RETURNING id
            """,
            user_id,
            language_id,
            vocab_id,
        )
        if row is not None:
            inserted_ids.append(str(row["id"]))

    return {"added": len(inserted_ids), "items": inserted_ids}


async def add_grammar_learn_batch(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
    level: str | None = None,
) -> dict:
    """Add a batch of new grammar cards from the user's subscribed grammar lists.

    Mirrors add_learn_batch but for grammar_points: selects points the user
    hasn't started, ordered by display_order, from grammar content lists the
    user is subscribed to (matched by level), and inserts grammar user_cards
    due immediately. When *level* is given, only that deck's points qualify.
    """
    rows = await conn.fetch(
        """
        SELECT DISTINCT gp.id, gp.display_order
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        JOIN content_lists cl
               ON gp.language_id = cl.language_id
              AND cl.list_type = 'grammar'
              AND (cl.level IS NULL OR cl.level = gp.level)
        JOIN user_content_subscriptions ucs
               ON cl.id = ucs.content_list_id
              AND ucs.user_id = $1
        WHERE gp.language_id = $2
          -- review policy: strict = reviewed only; ai_ok = also AI-passed
          AND (gp.reviewed = true
               OR (l.grammar_review_policy = 'ai_ok' AND gp.ai_check_status = 'pass'))
          -- a point with no drills has nothing to quiz — never learnable
          AND EXISTS (
              SELECT 1 FROM drill_sentences ds WHERE ds.grammar_point_id = gp.id
          )
          AND ($4::text IS NULL OR gp.level = $4)
          AND gp.id NOT IN (
              SELECT card_id FROM user_cards
              WHERE user_id = $1 AND card_type = 'grammar'
                AND NOT (is_suspended AND repetitions = 0)
          )
        ORDER BY gp.display_order ASC
        LIMIT $3
        """,
        user_id,
        language_id,
        batch_size,
        level,
    )
    if not rows:
        return {"added": 0, "items": []}

    # Same suspended-until-confirmed + racing-learn-call handling as
    # add_learn_batch.
    inserted_ids = []
    for r in rows:
        row = await conn.fetchrow(
            """
            INSERT INTO user_cards
                (user_id, language_id, card_type, card_id,
                 ease_factor, interval, repetitions, streak, lapses,
                 next_review, is_suspended)
            VALUES
                ($1, $2, 'grammar', $3, 2.5, 0, 0, 0, 0, now(), true)
            ON CONFLICT (user_id, card_type, card_id) DO UPDATE
                SET is_suspended = true
                WHERE user_cards.is_suspended AND user_cards.repetitions = 0
            RETURNING id
            """,
            user_id,
            language_id,
            r["id"],
        )
        if row is not None:
            inserted_ids.append(str(row["id"]))

    return {"added": len(inserted_ids), "items": inserted_ids}


async def confirm_learn_batch(
    conn: asyncpg.Connection, user_id: str, card_ids: list[str]
) -> int:
    """Activate learned cards after the lesson walkthrough is completed.

    Cards are created suspended by the learn batch; this flips them into the
    review queue, due immediately. Only never-reviewed cards qualify — a card
    with history can't be re-activated through the learn flow.
    """
    if not card_ids:
        return 0
    result = await conn.execute(
        """
        UPDATE user_cards
        SET is_suspended = false, next_review = now()
        WHERE id = ANY($1::uuid[])
          AND user_id = $2
          AND is_suspended
          AND repetitions = 0
        """,
        card_ids,
        user_id,
    )
    return int(result.split(" ")[-1])


async def get_learn_decks(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> list[dict]:
    """Return the language's learn decks (content lists) with progress.

    One row per content list (Bunpro-style deck): what it is, how many items
    it holds (only learnable ones — visible grammar with drills, all vocab),
    how many the user has started, and whether they're subscribed. The learned
    counts intentionally ignore subscription: progress shows even on decks the
    user hasn't queued yet.
    """
    rows = await conn.fetch(
        """
        SELECT
            cl.id,
            cl.list_type,
            cl.level,
            cl.title,
            (ucs.user_id IS NOT NULL) AS subscribed,
            CASE WHEN cl.list_type = 'grammar' THEN (
                SELECT COUNT(*)
                FROM grammar_points gp
                JOIN languages l ON gp.language_id = l.id
                WHERE gp.language_id = cl.language_id
                  AND (cl.level IS NULL OR gp.level = cl.level)
                  AND (gp.reviewed = true
                       OR (l.grammar_review_policy = 'ai_ok'
                           AND gp.ai_check_status = 'pass'))
                  AND EXISTS (
                      SELECT 1 FROM drill_sentences ds
                      WHERE ds.grammar_point_id = gp.id
                  )
            ) ELSE (
                SELECT COUNT(*)
                FROM vocabulary v
                WHERE v.language_id = cl.language_id
                  AND (cl.level IS NULL OR v.level = cl.level)
            ) END AS total,
            CASE WHEN cl.list_type = 'grammar' THEN (
                SELECT COUNT(*)
                FROM user_cards uc
                JOIN grammar_points gp
                     ON uc.card_id = gp.id AND uc.card_type = 'grammar'
                WHERE uc.user_id = $1
                  AND gp.language_id = cl.language_id
                  AND (cl.level IS NULL OR gp.level = cl.level)
                  -- unconfirmed walkthroughs don't count as learned
                  AND NOT (uc.is_suspended AND uc.repetitions = 0)
            ) ELSE (
                SELECT COUNT(*)
                FROM user_cards uc
                JOIN vocabulary v
                     ON uc.card_id = v.id AND uc.card_type = 'vocabulary'
                WHERE uc.user_id = $1
                  AND v.language_id = cl.language_id
                  AND (cl.level IS NULL OR v.level = cl.level)
                  AND NOT (uc.is_suspended AND uc.repetitions = 0)
            ) END AS learned
        FROM content_lists cl
        LEFT JOIN user_content_subscriptions ucs
               ON ucs.content_list_id = cl.id AND ucs.user_id = $1
        WHERE cl.language_id = $2
          AND cl.list_type IN ('grammar', 'vocabulary')
        ORDER BY cl.list_type ASC, cl.level ASC NULLS LAST
        """,
        user_id,
        language_id,
    )
    return [
        {
            "id": str(r["id"]),
            "list_type": r["list_type"],
            "level": r["level"],
            "title": r["title"],
            "subscribed": r["subscribed"],
            "total": int(r["total"]),
            "learned": int(r["learned"]),
        }
        for r in rows
    ]


async def update_card_srs(
    conn: asyncpg.Connection, card_id: str, srs_update: dict
) -> None:
    """Update a card's FSRS fields after review."""
    await conn.execute(
        """
        UPDATE user_cards
        SET stability = $1,
            difficulty = $2,
            state = $3,
            interval = $4,
            repetitions = $5,
            streak = $6,
            lapses = $7,
            next_review = $8,
            last_review = now()
        WHERE id = $9
        """,
        srs_update["stability"],
        srs_update["difficulty"],
        srs_update["state"],
        srs_update["interval"],
        srs_update["repetitions"],
        srs_update["streak"],
        srs_update["lapses"],
        srs_update["next_review"],
        card_id,
    )


async def get_card_details_bulk(
    conn: asyncpg.Connection, card_ids: list[str]
) -> dict[str, dict]:
    """Return {user_card_id: detail} for many cards in a few bulk queries.

    Same payload shape as get_card_detail, but batched: the learn endpoint
    builds a lesson per new card, and doing that one card at a time is an
    N+1 that hurts badly over a pooled (high-latency) database connection.
    Personal cards fall back to the single-card path (never produced by the
    learn flow).
    """
    if not card_ids:
        return {}
    cards = await conn.fetch(
        "SELECT id, card_type, card_id FROM user_cards WHERE id = ANY($1::uuid[])",
        card_ids,
    )
    vocab_ids = [c["card_id"] for c in cards if c["card_type"] == "vocabulary"]
    grammar_ids = [c["card_id"] for c in cards if c["card_type"] == "grammar"]

    vocab_by_id: dict = {}
    vocab_examples: dict = {}
    vocab_quiz: dict = {}
    if vocab_ids:
        for v in await conn.fetch(
            """
            SELECT v.id, v.word, v.reading, v.part_of_speech, v.usage_note,
                   v.morphology, v.alternatives, t.definition
            FROM vocabulary v
            LEFT JOIN translations t
                   ON v.id = t.vocabulary_id AND t.locale = 'en'
            WHERE v.id = ANY($1::uuid[])
            """,
            vocab_ids,
        ):
            vocab_by_id[v["id"]] = v
        for e in await conn.fetch(
            """
            SELECT vocabulary_id, sentence, translation, gloss, transliteration
            FROM example_sentences
            WHERE vocabulary_id = ANY($1::uuid[])
            ORDER BY difficulty_rank ASC NULLS LAST
            """,
            vocab_ids,
        ):
            bucket = vocab_examples.setdefault(e["vocabulary_id"], [])
            if len(bucket) < 5:
                bucket.append(
                    {"sentence": e["sentence"], "translation": e["translation"], "hint": None}
                )
            # First-check quiz: the first sentence where the word clozes.
            v = vocab_by_id.get(e["vocabulary_id"])
            if v is not None and e["vocabulary_id"] not in vocab_quiz:
                cloze = make_cloze(e["sentence"], v["word"])
                if cloze:
                    vocab_quiz[e["vocabulary_id"]] = {
                        "sentence": cloze,
                        "translation": e["translation"],
                        "gloss": e["gloss"],
                        "transliteration": e["transliteration"],
                        "hint": v["definition"],
                    }

    grammar_by_id: dict = {}
    grammar_examples: dict = {}
    grammar_quiz: dict = {}
    if grammar_ids:
        for gp in await conn.fetch(
            """
            SELECT id, title, function_note, explanation, culture_note,
                   reference_links, reviewed
            FROM grammar_points WHERE id = ANY($1::uuid[])
            """,
            grammar_ids,
        ):
            grammar_by_id[gp["id"]] = gp
        for e in await conn.fetch(
            """
            SELECT grammar_point_id, sentence, answer, translation, hint,
                   gloss, transliteration
            FROM drill_sentences
            WHERE grammar_point_id = ANY($1::uuid[])
            ORDER BY display_order ASC
            """,
            grammar_ids,
        ):
            bucket = grammar_examples.setdefault(e["grammar_point_id"], [])
            if len(bucket) < 5:
                bucket.append({
                    # Lesson views show the COMPLETED sentence, not the blank
                    "sentence": e["sentence"].replace(ANSWER_MARKER, e["answer"]),
                    "translation": e["translation"],
                    "hint": e["hint"],
                })
            # First-check quiz: the point's first drill, blank kept.
            if e["grammar_point_id"] not in grammar_quiz:
                grammar_quiz[e["grammar_point_id"]] = {
                    "sentence": e["sentence"],
                    "answer": e["answer"],
                    "translation": e["translation"],
                    "gloss": e["gloss"],
                    "transliteration": e["transliteration"],
                    "hint": e["hint"],
                }

    details: dict[str, dict] = {}
    for c in cards:
        if c["card_type"] == "vocabulary":
            v = vocab_by_id.get(c["card_id"])
            if v is None:
                continue
            # The learner must answer this before the card enters reviews
            # (teach → check → queue). Falls back to the type-the-word
            # prompt when no example sentence clozes.
            quiz = vocab_quiz.get(c["card_id"]) or {
                "sentence": v["definition"] or v["word"],
                "translation": None,
                "gloss": None,
                "transliteration": None,
                "hint": v["definition"],
            }
            details[str(c["id"])] = {
                "card_type": "vocabulary",
                "title": v["word"],
                "reading": v["reading"],
                "part_of_speech": v["part_of_speech"],
                "definition": v["definition"],
                "usage_note": v["usage_note"],
                "morphology": v["morphology"],
                "explanation": None,
                "culture_note": None,
                "reviewed": True,
                "references": [],
                "examples": vocab_examples.get(c["card_id"], []),
                "quiz": {
                    **quiz,
                    "answer": v["word"],
                    "morphology": v["morphology"],
                    "alternatives": v["alternatives"] or [],
                },
            }
        elif c["card_type"] == "grammar":
            gp = grammar_by_id.get(c["card_id"])
            if gp is None:
                continue
            references = []
            if gp["reference_links"]:
                raw = gp["reference_links"]
                if isinstance(raw, str):
                    try:
                        raw = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        raw = []
                references = clean_references(raw)
            quiz = grammar_quiz.get(c["card_id"])
            details[str(c["id"])] = {
                "card_type": "grammar",
                "title": gp["title"],
                "function_note": gp["function_note"],
                "reading": None,
                "part_of_speech": None,
                "definition": None,
                "usage_note": None,
                "morphology": None,
                "explanation": gp["explanation"],
                "culture_note": gp["culture_note"],
                "reviewed": gp["reviewed"],
                "references": references,
                "examples": grammar_examples.get(c["card_id"], []),
                "quiz": (
                    {**quiz, "morphology": None, "alternatives": []}
                    if quiz else None
                ),
            }
        else:
            detail = await get_card_detail(conn, str(c["id"]))
            if detail:
                details[str(c["id"])] = detail
    return details


async def get_card_detail(
    conn: asyncpg.Connection, card_id: str
) -> dict | None:
    """Return the rich "review this card" content for the optional panel.

    The shape differs by card type (vocab vs grammar sets review differently):
      - vocabulary: word, definition, usage note, morphology, and graded
        example sentences (word seen in context).
      - grammar: title, broad explanation, culture note, and the point's
        drill sentences with translations.

    *card_id* is a user_cards id; RLS on the connection scopes it to the
    authenticated user, so a card the user doesn't own returns None.
    """
    card = await conn.fetchrow(
        """
        SELECT card_type, card_id, language_id, repetitions, streak, lapses,
               next_review, created_at, stability, state
        FROM user_cards WHERE id = $1
        """,
        card_id,
    )
    if card is None:
        return None

    # The learner's history with this card: named stage + accuracy from the
    # actual review log (RLS scopes the log to this user).
    log = await conn.fetchrow(
        """
        SELECT count(*) AS n,
               count(*) FILTER (WHERE answer_result IN ('correct', 'correct_sloppy')) AS ok,
               min(created_at) AS first_studied
        FROM review_log WHERE card_id = $1
        """,
        card_id,
    )
    first = (log["first_studied"] if log else None) or card["created_at"]
    progress = {
        "stage": stage_for(card["card_type"], card["state"], card["stability"]),
        "first_studied": first.isoformat() if first else None,
        "times_studied": int(log["n"]) if log else 0,
        "accuracy": (int(log["ok"]) / int(log["n"])) if log and log["n"] else None,
        "streak": card["streak"],
        "misses": card["lapses"],
        "next_review": card["next_review"].isoformat() if card["next_review"] else None,
    }

    if card["card_type"] == "personal":
        cc = await conn.fetchrow(
            """
            SELECT cc.answer, cc.translation, cc.sentence, n.title AS note_title
            FROM user_cloze_cards cc
            LEFT JOIN user_notes n ON cc.note_id = n.id
            WHERE cc.id = $1
            """,
            card["card_id"],
        )
        # Show the word back in its original sentence — the "seen in context"
        # payoff of learning from your own text.
        examples = []
        if cc and cc["sentence"]:
            full = cc["sentence"].replace(ANSWER_MARKER, cc["answer"] or "")
            examples = [{
                "sentence": full,
                "translation": cc["translation"],
                "hint": None,
            }]
        usage = (
            f"From your note: {cc['note_title']}"
            if cc and cc["note_title"] else None
        )
        return {
            "card_type": "personal",
            "title": cc["answer"] if cc else None,
            "reading": None,
            "part_of_speech": None,
            "definition": cc["translation"] if cc else None,
            "usage_note": usage,
            "morphology": None,
            "explanation": None,
            "culture_note": None,
            "reviewed": True,
            "references": [],
            "examples": examples,
            "progress": progress,
        }

    if card["card_type"] == "vocabulary":
        v = await conn.fetchrow(
            """
            SELECT v.word, v.reading, v.part_of_speech, v.usage_note, v.morphology,
                   t.definition
            FROM vocabulary v
            LEFT JOIN translations t
                   ON v.id = t.vocabulary_id AND t.locale = 'en'
            WHERE v.id = $1
            """,
            card["card_id"],
        )
        examples = await conn.fetch(
            """
            SELECT sentence, translation
            FROM example_sentences
            WHERE vocabulary_id = $1
            ORDER BY difficulty_rank ASC NULLS LAST
            LIMIT 5
            """,
            card["card_id"],
        )
        # The learner's OWN sentences with this word (from notes → cloze
        # cards), shown under Examples — RLS scopes them to this user.
        own = []
        if v and v["word"]:
            own = await conn.fetch(
                """
                SELECT sentence, answer, translation
                FROM user_cloze_cards
                WHERE language_id = $1 AND lower(answer) = lower($2)
                ORDER BY created_at ASC
                LIMIT 5
                """,
                card["language_id"],
                v["word"],
            )
        return {
            "card_type": "vocabulary",
            "title": v["word"] if v else None,
            "reading": v["reading"] if v else None,
            "part_of_speech": v["part_of_speech"] if v else None,
            "definition": v["definition"] if v else None,
            "usage_note": v["usage_note"] if v else None,
            "morphology": v["morphology"] if v else None,
            "explanation": None,
            "culture_note": None,
            "reviewed": True,  # vocabulary has no review gate
            "references": [],
            "examples": [
                {"sentence": e["sentence"], "translation": e["translation"], "hint": None}
                for e in examples
            ],
            "your_sentences": [
                {
                    "sentence": o["sentence"].replace(ANSWER_MARKER, o["answer"] or ""),
                    "translation": o["translation"],
                }
                for o in own
            ],
            "progress": progress,
        }

    # grammar
    gp = await conn.fetchrow(
        """
        SELECT title, function_note, explanation, culture_note,
               explanation_source, reference_links, related, reviewed
        FROM grammar_points WHERE id = $1
        """,
        card["card_id"],
    )
    related = (
        await resolve_related(conn, card["language_id"], gp["related"]) if gp else []
    )
    read_refs = await get_read_ref_keys(conn, str(card["card_id"]))
    examples = await conn.fetch(
        """
        SELECT sentence, answer, translation, hint
        FROM drill_sentences
        WHERE grammar_point_id = $1
        ORDER BY display_order ASC
        LIMIT 5
        """,
        card["card_id"],
    )
    references = []
    if gp and gp["reference_links"]:
        raw = gp["reference_links"]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = []
        references = clean_references(raw)
    return {
        "card_type": "grammar",
        "point_id": str(card["card_id"]),
        "title": gp["title"] if gp else None,
        "function_note": gp["function_note"] if gp else None,
        "reading": None,
        "part_of_speech": None,
        "definition": None,
        "usage_note": None,
        "morphology": None,
        "explanation": gp["explanation"] if gp else None,
        "culture_note": gp["culture_note"] if gp else None,
        "reviewed": gp["reviewed"] if gp else True,
        "references": references,
        "read_refs": read_refs,
        "related": related,
        "progress": progress,
        "examples": [
            {
                # Detail/lesson views show the COMPLETED sentence, not the blank
                "sentence": e["sentence"].replace(ANSWER_MARKER, e["answer"]),
                "translation": e["translation"],
                "hint": e["hint"],
            }
            for e in examples
        ],
    }
