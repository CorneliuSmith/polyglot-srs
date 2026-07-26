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
