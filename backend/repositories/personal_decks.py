"""Personal decks — learner-named folders for personal cloze cards.

Decks group the cards minted from the Tutor and the Reader, and (owner
request, superseding the original organization-only rule) cards the learner
writes or deletes themselves. All queries run under RLS, so user scoping is
the connection's context.
"""
from __future__ import annotations

import re

import asyncpg

# The 20260811 migration (personal_decks + the personal_deck_id column) may
# not have landed. Every read here degrades to "no decks, everything
# unfiled" rather than 500ing — an unguarded read took the whole section
# down, so the learner saw no personal cards at all and no reason why.
_MISSING = (asyncpg.exceptions.UndefinedTableError,
            asyncpg.exceptions.UndefinedColumnError)


async def list_decks(conn: asyncpg.Connection, language_id: str) -> list[dict]:
    try:
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
    except _MISSING:
        return []
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


async def get_or_create_deck(
    conn: asyncpg.Connection, user_id: str, language_id: str, name: str
) -> str:
    """The deck called *name* for this learner+language, created if absent.

    Cards minted from the Reader and the Tutor used to land with no deck at
    all. They were saved and scheduled correctly, but every screen that
    lists personal cards groups by deck, so the learner's own saved words
    were invisible — indistinguishable from the save having failed.

    Case-insensitive match so a learner who already made "From reading"
    keeps using it rather than accumulating near-duplicates. Renaming or
    deleting the deck later is fine: this only ever creates one when no
    deck by that name exists, and a deleted deck's cards fall back to
    unfiled rather than disappearing.
    """
    existing = await conn.fetchval(
        """
        SELECT id FROM personal_decks
        WHERE language_id = $1 AND lower(name) = lower($2)
        ORDER BY created_at ASC
        LIMIT 1
        """,
        language_id, name,
    )
    if existing:
        return str(existing)
    return await create_deck(conn, user_id, language_id, name)


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
    try:
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
    except _MISSING:
        # No filing column yet — still list the cards, all unfiled. Losing
        # the folders is a smaller loss than losing every card.
        rows = [
            {**dict(r), "personal_deck_id": None}
            for r in await conn.fetch(
                """
                SELECT cc.id, cc.answer, cc.sentence, cc.translation,
                       cc.created_at
                FROM user_cloze_cards cc
                WHERE cc.language_id = $1
                ORDER BY cc.created_at DESC
                """,
                language_id,
            )
        ]
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


async def untranslated_cards(
    conn: asyncpg.Connection, language_id: str, locale: str,
) -> list[dict]:
    """The learner's personal cards with no rendering in *locale* yet.

    Private content, so this is never swept by the background loop — it
    exists so the learner can be told how many of their own cards would be
    translated, and what it costs, BEFORE anything is spent.
    """
    if not locale or locale == "en":
        return []
    try:
        rows = await conn.fetch(
            """
            SELECT cc.id, cc.sentence, cc.answer, cc.translation
            FROM user_cloze_cards cc
            WHERE cc.language_id = $1
              AND cc.translation IS NOT NULL AND cc.translation <> ''
              AND NOT EXISTS (
                SELECT 1 FROM user_cloze_card_translations t
                 WHERE t.cloze_id = cc.id AND t.locale = $2)
            ORDER BY cc.created_at DESC
            """,
            language_id, locale,
        )
    except _MISSING:
        return []
    return [dict(r) for r in rows]


async def store_card_translations(
    conn: asyncpg.Connection, rows: list[tuple[str, str]], locale: str,
) -> int:
    """Persist (cloze_id, translation) pairs. Idempotent per (card, locale)
    so a retry after a partial failure never double-charges the learner for
    work already paid for."""
    stored = 0
    for cloze_id, translation in rows:
        if not translation:
            continue
        await conn.execute(
            """INSERT INTO user_cloze_card_translations
                   (cloze_id, locale, translation)
               VALUES ($1, $2, $3)
               ON CONFLICT (cloze_id, locale) DO NOTHING""",
            cloze_id, locale, translation,
        )
        stored += 1
    return stored


def build_cloze(sentence: str, answer: str) -> str | None:
    """Put the {{answer}} marker into a learner-written sentence.

    Review renders the sentence with the marker blanked, so a card without
    one would present the answer in plain sight. Matches whole words only
    and case-insensitively — "Büyük" at the start of a sentence is still the
    answer "büyük". Returns None when the word isn't in the sentence, which
    the router turns into a message rather than storing a broken card.
    """
    if "{{answer}}" in sentence:
        return sentence
    word = answer.strip()
    if not word:
        return None
    pattern = re.compile(rf"(?<!\w){re.escape(word)}(?!\w)", re.IGNORECASE)
    replaced, count = pattern.subn("{{answer}}", sentence, count=1)
    return replaced if count else None


async def delete_personal_card(conn: asyncpg.Connection, cloze_id: str) -> bool:
    """Remove a personal card and its scheduling row.

    user_cards.card_id is polymorphic — no foreign key to user_cloze_cards —
    so nothing cascades and the scheduling row has to go explicitly. Left
    behind it would keep surfacing in reviews as a card whose text no longer
    exists. RLS scopes both statements to the owner.
    """
    await conn.execute(
        "DELETE FROM user_cards WHERE card_type = 'personal' AND card_id = $1",
        cloze_id,
    )
    res = await conn.execute("DELETE FROM user_cloze_cards WHERE id = $1", cloze_id)
    return res.endswith(" 1")
