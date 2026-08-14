"""The English-on-trial pass, against the real schema.

The unit tests mock the connection, so they prove the control flow and
prove nothing about the SQL. A mistyped column in a candidate query is
exactly the kind of thing that passes every mock and fails the first time
it is pointed at a database — and this pass is only ever run against a
live one.

What is load-bearing here:

  * Both pivots are read by queries that actually execute. The pass first
    shipped reading example_sentences only; drills carry their own English
    and feed drill_hint_translations, so half the cards in the product
    were unexamined.
  * Correcting an English deletes the locale rows derived from it. For a
    drill that means the WHOLE drill_hint_translations row, because
    auto_translate refills only rows that are absent.
  * An uncertain pair is flagged in its own table, not guessed at.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import asyncpg
import pytest

from backend.services.seeder import review_translations as rt

from .conftest import INTEGRATION_DSN, requires_db

pytestmark = requires_db

HINDI = "मैं चाय {{answer}} हूँ।"


async def _fixture(conn) -> dict:
    """One language with one drill and one example sentence, both English."""
    code = f"zz{uuid.uuid4().hex[:4]}"
    lang_id = await conn.fetchval(
        "INSERT INTO languages (code, name) VALUES ($1, $2) RETURNING id",
        code, "Hindi",
    )
    point_id = await conn.fetchval(
        """INSERT INTO grammar_points (language_id, title, level, display_order)
           VALUES ($1, 'Present habitual', 'A1', 1) RETURNING id""",
        lang_id,
    )
    drill_id = await conn.fetchval(
        """INSERT INTO drill_sentences
               (grammar_point_id, sentence, answer, translation, hint, display_order)
           VALUES ($1, $2, 'पीता', 'I drink tea.', 'to drink, masc.', 1)
           RETURNING id""",
        point_id, HINDI,
    )
    await conn.execute(
        """INSERT INTO drill_hint_translations (drill_id, locale, hint, translation)
           VALUES ($1, 'es', 'beber, masc.', 'Bebo té.')""",
        drill_id,
    )
    vocab_id = await conn.fetchval(
        """INSERT INTO vocabulary (language_id, word, level)
           VALUES ($1, 'चाय', 'A1') RETURNING id""",
        lang_id,
    )
    for locale, text in (("en", "What else is there?"), ("es", "¿Qué más hay?")):
        await conn.execute(
            """INSERT INTO example_sentences
                   (language_id, vocabulary_id, sentence, translation,
                    translation_locale)
               VALUES ($1, $2, 'और क्या है?', $3, $4)""",
            lang_id, vocab_id, text, locale,
        )
    return {"code": code, "lang_id": lang_id, "drill_id": drill_id}


@pytest.fixture
async def conn(schema):
    c = await asyncpg.connect(INTEGRATION_DSN)
    try:
        yield c
    finally:
        await c.close()


def _fix(new: str):
    return AsyncMock(return_value=[
        {"i": 0, "verdict": "fixed", "translation": new, "note": "register"}])


class TestTheQueriesRunAgainstTheRealSchema:
    async def test_a_drill_candidate_comes_back_with_its_blank_filled(self, conn):
        fx = await _fixture(conn)
        items = await rt._drill_candidates(conn, fx["lang_id"], 10)
        assert len(items) == 1
        assert items[0]["display"] == "मैं चाय पीता हूँ।"
        assert items[0]["translation"] == "I drink tea."

    async def test_an_example_candidate_is_the_english_row_only(self, conn):
        fx = await _fixture(conn)
        items = await rt._example_candidates(conn, fx["lang_id"], 10)
        # The Spanish row is a RENDERING of the English, not a pivot; judging
        # it here would put the wrong text on trial.
        assert [i["translation"] for i in items] == ["What else is there?"]

    async def test_a_flagged_row_is_left_for_the_human_who_flagged_it(self, conn):
        fx = await _fixture(conn)
        await conn.execute("UPDATE drill_sentences SET flagged = true WHERE id = $1",
                           fx["drill_id"])
        assert await rt._drill_candidates(conn, fx["lang_id"], 10) == []


class TestFixingADrillEnglish:
    async def test_the_fix_lands_and_the_locale_overlay_is_dropped(
            self, conn, monkeypatch, tmp_path):
        fx = await _fixture(conn)
        monkeypatch.setattr(rt, "REPO", tmp_path)  # no grammar file for a fake code
        monkeypatch.setattr(rt, "BACKUP_DIR", tmp_path / "backups")
        monkeypatch.setattr(rt, "review_source_translations",
                            _fix("I drink tea (masc. speaker)."))

        counts = await rt.review_source(
            conn, "drill", fx["code"], {"id": fx["lang_id"], "name": "Hindi"},
            limit=10, batch_size=20, dry_run=False, write_tsv=False)

        assert counts["fixed"] == 1
        assert counts["stale_dropped"] == 1
        assert await conn.fetchval(
            "SELECT translation FROM drill_sentences WHERE id = $1", fx["drill_id"]
        ) == "I drink tea (masc. speaker)."
        # The whole row, hint included — pending_drills gates on ABSENCE, so a
        # row with a blanked column would never be refilled.
        assert await conn.fetchval(
            "SELECT count(*) FROM drill_hint_translations WHERE drill_id = $1",
            fx["drill_id"]) == 0

    async def test_an_uncertain_drill_is_flagged_in_its_own_table(
            self, conn, monkeypatch, tmp_path):
        fx = await _fixture(conn)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        monkeypatch.setattr(rt, "review_source_translations", AsyncMock(
            return_value=[{"i": 0, "verdict": "reject", "translation": "",
                           "note": "the English translates a different sentence"}]))

        counts = await rt.review_source(
            conn, "drill", fx["code"], {"id": fx["lang_id"], "name": "Hindi"},
            limit=10, batch_size=20, dry_run=False, write_tsv=False)

        assert counts["queued"] == 1 and counts["fixed"] == 0
        row = await conn.fetchrow(
            "SELECT flagged, flag_reason, translation FROM drill_sentences "
            "WHERE id = $1", fx["drill_id"])
        assert row["flagged"] is True
        assert "different sentence" in row["flag_reason"]
        assert row["translation"] == "I drink tea."  # never guessed at


class TestFixingAnExampleEnglish:
    async def test_the_derived_locale_rows_go_and_the_english_stays(
            self, conn, monkeypatch, tmp_path):
        fx = await _fixture(conn)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        monkeypatch.setattr(rt, "BACKUP_DIR", tmp_path / "backups")
        monkeypatch.setattr(rt, "review_source_translations",
                            _fix("What else is new?"))

        counts = await rt.review_source(
            conn, "example", fx["code"], {"id": fx["lang_id"], "name": "Hindi"},
            limit=10, batch_size=20, dry_run=False, write_tsv=False)

        assert counts["fixed"] == 1
        assert counts["stale_dropped"] == 1  # the Spanish rendering
        rows = await conn.fetch(
            "SELECT translation_locale, translation FROM example_sentences "
            "WHERE language_id = $1", fx["lang_id"])
        assert [(r["translation_locale"], r["translation"]) for r in rows] == [
            ("en", "What else is new?")]


class TestEveryLanguageAndBothPivots:
    async def test_one_call_covers_both_content_types(self, conn, monkeypatch,
                                                      tmp_path):
        fx = await _fixture(conn)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        monkeypatch.setattr(rt, "BACKUP_DIR", tmp_path / "backups")
        monkeypatch.setattr(rt, "review_source_translations",
                            _fix("A better English."))

        out = await rt.review_language(
            INTEGRATION_DSN, fx["code"], limit=10, batch_size=20,
            dry_run=False, write_tsv=False)

        assert set(out["by_source"]) == {"example", "drill"}
        assert out["by_source"]["example"]["checked"] == 1
        assert out["by_source"]["drill"]["checked"] == 1
        assert out["fixed"] == 2

    async def test_the_all_sweep_enumerates_courses_and_skips_english(self, conn):
        # --all reads this list; if it ever returned one language the sweep
        # would look like it ran and cover nothing.
        codes = [r["code"] for r in await conn.fetch(
            "SELECT code FROM languages WHERE code <> 'en' ORDER BY code")]
        assert len(codes) > 20
        assert "en" not in codes
        assert {"hi", "es", "ar", "ca"} <= set(codes)


class TestOfflineJudging:
    """Judging in a Claude Code session instead of paying the API per row.

    The model is already in the room, so the module's job shrinks to moving
    rows out to a file and verdicts back in. The write path is shared with
    the API path, so what matters here is the file contract and the one
    hazard the API path does not have: time passes between export and apply.
    """

    async def test_export_writes_what_a_judge_needs_and_calls_nothing(
            self, conn, tmp_path):
        fx = await _fixture(conn)
        out = tmp_path / "export.jsonl"
        n = await rt.export_file(INTEGRATION_DSN, [fx["code"]], limit=10,
                                 sources=rt.SOURCES, path=out)
        assert n == 2
        rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
        by_source = {r["source"]: r for r in rows}
        assert set(by_source) == {"drill", "example"}
        # The drill's blank is filled — the judge compares English against a
        # whole sentence, not a gapped one.
        assert by_source["drill"]["sentence"] == "मैं चाय पीता हूँ।"
        assert by_source["drill"]["english"] == "I drink tea."
        # Blank fields for the judge, present so the file is fillable in place.
        assert by_source["drill"]["verdict"] == ""
        assert by_source["drill"]["fixed"] == ""

    async def _export(self, conn, tmp_path):
        fx = await _fixture(conn)
        out = tmp_path / "export.jsonl"
        await rt.export_file(INTEGRATION_DSN, [fx["code"]], limit=10,
                             sources=rt.SOURCES, path=out)
        rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
        return fx, out, rows

    def _write(self, path, rows):
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False)
                                  for r in rows) + "\n", encoding="utf-8")

    async def test_a_filled_export_applies_exactly_like_the_api_path(
            self, conn, tmp_path, monkeypatch):
        fx, out, rows = await self._export(conn, tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        monkeypatch.setattr(rt, "BACKUP_DIR", tmp_path / "backups")
        for r in rows:
            r["verdict"], r["fixed"], r["note"] = "fixed", "A better English.", "x"
        self._write(out, rows)

        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=False,
                                     write_tsv=False)

        assert counts["fixed"] == 2
        assert counts["stale_dropped"] == 2   # the es example row + the overlay
        assert await conn.fetchval(
            "SELECT translation FROM drill_sentences WHERE id = $1",
            fx["drill_id"]) == "A better English."
        assert await conn.fetchval(
            "SELECT count(*) FROM drill_hint_translations WHERE drill_id = $1",
            fx["drill_id"]) == 0
        # And it is undoable, exactly like the API path.
        journal = next((tmp_path / "backups").glob("*drill*.jsonl"))
        await rt.restore(INTEGRATION_DSN, journal)
        assert await conn.fetchval(
            "SELECT translation FROM drill_sentences WHERE id = $1",
            fx["drill_id"]) == "I drink tea."

    async def test_a_row_edited_since_the_export_is_never_overwritten(
            self, conn, tmp_path, monkeypatch):
        # The hazard the API path does not have: a human fixes the row while
        # the session is judging. Applying blind would silently undo them.
        fx, out, rows = await self._export(conn, tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        monkeypatch.setattr(rt, "BACKUP_DIR", tmp_path / "backups")
        await conn.execute(
            "UPDATE drill_sentences SET translation = $2 WHERE id = $1",
            fx["drill_id"], "A human got here first.")
        for r in rows:
            r["verdict"], r["fixed"] = "fixed", "The machine's version."
        self._write(out, rows)

        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=False,
                                     write_tsv=False)

        assert counts["stale"] == 1
        assert counts["fixed"] == 1           # the untouched example still lands
        assert await conn.fetchval(
            "SELECT translation FROM drill_sentences WHERE id = $1",
            fx["drill_id"]) == "A human got here first."

    async def test_an_unjudged_or_half_finished_file_writes_nothing(
            self, conn, tmp_path, monkeypatch):
        fx, out, rows = await self._export(conn, tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        # Straight from --export: every verdict still blank.
        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=False,
                                     write_tsv=False)
        assert counts["unjudged"] == 2
        assert counts["fixed"] == 0 and counts["queued"] == 0
        assert counts["checked"] == 0     # nothing was judged, so nothing checked
        assert await conn.fetchval(
            "SELECT translation FROM drill_sentences WHERE id = $1",
            fx["drill_id"]) == "I drink tea."

    async def test_judged_and_left_alone_is_not_reported_as_unjudged(
            self, conn, tmp_path, monkeypatch):
        # A careful pass that concludes "this English is fine" must not read
        # like a file nobody opened — the operator uses these counters to
        # decide whether the run actually happened.
        fx, out, rows = await self._export(conn, tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        for r in rows:
            r["verdict"] = "ok"
        self._write(out, rows)

        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=False,
                                     write_tsv=False)

        assert counts["checked"] == 2
        assert counts["unchanged"] == 2
        assert counts["unjudged"] == 0
        assert counts["fixed"] == 0

    async def test_a_fix_identical_to_the_original_counts_as_left_alone(
            self, conn, tmp_path, monkeypatch):
        fx, out, rows = await self._export(conn, tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        for r in rows:
            r["verdict"], r["fixed"] = "fixed", r["english"]
        self._write(out, rows)

        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=False,
                                     write_tsv=False)

        assert counts["unchanged"] == 2 and counts["unjudged"] == 0
        assert counts["fixed"] == 0

    async def test_reject_flags_for_a_human_and_ok_changes_nothing(
            self, conn, tmp_path, monkeypatch):
        fx, out, rows = await self._export(conn, tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        for r in rows:
            if r["source"] == "drill":
                r["verdict"], r["note"] = "reject", "translates a different sentence"
            else:
                r["verdict"] = "ok"
        self._write(out, rows)

        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=False,
                                     write_tsv=False)

        assert counts["queued"] == 1 and counts["fixed"] == 0
        row = await conn.fetchrow(
            "SELECT flagged, flag_reason FROM drill_sentences WHERE id = $1",
            fx["drill_id"])
        assert row["flagged"] is True
        assert "different sentence" in row["flag_reason"]

    async def test_a_dry_run_apply_writes_nothing(self, conn, tmp_path,
                                                  monkeypatch):
        fx, out, rows = await self._export(conn, tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        for r in rows:
            r["verdict"], r["fixed"] = "fixed", "Different English."
        self._write(out, rows)

        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=True,
                                     write_tsv=False)

        assert counts["fixed"] == 0
        assert await conn.fetchval(
            "SELECT translation FROM drill_sentences WHERE id = $1",
            fx["drill_id"]) == "I drink tea."

    async def test_an_unknown_id_is_reported_rather_than_crashing(
            self, conn, tmp_path):
        out = tmp_path / "bad.jsonl"
        out.write_text("\n".join([
            json.dumps({"id": str(uuid.uuid4()), "source": "drill",
                        "verdict": "fixed", "english": "x", "fixed": "y"}),
            json.dumps({"id": "not-a-uuid", "source": "drill",
                        "verdict": "fixed", "english": "x", "fixed": "y"}),
        ]) + "\n", encoding="utf-8")
        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=False,
                                     write_tsv=False)
        assert counts["unknown"] == 2 and counts["fixed"] == 0

    async def test_the_source_is_recovered_when_the_file_omits_it(
            self, conn, tmp_path, monkeypatch):
        # A hand-written or agent-rewritten file may drop the field; the id
        # is enough to find the row.
        fx, out, rows = await self._export(conn, tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        monkeypatch.setattr(rt, "BACKUP_DIR", tmp_path / "backups")
        drill = next(r for r in rows if r["source"] == "drill")
        drill.pop("source")
        drill["verdict"], drill["fixed"] = "fixed", "Recovered anyway."
        self._write(out, [drill])

        counts = await rt.apply_file(INTEGRATION_DSN, out, dry_run=False,
                                     write_tsv=False)

        assert counts["fixed"] == 1
        assert await conn.fetchval(
            "SELECT translation FROM drill_sentences WHERE id = $1",
            fx["drill_id"]) == "Recovered anyway."
