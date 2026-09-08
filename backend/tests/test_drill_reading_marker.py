"""A drill's reading line must not print the literal {{answer}} marker.

The vocabulary card learned this in CHECKS §11: the marker is Latin text,
so every romaniser passes it through untouched and the learner reads
"READING {{answer}}?" under a script they cannot yet decode. `_vocab_card`
blanks before it romanises. The GRAMMAR card served whatever the drill row
stored — and 1,612 committed drill rows store the marker in their
transliteration: ko 921, th 268, hi 248, he 88, fa 87, every one a course
whose layer order shows a reading (`hintLayers.ts` WITH_READING).

Fixed in the card rather than in the data, because the rows are already in
production and this way no reseed is needed to stop showing it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.repositories.cards import (
    ANSWER_MARKER,
    BLANK_READING,
    _blanked,
    _grammar_card,
)

REPO = Path(__file__).resolve().parents[2]


class TestTheHelper:
    def test_it_swaps_the_marker_for_the_blank(self):
        assert _blanked(f"u mu'allim {ANSWER_MARKER}.") == f"u mu'allim {BLANK_READING}."

    def test_it_leaves_a_clean_reading_alone(self):
        assert _blanked("jeoneun ___ dongan jassoyo.") == "jeoneun ___ dongan jassoyo."

    def test_none_and_empty_pass_through(self):
        assert _blanked(None) is None
        assert _blanked("") == ""

    def test_every_occurrence_goes(self):
        assert ANSWER_MARKER not in _blanked(f"{ANSWER_MARKER} wa {ANSWER_MARKER}")


class TestTheGrammarCard:
    @staticmethod
    def _row(**over):
        row = {
            "id": "c1", "user_id": "u1", "language_id": "l1",
            "card_type": "grammar", "card_id": "g1", "language_code": "ko",
            "title": "Sino-Korean counters", "explanation": None,
            "drill_sentences": [f"저는 {ANSWER_MARKER} 동안 잤어요."],
            "drill_answers": ["여덟 시간"], "drill_hints": ["hours, native counter"],
            "drill_translations": ["I slept for eight hours."],
            "drill_base_translations": [None],
            "drill_glosses": [f"1SG · {ANSWER_MARKER} · during · sleep.PST"],
            "drill_transliterations": [f"jeoneun {ANSWER_MARKER} dongan jassoyo."],
            "last_prompt": None,
            "ease_factor": 2.5, "interval": 1, "repetitions": 0, "streak": 0,
            "lapses": 0, "next_review": None,
        }
        row.update(over)
        return row

    def test_the_reading_shows_a_blank_not_the_marker(self):
        card = _grammar_card(self._row(), {})
        assert ANSWER_MARKER not in (card["transliteration"] or "")
        assert BLANK_READING in card["transliteration"]

    def test_the_gloss_too(self):
        card = _grammar_card(self._row(), {})
        assert ANSWER_MARKER not in (card["gloss"] or "")

    def test_the_sentence_keeps_its_marker(self):
        """The card layer splits the sentence at the marker to draw the input
        box; blanking it there would break the drill."""
        card = _grammar_card(self._row(), {})
        assert ANSWER_MARKER in card["sentence"]

    def test_a_row_with_no_reading_is_unchanged(self):
        card = _grammar_card(self._row(drill_transliterations=[None]), {})
        assert card["transliteration"] is None


class TestTheCorpusThisProtects:
    def test_the_committed_rows_that_carry_the_marker_are_still_there(self):
        """Not a rule — a measurement, so the next reader knows the card fix
        is load-bearing and the data was never cleaned. If this reaches zero
        because a pass rewrote the rows, the card fix stays anyway: it costs
        nothing and covers rows already seeded into production."""
        counts = {}
        for path in sorted((REPO / "data" / "grammar").glob("*_grammar.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            points = data["points"] if isinstance(data, dict) else data
            n = sum(
                1 for p in points for d in (p.get("drills") or [])
                if ANSWER_MARKER in (d.get("transliteration") or "")
            )
            if n:
                counts[path.stem.replace("_grammar", "")] = n
        assert set(counts) <= {"ko", "th", "hi", "he", "fa"}, counts

    @pytest.mark.parametrize("code", ["ko", "th", "hi", "he", "fa"])
    def test_those_courses_show_a_reading_layer(self, code):
        """Which is what makes it a defect rather than dead data."""
        tsx = (REPO / "frontend" / "src" / "features" / "review"
               / "hintLayers.ts").read_text(encoding="utf-8")
        block = tsx[tsx.index("WITH_READING"):]
        assert "'transliteration'" in block[:400]
        assert f"'{code}'" in tsx, f"{code} is not routed to a layer order"
