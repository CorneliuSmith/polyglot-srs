"""A Russian learner of English was served Spanish, French and Romanian.

The screenshot: the card for "we" (ЗНАЧЕНИЕ мы — correct), and under
В КОНТЕКСТЕ five English sentences glossed "Somos el 99%.",
"À nous.", "¿Hemos terminado?", "Nous avons réussi !", "Lo logramos." — and
on the drill, a Romanian line labelled "ПЕРЕВОД (НА АНГЛИЙСКОМ — ЕЩЁ НЕ
ПЕРЕВЕДЕНО)".

Nothing was wrong with the query. `get_due_cards` filters
`translation_locale IN ($3,'en')` and prefers $3, which is right. The rows
were LYING: data/en_sentences.tsv carries a translation_locale column whose
202,772 rows span 13 locales and include not one 'en', and the seeder never
read the column — so every Spanish, French and Romanian translation was
stored as English and served to everybody.

The conflict key made it worse. It is (vocabulary_id, sentence,
translation_locale); with all 13 locales collapsed onto 'en', the first row
for a sentence won and the other twelve were silently dropped. That is why
one sentence kept Spanish and the next kept French — whichever the file
listed first.
"""
from __future__ import annotations

import uuid

import asyncpg
import pytest

from backend.services.seeder import seed_sentences

from .conftest import INTEGRATION_DSN, requires_db

pytestmark = requires_db

# One English sentence with the SAME shape as the real file: several
# locales, none of them 'en'.
TSV = (
    "word\tsentence\ttranslation\tdifficulty_rank\ttranslation_locale\n"
    "we\tWe are the 99%.\tSomos el 99%.\t3\tes\n"
    "we\tWe are the 99%.\tМы — те самые 99%.\t3\tru\n"
    "we\tWe are the 99%.\tNous sommes les 99 %.\t3\tfr\n"
    "we\tTo us!\tÀ nous.\t4\tfr\n"
    "we\tTo us!\tЗа нас!\t4\tru\n"
)

# A course whose file has no locale column at all — those really are English.
PLAIN_TSV = (
    "word\tsentence\ttranslation\tdifficulty_rank\n"
    "casa\tLa casa es grande.\tThe house is big.\t2\n"
)


@pytest.fixture
async def conn(schema):
    c = await asyncpg.connect(INTEGRATION_DSN)
    try:
        yield c
    finally:
        await c.close()


async def _course(conn, word: str) -> dict:
    code = f"zz{uuid.uuid4().hex[:4]}"
    lang_id = await conn.fetchval(
        "INSERT INTO languages (code, name) VALUES ($1, 'Test') RETURNING id", code)
    await conn.execute(
        "INSERT INTO vocabulary (language_id, word, level) VALUES ($1, $2, 'A1')",
        lang_id, word)
    return {"code": code, "lang_id": lang_id}


def _write(tmp_path, monkeypatch, code, body, plain=False):
    data = tmp_path / "data"
    (data / "sentences").mkdir(parents=True, exist_ok=True)
    (data / f"{code}_sentences.tsv").write_text(body, encoding="utf-8")
    monkeypatch.setattr(seed_sentences, "DATA_DIR", data)
    monkeypatch.setattr(seed_sentences, "SENTENCES_DIR", data / "sentences")


class TestTheLocaleIsCarried:
    async def test_each_translation_is_filed_under_its_own_language(
            self, conn, tmp_path, monkeypatch):
        fx = await _course(conn, "we")
        _write(tmp_path, monkeypatch, fx["code"], TSV)

        await seed_sentences.seed(INTEGRATION_DSN, fx["code"])

        rows = await conn.fetch(
            "SELECT sentence, translation, translation_locale FROM "
            "example_sentences WHERE language_id = $1 ORDER BY sentence, "
            "translation_locale", fx["lang_id"])
        got = {(r["sentence"], r["translation_locale"]): r["translation"]
               for r in rows}
        assert got[("We are the 99%.", "es")] == "Somos el 99%."
        assert got[("We are the 99%.", "ru")] == "Мы — те самые 99%."
        assert got[("We are the 99%.", "fr")] == "Nous sommes les 99 %."
        # Nothing pretending to be English.
        assert not any(r["translation_locale"] == "en" for r in rows)

    async def test_every_locale_survives_instead_of_one_winning(
            self, conn, tmp_path, monkeypatch):
        # The old bug: 13 locales collapsed onto 'en', so the conflict key
        # (vocabulary_id, sentence, translation_locale) kept the first and
        # dropped the rest — one sentence ended up Spanish, the next French.
        fx = await _course(conn, "we")
        _write(tmp_path, monkeypatch, fx["code"], TSV)

        await seed_sentences.seed(INTEGRATION_DSN, fx["code"])

        n = await conn.fetchval(
            "SELECT count(*) FROM example_sentences WHERE language_id = $1 "
            "AND sentence = 'We are the 99%.'", fx["lang_id"])
        assert n == 3

    async def test_a_file_without_the_column_still_means_english(
            self, conn, tmp_path, monkeypatch):
        # Every course except English omits it, and those translations really
        # are English — the default must not change under them.
        fx = await _course(conn, "casa")
        _write(tmp_path, monkeypatch, fx["code"], PLAIN_TSV)

        await seed_sentences.seed(INTEGRATION_DSN, fx["code"])

        assert await conn.fetchval(
            "SELECT translation_locale FROM example_sentences "
            "WHERE language_id = $1", fx["lang_id"]) == "en"


