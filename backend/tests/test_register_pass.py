"""The Arabic register pass: the judge's prompt, its schema, and its gates.

`docs/quality/ar-register-programme.md` §3 is the brief. Nothing here reaches
a model — the judge is a callable, so every test fakes it the way
`test_write.py` fakes the Anthropic client and `test_strokes.py` fakes a
connection. That is quality rule 15: a unit test must not be the place this
programme spends the API key, and an absent key is worse than a spend because
it silently exercises the exception branch instead of the behaviour.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.quality import register_pass as rp

REPO = Path(__file__).resolve().parents[2]


def _verdict(i: int, verdict: str = "msa", **kw) -> dict:
    base = {"i": i, "verdict": verdict, "variety": None, "evidence": [],
            "kind": None, "msa": None, "meaning_kept": True,
            "confidence": 0.9, "note": ""}
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_carries_the_same_register_pin_as_every_maker(self):
        """The judge and the makers must hold ONE standard. PR #473 put the
        pin in `register_line`; a judge with its own paraphrase would drift
        away from the prompt it is grading the output of."""
        from backend.services.quality_rules import register_line

        prompt = rp.system_prompt()
        assert register_line("ar").strip() in prompt
        assert "Modern Standard Arabic" in prompt

    def test_states_the_non_tells_and_the_b_preposition(self):
        """Programme §1.1: the false alarms have cost more than the misses.
        The judge is told the documented non-tells by name, and told that بـ
        before a noun is the preposition — the class that is every one of the
        1,212 prefix matches in the sentence bank."""
        prompt = rp.system_prompt()
        for non_tell in ("عمال", "بدون", "الموظفين", "كمان"):
            assert non_tell in prompt, f"{non_tell} missing from the non-tells"
        assert "بالنسبة" in prompt and "بنفسك" in prompt

    def test_forbids_filing_spelling_as_register(self):
        """§1.3: ى/ي, ة/ه, hamza seats and tashkeel are coached by the grader,
        not failed. A reviewer who 'fixes' one is making a spelling edit."""
        prompt = rp.system_prompt()
        assert "orthography_only" in prompt
        assert "ORTHOGRAPHY IS NOT REGISTER" in prompt

    def test_says_retire_rather_than_invent(self):
        """Owner decision, settled: a dialect-only meaning is retired, not
        replaced with MSA nobody says."""
        assert "inventing an" in rp.system_prompt().lower() or \
               "nobody says" in rp.system_prompt()


class TestSchema:
    def test_is_exactly_the_programme_fields(self):
        """§3.1 is a contract with the reviewers' TSV and with the local
        endpoint's guided decoding. A field added here silently is a field
        the fix file cannot carry."""
        assert set(rp.VERDICT_SCHEMA["properties"]) == {
            "i", "verdict", "variety", "evidence", "kind", "msa",
            "meaning_kept", "confidence", "note"}
        assert rp.VERDICT_SCHEMA["properties"]["verdict"]["enum"] == [
            "dialect", "classical", "msa", "unsure"]
        assert rp.VERDICT_SCHEMA["additionalProperties"] is False

    def test_the_fix_columns_are_the_programme_write_up_shape(self):
        assert rp.FIX_COLUMNS == [
            "id", "store", "field", "verdict", "variety", "evidence",
            "before", "after", "meaning_kept", "decision", "reviewer", "note"]


# ---------------------------------------------------------------------------
# Talking to the two providers
# ---------------------------------------------------------------------------


class TestProviders:
    async def test_anthropic_call_sends_the_schema_and_the_checker_tier(self):
        """Without --base-url the judge is Claude at the CHECKER tier —
        `sentence_checker`, one up from the maker. Passing the maker tier
        here would be self-certification (quality rule §6)."""
        class Block:
            text = json.dumps({"verdicts": [_verdict(0, "dialect",
                                                     evidence=["بكرة"])]})

        class FakeResponse:
            content = [Block()]
            usage = None

        class FakeSettings:
            anthropic_api_key = "sk-test"

        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("anthropic.AsyncAnthropic") as client_cls:
            create = AsyncMock(return_value=FakeResponse())
            client_cls.return_value.messages.create = create
            out = await rp._judge_anthropic([{"i": 0, "text": "x"}], None)

        kwargs = create.await_args.kwargs
        assert kwargs["output_config"]["format"]["schema"] is rp.BATCH_SCHEMA
        assert "Modern Standard Arabic" in kwargs["system"]
        from backend.services.models import resolve_model
        assert kwargs["model"] == resolve_model("sentence_checker", "ar")
        assert out[0]["verdict"] == "dialect"

    async def test_local_endpoint_uses_guided_json_on_chat_completions(self):
        """The local judge arrives as a base URL and nothing else. vLLM's
        guided decoding is what makes it hold the same schema as Claude."""
        captured = {}

        class FakeResponse:
            @staticmethod
            def raise_for_status():
                return None

            @staticmethod
            def json():
                return {"choices": [{"message": {"content": json.dumps(
                    {"verdicts": [_verdict(0)]})}}]}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, json=None):
                captured["url"] = url
                captured["payload"] = json
                return FakeResponse()

        with patch("httpx.AsyncClient", return_value=FakeClient()):
            out = await rp._judge_openai([{"i": 0, "text": "x"}],
                                         "http://gpu:8000/v1", "jais-2-8b")
        assert captured["url"] == "http://gpu:8000/v1/chat/completions"
        fmt = captured["payload"]["response_format"]
        assert fmt["type"] == "json_schema"
        assert fmt["json_schema"]["schema"] is rp.BATCH_SCHEMA
        assert captured["payload"]["temperature"] == 0
        assert out[0]["verdict"] == "msa"

    def test_a_local_endpoint_without_a_model_is_refused(self):
        with pytest.raises(SystemExit):
            rp.judge_for("http://gpu:8000/v1", None)

    def test_the_judge_is_named_without_leaking_the_endpoint(self):
        """The run is journaled with WHICH judge produced it; a URL with
        credentials in it must not be what lands in the file."""
        name = rp.judge_name("http://user:pw@gpu.internal:8000/v1", "jais-2-8b")
        assert name == "local:jais-2-8b@gpu.internal"
        assert "pw" not in name


class TestParsing:
    def test_an_empty_reply_is_an_error_not_a_clean_bill(self):
        """Quality rule 14: a pass that returns nothing because the call
        failed must not read as 'every row is MSA'."""
        with pytest.raises(ValueError):
            rp._parse("")
        with pytest.raises(ValueError):
            rp._parse("I'm sorry, I can't do that.")

    def test_json_wrapped_in_prose_is_still_read(self):
        out = rp._parse("Here you go:\n{\"verdicts\": [" +
                        json.dumps(_verdict(0)) + "]}\nHope that helps!")
        assert out[0]["i"] == 0

    async def test_a_failed_batch_becomes_unsure_not_silence(self):
        """A dropped row and an MSA row are indistinguishable in a count.
        Every item must come back."""
        async def broken(items):
            raise RuntimeError("endpoint down")

        items = [{"id": f"x{i}", "field": "sentence", "text": "t"}
                 for i in range(5)]
        out = await rp.run_items(items, broken, batch_size=2, concurrency=2)
        assert len(out) == 5
        assert {r["verdict"] for r in out} == {"unsure"}
        assert all("endpoint down" in r["note"] for r in out)

    async def test_an_item_the_judge_skipped_becomes_unsure(self):
        async def partial(items):
            return [_verdict(items[0]["i"])]          # answers only the first

        items = [{"id": f"x{i}", "field": "sentence", "text": "t"}
                 for i in range(3)]
        out = await rp.run_items(items, partial, batch_size=3, concurrency=1)
        assert len(out) == 3
        assert [r["verdict"] for r in out] == ["msa", "unsure", "unsure"]

    async def test_the_id_is_never_sent_to_the_judge(self):
        """The judge reads Arabic, not our row keys. Sending the id invites
        it to pattern-match on the corpus rather than read the sentence."""
        seen = {}

        async def judge(items):
            seen["items"] = items
            return [_verdict(i["i"]) for i in items]

        await rp.run_items([{"id": "ar-sent-abc", "field": "sentence",
                             "text": "جملة"}], judge, batch_size=20,
                           concurrency=1)
        assert "id" not in seen["items"][0]
        assert seen["items"][0]["text"] == "جملة"


# ---------------------------------------------------------------------------
# The fix queue
# ---------------------------------------------------------------------------


class TestFixRows:
    def test_clean_msa_rows_are_not_queued(self):
        rows = rp.fix_rows([dict(_verdict(0), id="a", field="sentence",
                                 text="جملة")], "sentences")
        assert rows == []

    def test_an_orthography_only_finding_is_carried_but_not_as_a_fix(self):
        """§7: this pass does not fix spelling. It logs it for the pass that
        does, and the verdict stays `msa` so nobody reads it as register."""
        rows = rp.fix_rows([dict(_verdict(0, "msa", kind="orthography_only",
                                          note="final ya"),
                                 id="a", field="sentence", text="جملة")],
                           "sentences")
        assert len(rows) == 1
        assert rows[0]["verdict"] == "msa"
        assert "orthography_only" in rows[0]["note"]

    def test_decision_and_reviewer_ship_blank(self):
        """The TSV is a queue, not a changelog. Nothing is applied unreviewed
        (programme §5 step 5)."""
        rows = rp.fix_rows([dict(_verdict(0, "dialect", evidence=["بكرة"],
                                          msa="غدًا", variety="egyptian"),
                                 id="a", field="sentence", text="بكرة")],
                           "sentences")
        assert rows[0]["decision"] == "" and rows[0]["reviewer"] == ""
        assert rows[0]["evidence"] == "بكرة" and rows[0]["after"] == "غدًا"

    def test_tabs_in_content_cannot_break_the_columns(self):
        rows = rp.fix_rows([dict(_verdict(0, "dialect", msa="a\tb"),
                                 id="a", field="sentence", text="x\ty")],
                           "sentences")
        assert "\t" not in rows[0]["before"] and "\t" not in rows[0]["after"]


class TestSummary:
    def test_confident_dialect_is_the_gate_number(self):
        """§8's gate is zero CONFIDENT dialect verdicts; a low-confidence one
        is a review item, not a failure."""
        results = [dict(_verdict(0, "dialect", confidence=0.9)),
                   dict(_verdict(1, "dialect", confidence=0.4)),
                   dict(_verdict(2, "msa"))]
        s = rp.summarise(results)
        assert s["verdicts"]["dialect"] == 2
        assert s["confident_dialect"] == 1


# ---------------------------------------------------------------------------
# --gold: the §3.2 gates
# ---------------------------------------------------------------------------


class TestGoldGrading:
    def _gold(self, *labels):
        return [{"id": f"g{i}", "store": "sentences", "stratum": "whole_word",
                 "label": lab} for i, lab in enumerate(labels)]

    def _results(self, *verdicts):
        return [dict(_verdict(i, v), id=f"g{i}", field="sentence", text="t")
                for i, v in enumerate(verdicts)]

    def test_an_unlabelled_set_grades_nothing_rather_than_claiming_agreement(self):
        """The set ships with `label` blank. Reporting 100% agreement against
        no labels is the failure mode this guards."""
        report = rp.grade_gold([{"id": "g0", "label": "", "store": "s"}],
                               self._results("msa"))
        assert report["labelled"] == 0
        assert rp.print_gold_report(report) is False

    def test_agreement_gate_is_ninety_five_percent(self):
        gold = self._gold(*(["msa"] * 19 + ["dialect"]))
        good = rp.grade_gold(gold, self._results(*(["msa"] * 19 + ["dialect"])))
        assert good["agreement"] == 1.0 and good["gate_agreement"]
        bad = rp.grade_gold(gold, self._results(*(["dialect"] * 2 + ["msa"] * 18)))
        assert bad["gate_agreement"] is False

    def test_one_missed_dialect_row_fails_the_recall_gate(self):
        """§3.2: recall on the labelled positives is 100%, because they are
        few and known. A judge that finds nine of ten is not calibrated."""
        gold = self._gold("dialect", "dialect", "msa")
        report = rp.grade_gold(gold, self._results("dialect", "msa", "msa"))
        assert report["recall"] == 0.5
        assert report["gate_recall"] is False
        assert report["misses"][0]["id"] == "g1"

    def test_orthography_only_filed_as_dialect_fails_its_own_gate(self):
        """The third §3.2 gate, and the one a keen judge fails: a spelling
        difference is coached by the grader, and calling it dialect would
        send the spelling pass's work into the register queue."""
        gold = self._gold("orthography_only", "msa")
        ok = rp.grade_gold(gold, self._results("msa", "msa"))
        assert ok["gate_orthography"] and ok["orthography_misfiled"] == 0
        bad = rp.grade_gold(gold, self._results("dialect", "msa"))
        assert bad["gate_orthography"] is False
        assert bad["orthography_misfiled"] == 1

    def test_an_orthography_label_counts_as_msa_not_as_its_own_class(self):
        """A reviewer writing `orthography_only` is saying 'MSA, with a
        spelling note'. If the two were not comparable the agreement figure
        would silently exclude exactly the rows the gate is about."""
        report = rp.grade_gold(self._gold("orthography_only"),
                               self._results("msa"))
        assert report["binary_n"] == 1 and report["binary_agree"] == 1

    def test_false_alarms_are_named_not_only_counted(self):
        report = rp.grade_gold(self._gold("msa", "msa"),
                               self._results("dialect", "msa"))
        assert [f["id"] for f in report["false_alarms"]] == ["g0"]


