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
    maqsura ى, and phone keyboards offer ي far more readily.

    That used to grade fully CORRECT. It is now amber (20 Aug 2026): in MSA,
    the variety this course teaches, word-final ى is /aː/ and ي is /iː/ —
    different sounds, and 84 cards were merged onto other cards by folding
    them, rank 8 على "on" with rank 144 علي "to be exalted" among them. The
    green ruling rested on Egyptian convention, which ar.md puts explicitly
    out of scope. The learner still passes; the proper form is now named.
    """

    def test_yeh_typed_for_alef_maqsura_is_coached(self):
        result, msg = get_nlp("ar").check_answer("إلي", "إلى")
        assert result is AnswerResult.CORRECT_SLOPPY
        assert "إلى" in (msg or "")

    def test_farsi_yeh_from_a_persian_keyboard_is_coached(self):
        result, _ = get_nlp("ar").check_answer("إلی", "إلى")
        assert result is AnswerResult.CORRECT_SLOPPY

    def test_a_yeh_slip_that_lands_on_another_card_is_wrong_form(self):
        """The whole point of amber over green: على and علي are two words."""
        result, msg = get_nlp("ar").check_answer("علي", "على")
        assert result is AnswerResult.WRONG_FORM
        assert "different word" in (msg or "")

    def test_hamza_over_or_under_alif_is_fully_correct(self):
        # The alphabet card is bare ا; a phone's long-press row offers أ/إ.
        for typed in ("أ", "إ", "آ"):
            result, _ = get_nlp("ar").check_answer(typed, "ا")
            assert result is AnswerResult.CORRECT, typed

    def test_exact_answer_still_grades_clean(self):
        assert get_nlp("ar").check_answer("إلى", "إلى")[0] is AnswerResult.CORRECT

    def test_a_different_word_is_still_wrong(self):
        # The fold must not turn "unrelated word" into "close enough".
        result, _ = get_nlp("ar").check_answer("كتاب", "إلى")
        assert result is AnswerResult.WRONG


class TestArabicDroppedHamza:
    """سماء typed as سما: the standalone word-final hamza is the single
    most-omitted letter — accepted amber, with the real spelling named."""

    @pytest.mark.parametrize("user,correct", [("سما", "سماء"), ("شي", "شيء")])
    def test_omitted_final_hamza_is_coached_not_failed(self, user, correct):
        result, msg = get_nlp("ar").check_answer(user, correct)
        assert result is AnswerResult.CORRECT_SLOPPY
        assert correct in msg

    def test_hamza_omission_does_not_merge_different_words(self):
        result, _ = get_nlp("ar").check_answer("قال", "سماء")
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


class TestKoreanJamoEncodings:
    """The alphabet deck stores compatibility jamo (ㄱ, U+3131); a system
    IME mid-composition and the on-screen keyboard emit conjoining jamo
    (ᄀ, U+1100). Same letter, different codepoint, and the single-letter
    cards were graded by which keyboard the learner touched."""

    def test_conjoining_jamo_matches_the_compat_card(self):
        result, _ = get_nlp("ko").check_answer("ᄀ", "ㄱ")
        assert result is AnswerResult.CORRECT

    def test_conjoining_vowel_matches_the_compat_card(self):
        result, _ = get_nlp("ko").check_answer("ᅡ", "ㅏ")
        assert result is AnswerResult.CORRECT

    def test_uncomposed_jamo_sequence_matches_the_syllable(self):
        result, _ = get_nlp("ko").check_answer("ㄱㅏ", "가")
        assert result is AnswerResult.CORRECT

    def test_a_different_letter_is_still_wrong(self):
        result, _ = get_nlp("ko").check_answer("ㄴ", "ㄱ")
        assert result is AnswerResult.WRONG


class TestKoreanBatchimCoaching:
    """밥 typed as 바: single-syllable answers are too short for the generic
    near-miss hint, so the learner was told nothing about the one part of
    the block beginners actually miss — the final consonant."""

    @pytest.mark.parametrize("user,correct", [("바", "밥"), ("갑", "감"), ("하교", "학교")])
    def test_batchim_only_miss_names_the_batchim(self, user, correct):
        result, msg = get_nlp("ko").check_answer(user, correct)
        assert result is AnswerResult.WRONG
        assert "받침" in msg and correct in msg

    def test_a_different_vowel_is_not_called_a_batchim_miss(self):
        _, msg = get_nlp("ko").check_answer("법", "밥")
        assert msg is None or "받침" not in msg


class TestGreekFinalSigma:
    """ς is the word-final POSITION of σ, not a different letter — and the
    seed deck's own definition says so while the grader failed it."""

    def test_final_sigma_matches_the_sigma_card_both_ways(self):
        assert get_nlp("el").check_answer("ς", "σ")[0] is AnswerResult.CORRECT
        assert get_nlp("el").check_answer("σ", "ς")[0] is AnswerResult.CORRECT

    def test_word_typed_with_non_final_sigma_is_correct(self):
        result, _ = get_nlp("el").check_answer("τέλοσ", "τέλος")
        assert result is AnswerResult.CORRECT

    def test_a_different_letter_is_still_wrong(self):
        assert get_nlp("el").check_answer("π", "σ")[0] is AnswerResult.WRONG


class TestHebrewFinalForms:
    def test_non_final_form_at_word_end_is_coached(self):
        # שלום typed with an ordinary מ — accepted amber, proper form named.
        result, msg = get_nlp("he").check_answer("שלומ", "שלום")
        assert result is AnswerResult.CORRECT_SLOPPY
        assert "שלום" in msg

    def test_final_form_matches_its_letter_card(self):
        result, _ = get_nlp("he").check_answer("ם", "מ")
        assert result is AnswerResult.CORRECT_SLOPPY

    def test_a_different_letter_is_still_wrong(self):
        assert get_nlp("he").check_answer("ב", "מ")[0] is AnswerResult.WRONG


class TestBareMarksNeverFalseAccept:
    """Two DIFFERENT bare niqqud/harakat both strip to "" in the accent-fold
    layer and matched each other — a wrong answer graded almost-right."""

    def test_two_different_niqqud_marks_do_not_match(self):
        # patah U+05B7 vs hiriq U+05B4
        result, _ = get_nlp("he").check_answer("ַ", "ִ")
        assert result is AnswerResult.WRONG

    def test_a_bare_mark_never_matches_a_letter(self):
        result, _ = get_nlp("he").check_answer("ַ", "מ")
        assert result is AnswerResult.WRONG

    def test_niqqud_folding_still_works_on_real_words(self):
        result, _ = get_nlp("he").check_answer("בית", "בַּיִת")
        assert result is AnswerResult.CORRECT_SLOPPY
