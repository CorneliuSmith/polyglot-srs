"""Unit tests for the maker-checker drill generator (Part C). No API key or
DB: the maker runs in dev-mock, and the checker's answerability gate is
patched so the deterministic guards are what's under test."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.services import generate


def _mock_settings(**over):
    base = {"tutor_dev_mock": True, "anthropic_api_key": ""}
    base.update(over)
    return SimpleNamespace(**base)


async def test_make_drills_returns_candidates_in_mock():
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        drills = await generate.make_drills({"title": "Present tense"}, 4, "Spanish")
    assert len(drills) == 4
    assert all("{{answer}}" in d["sentence"] for d in drills)


@pytest.mark.parametrize(
    "cand,ok,reason_contains",
    [
        ({"sentence": "Yo {{answer}} café.", "answer": "bebo", "hint": "to drink"}, True, "ok"),
        ({"sentence": "El gato {{answer}} gato.", "answer": "gato", "hint": "pet"}, False, "leak"),
        ({"sentence": "Yo {{answer}}.", "answer": "dos palabras", "hint": "x"}, False, "single token"),
        ({"sentence": "Yo {{answer}} café.", "answer": "bebo", "hint": "type bebo"}, False, "hint reveals"),
        ({"sentence": "no blank here", "answer": "", "hint": "x"}, False, "missing"),
    ],
)
async def test_check_drill_guards(cand, ok, reason_contains):
    # Answerability gate forced True so the deterministic guards are isolated.
    with patch("backend.services.generate.validate_drill", new=AsyncMock(return_value=True)):
        accepted, reason = await generate.check_drill("es", cand)
    assert accepted is ok
    assert reason_contains in reason


async def test_check_drill_respects_answerability_gate():
    cand = {"sentence": "Yo {{answer}} café.", "answer": "bebo", "hint": "to drink"}
    with patch("backend.services.generate.validate_drill", new=AsyncMock(return_value=False)):
        accepted, reason = await generate.check_drill("es", cand)
    assert accepted is False
    assert "answerability" in reason


async def test_generate_drills_drops_the_bad_candidate():
    # The mock's first candidate deliberately leaks its answer; generate_drills
    # must return only the ones that passed.
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()), \
         patch("backend.services.generate.validate_drill", new=AsyncMock(return_value=True)):
        passed = await generate.generate_drills(
            {"title": "Present tense"}, 4, "Spanish", "es"
        )
    assert len(passed) == 3  # 4 drafted, the leaking first one rejected
    assert all(p["accepted"] for p in passed)
    assert all(not generate._leaks(p["sentence"], p["answer"]) for p in passed)


# ---------------------------------------------------------------------------
# Vocabulary example generation (WP42)
# ---------------------------------------------------------------------------


async def test_make_examples_returns_candidates_in_mock():
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        made = await generate.make_examples({"word": "gato"}, 4, "Spanish")
    assert len(made) == 4
    assert all("sentence" in c and "translation" in c for c in made)


def test_contains_word_surface_match_no_backend():
    # A language with no NLP backend still gets a whole-word surface check.
    assert generate._contains_word("es", "El gato duerme aquí.", "gato") is True
    assert generate._contains_word("es", "No hay nada aquí.", "gato") is False
    # substring is NOT a match — must be a whole word
    assert generate._contains_word("es", "El gatito duerme.", "gato") is False


@pytest.mark.parametrize(
    "cand,ok,reason_contains",
    [
        ({"sentence": "El gato duerme.", "translation": "The cat sleeps."}, True, "ok"),
        ({"sentence": "El gato duerme.", "translation": ""}, False, "translation"),
        ({"sentence": "", "translation": "x"}, False, "missing sentence"),
        ({"sentence": "No aparece.", "translation": "Absent."}, False, "target word"),
        ({"sentence": "gato.", "translation": "cat"}, False, "length"),
    ],
)
async def test_check_example_guards(cand, ok, reason_contains):
    accepted, reason = await generate.check_example("es", cand, "gato")
    assert accepted is ok
    assert reason_contains in reason


async def test_generate_examples_drops_the_wordless_candidate():
    # The mock's first candidate omits the target word; generate_examples must
    # return only the ones that actually use it.
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        passed = await generate.generate_examples(
            {"word": "gato", "definition": "cat"}, 4, "Spanish", "es"
        )
    assert len(passed) == 3  # 4 drafted, the wordless first one rejected
    assert all(generate._contains_word("es", p["sentence"], "gato") for p in passed)
