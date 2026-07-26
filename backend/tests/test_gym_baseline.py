"""The standardized Gym baseline: one "word (form)" shape from every legacy
hint format, upgraded to the native language where the chart gloss is known."""
from __future__ import annotations

from backend.repositories.cards import _gym_baseline, _short_gloss, _split_hint


class TestSplitHint:
    def test_legacy_lemma_person(self):
        assert _split_hint("preparar, tú") == ("preparar", "tú")

    def test_plain_english_infinitive(self):
        assert _split_hint("to live") == ("to live", "")

    def test_recipe_tail_stripped(self):
        assert _split_hint("to watch — add -es") == ("to watch", "")

    def test_descriptive_dash_kept(self):
        # A dash tail that is NOT a spelling recipe stays (it's the cue).
        word, tail = _split_hint("to go — verb stays second, subject flips")
        assert word == "to go — verb stays second"
        assert tail == "subject flips"

    def test_empty(self):
        assert _split_hint(None) == ("", "")


class TestShortGloss:
    def test_first_sense(self):
        assert _short_gloss("to prepare; to get ready") == "to prepare"

    def test_run_on_rejected(self):
        assert _short_gloss("x" * 60) is None

    def test_none(self):
        assert _short_gloss(None) is None


class TestGymBaseline:
    def test_cell_wins_over_hint_tail(self):
        card = {"hint": "preparar, tú", "cell": "vosotros"}
        assert _gym_baseline(card) == "preparar (vosotros)"

    def test_legacy_lemma_hint_upgraded_to_native_gloss(self):
        # "preparar, tú" + chart hit whose gloss is English → native baseline.
        card = {
            "hint": "preparar, tú",
            "chart_word": "preparar",
            "chart_gloss": "to prepare",
        }
        assert _gym_baseline(card) == "to prepare (tú)"

    def test_english_hint_kept_and_gets_cell(self):
        card = {"hint": "to live", "cell": "wij"}
        assert _gym_baseline(card) == "to live (wij)"

    def test_recipe_hint_standardized(self):
        card = {"hint": "to watch — add -es", "cell": "él/ella"}
        assert _gym_baseline(card) == "to watch (él/ella)"

    def test_description_hint_passes_through(self):
        assert _gym_baseline({"hint": "indefinite article"}) == "indefinite article"

    def test_no_hint_falls_back_to_gloss_then_lemma(self):
        assert (
            _gym_baseline({"hint": None, "chart_gloss": "to listen", "cell": "я"})
            == "to listen (я)"
        )
        assert _gym_baseline({"hint": "", "lemma": "слушать"}) == "слушать"

    def test_totally_bare_card_is_blank(self):
        assert _gym_baseline({}) == ""
