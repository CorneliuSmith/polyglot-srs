"""An alphabet card is a production drill, so it never draws a sentence.

The owner asked whether the alphabet decks' sentences had been fixed. They
had not. Ten rows hung off four Russian letter cards in production, and every
one had matched the character somewhere it was not a word:

    й   "У меня есть несколько билетов в 15-й ряд."   an ordinal suffix
    х   "Я буду занят до 4-х."                        a numeral ending
    н   "Рим был основан в 753 году до н.э."          inside an abbreviation
    н   "Г-н Молодой стар."                           inside an abbreviation
    ё   "Ах ты ж ё!"  ->  "Oh sod."                   crude, on an A0 card

`_vocab_card` preferred a cloze sentence for every vocabulary row, so the
alphabet card — whose whole design is "here is the sound, type the letter"
(`seed_alphabet`: the romanisation doubles as the keystrokes) — was showing a
blanked sentence instead of its prompt.

A letter has nothing to exemplify. Both halves are pinned here: the card
refuses the sentence, and the prune removes the rows, the latter WITHOUT the
never-strand protection, because that rule protects a word from losing its
last example and a letter is not a word.
"""
from __future__ import annotations

import inspect

from backend.repositories import cards
from backend.services.seeder import prune_sentences


class TestTheCardRefusesTheSentence:
    def test_a_letter_row_draws_no_sentence(self):
        src = inspect.getsource(cards._vocab_card)
        assert '"letter"' in src and "example_sentences" in src, (
            "_vocab_card no longer special-cases the alphabet deck — a letter "
            "card will serve a cloze sentence again"
        )
        # the guard must sit on the sentence list itself, not on a later branch:
        # everything downstream (cloze, transliteration, phonetics) reads from it
        assert 'sentences = [] if r["part_of_speech"] == "letter"' in src

    def test_an_ordinary_row_still_prefers_its_sentence(self):
        src = inspect.getsource(cards._vocab_card)
        assert 'r["example_sentences"] or []' in src, (
            "the fallback for non-letter rows was lost"
        )


class TestThePruneRemovesThem:
    def test_is_letter_row_reads_the_part_of_speech(self):
        assert prune_sentences.is_letter_row({"part_of_speech": "letter"})
        assert not prune_sentences.is_letter_row({"part_of_speech": "noun"})
        assert not prune_sentences.is_letter_row({"part_of_speech": None})
        assert not prune_sentences.is_letter_row({})

    def test_the_survey_selects_the_column_it_judges_on(self):
        """A predicate reading a column the query does not fetch is a silent
        no-op — it would return False for every row and delete nothing."""
        src = inspect.getsource(prune_sentences.survey)
        assert "v.part_of_speech" in src

    def test_letter_rows_skip_the_never_strand_rule(self):
        """The ONLY prunable shape that is allowed to empty its card.

        Every other candidate goes through `kept_empty`, which refuses to
        leave a word with no example (CHECKS §24) — that is why 14 rows about
        Tatoeba survive today (§35). A letter is not a word, and its card
        never asks for a sentence, so stranding is the intended outcome.
        """
        src = inspect.getsource(prune_sentences.survey)
        letters_at = src.index("letter_rows = [")
        grouping_at = src.index("by_word")
        assert letters_at < grouping_at, (
            "alphabet rows must be lifted out BEFORE the per-word grouping, or "
            "the never-strand rule will protect them"
        )
        assert "delete.extend(letter_rows)" in src