class TestRepairingWhatIsAlreadyWrong:
    async def test_reseeding_alone_leaves_the_bad_row_and_adds_a_duplicate(
            self, conn, tmp_path, monkeypatch):
        # Worse than "the fix doesn't apply". The corrected insert carries
        # locale 'es', which does NOT conflict with the stale 'en' row, so
        # the Spanish text ends up stored TWICE — once correctly labelled and
        # once still masquerading as English, which the card query happily
        # serves on its 'en' arm. Hence a repair pass, run first.
        fx = await _course(conn, "we")
        vocab_id = await conn.fetchval(
            "SELECT id FROM vocabulary WHERE language_id = $1", fx["lang_id"])
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'We are the 99%.', 'Somos el 99%.', 'en')""",
            fx["lang_id"], vocab_id)
        _write(tmp_path, monkeypatch, fx["code"], TSV)

        await seed_sentences.seed(INTEGRATION_DSN, fx["code"])

        locales = sorted(r["translation_locale"] for r in await conn.fetch(
            "SELECT translation_locale FROM example_sentences WHERE "
            "language_id = $1 AND translation = 'Somos el 99%.'",
            fx["lang_id"]))
        assert locales == ["en", "es"]

    async def test_repair_relabels_it_from_the_file(
            self, conn, tmp_path, monkeypatch):
        fx = await _course(conn, "we")
        vocab_id = await conn.fetchval(
            "SELECT id FROM vocabulary WHERE language_id = $1", fx["lang_id"])
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'We are the 99%.', 'Somos el 99%.', 'en')""",
            fx["lang_id"], vocab_id)
        _write(tmp_path, monkeypatch, fx["code"], TSV)

        await seed_sentences.repair_locales(INTEGRATION_DSN, fx["code"])

        assert await conn.fetchval(
            "SELECT translation_locale FROM example_sentences WHERE "
            "language_id = $1 AND translation = 'Somos el 99%.'",
            fx["lang_id"]) == "es"

    async def test_repair_then_reseed_restores_the_dropped_translations(
            self, conn, tmp_path, monkeypatch):
        # The documented order, end to end: repair the survivor's label,
        # then re-seed to insert the twelve-in-thirteen that were swallowed.
        fx = await _course(conn, "we")
        vocab_id = await conn.fetchval(
            "SELECT id FROM vocabulary WHERE language_id = $1", fx["lang_id"])
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'We are the 99%.', 'Somos el 99%.', 'en')""",
            fx["lang_id"], vocab_id)
        _write(tmp_path, monkeypatch, fx["code"], TSV)

        await seed_sentences.repair_locales(INTEGRATION_DSN, fx["code"])
        await seed_sentences.seed(INTEGRATION_DSN, fx["code"])

        locales = [r["translation_locale"] for r in await conn.fetch(
            "SELECT translation_locale FROM example_sentences WHERE "
            "language_id = $1 AND sentence = 'We are the 99%.' "
            "ORDER BY translation_locale", fx["lang_id"])]
        assert locales == ["es", "fr", "ru"]

    async def test_repair_never_touches_text_the_file_does_not_claim(
            self, conn, tmp_path, monkeypatch):
        # A reviewer's edit no longer matches the file, so it keeps its
        # label rather than being relabelled on a guess.
        fx = await _course(conn, "we")
        vocab_id = await conn.fetchval(
            "SELECT id FROM vocabulary WHERE language_id = $1", fx["lang_id"])
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'We are the 99%.', 'Edited by a human.', 'en')""",
            fx["lang_id"], vocab_id)
        _write(tmp_path, monkeypatch, fx["code"], TSV)

        await seed_sentences.repair_locales(INTEGRATION_DSN, fx["code"])

        assert await conn.fetchval(
            "SELECT translation_locale FROM example_sentences WHERE "
            "language_id = $1 AND translation = 'Edited by a human.'",
            fx["lang_id"]) == "en"
