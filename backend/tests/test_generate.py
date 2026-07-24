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


async def test_contains_word_surface_match_no_backend():
    # A language with no NLP backend (and no Apertium configured) still gets a
    # whole-word surface check.
    assert await generate._contains_word("es", "El gato duerme aquí.", "gato") is True
    assert await generate._contains_word("es", "No hay nada aquí.", "gato") is False
    # substring is NOT a match — must be a whole word
    assert await generate._contains_word("es", "El gatito duerme.", "gato") is False


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
    for p in passed:
        assert await generate._contains_word("es", p["sentence"], "gato")


# ---------------------------------------------------------------------------
# Quality audit of existing sentences + English descriptions (recheck)
# ---------------------------------------------------------------------------


async def test_make_examples_english_uses_description_gloss():
    # For English the translation slot carries a plain-English description, not
    # a redundant echo — the mock reflects that via the gloss wording.
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        en = await generate.make_examples({"word": "run"}, 3, "English", "en")
        es = await generate.make_examples({"word": "gato"}, 3, "Spanish", "es")
    assert any("simpler words" in c["translation"].lower() for c in en[1:])
    assert all("simpler words" not in c["translation"].lower() for c in es[1:])


async def test_audit_examples_flags_bad_and_backfills_missing():
    sentences = [
        {"sentence": "A perfectly fine sentence.", "translation": "Fine."},
        {"sentence": "This one is bad somehow.", "translation": ""},
        {"sentence": "Good but untranslated here.", "translation": ""},
    ]
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        verdicts = await generate.audit_examples(
            {"word": "x"}, sentences, "Spanish", "es"
        )
    assert [v["ok"] for v in verdicts] == [True, False, True]
    # A good-but-untranslated sentence gets a backfill translation (the caller
    # ignores whatever the judge returns for a flagged row, so only this matters).
    assert verdicts[2]["translation"].startswith("Translation:")


async def test_audit_examples_english_backfill_is_a_description():
    sentences = [{"sentence": "The dog runs fast today.", "translation": ""}]
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        verdicts = await generate.audit_examples(
            {"word": "run"}, sentences, "English", "en"
        )
    assert verdicts[0]["ok"] is True
    assert verdicts[0]["translation"].startswith("Description:")


async def test_audit_examples_empty_is_noop():
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        assert await generate.audit_examples({"word": "x"}, [], "English", "en") == []


async def test_audit_examples_flags_too_simple_sentences():
    # A 'simple' sentence is flagged on complexity even though it's grammatical.
    sentences = [
        {"sentence": "A rich, contextful sentence.", "translation": "Fine."},
        {"sentence": "This one is simple.", "translation": "x."},
    ]
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        verdicts = await generate.audit_examples(
            {"word": "x"}, sentences, "Spanish", "es"
        )
    assert verdicts[0]["ok"] is True
    assert verdicts[1]["ok"] is False
    assert "simple" in verdicts[1]["reason"].lower()


async def test_audit_examples_suggests_replacement_for_weak_translation():
    # A present-but-weak ('vague') translation is judged unhelpful and a clearer
    # replacement recommended, without the sentence itself being flagged.
    sentences = [{"sentence": "El gato duerme mucho.", "translation": "vague thing"}]
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        verdicts = await generate.audit_examples(
            {"word": "gato"}, sentences, "Spanish", "es"
        )
    assert verdicts[0]["ok"] is True
    assert verdicts[0]["translation_ok"] is False
    assert verdicts[0]["translation"].startswith("Clearer translation:")


async def test_audit_examples_good_translation_needs_no_suggestion():
    sentences = [{"sentence": "El gato duerme mucho.", "translation": "The cat sleeps a lot."}]
    with patch("backend.services.generate.get_settings", return_value=_mock_settings()):
        verdicts = await generate.audit_examples(
            {"word": "gato"}, sentences, "Spanish", "es"
        )
    assert verdicts[0]["translation_ok"] is True
    assert verdicts[0]["translation"] == ""


async def test_contains_word_uses_apertium_when_no_backend():
    # A backend-less language: an inflected form ('anakimbia' for lemma
    # 'kimbia') isn't a surface match, but Apertium rescues it.
    with patch("backend.services.generate.get_nlp", side_effect=ValueError), \
         patch("backend.services.generate.apertium_available", return_value=True), \
         patch("backend.services.generate.analyze_lemmas",
               new=AsyncMock(return_value={"kimbia", "mbwa"})):
        assert await generate._contains_word("sw", "Mbwa anakimbia leo.", "kimbia")
    # Apertium finds nothing useful -> the surface match still stands (fails).
    with patch("backend.services.generate.get_nlp", side_effect=ValueError), \
         patch("backend.services.generate.apertium_available", return_value=True), \
         patch("backend.services.generate.analyze_lemmas",
               new=AsyncMock(return_value=set())):
        assert not await generate._contains_word("sw", "Mbwa analala leo.", "kimbia")
