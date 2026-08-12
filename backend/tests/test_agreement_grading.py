"""Two ways the grader was handing out full marks for a wrong answer.

Both were found by reading the content against the standards in
docs/quality/, and both are the same shape: a normalization step that
exists to be lenient about something OPTIONAL was also erasing the
contrast a drill existed to teach.

  * Leading articles are stripped so "libro" passes for "el libro" —
    fine. But it stripped just as happily when the learner typed a
    DIFFERENT article, so "la libro" graded fully CORRECT and every
    gendered Latin-script course silently accepted the wrong gender on
    every noun. Reported against Catalan; it was all ten of them.

  * Arabic normalize() dediacritizes, which is right for vocabulary
    (NLP-07: an answer never fails purely on tashkeel). On a grammar
    drill it accepted the ACTIVE ولد for the passive وُلد — inside a
    point whose own explanation says the passive changes the verb's
    vowels and not its letters.
"""
from __future__ import annotations

import pytest

from backend.services.nlp import get_nlp, init_nlp_backends
from backend.services.nlp.base import AnswerResult

GRAMMAR = {"card_type": "grammar"}
VOCAB = {"card_type": "vocabulary"}


@pytest.fixture(scope="module", autouse=True)
def _backends():
    init_nlp_backends()


class TestArticleAgreement:
    """The article carries the gender. Getting it wrong is not a typo."""

    @pytest.mark.parametrize(
        "code,user,correct",
        [
            ("ca", "la te", "el te"),           # tea is masculine
            ("ca", "el casa", "la casa"),
            ("ca", "els cases", "les cases"),
            ("es", "la libro", "el libro"),
            ("es", "un mesa", "una mesa"),
            ("fr", "la livre", "le livre"),
            ("it", "la libro", "il libro"),
            ("pt", "a livro", "o livro"),
            ("de", "die Buch", "das Buch"),
            ("nl", "de boek", "het boek"),
        ],
    )
    def test_a_wrong_article_is_never_fully_correct(self, code, user, correct):
        result, message = get_nlp(code).check_answer(user, correct, VOCAB)
        assert result is AnswerResult.CORRECT_SLOPPY, f"{code}: {user!r}"
        assert correct in message

    def test_on_a_grammar_drill_the_article_is_the_answer(self):
        # The drill tests the article itself, so a lenient pass would be
        # marking the exact thing under test as right.
        result, message = get_nlp("ca").check_answer("el casa", "la casa", GRAMMAR)
        assert result is AnswerResult.WRONG_FORM
        assert "la casa" in message

    @pytest.mark.parametrize(
        "user,correct",
        [
            ("libro", "el libro"),   # omitted entirely — the leniency this exists for
            ("el libro", "libro"),
            ("el libro", "el libro"),
            ("casa", "la casa"),
        ],
    )
    def test_omitting_the_article_stays_free(self, user, correct):
        assert get_nlp("es").check_answer(user, correct, VOCAB)[0] is AnswerResult.CORRECT

    def test_an_accent_only_article_difference_is_not_a_gender_error(self):
        # The comparison folds diacritics, so a missing accent on the
        # article is graded by the accent layer, not called wrong gender.
        result, _ = get_nlp("el").check_answer("η μέρα", "η μέρα")
        assert result is AnswerResult.CORRECT

    def test_a_language_without_articles_is_untouched(self):
        # Latin and Russian strip nothing; the override must not invent a
        # rule for them.
        assert get_nlp("la").check_answer("puella", "puella")[0] is AnswerResult.CORRECT
        assert get_nlp("ru").check_answer("книга", "книга")[0] is AnswerResult.CORRECT


class TestArabicVocalizedAnswers:
    """When the author vocalized the answer, the vowels are the point."""

    @pytest.mark.parametrize(
        "user,correct,what",
        [
            ("أنت", "أنتِ", "masculine you for feminine you"),
            ("ولد", "وُلد", "active for passive"),
            ("اعلن", "أُعلن", "active for passive"),
            ("يدرس", "يدرّس", "Form I for Form II"),
            ("ماء", "ماءً", "accusative tanwin dropped"),
        ],
    )
    def test_a_bare_answer_to_a_vocalized_form_drill_is_wrong_form(
        self, user, correct, what
    ):
        result, message = get_nlp("ar").check_answer(user, correct, GRAMMAR)
        assert result is AnswerResult.WRONG_FORM, what
        assert correct in message

    def test_the_vocalized_answer_itself_still_grades_clean(self):
        assert get_nlp("ar").check_answer("وُلد", "وُلد", GRAMMAR)[0] is AnswerResult.CORRECT

    @pytest.mark.parametrize(
        "user,correct",
        [("كتاب", "كِتَاب"), ("مدرسة", "مَدْرَسَة")],
    )
    def test_vocabulary_keeps_diacritic_invariance(self, user, correct):
        # NLP-07 is unchanged: on a vocabulary card the marks are optional
        # decoration and an answer never fails on them.
        assert get_nlp("ar").check_answer(user, correct, VOCAB)[0] is AnswerResult.CORRECT
        assert get_nlp("ar").check_answer(user, correct)[0] is AnswerResult.CORRECT

    def test_an_unvocalized_grammar_answer_is_unaffected(self):
        # Most drills carry no tashkeel at all; they must not start failing.
        assert get_nlp("ar").check_answer("يكتب", "يكتب", GRAMMAR)[0] is AnswerResult.CORRECT

    def test_the_taa_marbuta_coaching_still_fires(self):
        result, _ = get_nlp("ar").check_answer("مدرسه", "مدرسة", VOCAB)
        assert result is AnswerResult.CORRECT_SLOPPY
