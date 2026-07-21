"""Personal decks — learner-named folders for personal cloze cards.

Organization only (owner decision): decks group the cards minted from the
Tutor and the Reader; learners cannot author cards directly yet. All
queries run under RLS, so user scoping is the connection's context.
"""
from __future__ import annotations

import asyncpg


async def list_decks(conn: asyncpg.Connection, language_id: str) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT pd.id, pd.name, pd.created_at,
               count(cc.id) AS card_count
        FROM personal_decks pd
        LEFT JOIN user_cloze_cards cc ON cc.personal_deck_id = pd.id
        WHERE pd.language_id = $1
        GROUP BY pd.id
        ORDER BY pd.created_at ASC
        """,
        language_id,
    )
    return [
        {"id": str(r["id"]), "name": r["name"], "card_count": r["card_count"]}
        for r in rows
    ]


async def create_deck(
    conn: asyncpg.Connection, user_id: str, language_id: str, name: str
) -> str:
    return str(await conn.fetchval(
        """
        INSERT INTO personal_decks (user_id, language_id, name)
        VALUES ($1, $2, $3) RETURNING id
        """,
        user_id, language_id, name,
    ))


async def rename_deck(conn: asyncpg.Connection, deck_id: str, name: str) -> bool:
    res = await conn.execute(
        "UPDATE personal_decks SET name = $2 WHERE id = $1", deck_id, name
    )
    return res.endswith(" 1")


async def delete_deck(conn: asyncpg.Connection, deck_id: str) -> bool:
    """Cards fall back to unfiled (FK is ON DELETE SET NULL)."""
    res = await conn.execute("DELETE FROM personal_decks WHERE id = $1", deck_id)
    return res.endswith(" 1")


async def list_personal_cards(
    conn: asyncpg.Connection, language_id: str
) -> list[dict]:
    """Every personal card for the language, with its filing state."""
    rows = await conn.fetch(
        """
        SELECT cc.id, cc.answer, cc.sentence, cc.translation,
               cc.personal_deck_id, cc.created_at
        FROM user_cloze_cards cc
        WHERE cc.language_id = $1
        ORDER BY cc.created_at DESC
        """,
        language_id,
    )
    return [
        {
            "id": str(r["id"]),
            "answer": r["answer"],
            "sentence": r["sentence"],
            "translation": r["translation"],
            "deck_id": str(r["personal_deck_id"]) if r["personal_deck_id"] else None,
        }
        for r in rows
    ]


async def file_card(
    conn: asyncpg.Connection, card_id: str, deck_id: str | None
) -> bool:
    """Move a card into a deck (or out of every deck with None).

    The subquery pins the deck to the same owner+language under RLS —
    a card can never be filed into someone else's deck.
    """
    res = await conn.execute(
        """
        UPDATE user_cloze_cards cc
        SET personal_deck_id = $2
        WHERE cc.id = $1
          AND ($2::uuid IS NULL OR EXISTS (
              SELECT 1 FROM personal_decks pd
              WHERE pd.id = $2 AND pd.language_id = cc.language_id
          ))
        """,
        card_id, deck_id,
    )
    return res.endswith(" 1")
