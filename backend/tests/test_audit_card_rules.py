"""The two card-level audit rules, `unclozable_rows` and `frame_collision`.

Both were designed from defects the owner met on real cards and both are
report-level: they measure supply and ambiguity, which move with editorial
work rather than with a bug, so a threshold on either would be a number
nobody could set honestly (CHECKS §28, §29).
"""

import csv

from backend.services.quality import audit_content as ac


def _bank(tmp_path, monkeypatch, code, rows, ranks):
    """Write a throwaway frequency list and sentence bank for *code*."""
    with (tmp_path / f"{code}_frequency.tsv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["rank", "word", "pos", "en"])
        for word, rank in ranks.items():
            w.writerow([rank, word, "noun", f"the {word}"])
    with (tmp_path / f"{code}_sentences.tsv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["word", "sentence", "translation", "difficulty_rank"])
        for word, sentence in rows:
            w.writerow([word, sentence, "", ranks.get(word, 1)])
    monkeypatch.setattr(ac, "DATA", tmp_path)


class TestUnclozableRows:
    """A word whose every sentence the card cannot blank serves a
    definition-only prompt, and nothing said so — 93% of Thai, 54% of Korean
    and 47% of Arabic rows were in that state with every coverage table
    counting them as coverage (CHECKS §29)."""

    def test_a_word_whose_rows_cannot_be_blanked_is_reported(self, tmp_path, monkeypatch):
        _bank(tmp_path, monkeypatch, "xx",
              [("run", "She was running to the shop."),
               ("run", "He runs every morning.")],
              {"run": 12})
        unclozable, _ = ac._audit_sentence_cards("xx")
        assert len(unclozable) == 1
        assert "'run'" in unclozable[0] and "rank 12" in unclozable[0]

    def test_a_word_with_one_usable_row_is_not_reported(self, tmp_path, monkeypatch):
        _bank(tmp_path, monkeypatch, "xx",
              [("run", "She was running to the shop."),
               ("run", "I run to the shop every morning.")],
              {"run": 12})
        unclozable, _ = ac._audit_sentence_cards("xx")
        assert unclozable == []

    def test_it_is_scoped_to_the_band_a_learner_reaches(self, tmp_path, monkeypatch):
        """A defect on rank 9,000 is real and nobody meets it."""
        _bank(tmp_path, monkeypatch, "xx",
              [("obscurity", "He was running.")],
              {"obscurity": 9000})
        unclozable, _ = ac._audit_sentence_cards("xx")
        assert unclozable == []


class TestFrameCollision:
    """One blanked sentence with several answers is the corpus proving its own
    prompt does not determine an answer — the mechanical half of §28."""

    def test_two_words_sharing_a_prompt_are_reported(self, tmp_path, monkeypatch):
        _bank(tmp_path, monkeypatch, "xx",
              [("happy", "I am happy."), ("tired", "I am tired.")],
              {"happy": 30, "tired": 31})
        _, collisions = ac._audit_sentence_cards("xx")
        assert len(collisions) == 1
        assert "2 answers share one prompt" in collisions[0]

    def test_one_word_in_two_sentences_is_not_a_collision(self, tmp_path, monkeypatch):
        _bank(tmp_path, monkeypatch, "xx",
              [("happy", "I am happy."), ("happy", "She is happy.")],
              {"happy": 30})
        _, collisions = ac._audit_sentence_cards("xx")
        assert collisions == []

    def test_a_row_the_card_cannot_blank_cannot_collide(self, tmp_path, monkeypatch):
        """Only rows a learner can actually be shown count — otherwise the
        rule reports ambiguity between two cards nobody ever sees."""
        _bank(tmp_path, monkeypatch, "xx",
              [("happy", "I am happy."), ("tire", "I am tired.")],
              {"happy": 30, "tire": 31})
        _, collisions = ac._audit_sentence_cards("xx")
        assert collisions == []


class TestBothRulesAreWiredIn:
    def test_they_are_report_level_not_scored(self):
        """They measure editorial supply, not a bug, so they must never gate
        CI — the `gender_marking` argument."""
        assert "unclozable_rows" in ac.REPORT_RULES
        assert "frame_collision" in ac.REPORT_RULES
        assert "unclozable_rows" not in ac.FAIL_RULES
        assert "frame_collision" not in ac.FAIL_RULES

    def test_a_missing_bank_is_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ac, "DATA", tmp_path)
        assert ac._audit_sentence_cards("nope") == ([], [])
