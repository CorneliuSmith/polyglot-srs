"""The gate that stands between an agent's gloss and a learner's card.

Every rule here rejected something real during this session's authoring runs,
or would have if it had existed earlier.
"""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "apply_drill_glosses", REPO / "scripts" / "apply_drill_glosses.py")
adg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adg)


class TestCheck:
    def test_a_good_gloss_passes(self):
        assert adg.check("1SG · ___ · DEF · book", "I {{answer}} the book",
                         "read") is None

    def test_cell_count_must_equal_token_count(self):
        assert adg.check("1SG · ___ · DEF", "I {{answer}} the book",
                         "read") == "cell count != token count"

    def test_the_blank_must_sit_on_the_answer_token(self):
        assert adg.check("___ · read · DEF · book", "I {{answer}} the book",
                         "read") == "blank is not on the answer token"

    def test_a_gloss_may_not_contain_the_answer(self):
        """The support layer spelling out the word being tested — the class
        that has now shipped on romanisation, hints and glosses in turn."""
        assert adg.check("1SG · ___ · DEF · read", "I {{answer}} the book",
                         "read") == "gloss contains the answer"

    def test_the_leak_check_folds_marks_and_hyphens(self):
        # Devanagari mark that Python's \w drops; must still be caught
        assert adg.check("1SG · ___ · रही", "I {{answer}} x",
                         "रही") == "gloss contains the answer"
        # hyphen part
        assert adg.check("1SG · ___ · man-passive", "I {{answer}} x",
                         "Man") == "gloss contains the answer"

    def test_a_line_where_nothing_decomposes_is_refused(self):
        """English glossed into English, every cell echoing its token. The
        gloss is a decomposition; a pure echo teaches nothing."""
        assert adg.check("the · dog · ___ · today", "the dog {{answer}} today",
                         "barks") == "every cell echoes its token"

    def test_an_echo_line_is_fine_once_one_cell_decomposes(self):
        assert adg.check("DEF · dog · ___ · today", "the dog {{answer}} today",
                         "barks") is None


class TestHarvest:
    def test_it_reads_a_plain_key_to_gloss_map(self, tmp_path):
        p = tmp_path / "task.output"
        p.write_text('{"result": {"en:1:2": "a · ___ · b"}}', encoding="utf-8")
        assert adg.harvest([p]) == {"en:1:2": "a · ___ · b"}

    def test_checker_fixes_override_the_makers_gloss(self, tmp_path):
        """The journal carries both stages; the checker's correction is the
        one that must win, or the run's whole verification pass is discarded."""
        p = tmp_path / "journal.jsonl"
        p.write_text(
            '{"type":"result","result":{"glosses":[{"k":"en:0:0","gloss":"WRONG"}]}}\n'
            '{"type":"result","result":{"glosses":[],"fixes":'
            '[{"k":"en:0:0","gloss":"RIGHT","why":"x"}]}}\n', encoding="utf-8")
        assert adg.harvest([p]) == {"en:0:0": "RIGHT"}


def test_a_gloss_that_is_only_the_blank_says_nothing():
    """A one-token sentence ({{answer}}?) glossed as `___` passes every
    structural rule and conveys nothing. Two Korean drills reached the tree
    that way before test_gloss_layer caught them."""
    assert adg.check("___", "{{answer}}?", "네") == "the whole gloss is the blank"


def test_thai_is_segmented_not_split_on_whitespace():
    """Thai writes without spaces, so a whole sentence is ONE whitespace
    token and a correct three-cell gloss looks like a count error. 100
    correct Thai glosses were rejected that way before the gate learned to
    segment, which it does by borrowing the reading pipeline's own
    segmentation — the same one the learner sees under the sentence."""
    assert adg.tokenize("ผม{{answer}}ข้าว", "th") == ["phom", "{{answer}}", "khao"]
    assert adg.check("1SG.M · ___ · rice", "ผม{{answer}}ข้าว", "กิน", "th") is None


def test_spaced_languages_are_untouched_by_the_segmenter():
    assert adg.tokenize("Yo {{answer}} pan", "es") == ["Yo", "{{answer}}", "pan"]
    assert adg.check("1SG · ___ · bread", "Yo {{answer}} pan", "como", "es") is None
