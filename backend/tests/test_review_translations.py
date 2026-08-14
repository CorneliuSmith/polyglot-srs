"""The English is the pivot, and nothing was checking it.

`generate_sentence_translations` produces every locale FROM the English,
and the checker then grades that locale against that same English. So the
English is ground truth in every direction and is never itself examined —
a loose rendering caps every language derived from it, while each
downstream locale still looks correct *relative to its source*.

These cover the pass that finally reads in the other direction, and the
two consequences of changing an English that other rows were built on.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.services import translate
from backend.services.seeder import review_translations as rt


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, text):
        self.content = [_Block(text)]


def _verdicts(*rows) -> str:
    import json
    return json.dumps({"verdicts": list(rows)})


class _Settings:
    tutor_dev_mock = False
    anthropic_api_key = "sk-test"


async def _review(items, reply):
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=_Resp(reply))
    with patch.object(translate, "_client", return_value=client), \
         patch.object(translate, "get_settings", return_value=_Settings()):
        return await translate.review_source_translations("Hindi", items)


ITEM = [{"i": 0, "sentence": "और क्या है?", "translation": "What else is there?"}]


class TestJudgingTheEnglish:
    @pytest.mark.asyncio
    async def test_a_good_english_is_left_alone(self):
        out = await _review(ITEM, _verdicts(
            {"i": 0, "verdict": "ok", "final": "", "note": ""}))
        assert out[0]["verdict"] == "ok"
        assert out[0]["translation"] == "What else is there?"

    @pytest.mark.asyncio
    async def test_a_correction_comes_back_to_be_applied(self):
        out = await _review(ITEM, _verdicts(
            {"i": 0, "verdict": "fixed", "final": "What else is new?",
             "note": "conversational, not existential"}))
        assert out[0]["verdict"] == "fixed"
        assert out[0]["translation"] == "What else is new?"
        assert out[0]["note"]

    @pytest.mark.asyncio
    async def test_a_fix_identical_to_the_original_is_just_ok(self):
        # Otherwise it spends a write, journals a no-op, and needlessly
        # marks every locale rendering of that sentence stale.
        out = await _review(ITEM, _verdicts(
            {"i": 0, "verdict": "fixed", "final": "What else is there?",
             "note": "reworded"}))
        assert out[0]["verdict"] == "ok"
        assert out[0]["note"] == ""

    @pytest.mark.asyncio
    async def test_an_unsure_pair_yields_nothing_to_apply(self):
        out = await _review(ITEM, _verdicts(
            {"i": 0, "verdict": "reject", "final": "", "note": "ambiguous"}))
        assert out[0]["verdict"] == "reject"
        assert out[0]["translation"] == ""

    @pytest.mark.asyncio
    async def test_a_missing_verdict_never_silently_keeps_the_old_text(self):
        # A short reply used to mean "unchanged", which is indistinguishable
        # from "checked and fine".
        out = await _review(ITEM, _verdicts())
        assert out[0]["verdict"] == "reject"
        assert out[0]["translation"] == ""

    @pytest.mark.asyncio
    async def test_an_unparseable_reply_changes_nothing(self):
        out = await _review(ITEM, "not json at all")
        assert out == []

    @pytest.mark.asyncio
    async def test_an_unknown_verdict_is_treated_as_unsure(self):
        out = await _review(ITEM, _verdicts(
            {"i": 0, "verdict": "excellent", "final": "whatever", "note": ""}))
        assert out[0]["verdict"] == "reject"

    @pytest.mark.asyncio
    async def test_the_prompt_carries_the_source_sentence_not_just_english(self):
        # The whole point of this pass: without the Hindi in the prompt the
        # model is grading English prose in a vacuum.
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_Resp(_verdicts()))
        with patch.object(translate, "_client", return_value=client), \
             patch.object(translate, "get_settings", return_value=_Settings()):
            await translate.review_source_translations("Hindi", ITEM)
        sent = client.messages.create.await_args.kwargs
        assert "और क्या है?" in sent["messages"][0]["content"]
        assert "Hindi" in sent["system"]


class TestDevMock:
    @pytest.mark.asyncio
    async def test_the_mock_path_never_invents_corrections(self):
        class Mocked:
            tutor_dev_mock = True

        with patch.object(translate, "get_settings", return_value=Mocked()):
            out = await translate.review_source_translations("Hindi", ITEM)
        assert out[0]["verdict"] == "ok"
        assert out[0]["translation"] == "What else is there?"


class _Conn:
    """Enough asyncpg surface for the pass, with the calls recorded."""

    def __init__(self, rows=()):
        self.rows = list(rows)
        self.executed: list[tuple[str, tuple]] = []

    async def fetch(self, sql, *args):
        self.last_fetch = sql
        return self.rows

    async def execute(self, sql, *args):
        self.executed.append((" ".join(sql.split()), args))
        return "DELETE 3" if sql.strip().startswith("DELETE") else "UPDATE 1"

    async def fetchrow(self, sql, *args):
        return {"id": "lang-1", "name": "Hindi"}

    async def close(self):
        pass


DRILL_ROW = {
    "id": "drill-1",
    "sentence": "मैं चाय {{answer}} हूँ।",
    "answer": "पीता",
    "translation": "I drink tea.",
}


class TestBothPivotsAreCovered:
    """The English lives in two tables and BOTH feed every other locale.

    The first version of this pass read example_sentences only, which left
    every grammar drill in every course unexamined.
    """

    def test_the_default_is_both_content_types(self):
        assert rt.SOURCES == ("example", "drill")
        assert set(rt._SOURCE) == set(rt.SOURCES)

    @pytest.mark.asyncio
    async def test_a_drill_reaches_the_judge_with_its_blank_filled(self):
        # The stored sentence is gapped; the translation renders the
        # COMPLETED sentence. Handing over "मैं चाय ___ हूँ।" would have the
        # judge call a correct English a mistranslation.
        out = await rt._drill_candidates(_Conn([DRILL_ROW]), "lang-1", 10)
        assert out[0]["display"] == "मैं चाय पीता हूँ।"
        assert out[0]["sentence"] == DRILL_ROW["sentence"]  # match key preserved

    @pytest.mark.asyncio
    async def test_an_example_sentence_is_its_own_display(self):
        row = {"id": "ex-1", "sentence": "और क्या है?",
               "translation": "What else is there?"}
        out = await rt._example_candidates(_Conn([row]), "lang-1", 10)
        assert out[0]["display"] == "और क्या है?"
        assert out[0]["answer"] is None

    @pytest.mark.asyncio
    async def test_a_drill_answer_that_is_missing_does_not_crash(self):
        row = {**DRILL_ROW, "answer": None}
        out = await rt._drill_candidates(_Conn([row]), "lang-1", 10)
        assert out[0]["display"] == "मैं चाय  हूँ।"


class TestStaleLocaleRows:
    @pytest.mark.asyncio
    async def test_fixing_a_drill_drops_the_whole_overlay_row(self):
        # drill_hint_translations holds the locale hint AND translation in
        # one row, and pending_drills gates on the row being ABSENT —
        # blanking a column would leave a row that never refills.
        conn = _Conn()
        n = await rt._stale_drill(conn, {"id": "drill-1"}, "lang-1")
        assert n == 3
        sql, args = conn.executed[0]
        assert sql.startswith("DELETE FROM drill_hint_translations")
        assert args == ("drill-1",)

    @pytest.mark.asyncio
    async def test_fixing_an_example_drops_by_sentence_not_by_id(self):
        # One sentence is an example for several words, each with its own
        # locale rows; keying on id would leave the others stale.
        conn = _Conn()
        await rt._stale_example(conn, {"id": "ex-1", "sentence": "और क्या है?"},
                                "lang-1")
        sql, args = conn.executed[0]
        assert "translation_locale <> 'en'" in sql
        assert args == ("lang-1", "और क्या है?")


class TestQueueingForAHuman:
    @pytest.mark.asyncio
    async def test_each_source_flags_its_own_table(self):
        conn = _Conn()
        await rt._queue_drill(conn, {"id": "drill-1"}, "ambiguous")
        await rt._queue_example(conn, {"id": "ex-1"}, "ambiguous")
        assert conn.executed[0][0].startswith("UPDATE drill_sentences")
        assert conn.executed[1][0].startswith("UPDATE example_sentences")

    @pytest.mark.asyncio
    async def test_a_pre_migration_table_loses_the_flag_not_the_run(self):
        class Old(_Conn):
            async def execute(self, sql, *args):
                raise __import__("asyncpg").UndefinedColumnError("no flagged")

        await rt._queue_drill(Old(), {"id": "drill-1"}, "ambiguous")  # no raise


class TestGrammarJsonMirror:
    """For drills the mirror is REQUIRED, not a courtesy.

    seed_grammar matches on (sentence, answer) and UPDATEs translation in
    place, so a database-only fix is reverted by the next seed.
    """

    def _write(self, tmp_path, indent=2):
        import json as _json
        path = tmp_path / "data" / "grammar" / "hi_grammar.json"
        path.parent.mkdir(parents=True)
        doc = {"language": "hi", "points": [{"title": "P1", "drills": [
            {"sentence": "मैं चाय {{answer}} हूँ।", "answer": "पीता",
             "translation": "I drink tea.", "hint": "to drink, masc."},
            {"sentence": "मैं चाय {{answer}} हूँ।", "answer": "पीती",
             "translation": "I drink tea.", "hint": "to drink, fem."},
        ]}]}
        path.write_text(_json.dumps(doc, ensure_ascii=False, indent=indent) + "\n",
                        encoding="utf-8")
        return path

    def test_the_match_key_is_sentence_and_answer_together(self, tmp_path,
                                                           monkeypatch):
        # Both drills share a sentence and a translation; only the one whose
        # ANSWER matches may change, or the masculine fix lands on the
        # feminine drill too.
        path = self._write(tmp_path)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        n = rt._rewrite_grammar_json(
            "hi", {("मैं चाय {{answer}} हूँ।", "पीता"): "I drink tea (m.)."})
        assert n == 1
        drills = json.loads(path.read_text(encoding="utf-8"))["points"][0]["drills"]
        assert drills[0]["translation"] == "I drink tea (m.)."
        assert drills[1]["translation"] == "I drink tea."
        assert drills[0]["hint"] == "to drink, masc."  # nothing else touched

    def test_the_file_keeps_its_own_indent(self, tmp_path, monkeypatch):
        # ha, ko, mi, pt and yo are indent=1. Re-dumping at 2 rewrites every
        # line of a 3000-line file and buries the one that changed.
        path = self._write(tmp_path, indent=1)
        monkeypatch.setattr(rt, "REPO", tmp_path)
        rt._rewrite_grammar_json(
            "hi", {("मैं चाय {{answer}} हूँ।", "पीता"): "I drink tea (m.)."})
        body = path.read_text(encoding="utf-8")
        assert '\n "language": "hi",' in body
        assert '\n  "language"' not in body

    def test_a_missing_file_warns_rather_than_raising(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rt, "REPO", tmp_path)
        assert rt._rewrite_grammar_json("zz", {("a", "b"): "c"}) == 0

    def test_detect_indent_falls_back_when_nothing_is_indented(self):
        assert rt._detect_indent('{"a":1}') == 2
        assert rt._detect_indent('{\n  "a": 1\n}') == 2
        assert rt._detect_indent('{\n "a": 1\n}') == 1


class TestJournalAndRestore:
    def test_the_journal_records_which_table_a_fix_came_from(self, tmp_path,
                                                             monkeypatch):
        monkeypatch.setattr(rt, "BACKUP_DIR", tmp_path)
        path = rt._journal("hi", "drill", [{
            "item": DRILL_ROW, "old": "I drink tea.", "new": "I drink tea (m.)."}])
        rec = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert rec["source"] == "drill"
        assert rec["language"] == "hi"
        assert rec["answer"] == "पीता"
        assert "drill" in path.name

    @pytest.mark.asyncio
    async def test_restore_sends_each_record_to_its_own_table(self, tmp_path,
                                                              monkeypatch):
        journal = tmp_path / "j.jsonl"
        journal.write_text(
            json.dumps({"id": "d1", "source": "drill", "language": "hi",
                        "sentence": "s", "answer": "a", "old": "was",
                        "new": "now"}) + "\n"
            + json.dumps({"id": "e1", "source": "example", "sentence": "s2",
                          "old": "was2", "new": "now2"}) + "\n",
            encoding="utf-8")
        conn = _Conn()
        monkeypatch.setattr(rt.asyncpg, "connect", AsyncMock(return_value=conn))
        monkeypatch.setattr(rt, "REPO", tmp_path)  # no grammar file: warn, no raise
        assert await rt.restore("postgres://x", journal) == 2
        assert conn.executed[0][0].startswith("UPDATE drill_sentences")
        assert conn.executed[1][0].startswith("UPDATE example_sentences")

    @pytest.mark.asyncio
    async def test_a_journal_from_before_drills_still_restores(self, tmp_path,
                                                              monkeypatch):
        # Runs already on disk have no `source` key; they are all examples.
        journal = tmp_path / "old.jsonl"
        journal.write_text(
            json.dumps({"id": "e1", "sentence": "s", "old": "was", "new": "now"})
            + "\n", encoding="utf-8")
        conn = _Conn()
        monkeypatch.setattr(rt.asyncpg, "connect", AsyncMock(return_value=conn))
        assert await rt.restore("postgres://x", journal) == 1
        assert conn.executed[0][0].startswith("UPDATE example_sentences")


class TestTheDrillPassEndToEnd:
    @pytest.mark.asyncio
    async def test_a_fix_lands_in_the_db_and_the_file_and_clears_the_overlay(
            self, tmp_path, monkeypatch):
        path = tmp_path / "data" / "grammar" / "hi_grammar.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"language": "hi", "points": [{"drills": [
            {"sentence": DRILL_ROW["sentence"], "answer": "पीता",
             "translation": "I drink tea."}]}]}, ensure_ascii=False, indent=2)
            + "\n", encoding="utf-8")
        monkeypatch.setattr(rt, "REPO", tmp_path)
        monkeypatch.setattr(rt, "BACKUP_DIR", tmp_path / "backups")
        monkeypatch.setattr(rt, "review_source_translations", AsyncMock(
            return_value=[{"i": 0, "verdict": "fixed",
                           "translation": "I drink tea (m.).", "note": "gender"}]))
        conn = _Conn([DRILL_ROW])
        counts = await rt.review_source(
            conn, "drill", "hi", {"id": "lang-1", "name": "Hindi"},
            limit=10, batch_size=20, dry_run=False, write_tsv=False)

        assert counts == {"checked": 1, "fixed": 1, "queued": 0,
                          "stale_dropped": 3}
        assert conn.executed[0][0].startswith("UPDATE drill_sentences")
        assert conn.executed[1][0].startswith(
            "DELETE FROM drill_hint_translations")
        drills = json.loads(path.read_text(encoding="utf-8"))["points"][0]["drills"]
        assert drills[0]["translation"] == "I drink tea (m.)."

    @pytest.mark.asyncio
    async def test_a_dry_run_touches_neither_the_db_nor_the_file(
            self, tmp_path, monkeypatch):
        path = tmp_path / "data" / "grammar" / "hi_grammar.json"
        path.parent.mkdir(parents=True)
        original = json.dumps({"language": "hi", "points": [{"drills": [
            {"sentence": DRILL_ROW["sentence"], "answer": "पीता",
             "translation": "I drink tea."}]}]}, ensure_ascii=False, indent=2) + "\n"
        path.write_text(original, encoding="utf-8")
        monkeypatch.setattr(rt, "REPO", tmp_path)
        monkeypatch.setattr(rt, "review_source_translations", AsyncMock(
            return_value=[{"i": 0, "verdict": "reject", "translation": "",
                           "note": "ambiguous"}]))
        conn = _Conn([DRILL_ROW])
        counts = await rt.review_source(
            conn, "drill", "hi", {"id": "lang-1", "name": "Hindi"},
            limit=10, batch_size=20, dry_run=True, write_tsv=False)

        assert counts["checked"] == 1 and counts["queued"] == 1
        assert conn.executed == []  # not even the flag
        assert path.read_text(encoding="utf-8") == original

    @pytest.mark.asyncio
    async def test_every_language_runs_every_source(self, monkeypatch):
        seen = []

        async def _spy(conn, source, code, lang, **kw):
            seen.append((code, source))
            return rt._zero()

        monkeypatch.setattr(rt, "review_source", _spy)
        monkeypatch.setattr(rt.asyncpg, "connect", AsyncMock(return_value=_Conn()))
        out = await rt.review_language(
            "postgres://x", "hi", limit=10, batch_size=20, dry_run=True,
            write_tsv=False)
        assert seen == [("hi", "example"), ("hi", "drill")]
        assert set(out["by_source"]) == {"example", "drill"}


class TestTsvMirror:
    def test_only_the_matching_sentence_row_is_rewritten(self, tmp_path, monkeypatch):
        tsv = tmp_path / "data" / "hi_sentences.tsv"
        tsv.parent.mkdir(parents=True)
        tsv.write_text(
            "word\tsentence\ttranslation\trank\n"
            "है\tऔर क्या है?\tWhat else is there?\t14\n"
            "क्या\tऔर क्या है?\tWhat else is there?\t14\n"
            "कुछ\tकुछ और?\tAnything more?\t20\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(rt, "REPO", tmp_path)
        n = rt._rewrite_tsv("hi", {"और क्या है?": "What else is new?"})
        # BOTH rows carrying that sentence — it is an example for several
        # words, and leaving one behind would put two Englishes on one
        # sentence.
        assert n == 2
        body = tsv.read_text(encoding="utf-8")
        assert body.count("What else is new?") == 2
        assert "Anything more?" in body  # untouched
        assert body.startswith("word\tsentence\ttranslation\trank\n")

    def test_a_missing_file_is_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rt, "REPO", tmp_path)
        assert rt._rewrite_tsv("zz", {"x": "y"}) == 0
