"""Content audit log + rollback: edits/approvals are logged with before/after,
and a logged edit can be reverted. Runs against real Postgres."""
from __future__ import annotations

from backend.repositories.audit import (
    list_entity_changes,
    list_recent_changes,
    revert_change,
)
from backend.repositories.contributor import (
    add_example_sentence,
    approve_explanation,
    confirm_vocab_level,
    edit_example_sentence,
)

from .conftest import requires_db

pytestmark = requires_db


async def _lang(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def _word(pool, lang: str, word: str, level=None) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, level) VALUES ($1, $2, $3) "
            "RETURNING id", lang, word, level,
        ))


async def test_example_edit_is_logged_and_revertible(pool):
    lang = await _lang(pool, "aud")
    vocab = await _word(pool, lang, "dog")
    editor = await _user(pool, "editor@aud")

    async with pool.privileged_connection() as conn:
        eid = await add_example_sentence(
            conn, vocab, lang, "The dog runs.", "A dog runs.", source="human"
        )
        # Edit it → an 'edited' entry with before/after.
        assert await edit_example_sentence(
            conn, eid, "The big dog runs fast.", "A big dog runs.", editor
        )
        hist = await list_entity_changes(conn, "example_sentence", eid)
        edited = next(h for h in hist if h["action"] == "edited")
        assert edited["actor_email"] == "editor@aud"
        assert edited["before"]["sentence"] == "The dog runs."
        assert edited["after"]["sentence"] == "The big dog runs fast."
        assert edited["revertible"] is True

        # Roll it back → the row is restored and a 'reverted' entry is appended.
        assert await revert_change(conn, edited["id"], editor) == "ok"
        row = await conn.fetchrow(
            "SELECT sentence, translation FROM example_sentences WHERE id = $1", eid
        )
        assert row["sentence"] == "The dog runs."
        assert row["translation"] == "A dog runs."
        hist2 = await list_entity_changes(conn, "example_sentence", eid)
        assert hist2[0]["action"] == "reverted"


async def test_level_confirm_logged_and_reverts(pool):
    lang = await _lang(pool, "aul")
    vocab = await _word(pool, lang, "kupanga", level="B1")
    reviewer = await _user(pool, "rev@aud")
    async with pool.privileged_connection() as conn:
        # Simulate an AI-provisional level, then a reviewer confirms A2.
        await conn.execute(
            "UPDATE vocabulary SET level_source = 'ai' WHERE id = $1", vocab
        )
        assert await confirm_vocab_level(conn, vocab, "A2", actor_id=reviewer)
        hist = await list_entity_changes(conn, "vocabulary", vocab)
        entry = hist[0]
        assert entry["action"] == "level_confirmed"
        assert entry["before"] == {"level": "B1", "level_source": "ai"}
        assert entry["after"] == {"level": "A2", "level_source": "curated"}
        # Revert restores the prior level + source.
        assert await revert_change(conn, entry["id"], reviewer) == "ok"
        row = await conn.fetchrow(
            "SELECT level, level_source FROM vocabulary WHERE id = $1", vocab
        )
        assert row["level"] == "B1" and row["level_source"] == "ai"


async def test_grammar_approval_logged(pool):
    lang = await _lang(pool, "aug")
    reviewer = await _user(pool, "ling@aud")
    async with pool.privileged_connection() as conn:
        pid = str(await conn.fetchval(
            "INSERT INTO grammar_points (language_id, title, level, reviewed) "
            "VALUES ($1, 'Present tense', 'A1', false) RETURNING id", lang,
        ))
        assert await approve_explanation(conn, pid, reviewer)
        hist = await list_entity_changes(conn, "grammar_point", pid)
        assert hist[0]["action"] == "approved"
        assert hist[0]["actor_email"] == "ling@aud"

        # Reverting an approval sends the point back to pending.
        assert await revert_change(conn, hist[0]["id"], reviewer) == "ok"
        reviewed = await conn.fetchval(
            "SELECT reviewed FROM grammar_points WHERE id = $1", pid
        )
        assert reviewed is False

        # The per-language audit feed sees all of it.
        feed = await list_recent_changes(conn, lang)
        assert any(c["action"] == "approved" for c in feed)
        assert any(c["action"] == "reverted" for c in feed)
