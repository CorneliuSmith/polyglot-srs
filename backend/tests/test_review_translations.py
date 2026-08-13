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
