"""Multi-locale example sentences: English-course serving prefers the learner's
support locale and falls back to English; the generator adds locale rows."""
from __future__ import annotations

from backend.repositories.cards import get_card_detail
from backend.repositories.contributor import (
    add_example_sentence,
    sentences_needing_locale,
)

from .conftest import requires_db

pytestmark = requires_db


class _MockSettings:
    tutor_dev_mock = True
    anthropic_api_key = ""


async def _english(pool) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ('en', 'English', false) "
            "ON CONFLICT (code) DO UPDATE SET name = 'English' RETURNING id",
        ))


async def _word(pool, language_id: str, word: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word) VALUES ($1, $2) RETURNING id",
            language_id, word,
        ))


async def _card(pool, language_id: str, vocab_id: str) -> str:
    async with pool.privileged_connection() as conn:
        user = await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ('ml-card@t') RETURNING id"
        )
        return str(await conn.fetchval(
            "INSERT INTO user_cards (user_id, language_id, card_type, card_id) "
            "VALUES ($1, $2, 'vocabulary', $3) RETURNING id",
            user, language_id, vocab_id,
        ))


async def test_support_locale_prefers_then_falls_back(pool):
    lang = await _english(pool)
    vocab = await _word(pool, lang, "arrange")
    card = await _card(pool, lang, vocab)

    async with pool.privileged_connection() as conn:
        await add_example_sentence(
            conn, vocab, lang, "Please arrange the books.",
            "To put in order.", source="human",  # 'en' description
        )

        # Russian learner, no ru translation yet → falls back to the English one.
        detail = await get_card_detail(conn, card, support_locale="ru")
        assert detail["examples"][0]["translation"] == "To put in order."

        # Add the Russian translation of the same sentence → it's now preferred.
        await add_example_sentence(
            conn, vocab, lang, "Please arrange the books.",
            "Пожалуйста, расставьте книги.", source="human",
            translation_locale="ru",
        )
        detail = await get_card_detail(conn, card, support_locale="ru")
        assert detail["examples"][0]["translation"] == "Пожалуйста, расставьте книги."

        # An English learner with no support locale still sees English.
        detail_en = await get_card_detail(conn, card, support_locale=None)
        assert detail_en["examples"][0]["translation"] == "To put in order."


async def test_generate_locale_translations(pool, monkeypatch):
    from types import SimpleNamespace

    from backend.services.seeder import generate_content

    monkeypatch.setattr(
        "backend.services.translate.get_settings", lambda: _MockSettings()
    )
    lang = await _english(pool)
    vocab = await _word(pool, lang, "settle")
    async with pool.privileged_connection() as conn:
        for s in ("We settle the bill.", "They settle down."):
            await add_example_sentence(conn, vocab, lang, s, "desc", source="human")

        # Both English sentences lack a Russian translation.
        gap = await sentences_needing_locale(conn, lang, "ru", 50)
        assert len(gap) == 2

        lang_row = await conn.fetchrow(
            "SELECT id, code, name FROM languages WHERE id = $1", lang
        )
        args = SimpleNamespace(locale="ru", max=50, dry_run=False)
        await generate_content._run_translations(conn, lang_row, args)

        # The mock rejects one and stores one ru row (source='ai', reviewed=false).
        ru = await conn.fetch(
            "SELECT translation, source, reviewed FROM example_sentences "
            "WHERE vocabulary_id = $1 AND translation_locale = 'ru'",
            vocab,
        )
    assert len(ru) == 1
    assert ru[0]["translation"].startswith("[Russian] ")
    assert ru[0]["source"] == "ai" and ru[0]["reviewed"] is False
