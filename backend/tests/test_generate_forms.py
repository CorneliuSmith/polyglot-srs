"""Unit tests for the -k forms chart maker-checker (WP45 track 3). No API key
or DB: the maker runs in dev-mock, and the checker is pure. The checker's one
decisive gate is CONTAINMENT — the drill's answer is a known-true form of the
word, so a generated chart that doesn't contain it is provably wrong."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.services import generate
from backend.services.generate import check_chart, generate_chart, make_chart


def _mock_settings(**over):
    base = {"tutor_dev_mock": True, "anthropic_api_key": ""}
    base.update(over)
    return SimpleNamespace(**base)


def _chart(rows, title="Present"):
    return {
        "lemma": "morar",
        "part_of_speech": "verb",
        "usage_note": "",
        "charts": [{"title": title, "rows": rows}],
    }


class TestCheckChart:
    def test_accepts_a_chart_containing_the_answer(self):
        cand = _chart([["eu", "moro"], ["tu", "moras"]])
        accepted, reason = check_chart(cand, "moras")
        assert accepted is True
        assert reason == "ok"

    def test_stress_marks_do_not_defeat_containment(self):
        # Charts print stress the drills don't — same folding as the Gym.
        cand = _chart([["мы", "жи́ли"]])
        accepted, _ = check_chart(cand, "жили")
        assert accepted is True

    def test_rejects_a_chart_without_the_answer(self):
        cand = _chart([["eu", "moro"], ["ele", "mora"]])
        accepted, reason = check_chart(cand, "moramos")
        assert accepted is False
        assert "attested form" in reason

    @pytest.mark.parametrize("mutate,reason_contains", [
        (lambda c: c.update(lemma=""), "missing lemma"),
        (lambda c: c.update(lemma="two words"), "single word"),
        (lambda c: c.update(charts=[]), "no charts"),
        (lambda c: c["charts"][0].update(title=" "), "missing title"),
        (lambda c: c["charts"][0].update(rows=[]), "no rows"),
        (lambda c: c["charts"][0].update(rows=[["eu", "moras", "extra"]]),
         "malformed chart row"),
        (lambda c: c["charts"][0].update(rows=[["eu", ""]]),
         "malformed chart row"),
    ])
    def test_rejects_malformed_charts(self, mutate, reason_contains):
        cand = _chart([["tu", "moras"]])
        mutate(cand)
        accepted, reason = check_chart(cand, "moras")
        assert accepted is False
        assert reason_contains in reason

    def test_rejects_oversized_responses(self):
        many_charts = _chart([["tu", "moras"]])
        many_charts["charts"] = many_charts["charts"] * 13
        assert check_chart(many_charts, "moras")[0] is False

        many_rows = _chart([["x", "moras"]] * 41)
        assert check_chart(many_rows, "moras")[0] is False


class TestGenerateChartMock:
    async def test_mock_chart_contains_the_answer_and_passes(self):
        with patch("backend.services.generate.get_settings",
                   return_value=_mock_settings()):
            cand = await generate_chart(
                {"answer": "moras", "lemma": "morar"}, "Portuguese", "pt"
            )
        assert cand is not None
        assert cand["lemma"] == "morar"
        forms = [f for ch in cand["charts"] for _l, f in ch["rows"]]
        assert "moras" in forms

    async def test_mock_reject_path_returns_none(self):
        # The mock deliberately omits an answer containing 'bad' from its
        # chart, so the containment gate rejects it — the same convention the
        # other mocks in generate.py use to keep the reject path testable.
        with patch("backend.services.generate.get_settings",
                   return_value=_mock_settings()):
            cand = await generate_chart({"answer": "badform"}, "Portuguese", "pt")
        assert cand is None

    async def test_mock_without_lemma_derives_one(self):
        with patch("backend.services.generate.get_settings",
                   return_value=_mock_settings()):
            made = await make_chart({"answer": "moras"}, "Portuguese")
        assert made["lemma"]
        assert generate.check_chart(made, "moras")[0] is True
