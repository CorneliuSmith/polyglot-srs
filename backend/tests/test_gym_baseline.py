"""The standardized Gym baseline: "base (form; gloss)" — the target-language
word the learner works FROM (practice, not recall), the cell to produce, and
a native-language explanation of that cell where one exists."""
from __future__ import annotations

from backend.repositories.cards import _gym_baseline, _split_hint
from backend.services.cell_glosses import cell_gloss


class TestSplitHint:
    def test_legacy_lemma_person(self):
        assert _split_hint("preparar, tú") == ("preparar", "tú")

    def test_plain_english_infinitive(self):
        assert _split_hint("to live") == ("to live", "")

    def test_recipe_tail_stripped(self):
        assert _split_hint("to watch — add -es") == ("to watch", "")

    def test_empty(self):
        assert _split_hint(None) == ("", "")


class TestCellGloss:
    def test_language_pronouns(self):
        assert cell_gloss("es", "tú") == "you, singular"
        assert cell_gloss("es", "vosotros") == "you, plural (Spain)"
        assert cell_gloss("ro", "ele") == "they, feminine"
        assert cell_gloss("ru", "она") == "she"

    def test_universal_labels_any_language(self):
        assert cell_gloss("de", "1sg") == "I"
        assert cell_gloss("el", "m.pl") == "masculine plural"
        assert cell_gloss("xh", "3sg") == "he/she/it"

    def test_unexplainable_cells_get_no_gloss(self):
        # Articles/particles/suffix cells: never guess.
        assert cell_gloss("tr", "-de") is None
        assert cell_gloss("nl", "de") is None
        assert cell_gloss("es", "") is None


class TestGymBaseline:
    def test_users_exact_example(self):
        # "preparar (tú; you, singular)" — legacy "lemma, person" authoring.
        card = {"hint": "preparar, tú", "language_code": "es"}
        assert _gym_baseline(card) == "preparar (tú; you, singular)"

    def test_cell_wins_over_hint_tail(self):
        card = {"hint": "preparar, tú", "cell": "vosotros", "language_code": "es"}
        assert _gym_baseline(card) == "preparar (vosotros; you, plural (Spain))"

    def test_stored_lemma_beats_english_hint(self):
        # Practice, not recall: the target-language word leads even when the
        # authored hint is an English gloss.
        card = {
            "hint": "to prepare", "lemma": "preparar",
            "cell": "yo", "language_code": "es",
        }
        assert _gym_baseline(card) == "preparar (yo; I)"

    def test_unglossable_cell_renders_plain(self):
        card = {"lemma": "ev", "cell": "-de", "language_code": "tr"}
        assert _gym_baseline(card) == "ev (-de)"

    def test_english_course_recipe_standardized(self):
        # Recipe stripped; en cells need no gloss (they're already English).
        card = {
            "hint": "to watch — add -es", "cell": "he/she", "language_code": "en",
        }
        assert _gym_baseline(card) == "to watch (he/she)"

    def test_description_hint_passes_through(self):
        assert (
            _gym_baseline({"hint": "indefinite article", "language_code": "nl"})
            == "indefinite article"
        )

    def test_chart_word_fallback_with_glossed_cell(self):
        card = {"chart_word": "слушать", "cell": "она", "language_code": "ru"}
        assert _gym_baseline(card) == "слушать (она; she)"

    def test_totally_bare_card_is_blank(self):
        assert _gym_baseline({}) == ""
