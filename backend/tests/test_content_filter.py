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

from backend.services.content_filter import (
    is_explicit_gloss,
    is_explicit_sentence,
)


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
        assert is_explicit_gloss(gloss)

    def test_a_crude_sentence_translation(self):
        # The corpus supplied this as an example sentence.
        assert is_explicit_sentence("Fucking whore.")

    def test_a_lexicographer_s_own_label_generalises(self):
        # Catching the LABEL works across every language in the catalogue
        # without enumerating each one's profanity.
        assert is_explicit_gloss("vulgar term of abuse")
        assert is_explicit_gloss("obscene, taboo word")


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
        assert not is_explicit_gloss(gloss)

    def test_word_boundaries_are_real(self):
        # The Scunthorpe problem, stated as a test.
        assert not is_explicit_gloss("Scunthorpe")
        assert not is_explicit_gloss("Middlesex")

    def test_empty_and_missing_text_is_not_explicit(self):
        assert not is_explicit_gloss(None)
        assert not is_explicit_gloss("")
        assert not is_explicit_gloss(None, "", None)
        assert not is_explicit_sentence(None, "", None)


class TestAnyFieldMarksTheRow:
    def test_a_clean_word_with_a_crude_example_is_caught(self):
        # *maldita* is just "damned" — the corpus attached "Fucking whore."
        # to it. Filtering the headword alone would have left that sentence
        # on a card the learner keeps.
        assert is_explicit_sentence("Fucking whore.")
        assert not is_explicit_gloss("damned, cursed")

    def test_all_clean_fields_stay_clean(self):
        assert not is_explicit_gloss("damned, cursed")
        assert not is_explicit_sentence("A damned nuisance.")


class TestOnlyTheLeadingSenseDecides:
    """The correction to the first version of this filter.

    Matching anywhere in a gloss hid ordinary, high-frequency words over a
    register listed fourth. Dictionary glosses lead with the primary sense and
    push the rest behind a semicolon, so only the leading sense decides now.

    Every gloss below is real, from the shipped frequency lists, with its rank.
    """

    @pytest.mark.parametrize(
        "gloss,word",
        [
            ("cursed; damned, freaking, fucking", "es maldito (rank 583)"),
            ("filth, dirt; a vulgarity, expletive", "hi गंदगी (rank 471)"),
            ("comrade, colleague; A term of unspecific contempt for a man",
             "tr herif (rank 393)"),
            ("only used in avea habar (“have a clue”)", "ro habar (rank 1105)"),
            ("rude; impolite; vulgar", "th หยาบคาย (rank 1150)"),
        ],
    )
    def test_a_crude_secondary_sense_does_not_hide_an_ordinary_word(
        self, gloss, word
    ):
        assert not is_explicit_gloss(gloss), word

    def test_mild_is_taken_at_its_word(self):
        # "wow! (mild expletive)" — jam baxide, rank 361. The lexicographer
        # already said it is mild; the qualifier list must not override that.
        assert not is_explicit_gloss("wow! (mild expletive)")

    def test_a_leading_register_label_is_not_the_sense(self):
        # fr con, rank 911: "(dated) cunt, pussy". Treating the label as the
        # whole primary sense released a word nobody would call ordinary.
        assert is_explicit_gloss("(dated) cunt, pussy (the female genitalia)")

    @pytest.mark.parametrize(
        "gloss,word",
        [
            ("whore, slut, prostitute", "es puta (rank 505)"),
            ("dick, cock, prick", "it cazzo (rank 155)"),
            ("shit (solid excretory product evacuated from the bowels)",
             "es mierda (rank 210)"),
            ("whore, hooker; bitch, cow (an unpleasant woman)",
             "fr putain (rank 332)"),
            ("prostitute, whore", "ha karuwa (rank 362)"),
        ],
    )
    def test_a_word_whose_first_sense_is_explicit_stays_flagged(self, gloss, word):
        assert is_explicit_gloss(gloss), word

    def test_sentences_are_still_judged_whole(self):
        # A sentence has no "primary sense" — splitting one on its first
        # semicolon would let the second clause through.
        assert is_explicit_sentence("Nice weather today; fuck off.")
