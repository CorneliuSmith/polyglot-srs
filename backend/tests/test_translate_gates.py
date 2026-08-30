"""Mechanical gates on the translation pipeline (translate_checks.py).

A Spanish speaker learning English reads this pipeline's output on every
card: glosses, drill hints, translations, explanations, Gym labels. The
maker-checker grades meaning; these gates catch what a semantic grader has
already been caught missing — and they run in mock mode, so this file proves
them without a model (quality rule 15).
"""
from unittest.mock import patch

import pytest

from backend.services import translate as tr
from backend.services.translate_checks import (
    blanks_intact,
    gate,
    is_identity,
    leaks_answer,
    locale_punctuation_ok,
    safe_row,
)


class _MockSettings:
    anthropic_api_key = ""
    tutor_dev_mock = True


def _mock():
    def boom(*a, **k):
        raise AssertionError("no Anthropic client may be built in mock mode")
    return (patch.object(tr, "get_settings", return_value=_MockSettings()),
            patch.object(tr, "AsyncAnthropic", side_effect=boom))


class TestLeakGate:
    def test_a_hint_that_quotes_its_answer_is_a_leak(self):
        # Real row: the en drill hint 'be — bare'. The label charter
        # (correctly) copies quoted course-language material unchanged, so
        # every locale's rendering keeps the leak. The gate is what stops it.
        assert leaks_answer("be — forma base", "be")

    def test_folded_forms_leak_too(self):
        assert leaks_answer("la forma de buku-buku", "buku-buku")   # hyphen whole
        assert leaks_answer("uso del man-passive", "Man")           # hyphen part
        assert leaks_answer("con kutokata tamaa dentro", "kutokata tamaa")  # phrase

    def test_marks_that_python_w_drops_still_match(self):
        # रही is र+ह+ी where ी is category Mc: combining() == 0 AND \w drops
        # it, so token and answer disagree unless both fold to the skeleton.
        # The frontend guard had this bug for \p{L}; this is the same class.
        assert leaks_answer("toma रही aquí", "रही")

    def test_a_translation_of_the_meaning_is_not_a_leak(self):
        assert not leaks_answer("el modal formado de 'may'", "might")
        assert not leaks_answer("Diles que vengan.", "them")


class TestOtherGates:
    def test_identity_echo_is_refused(self):
        assert is_identity("Do you see?", "Do you see?")
        assert is_identity("Do you see?", "  do you see ")
        assert not is_identity("Do you see?", "¿Ves?")

    def test_cloze_blanks_must_survive(self):
        assert not blanks_intact("He {{answer}} be stuck.", "Él podría estar atascado.")
        assert blanks_intact("He {{answer}} be stuck.", "Él {{answer}} estar atascado.")
        assert not blanks_intact("gloss with ___ here", "glosa sin hueco")

    def test_spanish_needs_its_inverted_marks(self):
        assert not locale_punctuation_ok("es", "Ves?")
        assert locale_punctuation_ok("es", "¿Ves?")
        assert locale_punctuation_ok("es", "Claro.")
        assert locale_punctuation_ok("fr", "Tu vois ?")   # only mapped locales

    def test_gate_orders_and_reports(self):
        assert gate("be — bare", "be — forma base", answer="be") == "contains the answer"
        assert gate("Do you see?", "¿Ves?", locale="es") is None


class TestSafeRow:
    def test_negative_index_no_longer_misfiles(self):
        # rows[-1] used to file a rendering under the LAST drill silently —
        # the luna/stella class. Anything but an in-range int is dropped.
        rows = ["a", "b", "c"]
        assert safe_row(rows, -1) is None
        assert safe_row(rows, 3) is None
        assert safe_row(rows, True) is None
        assert safe_row(rows, "1") is None
        assert safe_row(rows, 1) == "b"


class TestGatesRunInsideThePipeline:
    """The mock maker echoes its source ('[Spanish] <text>'), which is exactly
    the shape of output the gates exist to catch — so mock mode exercises the
    real storage decision, not a stub of it."""

    @pytest.mark.asyncio
    async def test_a_leaking_hint_rendering_is_withheld(self):
        s, b = _mock()
        with s, b:
            res = await tr.generate_text_translations(
                "Spanish",
                [{"i": 0, "sentence": "warm-up"},           # mock rejects item 0
                 {"i": 1, "sentence": "be — bare", "answer": "be"}],
                kind="label", locale="es")
        row = next(r for r in res if r["i"] == 1)
        assert row["translation"] == ""
        assert row["verdict"] == "reject"
        assert row["note"] == "gate: contains the answer"

    @pytest.mark.asyncio
    async def test_a_question_without_inverted_marks_is_withheld(self):
        s, b = _mock()
        with s, b:
            res = await tr.generate_sentence_translations(
                "Spanish",
                [{"i": 0, "sentence": "warm-up"},
                 {"i": 1, "sentence": "Do you like it?"}],
                locale="es")
        row = next(r for r in res if r["i"] == 1)
        assert row["translation"] == ""
        assert row["note"] == "gate: missing inverted punctuation"

    @pytest.mark.asyncio
    async def test_a_clean_rendering_still_lands(self):
        s, b = _mock()
        with s, b:
            res = await tr.generate_sentence_translations(
                "Spanish",
                [{"i": 0, "sentence": "warm-up"},
                 {"i": 1, "sentence": "The dog barks."}],
                locale="es")
        row = next(r for r in res if r["i"] == 1)
        assert row["translation"] == "[Spanish] The dog barks."
        assert row["verdict"] == "ok"


def test_sentences_are_graded_by_their_own_charter():
    """Sentences were graded with the WORD-gloss charter — 'right part of
    speech' is meaningless for a sentence. The sentence charter must name the
    classes the program has been burned by: wrong language outright (the
    TRADUCCIÓN incident) and part-translation."""
    charter = tr.sentence_checker_system("Spanish")
    assert "wrong language" in charter
    assert "part-translated" in charter
    assert "part of speech" not in charter
