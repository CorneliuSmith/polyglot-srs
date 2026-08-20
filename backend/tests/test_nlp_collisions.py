"""The collision guard: a fold may excuse a mark, it may never launder a word.

Graders fold diacritics for typo tolerance. When the folded input is itself a
DIFFERENT course word, "Almost — check the accents" plus full credit schedules
the wrong card as known: typing `el` (the) against `él` (he) graded
CORRECT_SLOPPY. 1,098 contrastive pairs existed across 11 languages when the
guard was added (triage, 19-20 Aug 2026; docs/quality/CHECKS.md §3).

These tests instantiate backends directly and set language_code the way
init_nlp_backends does, so the guard loads each course's committed vocabulary.
"""
import csv
import unicodedata
from collections import Counter
from pathlib import Path

import pytest

from backend.services.nlp.base import AnswerResult
from backend.services.nlp.latin_base import (
    FrenchNLP,
    ItalianNLP,
    LatinNLP,
    RomanianNLP,
    SpanishNLP,
)
from backend.services.nlp.russian import RussianNLP

DATA = Path(__file__).resolve().parents[2] / "data"


def backend(cls, code):
    nlp = cls()
    nlp.language_code = code
    return nlp


# ── the guard fires: typed string is another course word ─────────────────────

class TestCollisionGuard:
    @pytest.mark.parametrize("cls,code,typed,card", [
        (SpanishNLP, "es", "el", "él"),        # the vs he
        (SpanishNLP, "es", "se", "sé"),        # reflexive vs I know
        (FrenchNLP, "fr", "a", "à"),           # has vs to
        (FrenchNLP, "fr", "la", "là"),         # the vs there
        (RussianNLP, "ru", "все", "всё"),      # all vs everything
        (LatinNLP, "la", "liber", "līber"),    # book vs free
        (LatinNLP, "la", "hic", "hīc"),        # this vs here
        (RomanianNLP, "ro", "sa", "să"),       # his vs subjunctive marker
    ])
    def test_typing_a_different_word_is_wrong_form(self, cls, code, typed, card):
        result, message = backend(cls, code).check_answer(typed, card)
        assert result is AnswerResult.WRONG_FORM
        assert "different word" in (message or "")

    @pytest.mark.parametrize("typed,card", [
        ("ان", "أن"),      # suffix vs "to, that" (rank 1)
        ("إن", "أن"),      # "if" vs "to, that"
        ("آن", "أن"),      # "time" vs "to, that"
        ("كأن", "كان"),    # "as if" vs "to be" (rank 4)
        ("هنأ", "هنا"),    # "to be wholesome" vs "here" (rank 21)
        ("آمر", "أمر"),    # "to ask advice of" vs "to order" (rank 33)
    ])
    def test_arabic_hamza_seats_are_guarded(self, typed, card):
        """The alef fold used to live inside ArabicNLP.normalize(), so these
        merged at layer 2 and graded full CORRECT — beneath every coaching
        layer and beneath this guard. rank 1 أن was the same card as إن and
        آن. The fold now runs in fold_lookalikes, where the guard can see it."""
        from backend.services.nlp.arabic import ArabicNLP

        result, message = backend(ArabicNLP, "ar").check_answer(typed, card)
        assert result is AnswerResult.WRONG_FORM
        assert "different word" in (message or "")

    def test_the_fold_level_guard_catches_marks_nfd_cannot_strip(self):
        """ro ș/ț have no combining decomposition, so the base layer never
        sees them fold together — only the AccentFolding fold does."""
        result, _ = backend(RomanianNLP, "ro").check_answer("si", "și")
        assert result is AnswerResult.WRONG_FORM


# ── the leniency survives where it is genuine typo tolerance ─────────────────

