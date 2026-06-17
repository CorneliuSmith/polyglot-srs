"""Tests for the AI grammar-curriculum generator and its NLP self-validation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.services.nlp import init_nlp_backends
from backend.services.seeder import generate_curriculum as gc


@pytest.fixture(scope="module", autouse=True)
def _nlp():
    # Registers the pure-Python backends (tr, sw, yo, ha, ...) used below.
    init_nlp_backends()


class FakeSettings:
    tutor_dev_mock = False
    anthropic_api_key = "fake"
    tutor_model = "claude-opus-4-8"
    tutor_summary_model = "claude-sonnet-4-6"


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, content):
        self.content = content


# ── drill self-validation ───────────────────────────────────────────────────

class TestValidateDrill:
    @pytest.mark.asyncio
    async def test_valid_drill_passes(self):
        drill = {
            "sentence": "Kitap {{answer}}.", "answer": "masada",
            "full_sentence": "Kitap masada.",
        }
        assert await gc.validate_drill("tr", drill) is True

    @pytest.mark.asyncio
    async def test_missing_blank_fails(self):
        drill = {"sentence": "Kitap masada.", "answer": "masada", "full_sentence": "Kitap masada."}
        assert await gc.validate_drill("tr", drill) is False

    @pytest.mark.asyncio
    async def test_blank_answer_mismatch_fails(self):
        # full_sentence doesn't match sentence with the answer filled in
        drill = {
            "sentence": "Araba {{answer}}.", "answer": "evde",
            "full_sentence": "Araba garajda.",
        }
        assert await gc.validate_drill("tr", drill) is False

    @pytest.mark.asyncio
    async def test_empty_answer_fails(self):
        drill = {"sentence": "Kitap {{answer}}.", "answer": "", "full_sentence": "Kitap ."}
        assert await gc.validate_drill("tr", drill) is False

    @pytest.mark.asyncio
    async def test_unknown_language_fails(self):
        drill = {"sentence": "x {{answer}}", "answer": "y", "full_sentence": "x y"}
        assert await gc.validate_drill("zz", drill) is False


# ── curriculum filtering ────────────────────────────────────────────────────

class TestValidateCurriculum:
    @pytest.mark.asyncio
    async def test_drops_invalid_drills_and_empty_points(self):
        raw = {
            "points": [
                {
                    "title": "Locative",
                    "explanation": "Location.",
                    "culture_note": "",
                    "drills": [
                        {"sentence": "Kitap {{answer}}.", "answer": "masada", "full_sentence": "Kitap masada."},
                        {"sentence": "broken", "answer": "x", "full_sentence": "broken"},
                    ],
                },
                {
                    "title": "AllBad",
                    "drills": [
                        {"sentence": "no blank", "answer": "x", "full_sentence": "no blank"},
                    ],
                },
            ]
        }
        cleaned = await gc.validate_curriculum("tr", raw, "A1")
        assert len(cleaned["points"]) == 1          # AllBad dropped
        assert len(cleaned["points"][0]["drills"]) == 1  # broken drill dropped
        assert cleaned["points"][0]["source"] == "ai"
        assert cleaned["points"][0]["reviewed"] is False
        assert cleaned["lists"][0]["level"] == "A1"


# ── generation (mock + real-parse) ──────────────────────────────────────────

class TestGenerateCurriculum:
    @pytest.mark.asyncio
    async def test_mock_pipeline_keeps_valid_drops_broken(self):
        # Mock returns one valid + one deliberately-broken drill.
        with patch.object(gc, "get_settings",
                          return_value=type("S", (), {"tutor_dev_mock": True})()):
            raw = await gc.generate_curriculum("tr", "A1")
        cleaned = await gc.validate_curriculum("tr", raw, "A1")
        assert len(cleaned["points"]) == 1
        assert len(cleaned["points"][0]["drills"]) == 1  # broken one filtered out

    @pytest.mark.asyncio
    async def test_real_mode_parses_structured_output(self):
        payload = (
            '{"points": [{"title": "Locative", "explanation": "Loc.", '
            '"culture_note": "", "drills": [{"sentence": "Kitap {{answer}}.", '
            '"answer": "masada", "full_sentence": "Kitap masada.", '
            '"translation": "The book is on the table.", "hint": "masa+da"}]}]}'
        )
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(return_value=_Resp([_TextBlock(payload)]))
        with patch.object(gc, "get_settings", return_value=FakeSettings()), \
             patch.object(gc, "AsyncAnthropic", return_value=fake_client):
            raw = await gc.generate_curriculum("tr", "A1", 1)
        assert raw["points"][0]["title"] == "Locative"
        assert fake_client.messages.create.await_args.kwargs["model"] == "claude-opus-4-8"

    @pytest.mark.asyncio
    async def test_generate_and_load_dry_run_does_not_write(self):
        with patch.object(gc, "get_settings",
                          return_value=type("S", (), {"tutor_dev_mock": True})()), \
             patch.object(gc.GrammarSeeder, "load", new=AsyncMock()) as mock_load:
            report = await gc.generate_and_load("fake://db", "tr", "A1", 6, dry_run=True)
        assert report["kept_drills"] == 1
        assert report["raw_drills"] == 2
        mock_load.assert_not_awaited()
