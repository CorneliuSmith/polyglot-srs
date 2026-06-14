"""User cards repository — RLS-protected queries."""

from __future__ import annotations

import json

import asyncpg

from backend.services.references import clean_references


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
    vocab_rows = await conn.fetch(
        """
        SELECT
            uc.id,
            uc.user_id,
            uc.language_id,
            uc.card_type,
            uc.card_id,
            -- type-the-word mode: sentence = definition, answer = word
            COALESCE(t.definition, v.word) AS sentence,
            v.word                          AS correct_answer,
            NULL::text                      AS hint,
            NULL::text                      AS translation,
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
    grammar_rows = await conn.fetch(
        """
        SELECT * FROM (
            SELECT DISTINCT ON (uc.id)
                uc.id,
                uc.user_id,
                uc.language_id,
                uc.card_type,
                uc.card_id,
                -- fill-in-the-blank mode: sentence contains {{answer}} marker;
                -- fall back to the grammar point title if no drill sentence exists
                COALESCE(ds.sentence, gp.title) AS sentence,
                -- the answer is the form that fills the {{answer}} blank;
                -- fall back to the title for points without authored drills
                COALESCE(ds.answer, gp.title)   AS correct_answer,
                ds.hint                         AS hint,
                ds.translation                  AS translation,
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
            JOIN grammar_points gp  ON uc.card_id = gp.id
            JOIN languages l        ON uc.language_id = l.id
            LEFT JOIN drill_sentences ds ON gp.id = ds.grammar_point_id
            WHERE uc.language_id = $1
              AND uc.card_type = 'grammar'
              AND uc.next_review <= now()
              AND uc.is_suspended = false
            ORDER BY uc.id, ds.display_order ASC
        ) g
        ORDER BY g.next_review ASC
        LIMIT $2
        """,
        language_id,
        limit,
    )

    # Merge and sort by next_review
    combined = [dict(r) for r in vocab_rows] + [dict(r) for r in grammar_rows]
    combined.sort(key=lambda r: r["next_review"])
    return combined[:limit]


async def add_learn_batch(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
) -> dict:
    """Add a batch of new vocabulary cards to user_cards from subscribed lists.

    Selects vocabulary the user has not yet learned, ordered by frequency_rank
    ASC (most frequent first), limited to batch_size.  Cards are inserted with
    default SRS values and next_review = now() so they are immediately due.

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
          AND v.id NOT IN (
              SELECT card_id FROM user_cards
              WHERE user_id = $1 AND card_type = 'vocabulary'
          )
        ORDER BY v.frequency_rank ASC NULLS LAST
        LIMIT $3
        """,
        user_id,
        language_id,
        batch_size,
    )

    if not vocab_rows:
        return {"added": 0, "items": []}

    vocab_ids = [r["id"] for r in vocab_rows]

    # Insert new user_cards for each selected vocabulary item
    inserted_ids = []
    for vocab_id in vocab_ids:
        row = await conn.fetchrow(
            """
            INSERT INTO user_cards
                (user_id, language_id, card_type, card_id,
                 ease_factor, interval, repetitions, streak, lapses,
                 next_review)
            VALUES
                ($1, $2, 'vocabulary', $3,
                 2.5, 0, 0, 0, 0,
                 now())
            RETURNING id
            """,
            user_id,
            language_id,
            vocab_id,
        )
        inserted_ids.append(str(row["id"]))

    return {"added": len(inserted_ids), "items": inserted_ids}


async def add_grammar_learn_batch(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
) -> dict:
    """Add a batch of new grammar cards from the user's subscribed grammar lists.

    Mirrors add_learn_batch but for grammar_points: selects points the user
    hasn't started, ordered by display_order, from grammar content lists the
    user is subscribed to (matched by level), and inserts grammar user_cards
    due immediately.
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
          AND gp.id NOT IN (
              SELECT card_id FROM user_cards
              WHERE user_id = $1 AND card_type = 'grammar'
          )
        ORDER BY gp.display_order ASC
        LIMIT $3
        """,
        user_id,
        language_id,
        batch_size,
    )
    if not rows:
        return {"added": 0, "items": []}

    inserted_ids = []
    for r in rows:
        row = await conn.fetchrow(
            """
            INSERT INTO user_cards
                (user_id, language_id, card_type, card_id,
                 ease_factor, interval, repetitions, streak, lapses, next_review)
            VALUES
                ($1, $2, 'grammar', $3, 2.5, 0, 0, 0, 0, now())
            RETURNING id
            """,
            user_id,
            language_id,
            r["id"],
        )
        inserted_ids.append(str(row["id"]))

    return {"added": len(inserted_ids), "items": inserted_ids}


async def update_card_srs(
    conn: asyncpg.Connection, card_id: str, srs_update: dict
) -> None:
    """Update a card's SRS fields after review."""
    await conn.execute(
        """
        UPDATE user_cards
        SET ease_factor = $1,
            interval = $2,
            repetitions = $3,
            streak = $4,
            lapses = $5,
            next_review = $6,
            last_review = now()
        WHERE id = $7
        """,
        srs_update["ease_factor"],
        srs_update["interval"],
        srs_update["repetitions"],
        srs_update["streak"],
        srs_update["lapses"],
        srs_update["next_review"],
        card_id,
    )


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
        "SELECT card_type, card_id FROM user_cards WHERE id = $1", card_id
    )
    if card is None:
        return None

    if card["card_type"] == "vocabulary":
        v = await conn.fetchrow(
            """
            SELECT v.word, v.part_of_speech, v.usage_note, v.morphology,
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
        return {
            "card_type": "vocabulary",
            "title": v["word"] if v else None,
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
        }

    # grammar
    gp = await conn.fetchrow(
        """
        SELECT title, explanation, culture_note, explanation_source,
               reference_links, reviewed
        FROM grammar_points WHERE id = $1
        """,
        card["card_id"],
    )
    examples = await conn.fetch(
        """
        SELECT sentence, translation, hint
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
        "title": gp["title"] if gp else None,
        "part_of_speech": None,
        "definition": None,
        "usage_note": None,
        "morphology": None,
        "explanation": gp["explanation"] if gp else None,
        "culture_note": gp["culture_note"] if gp else None,
        "reviewed": gp["reviewed"] if gp else True,
        "references": references,
        "examples": [
            {"sentence": e["sentence"], "translation": e["translation"], "hint": e["hint"]}
            for e in examples
        ],
    }
