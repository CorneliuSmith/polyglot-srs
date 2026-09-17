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


def test_the_register_line_pins_arabic_to_msa_by_code_or_name():
    for key in ("ar", "Arabic", "arabic", "Modern Standard Arabic", "MSA"):
        line = quality_rules.register_line(key)
        assert line.startswith(" ") and "Modern Standard Arabic" in line, key
        assert "Egyptian" in line
    # Languages without a variety to pin get nothing appended — every
    # other course's prompt is byte-identical to before.
    for key in ("es", "Spanish", "English", "ru", "", None, "zz"):
        assert quality_rules.register_line(key) == "", key


_CALL_SITE_EXEMPT = {
    # Recommends films, music and podcasts: dialect media is the right answer.
    "backend/services/recommend.py",
    # Digests the tutor skill files themselves, in English.
    "backend/services/tutor_skill_digest.py",
}
_PINS = ("register_line(", "language_brief(", "_load_skill(", "build_system_blocks(")


def test_every_model_call_carries_the_register_pin():
    """Every `messages.create` in backend/services must build its system
    prompt with `register_line` (or the fuller brief), so a course whose
    language has a variety to pin — Arabic to MSA — is pinned at every
    call, not only at the tutor. A new call site fails here until it does
    (docs/plans/arabic-msa-local-llm.md, §1). The check is by function:
    the pin must appear between the enclosing `def` and the call."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    unpinned = []
    for path in sorted((root / "backend" / "services").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel in _CALL_SITE_EXEMPT:
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"messages\.(create|parse)\(", text):
            start = max(text.rfind("\ndef ", 0, m.start()), text.rfind("\nasync def ", 0, m.start()))
            nxt = re.search(r"\n(?:async )?def ", text[m.end():])
            end = m.end() + nxt.start() if nxt else len(text)
            # The enclosing function, from its def to the next one: the pin
            # is usually inside the call's system= argument.
            body = text[max(start, 0):end]
            # A call may declare itself out of scope inline, with a reason.
            if "register: n/a" in text[m.start():m.start() + 400] or "register: n/a" in text[max(0, m.start() - 400):m.start()]:
                continue
            # The system prompt may be built by a helper in the same file
            # (speak._system_prompt, reader._system_prompt, translate.*_system):
            # follow one hop to any `system=<name>(` helper defined here.
            pinned = any(p in body for p in _PINS)
            if not pinned:
                for helper in re.findall(r"system=\(?\s*([A-Za-z_][A-Za-z0-9_]*)\(", text[m.start():m.start() + 600]):
                    hm = re.search(rf"\n(?:async )?def {helper}\(.*?(?=\n(?:async )?def |\Z)", text, re.S)
                    if hm and any(p in hm.group(0) for p in _PINS):
                        pinned = True
                        break
            if not pinned:
                line = text.count("\n", 0, m.start()) + 1
                unpinned.append(f"{rel}:{line}")
    assert not unpinned, "model calls without a register pin: " + ", ".join(unpinned)
