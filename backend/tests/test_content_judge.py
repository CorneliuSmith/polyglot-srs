"""The content judge: five questions, one schema builder, one set of gates.

`docs/plans/quality-guardrails-telemetry.md` §4.3 J1 is the brief. Nothing
here reaches a model — every judge is a callable, faked the way
`test_register_pass.py` fakes it, and the two provider functions are exercised
against a patched client. Quality rule 15: a unit test must not be the place
this programme spends the API key, and an absent key is worse than a spend
because it silently exercises the exception branch instead of the behaviour.
"""
from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.quality import content_judge as cj
from backend.services.quality import register_pass as rp

REPO = Path(__file__).resolve().parents[2]
ALL = list(cj.QUESTIONS.values())


def _verdict(question: cj.Question, i: int, verdict: str, **kw) -> dict:
    """A well-formed verdict object for *question*, the way a model returns it."""
    base = {"i": i, "verdict": verdict, "evidence": [], question.category_field: None,
            question.expected_field: None, "confidence": 0.9, "note": ""}
    if question.variety_enum:
        base["variety"] = None
    if question.asks_meaning_kept:
        base["meaning_kept"] = True
    base.update(kw)
    return base


def _usage(n: int) -> dict:
    return {"input_tokens": 100 * n, "output_tokens": 10 * n,
            "cache_write_tokens": n, "cache_read_tokens": 2 * n, "calls": 1}


# ---------------------------------------------------------------------------
# The questions and their rules
# ---------------------------------------------------------------------------


class TestQuestions:
    def test_the_five_the_plan_and_the_table_name(self):
        """`content_verdicts.question` is documented as exactly this set
        (migration 20261107000000); a sixth here would be a row the panel
        cannot group."""
        assert set(cj.QUESTIONS) == {"register", "sense", "gloss", "scripture", "card_shape"}
        for name, q in cj.QUESTIONS.items():
            assert q.name == name

    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_every_question_says_unsure_is_legal_and_asks_for_every_item(self, q):
        """Two rules the register calibration paid for: a judge that must
        guess produces false alarms, and a judge that may drop an item
        produces a count that reads as clean (quality rule 14)."""
        assert "unsure" in q.rules
        assert "IS A LEGAL ANSWER" in q.rules
        assert "Return every item exactly once" in q.rules
        assert "unsure" in q.verdict_enum

    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_the_gate_classes_are_verdicts_and_the_guard_is_a_label(self, q):
        """The gates compare verdicts, so the positive and negative classes
        must be things the judge can say; the guard is what a REVIEWER
        writes, so it must map to a verdict but need not be one."""
        assert q.positive <= set(q.verdict_enum)
        assert q.negative <= set(q.verdict_enum)
        assert not (q.positive & q.negative)
        for label in q.guard_labels:
            assert q.label_map[label] in q.verdict_enum
            assert q.label_map[label] not in q.positive
        assert q.label_map["unsure"] == "unsure"

    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_every_category_the_rules_name_is_in_the_enum(self, q):
        """A category quoted in the rules that the schema rejects is a
        verdict the model cannot return: the call fails on shape and the
        batch becomes unsure."""
        for category in q.category_enum:
            assert f'"{category}"' in q.rules or category in q.rules, category

    def test_register_rules_are_the_calibrated_text(self):
        """56/56 was measured on this string. `register_pass._RULES` and the
        register question must be the same text, not a paraphrase."""
        assert cj.REGISTER.rules == rp._RULES
        assert "ORTHOGRAPHY IS NOT REGISTER" in cj.REGISTER.rules

    def test_sense_rules_name_the_source_and_the_failure(self):
        """The defect is upstream of the model: a lexical database whose
        sense order is not frequency order, and a maker that took the first
        one. The judge must be told that, and told what a wrong answer looks
        like by name."""
        rules = cj.SENSE.rules
        assert "lexical database" in rules
        assert "NOT frequency order" in rules
        for example in ("runner", "smuggler", "cub", "awkward", "sadly"):
            assert example in rules, example
        assert '"expected"' in rules
        assert "relation" in rules            # CHECKS §36, the largest class left

    def test_gloss_rules_quote_the_makers_charter_verbatim(self):
        """The gloss judge checks the contract the gloss was written under,
        so the contract is quoted from the maker, not paraphrased. If
        `translate.maker_system` changes its wording this fails, which is
        the point."""
        from backend.services.translate import maker_system

        charter = maker_system("Arabic")
        for phrase in ("for THAT specific sense", "Match the part of speech"):
            assert phrase in charter, "the charter moved; update the quotation"
            assert phrase in cj.GLOSS.rules
        assert "synonym" in cj.GLOSS.rules.lower()      # the named false-alarm mode

    def test_card_shape_rules_state_the_two_hard_facts(self):
        """CHECKS §37: a `letter` row never carries a sentence, and that is
        code, not judgement. And a bound stem cannot be a whole orthographic
        word, which is why no sentence can legitimately contain one."""
        rules = cj.CARD_SHAPE.rules
        assert 'speech is "letter" NEVER carries a sentence' in rules
        assert "bound stem cannot be a whole orthographic word" in rules
        assert "758" in rules                 # the one-character WORDS, by count

    def test_scripture_rules_name_the_found_rows_and_the_non_tells(self):
        rules = cj.SCRIPTURE.rules
        assert "18:24" in rules and "hadith" in rules
        assert "ABOUT religion is not scripture" in rules


