"""Maker–checker English-gloss pipeline (mock mode: no key, no API calls)."""

from unittest.mock import patch

import pytest

from backend.services import translate as tr


class _MockSettings:
    anthropic_api_key = ""
    tutor_dev_mock = True
    tutor_summary_model = "claude-haiku-4-5-20251001"


def _mock():
    def boom(*a, **k):
        raise AssertionError("no Anthropic client may be built in mock mode")
    return (patch.object(tr, "get_settings", return_value=_MockSettings()),
            patch.object(tr, "AsyncAnthropic", side_effect=boom))


ITEMS = [
    {"i": 0, "word": "cat", "pos": "noun", "definition": "small feline", "example": "The cat sleeps."},
    {"i": 1, "word": "dog", "pos": "noun", "definition": "domestic canine", "example": "The dog runs."},
    {"i": 2, "word": "run", "pos": "verb", "definition": "to move fast", "example": "I run daily."},
]


class TestTranslate:
    def test_available_in_mock(self):
        with _mock()[0]:
            assert tr.translations_available() is True

    @pytest.mark.asyncio
    async def test_maker_produces_a_gloss_per_word(self):
        s, b = _mock()
        with s, b:
            out = await tr.make_glosses("Dutch", ITEMS)
        assert out == {0: "[cat]", 1: "[dog]", 2: "[run]"}

    @pytest.mark.asyncio
    async def test_checker_rejects_first_passes_rest(self):
        s, b = _mock()
        items = [{**it, "gloss": f"[{it['word']}]"} for it in ITEMS]
        with s, b:
            out = await tr.check_glosses("Dutch", items)
        assert out[0]["verdict"] == "reject"
        assert out[1]["verdict"] == "ok"

    @pytest.mark.asyncio
    async def test_maker_check_routes_apply_vs_queue(self):
        s, b = _mock()
        with s, b:
            res = await tr.maker_check_batch("Dutch", ITEMS)
        by_word = {r["word"]: r for r in res}
        # first item rejected -> no gloss to store (queues)
        assert by_word["cat"]["verdict"] == "reject"
        assert by_word["cat"]["gloss"] == ""
        # the rest approved -> gloss carried through for apply
        assert by_word["dog"]["verdict"] == "ok"
        assert by_word["dog"]["gloss"] == "[dog]"
        assert by_word["run"]["gloss"] == "[run]"
