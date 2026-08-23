"""Writing-sample baseline: judge bands (dev-mock), endpoint token-gating,
and the profile priming that feeds the assessment tiers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from backend.services import writing_baseline


def _settings(**over):
    base = {"tutor_dev_mock": True, "anthropic_api_key": ""}
    base.update(over)
    return SimpleNamespace(**base)


class TestAssessWriting:
    def _assess(self, text):
        with patch(
            "backend.services.writing_baseline.get_settings",
            return_value=_settings(),
        ):
            return asyncio.run(
                writing_baseline.assess_writing("es", "Spanish", text)
            )

    def test_mock_bands_scale_with_production(self):
        short, _ = self._assess("Hola amigo")
        mid, _ = self._assess("Ayer fui al mercado y compré mucha fruta fresca")
        long, _ = self._assess(
            "Cuando era pequeño vivía en una ciudad cerca del mar y todos "
            "los veranos íbamos a la playa con mis primos y mis abuelos"
        )
        assert short["level"] == "A1"
        assert mid["level"] == "A2"
        assert long["level"] == "B1"
        for r in (short, mid, long):
            assert r["focus"]
            assert r["notes"]

    def test_sample_is_bounded(self):
        # A pasted essay is truncated, never sent whole.
        result, usage = self._assess("palabra " * 500)
        assert result["level"]  # still assessed
        assert usage["input_tokens"] >= 0


class TestStructuredOutputIsNeverADependency:
    """The production failure behind "I was not able to submit my write-up":
    the summary-tier model rejects output_config with a 400 before it ever
    reads the sample, and dev-mock tests never touch the real path. The
    task-#115 rule applies here too — schema first, plain JSON on refusal.
    """

    def _real_settings(self):
        return _settings(tutor_dev_mock=False, anthropic_api_key="sk-test",
                         tutor_summary_model="claude-haiku-4-5-20251001")

    def _run(self, create):
        client = SimpleNamespace(
            messages=SimpleNamespace(create=create),
        )
        with patch("backend.services.writing_baseline.get_settings",
                   return_value=self._real_settings()), \
             patch("backend.services.writing_baseline.AsyncAnthropic",
                   return_value=client), \
             patch("backend.services.writing_baseline.resolve_model",
                   return_value="claude-haiku-4-5-20251001"):
            return asyncio.run(
                writing_baseline.assess_writing("es", "Spanish",
                                                "Estoy de acuerdo con la idea")
            )

    def test_a_rejected_schema_retries_as_plain_json(self):
        import anthropic
        calls = []

        async def create(**kwargs):
            calls.append(kwargs)
            if "output_config" in kwargs:
                raise anthropic.BadRequestError(
                    message="output_config is not supported on this model",
                    response=SimpleNamespace(status_code=400,
                                             headers={},
                                             request=None),
                    body=None,
                )
            return SimpleNamespace(
                content=[SimpleNamespace(
                    type="text",
                    text='{"level": "B1", "notes": "Solid clauses.",'
                         ' "focus": ["past tense"]}',
                )],
                usage=None,
            )

        result, _ = self._run(create)
        assert result["level"] == "B1"
        assert result["focus"] == ["past tense"]
        # Exactly two calls: the schema attempt, then the plain retry —
        # and the retry carries no output_config and asks for bare JSON.
        assert len(calls) == 2
        assert "output_config" not in calls[1]
        assert "ONLY a JSON object" in calls[1]["system"]

    def test_a_fenced_plain_reply_still_parses(self):
        """Models fence JSON despite instructions; a fence must cost
        nothing, not the assessment."""
        async def create(**kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(
                    type="text",
                    text='```json\n{"level": "B2", "notes": "ok",'
                         ' "focus": []}\n```',
                )],
                usage=None,
            )

        result, _ = self._run(create)
        assert result["level"] == "B2"
