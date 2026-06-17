"""Personal notes + cloze cards repository — all RLS-scoped to the owner."""

from __future__ import annotations

import asyncpg


async def create_note(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    title: str | None,
    content: str,
) -> str:
    """Store a learner's pasted text. Returns the note id."""
    return str(await conn.fetchval(
        "INSERT INTO user_notes (user_id, language_id, title, content) "
        "VALUES ($1, $2, $3, $4) RETURNING id",
        user_id, language_id, title, content,
    ))


async def list_notes(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> list[dict]:
    """List a learner's notes for a language (newest first)."""
    rows = await conn.fetch(
        "SELECT id, title, content, created_at FROM user_notes "
        "WHERE user_id = $1 AND language_id = $2 ORDER BY created_at DESC LIMIT 100",
        user_id, language_id,
    )
    return [
        {
            "id": str(r["id"]),
            "title": r["title"],
            "content": r["content"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def known_vocab(
    conn: asyncpg.Connection, language_id: str, words: list[str]
) -> dict[str, str | None]:
    """Return {word: definition|None} for the given words that exist in the
    global vocabulary for this language (lowercased match)."""
    if not words:
        return {}
    rows = await conn.fetch(
        """
        SELECT lower(v.word) AS word, t.definition
        FROM vocabulary v
        LEFT JOIN translations t
               ON v.id = t.vocabulary_id AND t.locale = 'en'
        WHERE v.language_id = $1 AND lower(v.word) = ANY($2::text[])
        """,
        language_id, [w.lower() for w in words],
    )
    return {r["word"]: r["definition"] for r in rows}


async def create_personal_card(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    sentence: str,
    answer: str,
    translation: str | None,
    note_id: str | None,
) -> str:
    """Create a cloze card from the learner's text and queue it for review."""
    cloze_id = await conn.fetchval(
        "INSERT INTO user_cloze_cards (user_id, language_id, sentence, answer, translation, note_id) "
        "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
        user_id, language_id, sentence, answer, translation or None, note_id,
    )
    user_card_id = await conn.fetchval(
        """
        INSERT INTO user_cards
            (user_id, language_id, card_type, card_id,
             ease_factor, interval, repetitions, streak, lapses, next_review)
        VALUES ($1, $2, 'personal', $3, 2.5, 0, 0, 0, 0, now())
        RETURNING id
        """,
        user_id, language_id, cloze_id,
    )
    return str(user_card_id)
