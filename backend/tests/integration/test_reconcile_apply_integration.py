"""The batched apply against a real Postgres, not a fake connection.

`test_reconcile_apply_batched.py` proves the shape — one statement per
chunk, the right arrays, the counters. It cannot prove the SQL RUNS: its
connection records strings. That is exactly the gap quality rule 14 names
("a test that passes because something crashed is not a passing test"), and
this write path is the one the owner points at production.

So: a throwaway course, every kind of change the survey can produce, one
`apply`, then read the rows back.
"""
from __future__ import annotations

import json
import uuid

import asyncpg
import pytest

from backend.services.seeder import reconcile

from .conftest import INTEGRATION_DSN, requires_db

pytestmark = requires_db


@pytest.fixture
async def conn(schema):
    c = await asyncpg.connect(INTEGRATION_DSN)
    try:
        yield c
    finally:
        await c.close()


async def _course(conn, words: int = 3) -> dict:
    code = f"zz{uuid.uuid4().hex}"
    lang_id = await conn.fetchval(
        "INSERT INTO languages (code, name) VALUES ($1, 'Test') RETURNING id", code)
    rows = []
    for i in range(words):
        vid = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, part_of_speech, "
            "frequency_rank, morphology) VALUES ($1, $2, 'noun', $3, $4::jsonb) "
            "RETURNING id",
            lang_id, f"w{i}", i + 1,
            json.dumps({"lemma": f"w{i}",
                        "chips": [{"label": "Gender", "value": "m"},
                                  {"label": "Stem", "value": "w"}]}))
        await conn.execute(
            "INSERT INTO translations (vocabulary_id, locale, definition) "
            "VALUES ($1, 'en', $2)", vid, f"old definition {i}")
        rows.append({"id": vid, "word": f"w{i}"})
    return {"code": code, "lang_id": lang_id, "rows": rows}


class TestEveryKindActuallyWrites:
    async def test_the_whole_survey_shape_applies(self, conn):
        c = await _course(conn, words=3)
        a, b, d = c["rows"]
        sentence_id = await conn.fetchval(
            "INSERT INTO example_sentences (vocabulary_id, language_id, sentence, "
            "translation, translation_locale, reviewed) "
            "VALUES ($1, $2, 'a sentence', 't', 'en', true) RETURNING id",
            a["id"], c["lang_id"])
        no_translation = await conn.fetchval(
            "INSERT INTO vocabulary (language_id, word, part_of_speech) "
            "VALUES ($1, 'w9', 'noun') RETURNING id", c["lang_id"])

        counts = await reconcile.apply(conn, [{
            "code": c["code"],
            "gloss_changes": [{"id": a["id"], "word": "w0",
                               "old": "old definition 0", "new": "NEW GLOSS"}],
            "pos_changes": [{"id": b["id"], "word": "w1",
                             "old": "noun", "new": "det"}],
            "morphology_changes": [{"id": b["id"], "word": "w1", "old": "{}",
                                    "new": json.dumps({"lemma": "w1"})}],
            "missing_translation": [{"id": no_translation, "word": "w9",
                                     "new": "INSERTED"}],
            "sentence_layers": [{"id": sentence_id, "transliteration": "a sentence",
                                 "gloss": None}],
            "retire": [{"id": d["id"], "word": "w2"}],
            "unretire": [],
        }])

        assert counts == {"gloss": 1, "pos": 1, "morphology": 1,
                          "added_translation": 1, "sentence_layers": 1,
                          "retired": 1, "unretired": 0}
        assert await conn.fetchval(
            "SELECT definition FROM translations WHERE vocabulary_id = $1 "
            "AND locale = 'en'", a["id"]) == "NEW GLOSS"
        assert await conn.fetchval(
            "SELECT part_of_speech FROM vocabulary WHERE id = $1", b["id"]) == "det"
        assert json.loads(await conn.fetchval(
            "SELECT morphology::text FROM vocabulary WHERE id = $1",
            b["id"])) == {"lemma": "w1"}
        assert await conn.fetchval(
            "SELECT definition FROM translations WHERE vocabulary_id = $1",
            no_translation) == "INSERTED"
        assert await conn.fetchval(
            "SELECT transliteration FROM example_sentences WHERE id = $1",
            sentence_id) == "a sentence"
        assert await conn.fetchval(
            "SELECT retired_at IS NOT NULL FROM vocabulary WHERE id = $1", d["id"])

    async def test_a_chunk_boundary_writes_every_row(self, conn, monkeypatch):
        """The chunking is where an off-by-one hides: with a chunk of 2 and
        three rows, a wrong slice loses the third silently."""
        monkeypatch.setattr(reconcile, "APPLY_CHUNK", 2)
        c = await _course(conn, words=3)
        counts = await reconcile.apply(conn, [{
            "code": c["code"],
            "gloss_changes": [{"id": r["id"], "word": r["word"], "old": "x",
                               "new": f"gloss for {r['word']}"} for r in c["rows"]],
        }])
        assert counts["gloss"] == 3
        got = await conn.fetch(
            "SELECT v.word, t.definition FROM vocabulary v "
            "JOIN translations t ON t.vocabulary_id = v.id AND t.locale = 'en' "
            "WHERE v.language_id = $1 ORDER BY v.word", c["lang_id"])
        assert [r["definition"] for r in got] == [
            "gloss for w0", "gloss for w1", "gloss for w2"]

    async def test_an_unretire_clears_the_column(self, conn):
        c = await _course(conn, words=1)
        row = c["rows"][0]
        await conn.execute(
            "UPDATE vocabulary SET retired_at = now() WHERE id = $1", row["id"])
        counts = await reconcile.apply(conn, [{
            "code": c["code"], "unretire": [{"id": row["id"], "word": "w0"}]}])
        assert counts["unretired"] == 1
        assert await conn.fetchval(
            "SELECT retired_at FROM vocabulary WHERE id = $1", row["id"]) is None

    async def test_a_failure_rolls_the_whole_batch_back(self, conn):
        """One transaction: a bad row must not leave half the course written."""
        c = await _course(conn, words=2)
        good, bad = c["rows"]
        with pytest.raises(asyncpg.PostgresError):
            await reconcile.apply(conn, [{
                "code": c["code"],
                "gloss_changes": [{"id": good["id"], "word": "w0", "old": "x",
                                   "new": "WOULD BE WRITTEN"}],
                "pos_changes": [{"id": "not-a-uuid", "word": "w1",
                                 "old": None, "new": "det"}],
            }])
        assert await conn.fetchval(
            "SELECT definition FROM translations WHERE vocabulary_id = $1 "
            "AND locale = 'en'", good["id"]) == "old definition 0"
