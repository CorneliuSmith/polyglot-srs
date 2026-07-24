"""Unit tests for the definition maker-checker (services/define.py). Mock mode,
no API key or DB."""
from types import SimpleNamespace
from unittest.mock import patch

from backend.services import define


def _mock_settings(**over):
    base = {"tutor_dev_mock": True, "anthropic_api_key": ""}
    base.update(over)
    return SimpleNamespace(**base)


async def test_generate_definitions_mock_flow():
    items = [
        {"i": 0, "word": "kupanga", "pos": "verb", "example": None},
        {"i": 1, "word": "chumba", "pos": "noun", "example": "Chumba changu."},
        {"i": 2, "word": "haraka", "pos": "adverb", "example": None},
    ]
    with patch("backend.services.define.get_settings", return_value=_mock_settings()):
        results = await define.generate_definitions("Swahili", "English", items)
    assert [r["word"] for r in results] == ["kupanga", "chumba", "haraka"]
    # First item is rejected by the mock checker → no definition to store.
    assert results[0]["verdict"] == "reject"
    assert results[0]["definition"] == ""
    # The rest pass with a definition.
    assert results[1]["verdict"] == "ok"
    assert results[1]["definition"] == "meaning of chumba"


async def test_fallback_rule_wording():
    # English target → "explain in English"; other locale → explain-in-locale rule.
    assert "English explanation" in define._fallback_rule("English")
    ru = define._fallback_rule("Russian")
    assert "Russian" in ru and "English explanation" in ru


async def test_generate_definitions_empty_is_noop():
    with patch("backend.services.define.get_settings", return_value=_mock_settings()):
        assert await define.generate_definitions("Swahili", "English", []) == []
