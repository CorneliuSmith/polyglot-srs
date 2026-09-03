"""One rules module for the generators (docs/plans/owner-notes-2026-09-03.md,
item 4): the maker writes to the bar the auditor judges by, and the makers
get the per-language brief the semantic reviewer always had."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from backend.services import generate, quality_rules


def test_maker_and_auditor_quote_the_same_bar():
    # Two independently worded descriptions of one CEFR bar is how a
    # sentence passes the maker and fails the auditor with nobody able to
    # say which was right. Both rules must carry the identical sentence.
    for level in ("A1", "A2", "B1", "B2", "C1"):
        bar = quality_rules.level_bar(level)
        assert bar
        assert bar in quality_rules.maker_complexity_rule(level)
        assert bar in quality_rules.auditor_level_rule(level)
    assert quality_rules.maker_complexity_rule(None) == ""
    assert quality_rules.auditor_level_rule("") == ""


def test_the_language_brief_is_the_tutors_skill_file():
    brief = quality_rules.language_brief("es")
    assert brief.startswith("\n\nLanguage brief:\n")
    # Spanish's brief talks about register; a random string would not.
    assert "usted" in brief or "Register" in brief
    assert quality_rules.language_brief(None) == ""
    assert quality_rules.language_brief("zz-not-a-language") == ""


class _Recorder:
    """A stand-in for AsyncAnthropic that keeps the system prompt it was
    asked for and answers with an empty, well-formed batch."""
    calls: list[dict] = []

    def __init__(self, **kw):
        pass

    class messages:  # noqa: N801 — mirrors the SDK's attribute
        @staticmethod
        async def create(**kw):
            _Recorder.calls.append(kw)
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text='{"drills": [], "examples": []}')],
                usage=SimpleNamespace(input_tokens=1, output_tokens=1),
            )


async def test_the_makers_carry_the_brief_and_the_bar():
    _Recorder.calls.clear()
    settings = SimpleNamespace(tutor_dev_mock=False, anthropic_api_key="k",
                               tutor_model="m", tutor_model_low_resource="m",
                               tutor_summary_model="m")
    with patch("backend.services.generate.get_settings", return_value=settings), \
         patch("backend.services.models.get_settings", return_value=settings), \
         patch("backend.services.generate.AsyncAnthropic", _Recorder):
        await generate.make_drills(
            {"title": "Ser vs estar", "level": "B1"}, 3, "Spanish",
            language_code="es",
        )
        await generate.make_examples(
            {"word": "gato", "level": "A1"}, 3, "Spanish", "es",
        )
    drill_system, example_system = (c["system"] for c in _Recorder.calls)
    for system in (drill_system, example_system):
        assert "Language brief:" in system
        assert quality_rules.DIVERSITY_RULES in system
    assert quality_rules.level_bar("B1") in drill_system
    assert quality_rules.level_bar("A1") in example_system