# ---------------------------------------------------------------------------
# The committed gold set itself
# ---------------------------------------------------------------------------


class TestGoldSetFile:
    def _rows(self):
        with rp.GOLD.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))

    def test_is_the_size_and_shape_the_programme_specifies(self):
        rows = self._rows()
        assert len(rows) == 614                     # 200 + 100 + 274 + 40
        by_store = {}
        for r in rows:
            by_store[r["store"]] = by_store.get(r["store"], 0) + 1
        assert by_store == {"sentences": 200, "vocab": 100, "grammar": 314}

    def test_every_reviewer_column_ships_blank(self):
        """A pre-filled label is an anchor, and an anchored gold set cannot
        calibrate anything."""
        for row in self._rows():
            for column in ("label", "variety", "evidence", "note"):
                assert row[column] == "", f"{row['id']} has {column} pre-filled"

    def test_ids_are_unique_and_content_addressed(self):
        rows = self._rows()
        assert len({r["id"] for r in rows}) == len(rows)

    def test_it_holds_the_three_documented_defects(self):
        """`docs/quality/ar.md` records بكرة and وانتا in the sentence bank
        and يلا in the frequency list. A gold set that cannot see the only
        verified positives cannot measure recall on them (§3.2)."""
        rows = self._rows()
        text = " ".join(r["text"] for r in rows)
        assert "وانتا" in text
        assert any("بكرة" in r["text"] and r["stratum"] == "known_defect"
                   for r in rows)
        assert any(r["store"] == "vocab" and r["text"] == "يلا" for r in rows)

    def test_it_holds_the_hard_negatives_too(self):
        """A set of positives measures recall and nothing else. The b-prefix
        rows (بالنسبة, بنفسك) and the MSA homographs (كمان violin, دول to
        internationalize) are what measure precision."""
        rows = self._rows()
        assert sum(1 for r in rows if r["stratum"] == "b_imperfect") >= 20
        vocab = {r["text"] for r in rows if r["store"] == "vocab"}
        assert {"كمان", "دول", "زين"} <= vocab

    def test_the_builder_still_reproduces_it(self):
        """Rule 31: never freeze a number the tool computes. If the corpus
        moves under the gold set, the labels point at rows that changed and
        this says so."""
        import subprocess
        result = subprocess.run(
            [".venv/bin/python", "-m", "scripts.build_ar_register_gold", "--check"],
            cwd=REPO, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Applying what a reviewer accepted
# ---------------------------------------------------------------------------


class TestApplyRegisterFixes:
    """`scripts/apply_register_fixes.py` — programme §5 step 6.

    The queue is the only thing between a model's opinion and the committed
    corpus, so these are all refusal tests: what the script declines to do
    matters more than what it does.
    """

    def _script(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apply_register_fixes", REPO / "scripts" / "apply_register_fixes.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _queue(self, tmp_path: Path, rows: list[dict]) -> Path:
        path = tmp_path / "fixes.tsv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=rp.FIX_COLUMNS,
                                    delimiter="\t", lineterminator="\n",
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _row(self, **kw) -> dict:
        base = {c: "" for c in rp.FIX_COLUMNS}
        base.update(kw)
        return base

    def test_a_blank_decision_is_never_applied(self, tmp_path, capsys):
        """The queue's whole contract. A row nobody looked at is not a
        decision, and the count is printed rather than silently dropped."""
        mod = self._script()
        queue = self._queue(tmp_path, [
            self._row(id="ar-vocab-7038", store="vocab", verdict="dialect",
                      decision=""),
        ])
        import sys as _sys
        argv = _sys.argv
        _sys.argv = ["apply", "--fixes", str(queue), "--dry-run"]
        try:
            assert mod.main() == 0
        finally:
            _sys.argv = argv
        out = capsys.readouterr().out
        assert "1 rows have NO decision" in out
        assert "nothing to apply" in out

    def test_a_culture_note_must_have_the_owners_shape(self):
        """Decision 5, settled: the culture note is the one place dialect
        lives, and only labelled. An unlabelled comparison there is the exact
        defect the programme exists to remove."""
        mod = self._script()
        assert mod.CULTURE_NOTE.match(
            "In MSA this is هكذا. In Egyptian you will hear كده, "
            "in Levantine هيك.")
        assert not mod.CULTURE_NOTE.match("Egyptians say kida a lot.")
        assert not mod.CULTURE_NOTE.match("In Egyptian you will hear كده.")

    def test_a_rewrite_the_card_cannot_blank_is_refused(self):
        """An MSA rewrite usually changes the headword's surface form — that
        is what rewriting Arabic does — and a sentence the card cannot blank
        is a dead row (CHECKS §29). This is the gate that catches it."""
        mod = self._script()
        # The documented defect: the headword IS the dialect word, so the
        # register fix necessarily removes it.
        assert mod.clozable("بكرة", "ستقلي خطاب بكرة، أليس كذلك؟")
        assert not mod.clozable("بكرة", "ستقلي خطاب غدًا، أليس كذلك؟")

    def test_retiring_a_word_drops_its_gloss_override(self):
        """Quality rule 51 / `TestNoDormantOverrides`: an override whose word
        is not in the frequency file is dormant, and an exclusion orphans it.
        That guard has fired twice on this programme, both times from a pass
        that excluded and glossed in one run."""
        from collections import Counter

        mod = self._script()
        report = Counter()
        rows = [self._row(id="ar-vocab-7038", store="vocab", after="come on",
                          decision="accept")]
        mod.apply_glosses(rows, {"يلا"}, report, dry_run=True)
        assert report["gloss_skipped_word_retired"] == 1
        assert report["gloss_fixed"] == 0

    def test_the_gloss_goes_in_the_gloss_column_not_the_pos_column(self):
        """`gloss_overrides.tsv` has four columns — language, word, pos, en.
        Writing positionally into the third puts English into every touched
        row's part-of-speech."""
        with (REPO / "data" / "gloss_overrides.tsv").open(
                encoding="utf-8-sig", newline="") as handle:
            columns = next(csv.reader(handle, delimiter="\t"))
        assert columns == ["language", "word", "pos", "en"]

    def test_only_a_vocabulary_entry_can_be_retired(self):
        """A dialect-only SENTENCE is removed by the prune, not by an
        exclusion row — exclusions are keyed on a word."""
        from collections import Counter

        mod = self._script()
        assert mod.apply_retirements([], Counter(), dry_run=True) == set()

    def test_a_live_table_row_is_refused_loudly_not_dropped(self, tmp_path, capsys):
        """A `db-sentences` row has no committed file to land in. Matching
        none of the handlers and being skipped in silence would read in the
        report as "applied" — the same shape as a dropped verdict reading as
        "this row is MSA" (quality rule 14)."""
        import sys as _sys

        mod = self._script()
        queue = self._queue(tmp_path, [
            self._row(id="es:abc", store="db-sentences", field="sentence",
                      verdict="dialect", after="x", decision="accept"),
        ])
        argv = _sys.argv
        _sys.argv = ["apply", "--fixes", str(queue), "--dry-run"]
        try:
            assert mod.main() == 0
        finally:
            _sys.argv = argv
        out = capsys.readouterr().out
        assert "db_row_not_applicable" in out
        assert "live table, not a file" in out
