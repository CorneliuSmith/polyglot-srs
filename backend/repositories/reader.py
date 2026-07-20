"""Reader repository (WP21) — learner model, readings shelf, gap log."""

from __future__ import annotations

import json

import asyncpg

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


async def get_learner_model(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> dict:
    """What this learner KNOWS, for level-locking a reading.

    - known_words: their strongest vocabulary (stability-ranked sample)
    - learned_structures: titles of grammar points they hold cards for
    - level: highest CEFR level where they've started a meaningful number
      of items (fallback A1)
    """
    word_rows = await conn.fetch(
        """
        SELECT v.word
        FROM user_cards uc
        JOIN vocabulary v ON uc.card_id = v.id AND uc.card_type = 'vocabulary'
        WHERE uc.user_id = $1 AND uc.language_id = $2
          AND uc.is_suspended = false
        ORDER BY COALESCE(uc.stability, 0) DESC
        LIMIT 40
        """,
        user_id, language_id,
    )
    structure_rows = await conn.fetch(
        """
        SELECT gp.title
        FROM user_cards uc
        JOIN grammar_points gp ON uc.card_id = gp.id AND uc.card_type = 'grammar'
        WHERE uc.user_id = $1 AND uc.language_id = $2
          AND uc.is_suspended = false
        ORDER BY gp.display_order
        """,
        user_id, language_id,
    )
    level_rows = await conn.fetch(
        """
        SELECT v.level, COUNT(*) AS n
        FROM user_cards uc
        JOIN vocabulary v ON uc.card_id = v.id AND uc.card_type = 'vocabulary'
        WHERE uc.user_id = $1 AND uc.language_id = $2 AND v.level IS NOT NULL
        GROUP BY v.level
        """,
        user_id, language_id,
    )
    level = "A1"
    counts = {r["level"]: int(r["n"]) for r in level_rows}
    for lvl in CEFR_ORDER:
        if counts.get(lvl, 0) >= 5:
            level = lvl
    return {
        "known_words": [r["word"] for r in word_rows],
        "learned_structures": [r["title"] for r in structure_rows],
        "level": level,
        "known_count": sum(counts.values()),
    }


async def save_reading(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    topic: str,
    reading: dict,
    level: str,
) -> str:
    row = await conn.fetchrow(
        """
        INSERT INTO readings
            (user_id, language_id, topic, title, level, content, new_words,
             structures, source)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8::jsonb,
                'generated')
        RETURNING id
        """,
        user_id, language_id, topic,
        reading["title"], level,
        json.dumps({"sentences": reading["sentences"]}, ensure_ascii=False),
        json.dumps(reading["new_words"], ensure_ascii=False),
        json.dumps(reading["structures"], ensure_ascii=False),
    )
    return str(row["id"])


async def list_readings(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, topic, title, level, created_at,
               jsonb_array_length(new_words) AS new_word_count
        FROM readings
        WHERE user_id = $1 AND language_id = $2
        ORDER BY created_at DESC
        LIMIT 50
        """,
        user_id, language_id,
    )
    return [
        {
            "id": str(r["id"]),
            "topic": r["topic"],
            "title": r["title"],
            "level": r["level"],
            "created_at": r["created_at"].isoformat(),
            "new_word_count": int(r["new_word_count"]),
        }
        for r in rows
    ]


async def get_reading(
    conn: asyncpg.Connection, user_id: str, reading_id: str
) -> dict | None:
    r = await conn.fetchrow(
        """
        SELECT id, topic, title, level, content, new_words, structures, created_at
        FROM readings
        WHERE id = $1 AND user_id = $2
        """,
        reading_id, user_id,
    )
    if r is None:
        return None
    content = r["content"]
    new_words = r["new_words"]
    structures = r["structures"]
    return {
        "id": str(r["id"]),
        "topic": r["topic"],
        "title": r["title"],
        "level": r["level"],
        "sentences": (json.loads(content) if isinstance(content, str) else content)["sentences"],
        "new_words": json.loads(new_words) if isinstance(new_words, str) else new_words,
        "structures": json.loads(structures) if isinstance(structures, str) else structures,
        "created_at": r["created_at"].isoformat(),
    }


async def log_grammar_gaps(
    conn: asyncpg.Connection,
    language_id: str,
    structures: list[str],
    example: str | None,
) -> int:
    """Record structures the grammar path doesn't cover (owner request):
    the app collects its own curriculum TODOs from real usage.

    Matching is deliberately forgiving — exact-insensitive OR containment
    either way — so 'present tense' matches 'Present tense of -ar verbs'.
    Returns how many NEW gap rows this call created or bumped.
    """
    title_rows = await conn.fetch(
        "SELECT lower(title) AS t FROM grammar_points WHERE language_id = $1",
        language_id,
    )
    titles = [r["t"] for r in title_rows]

    def covered(structure: str) -> bool:
        s = structure.lower().strip()
        if len(s) < 3:
            return True  # junk, not a structure name
        return any(s == t or s in t or t in s for t in titles)

    logged = 0
    for structure in structures:
        s = structure.strip()
        if not s or covered(s):
            continue
        await conn.execute(
            """
            INSERT INTO grammar_gap_log (language_id, structure, example)
            VALUES ($1, $2, $3)
            ON CONFLICT (language_id, structure) DO UPDATE SET
                count = grammar_gap_log.count + 1,
                updated_at = now()
            """,
            language_id, s[:200], example,
        )
        logged += 1
    return logged
