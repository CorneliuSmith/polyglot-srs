"""Explicit content is opt-in.

The report: a learner met "whore" in their vocabulary. Nobody chose to teach
it — the frequency lists are built from subtitle and web corpora, and Spanish
*puta* is rank 505, inside the first thousand words a beginner sees.

These tests pin BOTH directions, because the failure modes are opposite and
both are bad. Missing a slur is the reported bug. Over-matching is worse in a
quieter way: a learner who turns this on to avoid slurs did not ask to lose
"rooster", and a silently-hidden ordinary word is neither visible nor
reportable.
"""
from __future__ import annotations

import pytest

from backend.services.content_filter import is_explicit


class TestCatchesWhatWasReported:
    @pytest.mark.parametrize(
        "gloss",
        [
            "whore, slut, prostitute",       # es: puta, rank 505
            "whore (female prostitute)",     # de: hure
            "brothel, whorehouse",           # es: burdel
            "whore, hooker",                 # es: socia
            "to whore",                      # de: huren
        ],
    )
    def test_the_glosses_from_the_shipped_frequency_lists(self, gloss):
        assert is_explicit(gloss)

    def test_a_crude_sentence_translation(self):
        # The corpus supplied this as an example sentence.
        assert is_explicit("Fucking whore.")

    def test_a_lexicographer_s_own_label_generalises(self):
        # Catching the LABEL works across every language in the catalogue
        # without enumerating each one's profanity.
        assert is_explicit("vulgar term of abuse")
        assert is_explicit("obscene, taboo word")


class TestDoesNotOverreach:
    @pytest.mark.parametrize(
        "gloss",
        [
            "assassin",            # contains "ass"
            "bass guitar",         # contains "ass"
            "classic",             # contains "ass"
            "shore, coastline",    # near "whore"
            "shirt",               # near "shit"
            "cocktail",            # near a term not in the list anyway
            "rooster, cock",       # deliberately NOT matched — see the module
            "hell, underworld",    # mild; breaks religious vocabulary
            "damn, curse",         # mild
            "penis (anatomy)",     # clinical, appears in biology vocabulary
            "vagina (anatomy)",     # ditto
        ],
    )
    def test_ordinary_words_survive(self, gloss):
        assert not is_explicit(gloss)

    def test_word_boundaries_are_real(self):
        # The Scunthorpe problem, stated as a test.
        assert not is_explicit("Scunthorpe")
        assert not is_explicit("Middlesex")

    def test_empty_and_missing_text_is_not_explicit(self):
        assert not is_explicit(None)
        assert not is_explicit("")
        assert not is_explicit(None, "", None)


class TestAnyFieldMarksTheRow:
    def test_a_clean_word_with_a_crude_example_is_caught(self):
        # *maldita* is just "damned" — the corpus attached "Fucking whore."
        # to it. Filtering the headword alone would have left that sentence
        # on a card the learner keeps.
        assert is_explicit("damned, cursed", "Fucking whore.")

    def test_all_clean_fields_stay_clean(self):
        assert not is_explicit("damned, cursed", "A damned nuisance.")