class TestSystemPrompt:
    def test_the_register_question_carries_the_register_pin(self):
        """PR #473 put the pin in `register_line`; the judge and the makers
        hold ONE standard. `register_pass.system_prompt()` is the same string
        it was before the move."""
        from backend.services.quality_rules import register_line

        prompt = cj.REGISTER.system_prompt()
        assert register_line("ar").strip() in prompt
        assert prompt == rp.system_prompt()
        assert prompt == cj.system_prompt_for(cj.REGISTER, "ar")

    def test_a_course_with_nothing_to_pin_gets_the_rules_alone(self):
        """English has no variety to pin, and `register_line` returns "";
        the prompt must not end in a stray newline that changes it for
        every batch."""
        assert cj.system_prompt_for(cj.SENSE) == cj.SENSE.rules
        assert cj.system_prompt_for(cj.SENSE, "en") == cj.SENSE.rules

    def test_the_pin_follows_the_caller_s_code_not_the_question_s(self):
        """A gloss batch is Arabic when the locale is Arabic, whatever the
        headwords' language: the caller names the code and the pin follows."""
        from backend.services.quality_rules import register_line

        assert register_line("ar").strip() in cj.system_prompt_for(cj.GLOSS, "ar")
        assert cj.system_prompt_for(cj.GLOSS, "es") == cj.GLOSS.rules


# ---------------------------------------------------------------------------
# The schema
# ---------------------------------------------------------------------------


