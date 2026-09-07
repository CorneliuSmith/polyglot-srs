"""The gate that writes authored sentences into the committed banks.

It had no tests, and it shipped the defect that matters most: it verified
LEMMA presence, so a Russian sentence carrying `парня` satisfied the headword
`парень` and was written. The card blanks the SURFACE form (`make_cloze`), so
those rows are skipped at draw time and the learner gets the definition-only
fallback instead — 6,517 rows were written under that rule on 31 Aug
(CHECKS §29, quality rules 40 and 46).
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.apply_authored_sentences import (  # noqa: E402
    MAX_WORDS,
    MIN_WORDS,
    clozable,
    sentence_length,
    tokens,
)


class TestPresenceIsTheSurfaceForm:
    """The only presence test that counts is the one the card runs."""

    def test_the_surface_form_is_accepted(self):
        assert clozable(
            "парень", "Этот парень живёт рядом с нами уже три года.", "ru")

    def test_an_inflection_alone_is_refused(self):
        """`парня` is the same word and the card cannot blank it. This is the
        31 Aug rule, and the reason that pass produced dead rows."""
        assert not clozable(
            "парень", "Я видел парня возле магазина сегодня утром.", "ru")

    def test_every_language_is_checked_not_only_russian(self):
        """MORPH_LANGS was {"ru"}, so no other course had a presence check at
        all — a Spanish sentence missing its word was written without a word."""
        assert clozable("gato", "El gato duerme en la ventana toda la tarde.", "es")
        assert not clozable(
            "perro", "El gato duerme en la ventana toda la tarde.", "es")

    def test_a_word_absent_entirely_is_refused(self):
        assert not clozable("dog", "The cat sleeps by the window.", "en")


class TestUnspacedScriptsCanBeAuthoredAtAll:
    """Thai writes without spaces, so a whitespace count made every Thai
    sentence one word long and the 7-14 bar rejected the whole language
    (CHECKS §22). Length is a count of segments there."""

    def test_length_counts_segments_not_whitespace(self):
        thai = "ฉันไปตลาดกับแม่เมื่อวานนี้"
        assert len(tokens(thai)) == 1
        assert sentence_length(thai, "th") > 1

    def test_a_real_thai_sentence_can_pass_the_bar(self):
        """From the committed bank, and it segments cleanly:
        พวก · นี้ · เป็น · ของ · คุณ · หรือ · ไม่. 854 Thai sentences (27%)
        sit in the band, so the §23 bar is reachable for the language rather
        than only in principle."""
        thai = "พวกนี้เป็นของคุณหรือไม่?"
        assert MIN_WORDS <= sentence_length(thai, "th") <= MAX_WORDS

    def test_an_unparseable_run_does_not_inflate_the_count(self):
        """Greedy longest-match returns each character it cannot place as its
        own chunk. `ทอมเป็นลูกบุญธรรม` is three words plus a name the lexicon
        does not know; counting every chunk called it nine and would have let
        it through the bar as a scene."""
        assert sentence_length("ทอมเป็นลูกบุญธรรม", "th") < MIN_WORDS

    def test_thai_presence_goes_through_the_segmenter(self):
        assert clozable("ตลาด", "ฉันไปตลาดกับแม่เมื่อวานนี้", "th")

    def test_a_spaced_language_still_counts_words(self):
        assert sentence_length("The cat sleeps by the window all afternoon.", "en") == 8