class TestLeniencySurvives:
    @pytest.mark.parametrize("cls,code,typed,card", [
        (SpanishNLP, "es", "corazon", "corazón"),
        (FrenchNLP, "fr", "deja", "déjà"),
        (LatinNLP, "la", "femina", "fēmina"),
        (ItalianNLP, "it", "citta", "città"),  # the junk `citta` row is gone
    ])
    def test_bare_form_that_is_not_a_word_stays_sloppy(self, cls, code, typed, card):
        result, _ = backend(cls, code).check_answer(typed, card)
        assert result is AnswerResult.CORRECT_SLOPPY

    @pytest.mark.parametrize("typed,card", [
        ("انا", "أنا"),   # bare alef for the hamza seat — a spelling slip
        ("شي", "شيء"),    # dropped final hamza
        ("سما", "سماء"),  # dropped final hamza
    ])
    def test_arabic_spelling_slips_are_still_coached(self, typed, card):
        """Dropping the hamza seat stays amber. This is the leniency the fold
        exists for, and moving it out of normalize() must not remove it."""
        from backend.services.nlp.arabic import ArabicNLP

        result, _ = backend(ArabicNLP, "ar").check_answer(typed, card)
        assert result is AnswerResult.CORRECT_SLOPPY

    @pytest.mark.parametrize("typed,card", [
        ("schoen", "schön"),    # the Duden substitution when no umlaut key
        ("fuer", "für"),
        ("gruen", "grün"),
        ("groesser", "größer"),
        ("strasse", "straße"),  # Swiss ss for ß
        ("gross", "groß"),
    ])
    def test_german_digraphs_are_coached_not_failed(self, typed, card):
        """A learner on an English keyboard has exactly one sanctioned way to
        write schön, and it is schoen. It used to grade WRONG — "a different
        word" — while `schon`, which IS a different word, was credited. The
        typing reality and the grading were the wrong way round."""
        from backend.services.nlp.latin_base import GermanNLP

        result, _ = backend(GermanNLP, "de").check_answer(typed, card)
        assert result is AnswerResult.CORRECT_SLOPPY

    @pytest.mark.parametrize("typed,card", [
        ("schon", "schön"),     # already vs beautiful
        ("musste", "müsste"),   # had to vs would have to
        ("ass", "aß"),          # ace vs ate
    ])
    def test_german_bare_vowel_for_umlaut_is_still_a_different_word(self, typed, card):
        """Dropping the umlaut entirely is not the sanctioned substitution —
        it lands on another word, and the guard must still say so."""
        from backend.services.nlp.latin_base import GermanNLP

        result, message = backend(GermanNLP, "de").check_answer(typed, card)
        assert result is AnswerResult.WRONG_FORM
        assert "different word" in (message or "")

    def test_exact_match_is_untouched(self):
        result, _ = backend(SpanishNLP, "es").check_answer("él", "él")
        assert result is AnswerResult.CORRECT

    def test_an_alternative_spelling_is_exempt(self):
        result, _ = backend(SpanishNLP, "es").check_answer(
            "el", "él", {"answer_alternatives": ["el"]}
        )
        assert result is AnswerResult.CORRECT_SLOPPY

    def test_a_vocalized_rendering_of_the_stored_word_stays_sloppy(self):
        """he stores vocabulary unvocalized; a card may still show niqqud.
        Typing the bare form IS the standard spelling of the same word — the
        guard requires BOTH forms to be course words before it calls
        different-word."""
        from backend.services.nlp.latin_base import HebrewNLP

        result, _ = backend(HebrewNLP, "he").check_answer("בית", "בַּיִת")
        assert result is AnswerResult.CORRECT_SLOPPY

    def test_a_drill_inflection_outside_the_vocabulary_stays_sloppy(self):
        """la drills conjugate: vēnit is no card's answer, so bare venit is
        sloppy (the guard cannot know it is a different tense — the hint
        carries that; see la.md on venit/vēnit)."""
        result, _ = backend(LatinNLP, "la").check_answer("venit", "vēnit")
        assert result is AnswerResult.CORRECT_SLOPPY

    def test_no_language_code_means_no_guard(self):
        """A bare instance (no registration) behaves exactly as before."""
        result, _ = SpanishNLP().check_answer("el", "él")
        assert result is AnswerResult.CORRECT_SLOPPY


# ── the ratchet: no course may grow this class silently ──────────────────────

def _strip_marks(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )


# Measured 20 Aug 2026 with each language's real backend, after the junk-twin
# repair. `ar` ROSE from 209 to 200-with-a-different-shape when the alef fold
# moved out of ArabicNLP.normalize(): أ decomposes under NFD, so pairs that
# used to merge at layer 2 (full CORRECT, invisible to everything) now merge
# at the strip-marks key instead — i.e. inside the guard's view. A rise here
# caused by moving a fold INTO the guard is the fix working; a rise caused by
# new data is the thing this ratchet is for. A rising number means new rows collide under the grader's own fold —
# fix the data or raise the ceiling deliberately, in this file, with a reason.
# The nonzero numbers are CONTRASTIVE pairs by and large (see CHECKS.md §3):
# they are why the guard exists, not debt the guard leaves.
SLOPPY_KEY_CEILINGS = {
    "ru": 39, "ar": 116, "en": 10, "sw": 0, "tr": 122, "yo": 112, "ha": 0,
    "xh": 0, "es": 230, "it": 54, "fr": 491, "de": 127, "ca": 122, "mi": 0,
    "ro": 491, "el": 114, "pt": 108, "hi": 145, "jam": 0, "nl": 7, "th": 193,
    "ko": 0, "la": 3, "id": 0, "tl": 0, "he": 0, "fa": 0,
}


class TestCollisionRatchet:
    def test_no_course_grows_grader_collisions(self):
        from backend.services import nlp as nlp_module

        nlp_module.init_nlp_backends()
        over = []
        for code, ceiling in SLOPPY_KEY_CEILINGS.items():
            path = DATA / f"{code}_frequency.tsv"
            nlp = nlp_module.NLP_BACKENDS.get(code)
            if nlp is None or not path.exists():
                continue
            with path.open(encoding="utf-8-sig", newline="") as handle:
                surfaces = [
                    nlp.normalize(row["word"])
                    for row in csv.DictReader(handle, delimiter="\t")
                    if (row.get("word") or "").strip()
                ]
            counts = Counter(_strip_marks(s) for s in surfaces)
            found = sum(v - 1 for v in counts.values() if v > 1)
            if found > ceiling:
                over.append(f"{code}: {found} > ceiling {ceiling}")
        assert not over, (
            "grader-collision ratchet: " + "; ".join(over)
            + " — new rows fold onto existing cards. Fix the data or raise "
            "the ceiling here deliberately."
        )