class TestSchema:
    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_enums_are_the_question_s_and_every_property_is_required(self, q):
        schema = cj.schema_for(q)
        props = schema["properties"]
        assert props["verdict"]["enum"] == list(q.verdict_enum)
        assert props[q.category_field]["enum"] == [*q.category_enum, None]
        assert q.expected_field in props
        assert schema["required"] == list(props)
        assert schema["additionalProperties"] is False
        assert {"i", "verdict", "evidence", "confidence", "note"} <= set(props)

    def test_register_is_exactly_the_programme_s_nine_fields(self):
        """§3.1 is a contract with the reviewers' TSV and with the local
        endpoint's guided decoding; the general builder must reproduce it
        field for field, under the programme's names."""
        assert set(cj.schema_for(cj.REGISTER)["properties"]) == {
            "i", "verdict", "variety", "evidence", "kind", "msa",
            "meaning_kept", "confidence", "note"}
        assert rp.VERDICT_SCHEMA == cj.schema_for(cj.REGISTER)

    def test_later_questions_use_the_table_s_names(self):
        """`content_verdicts` has `category` and `expected`; a question that
        invented its own names would need a per-question writer."""
        for q in (cj.SENSE, cj.GLOSS, cj.SCRIPTURE, cj.CARD_SHAPE):
            props = cj.schema_for(q)["properties"]
            assert "category" in props and "expected" in props
            assert "variety" not in props and "meaning_kept" not in props

    def test_the_batch_schema_is_one_object_per_question(self):
        """Both providers must send the very same object, and
        `register_pass.BATCH_SCHEMA` must be it — its provider test checks
        identity, not equality."""
        assert cj.batch_schema_for(cj.SENSE) is cj.batch_schema_for(cj.SENSE)
        assert cj.batch_schema_for(cj.REGISTER) is rp.BATCH_SCHEMA
        assert cj.batch_schema_for(cj.SENSE) is not cj.batch_schema_for(cj.GLOSS)

    def test_the_blank_verdict_matches_what_register_pass_built_by_hand(self):
        assert cj.blank_verdict(cj.REGISTER, "judge error: x") == {
            "verdict": "unsure", "variety": None, "evidence": [], "kind": None,
            "msa": None, "meaning_kept": False, "confidence": 0.0,
            "note": "judge error: x"}
        blank = cj.blank_verdict(cj.SENSE, "n")
        assert blank["verdict"] == "unsure" and blank["category"] is None
        assert blank["expected"] is None and blank["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Running items: verdicts AND usage
# ---------------------------------------------------------------------------


class TestRunItems:
    def _items(self, n: int) -> list[dict]:
        return [{"id": f"x{i}", "word": f"w{i}", "rank": i, "pos": "noun",
                 "definition": "d"} for i in range(n)]

    async def test_returns_verdicts_and_usage_summed_across_batches(self):
        """The judge loop logs the spend to tutor_usage as kind='judge'; the
        owner's condition for a nightly judge was that its cost be visible.
        Three batches, three calls, tokens added not overwritten."""
        async def judge(items):
            return ([_verdict(cj.SENSE, it["i"], "primary") for it in items],
                    _usage(len(items)))

        results, usage = await cj.run_items(cj.SENSE, self._items(5), judge,
                                            batch_size=2, concurrency=2)
        assert len(results) == 5
        assert {r["verdict"] for r in results} == {"primary"}
        # batches of 2, 2, 1 → n = 5 in total
        assert usage == {"input_tokens": 500, "output_tokens": 50,
                         "cache_write_tokens": 5, "cache_read_tokens": 10, "calls": 3}

    async def test_a_failed_batch_becomes_unsure_for_every_item_and_costs_nothing(self):
        """A dropped row and a clean row are indistinguishable in a count
        (quality rule 14). And a batch that raised is not a call the loop
        should bill to the cap."""
        calls = {"n": 0}

        async def flaky(items):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("endpoint down")
            return ([_verdict(cj.SENSE, it["i"], "primary") for it in items],
                    _usage(len(items)))

        results, usage = await cj.run_items(cj.SENSE, self._items(4), flaky,
                                            batch_size=2, concurrency=1)
        assert len(results) == 4
        unsure = [r for r in results if r["verdict"] == "unsure"]
        assert len(unsure) == 2
        assert all("endpoint down" in r["note"] for r in unsure)
        assert all(r["category"] is None and r["expected"] is None for r in unsure)
        assert usage["calls"] == 1 and usage["input_tokens"] == 200

    async def test_an_item_the_judge_skipped_becomes_unsure(self):
        async def partial(items):
            return [_verdict(cj.GLOSS, items[0]["i"], "faithful")], _usage(1)

        items = [{"id": f"g{i}", "word": "w", "pos": "noun", "definition": "d",
                  "gloss": "x", "locale": "ar"} for i in range(3)]
        results, _ = await cj.run_items(cj.GLOSS, items, partial, batch_size=3,
                                        concurrency=1)
        assert [r["verdict"] for r in results] == ["faithful", "unsure", "unsure"]

    async def test_a_judge_returning_a_bare_list_is_counted_as_no_spend(self):
        """`register_pass`'s tests and any hand-written fake return a list.
        They are accepted; they simply report nothing to bill."""
        async def bare(items):
            return [_verdict(cj.REGISTER, it["i"], "msa") for it in items]

        results, usage = await cj.run_items(
            cj.REGISTER, [{"id": "a", "field": "sentence", "text": "t"}], bare)
        assert results[0]["verdict"] == "msa" and results[0]["kind"] is None
        assert usage == dict.fromkeys(cj.USAGE_KEYS, 0)

    async def test_the_id_is_never_sent_to_the_judge(self):
        """The judge reads content, not our row keys. Sending the id invites
        it to pattern-match on the corpus rather than read the row."""
        seen = {}

        async def judge(items):
            seen["items"] = items
            return [_verdict(cj.SENSE, it["i"], "primary") for it in items], _usage(1)

        await cj.run_items(cj.SENSE, self._items(1), judge)
        assert "id" not in seen["items"][0]
        assert seen["items"][0]["word"] == "w0"


# ---------------------------------------------------------------------------
# The two providers
# ---------------------------------------------------------------------------


class TestProviders:
    async def test_anthropic_returns_usage_beside_the_verdicts(self):
        """`response.usage` is read in the same four fields `tutor._add_usage`
        reads, so the judge's rows in tutor_usage price like every other
        kind. The schema sent is the question's cached batch object and the
        system prompt carries the pin."""
        class Block:
            text = json.dumps({"verdicts": [_verdict(cj.GLOSS, 0, "diverges",
                                                     category="wrong_pos")]})

        class Usage:
            input_tokens = 1200
            output_tokens = 80
            cache_creation_input_tokens = 900
            cache_read_input_tokens = 300

        class FakeResponse:
            content = [Block()]
            usage = Usage()

        class FakeSettings:
            anthropic_api_key = "sk-test"

        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("anthropic.AsyncAnthropic") as client_cls:
            create = AsyncMock(return_value=FakeResponse())
            client_cls.return_value.messages.create = create
            verdicts, usage = await cj._judge_anthropic(
                cj.GLOSS, [{"i": 0, "word": "whistle"}], None, "ar")

        kwargs = create.await_args.kwargs
        assert kwargs["output_config"]["format"]["schema"] is cj.batch_schema_for(cj.GLOSS)
        from backend.services.models import resolve_model
        from backend.services.quality_rules import register_line
        assert kwargs["model"] == resolve_model("sentence_checker", "ar")
        assert register_line("ar").strip() in kwargs["system"]
        assert verdicts[0]["category"] == "wrong_pos"
        assert usage == {"input_tokens": 1200, "output_tokens": 80,
                         "cache_write_tokens": 900, "cache_read_tokens": 300, "calls": 1}

    async def test_a_response_without_usage_still_counts_the_call(self):
        class Block:
            text = json.dumps({"verdicts": [_verdict(cj.SENSE, 0, "primary")]})

        class FakeResponse:
            content = [Block()]
            usage = None

        class FakeSettings:
            anthropic_api_key = "sk-test"

        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("anthropic.AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = AsyncMock(return_value=FakeResponse())
            _, usage = await cj._judge_anthropic(cj.SENSE, [{"i": 0}], "claude-x")
        assert usage["calls"] == 1 and usage["input_tokens"] == 0

    async def test_local_endpoint_reports_prompt_and_completion_tokens(self):
        """vLLM's `usage` has no cache counters; they come back as zero, not
        missing, so the loop sums one shape."""
        captured = {}

        class FakeResponse:
            @staticmethod
            def raise_for_status():
                return None

            @staticmethod
            def json():
                return {"choices": [{"message": {"content": json.dumps(
                    {"verdicts": [_verdict(cj.SCRIPTURE, 0, "plain")]})}}],
                    "usage": {"prompt_tokens": 700, "completion_tokens": 40}}

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
            verdicts, usage = await cj._judge_openai(
                cj.SCRIPTURE, [{"i": 0, "sentence": "s"}], "http://gpu:8000/v1", "jais")
        fmt = captured["payload"]["response_format"]["json_schema"]
        assert fmt["schema"] is cj.batch_schema_for(cj.SCRIPTURE)
        assert fmt["name"] == "scripture_verdicts"
        assert captured["payload"]["messages"][0]["content"] == cj.SCRIPTURE.rules
        assert verdicts[0]["verdict"] == "plain"
        assert usage == {"input_tokens": 700, "output_tokens": 40,
                         "cache_write_tokens": 0, "cache_read_tokens": 0, "calls": 1}

    def test_a_local_endpoint_without_a_model_is_refused(self):
        with pytest.raises(SystemExit):
            cj.judge_for(cj.SENSE, "http://gpu:8000/v1", None)

    def test_the_judge_is_named_without_leaking_the_endpoint(self):
        name = cj.judge_name("http://user:pw@gpu.internal:8000/v1", "jais-2-8b")
        assert name == "local:jais-2-8b@gpu.internal" and "pw" not in name


# ---------------------------------------------------------------------------
# The gold set and the three gates, for every question
# ---------------------------------------------------------------------------


def _gold(labels: list[str]) -> list[dict]:
    return [{"id": f"g{i}", "store": "s", "stratum": "random", "label": lab}
            for i, lab in enumerate(labels)]


def _results(q: cj.Question, verdicts: list[str]) -> list[dict]:
    return [dict(_verdict(q, i, v), id=f"g{i}") for i, v in enumerate(verdicts)]


def _some(s: frozenset[str]) -> str:
    return sorted(s)[0]


def _clean(q: cj.Question) -> str:
    """A clean label that is not also the guard label: `literary` is both a
    verdict and scripture's near miss, and a synthetic set must keep the
    guard rows countable."""
    return _some(q.negative - q.guard_labels)


class TestGoldGrading:
    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_a_perfect_judge_passes_all_three_gates(self, q):
        pos, neg, guard = _some(q.positive), _clean(q), _some(q.guard_labels)
        labels = [neg] * 18 + [pos, guard]
        got = [neg] * 18 + [pos, q.label_map[guard]]
        report = cj.grade_gold(q, _gold(labels), _results(q, got))
        assert report["labelled"] == 20
        assert report["gate_agreement"] and report["agreement"] == 1.0
        assert report["gate_recall"] and report["recall"] == 1.0
        assert report["gate_guard"] and report["guard_n"] == 1
        assert cj.print_gold_report(q, report) is True

    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_one_missed_positive_fails_recall_even_at_high_agreement(self, q):
        """§3.2: the positives are few and known; nine of ten is not
        calibrated. Agreement can stay above 95% while recall fails."""
        pos, neg = _some(q.positive), _clean(q)
        labels = [neg] * 38 + [pos, pos]
        got = [neg] * 38 + [pos, neg]
        report = cj.grade_gold(q, _gold(labels), _results(q, got))
        assert report["gate_agreement"] is True
        assert report["gate_recall"] is False and report["recall"] == 0.5
        assert report["misses"][0]["id"] == "g39"
        assert cj.print_gold_report(q, report) is False

    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_two_false_alarms_in_twenty_fail_the_agreement_gate(self, q):
        pos, neg = _some(q.positive), _clean(q)
        labels = [neg] * 19 + [pos]
        got = [pos, pos] + [neg] * 17 + [pos]
        report = cj.grade_gold(q, _gold(labels), _results(q, got))
        assert report["gate_recall"] is True
        assert report["gate_agreement"] is False
        assert [f["id"] for f in report["false_alarms"]] == ["g0", "g1"]

    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_the_guard_class_filed_as_the_finding_fails_its_own_gate(self, q):
        """The gate a keen judge fails: the near-miss class — a spelling
        variant, a second sense, a synonym, a proverb, a one-letter word —
        must never come back as the finding."""
        pos, neg, guard = _some(q.positive), _clean(q), _some(q.guard_labels)
        labels = [neg] * 38 + [pos, guard]
        got = [neg] * 38 + [pos, pos]
        report = cj.grade_gold(q, _gold(labels), _results(q, got))
        assert report["gate_agreement"] is True         # 39/40 still clears 95%
        assert report["gate_guard"] is False and report["guard_misfiled"] == 1

    @pytest.mark.parametrize("q", ALL, ids=lambda q: q.name)
    def test_the_guard_label_counts_in_the_binary_split_as_its_clean_verdict(self, q):
        """A reviewer's near-miss label means "clean, with a note". If it were
        excluded from the agreement figure, the rows the gate is about would
        silently drop out of it."""
        guard = _some(q.guard_labels)
        report = cj.grade_gold(q, _gold([guard]), _results(q, [q.label_map[guard]]))
        assert report["binary_n"] == 1 and report["binary_agree"] == 1

    def test_an_unlabelled_set_grades_nothing(self):
        report = cj.grade_gold(cj.SENSE, [{"id": "g0", "label": "", "store": "s"}],
                               _results(cj.SENSE, ["primary"]))
        assert report["labelled"] == 0
        assert cj.print_gold_report(cj.SENSE, report) is False

    def test_a_secondary_sense_verdict_is_not_a_finding(self):
        """The sense question's guard is a verdict in its own right: the
        judge may SAY secondary, and saying it for a secondary row is
        agreement."""
        report = cj.grade_gold(cj.SENSE, _gold(["secondary", "rare"]),
                               _results(cj.SENSE, ["secondary", "wrong"]))
        assert report["agreement"] == 1.0 and report["recall"] == 1.0

    def test_register_pass_reports_the_guard_under_the_programme_s_name(self):
        """`register_pass.grade_gold` is the same grader; the programme
        document and the reviewers' write-up say `orthography_only`, so the
        report carries both keys."""
        gold = _gold(["orthography_only", "msa"])
        bad = rp.grade_gold(gold, _results(cj.REGISTER, ["dialect", "msa"]))
        assert bad["gate_orthography"] is False and bad["orthography_misfiled"] == 1
        assert bad["gate_guard"] is False


class TestGoldItems:
    def test_items_are_the_question_s_fields_read_from_same_named_columns(self):
        rows = [{"id": "en-vocab-4975", "store": "vocab", "field": "definition",
                 "word": "sadly", "rank": "4975", "pos": "adverb",
                 "definition": "in an unfortunate way", "label": "", "stratum": "b5"}]
        assert cj.gold_items(cj.SENSE, rows) == [
            {"id": "en-vocab-4975", "word": "sadly", "rank": 4975, "pos": "adverb",
             "definition": "in an unfortunate way"}]

    def test_the_register_set_s_rank_comes_from_the_id(self):
        """`ar_register_gold.tsv` has no rank column; the builder put the
        rank in the id. A vocabulary item's rank is the question, so the
        general reader must recover it exactly as `register_pass` did."""
        rows = [{"id": "ar-vocab-7038", "field": "gloss", "text": "يلا",
                 "translation": "come on"},
                {"id": "ar-sent-abc", "field": "sentence", "text": "جملة",
                 "translation": ""}]
        items = cj.gold_items(cj.REGISTER, rows)
        assert items[0] == {"id": "ar-vocab-7038", "field": "gloss", "text": "يلا",
                            "translation": "come on", "rank": 7038}
        assert "rank" not in items[1]

    def test_a_missing_gold_set_says_where_the_columns_are_documented(self):
        with pytest.raises(SystemExit) as exc:
            cj.load_gold(replace(cj.SENSE, gold_path=cj.EVAL / "nope_gold.tsv"))
        assert "data/eval/README.md" in str(exc.value)


# ---------------------------------------------------------------------------
# The CLI
# ---------------------------------------------------------------------------


class TestCli:
    def _write_gold(self, tmp_path: Path, q: cj.Question, rows: list[dict]) -> Path:
        path = tmp_path / f"{q.name}_gold.tsv"
        columns = [*cj.GOLD_COMMON_COLUMNS, *q.item_fields]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t",
                                    lineterminator="\n", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path

    async def test_the_spend_notice_is_the_first_line_and_gold_is_required(self, capsys):
        """The owner's standing rule is that this agent never spends the key;
        a person running this does, and reads that before anything else.
        Without --gold there is nothing this unit may run."""
        with pytest.raises(SystemExit) as exc:
            await cj.main(["--question", "sense"])
        assert exc.value.code == 2
        out = capsys.readouterr()
        assert out.out.splitlines()[0].startswith("THIS RUN SPENDS THE ANTHROPIC API KEY")
        assert "--gold" in out.err

    def test_a_local_endpoint_is_named_and_the_key_is_said_to_be_unused(self):
        notice = cj.spend_notice("http://user:pw@gpu.internal:8000/v1")
        assert notice.startswith("LOCAL JUDGE") and "gpu.internal" in notice
        assert "pw" not in notice and "not used" in notice

    async def test_a_missing_gold_set_refuses_before_any_call(self, capsys):
        judge = AsyncMock()
        with patch.object(cj, "judge_for", lambda *a, **k: judge), \
             patch.object(cj, "judge_name", lambda *a, **k: "fake"), \
             pytest.raises(SystemExit) as exc:
            await cj.main(["--question", "gloss", "--gold"])
        assert "gloss_gold.tsv" in str(exc.value)
        judge.assert_not_awaited()

    async def test_exit_two_below_the_gate_and_zero_above_it(self, tmp_path, capsys,
                                                          monkeypatch):
        monkeypatch.setattr(cj, "OUT_DIR", tmp_path / "out")
        rows = [{"id": f"g{i}", "store": "vocab", "field": "definition", "label": "primary",
                 "stratum": "b1", "word": f"w{i}", "rank": str(i + 1), "pos": "noun",
                 "definition": "d"} for i in range(19)]
        rows.append({"id": "g19", "store": "vocab", "field": "definition", "label": "rare",
                     "stratum": "b1", "word": "runner", "rank": "2000", "pos": "noun",
                     "definition": "a smuggler"})
        path = self._write_gold(tmp_path, cj.SENSE, rows)
        question = replace(cj.SENSE, gold_path=path)

        def perfect(*a, **k):
            async def judge(items):
                return ([_verdict(cj.SENSE, it["i"], "rare" if it["word"] == "runner"
                                  else "primary") for it in items], _usage(len(items)))
            return judge

        def blind(*a, **k):
            async def judge(items):
                return ([_verdict(cj.SENSE, it["i"], "primary") for it in items],
                        _usage(len(items)))
            return judge

        with patch.dict(cj.QUESTIONS, {"sense": question}), \
             patch.object(cj, "judge_for", perfect), \
             patch.object(cj, "judge_name", lambda *a, **k: "fake"):
            assert await cj.main(["--question", "sense", "--gold"]) == 0
        out = capsys.readouterr().out
        assert "CALIBRATION — sense: 20 labelled items" in out
        assert "tokens: 2000 in" in out and "over 1 calls" in out

        with patch.dict(cj.QUESTIONS, {"sense": question}), \
             patch.object(cj, "judge_for", blind), \
             patch.object(cj, "judge_name", lambda *a, **k: "fake"):
            assert await cj.main(["--question", "sense", "--gold"]) == 2
        assert "MISS  g19 expected rare" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The reviewers' documentation keeps up with the questions
# ---------------------------------------------------------------------------


class TestReadmeNamesEveryQuestion:
    def test_every_question_and_its_item_columns_are_documented(self):
        """`data/eval/README.md` is what a reviewer builds a gold set from. A
        question or a column it does not name is a set nobody can fill —
        which is the DEBT entry this module ships with, and the reason the
        four new gates cannot yet pass."""
        readme = (REPO / "data" / "eval" / "README.md").read_text(encoding="utf-8")
        for q in ALL:
            assert f"`{q.gold_path.name}`" in readme, q.name
            for column in q.item_fields:
                assert f"`{column}`" in readme, f"{q.name}: {column}"
            for label in sorted(q.label_map):
                assert f"`{label}`" in readme, f"{q.name}: label {label}"
