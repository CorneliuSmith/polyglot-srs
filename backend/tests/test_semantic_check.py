"""Tests for the AI semantic-check service."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.services import semantic_check as sc


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, content):
        self.content = content


class _Settings:
    def __init__(self, mock=False, key="fake"):
        self.tutor_dev_mock = mock
        self.anthropic_api_key = key
        self.tutor_summary_model = "claude-sonnet-4-6"


class TestAiAvailable:
    def test_true_with_key(self):
        with patch.object(sc, "get_settings", return_value=_Settings(key="k")):
            assert sc.ai_available() is True

    def test_true_in_mock(self):
        with patch.object(sc, "get_settings", return_value=_Settings(mock=True, key="")):
            assert sc.ai_available() is True

    def test_false_when_unconfigured(self):
        with patch.object(sc, "get_settings", return_value=_Settings(mock=False, key="")):
            assert sc.ai_available() is False


class TestSemanticCheck:
    @pytest.mark.asyncio
    async def test_mock_passes_without_api_call(self):
        with patch.object(sc, "get_settings", return_value=_Settings(mock=True)), \
             patch.object(sc, "AsyncAnthropic", side_effect=AssertionError("no call in mock")):
            result = await sc.semantic_check_point("tr", "Locative", "...", [])
        assert result["status"] == "pass"

    @pytest.mark.asyncio
    async def test_parses_concerns_verdict(self):
        payload = '{"status": "concerns", "notes": "Answer for drill 1 is wrong."}'
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(return_value=_Resp([_TextBlock(payload)]))
        with patch.object(sc, "get_settings", return_value=_Settings()), \
             patch.object(sc, "AsyncAnthropic", return_value=fake_client):
            result = await sc.semantic_check_point(
                "tr", "Locative", "loc", [{"sentence": "x {{answer}}", "answer": "y"}]
            )
        assert result["status"] == "concerns"
        assert "wrong" in result["notes"]

    @pytest.mark.asyncio
    async def test_unparseable_flags_concerns(self):
        fake_client = AsyncMock()
        fake_client.messages.create = AsyncMock(return_value=_Resp([_TextBlock("not json")]))
        with patch.object(sc, "get_settings", return_value=_Settings()), \
             patch.object(sc, "AsyncAnthropic", return_value=fake_client):
            result = await sc.semantic_check_point("tr", "Locative", "loc", [])
        # Fail safe: unparseable review must not pass silently.
        assert result["status"] == "concerns"
