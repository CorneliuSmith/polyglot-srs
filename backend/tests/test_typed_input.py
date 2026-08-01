"""What a phone keyboard produces must grade the same as what a clipboard does.

Every case here is a real answer that was rejected when typed and accepted
when pasted — the learner sees identical text on screen either way, so a
rejection reads as the app being broken rather than as anything they did.

Two mechanisms, deliberately graded differently:

  * **Invisible characters** (ZWNJ, bidi marks) — nothing is rendered, so
    there is nothing a learner could have noticed or learned. Stripped from
    both sides, graded CORRECT.
  * **Look-alike letters** (ى/ي, ک/ك) — genuinely different letters that
    render near-identically. Accepted, but graded CORRECT_SLOPPY so the
    feedback still names the right spelling.
"""
from __future__ import annotations

import pytest

from backend.services.nlp import get_nlp, init_nlp_backends
from backend.services.nlp.base import AnswerResult

ZWNJ = "‌"
RLM = "‏"


@pytest.fixture(scope="module", autouse=True)
def _backends():
    init_nlp_backends()


class TestArabicLookalikes:
    """إلى — one of the commonest prepositions in Arabic — ends in alef
    maqsura ى, and phone keyboards offer ي far more readily."""

    def test_yeh_typed_for_alef_maqsura_is_accepted(self):
        result, msg = get_nlp("ar").check_answer("إلي", "إلى")
        assert result is AnswerResult.CORRECT_SLOPPY
        assert "إلى" in msg

    def test_farsi_yeh_from_a_persian_keyboard_is_accepted(self):
        result, _ = get_nlp("ar").check_answer("إلی", "إلى")
        assert result is AnswerResult.CORRECT_SLOPPY

    def test_exact_answer_still_grades_clean(self):
        assert get_nlp("ar").check_answer("إلى", "إلى")[0] is AnswerResult.CORRECT

    def test_a_different_word_is_still_wrong(self):
        # The fold must not turn "unrelated word" into "close enough".
        result, _ = get_nlp("ar").check_answer("كتاب", "إلى")
        assert result is AnswerResult.WRONG


class TestPersianKeyboardMismatch:
    """iOS ships an Arabic keyboard and not a Persian one by default, so
    learners type Arabic kaf/yeh into every Persian word containing them."""

    def test_arabic_kaf_for_persian_keheh(self):
        result, _ = get_nlp("fa").check_answer("كتاب", "کتاب")
        assert result is AnswerResult.CORRECT_SLOPPY

    def test_arabic_yeh_for_persian_yeh(self):
        result, _ = get_nlp("fa").check_answer("مي", "می")
        assert result is AnswerResult.CORRECT_SLOPPY

    @pytest.mark.parametrize(
        "user,correct",
        [
            ("میروم", f"می{ZWNJ}روم"),  # learner omitted the invisible joiner
            (f"می{ZWNJ}روم", "میروم"),  # ...or the stored answer omits it
        ],
    )
    def test_zwnj_never_decides_a_grade(self, user, correct):
        # Fully correct, not merely tolerated: nothing was rendered
        # differently, so there is nothing to coach.
        result, _ = get_nlp("fa").check_answer(user, correct)
        assert result is AnswerResult.CORRECT


class TestInvisibleCharactersAreLanguageAgnostic:
    def test_bidi_mark_from_an_rtl_clipboard(self):
        result, _ = get_nlp("he").check_answer(f"{RLM}שלום", "שלום")
        assert result is AnswerResult.CORRECT

    def test_soft_hyphen_does_not_fail_a_latin_answer(self):
        result, _ = get_nlp("es").check_answer("li­bro", "libro")
        assert result is AnswerResult.CORRECT


class TestEveryRejectionExplainsItself:
    """"It just says wrong" — the card the learner most needs the answer to
    was the one place we withheld it."""

    def test_a_wrong_answer_names_the_expected_one(self):
        result, msg = get_nlp("es").check_answer("zzzzz", "libro")
        assert result is AnswerResult.WRONG
        assert msg and "libro" in msg

    def test_an_empty_answer_says_so(self):
        result, msg = get_nlp("es").check_answer("   ", "libro")
        assert result is AnswerResult.WRONG
        assert msg and "libro" in msg

    def test_no_rejection_is_ever_silent(self):
        for user, correct in [
            ("zzzzz", "libro"),
            ("", "libro"),
            ("casa", "libro"),
            ("librx", "libro"),
        ]:
            _, msg = get_nlp("es").check_answer(user, correct)
            assert msg, f"no feedback for {user!r} vs {correct!r}"
