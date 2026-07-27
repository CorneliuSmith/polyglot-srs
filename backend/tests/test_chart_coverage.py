"""Gym chart coverage — a data test, because the gap that shipped was DATA.

Charts (the Gym's conjugation/declension tables) exist only for languages
whose `data/{code}_morphology.json` carries `charts` entries. Eleven of the
seeded languages have none at all, so no amount of lookup work can show a
chart there. These tests pin what we HAVE so it can't silently regress, and
record what's missing so the gap is visible rather than folklore.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "data"

# Languages whose morphology data carries real chart tables today, with the
# floor each must not fall below (well under current counts — this catches a
# broken build, not normal churn).
CHARTED_LANGUAGES = {
    "ru": 2000, "tr": 3000, "el": 3000, "ar": 1500, "de": 1000,
    "ro": 900, "fr": 700, "ca": 600, "pt": 700, "it": 500, "es": 500,
}

# Known-empty: no chart builder, no source dump, or a chips-only builder.
# Listed explicitly so adding charts for one is a deliberate, visible change.
# See ROADMAP WP45.
UNCHARTED_LANGUAGES = {
    "sw", "xh", "yo",                    # builder emits chips only
    "nl", "hi", "ko", "th", "ha", "mi",  # no builder registered
    "la", "id", "tl", "he", "fa",        # no builder registered (WP76 draft tier)
    "en", "jam",                         # no source dump
}


def _charted_words(code: str) -> dict:
    path = DATA / f"{code}_morphology.json"
    if not path.exists():
        return {}
    blob = json.loads(path.read_text(encoding="utf-8"))
    return {
        w: m for w, m in blob.items()
        if isinstance(m, dict) and m.get("charts")
    }


class TestChartData:
    @pytest.mark.parametrize("code,floor", sorted(CHARTED_LANGUAGES.items()))
    def test_charted_language_keeps_its_charts(self, code, floor):
        charted = _charted_words(code)
        assert len(charted) >= floor, (
            f"{code}: only {len(charted)} charted words (floor {floor}) — "
            f"did the morphology build break or get skipped?"
        )

    def test_uncharted_list_is_honest(self):
        """A language on the uncharted list that suddenly HAS charts means the
        list is stale — update it (and celebrate) rather than let it drift."""
        gained = {c for c in UNCHARTED_LANGUAGES if _charted_words(c)}
        assert not gained, (
            f"these now have charts and should move to CHARTED_LANGUAGES: {gained}"
        )

    def test_every_seeded_language_is_accounted_for(self):
        """No language may be silently absent from both lists — that's how the
        coverage hole went unnoticed."""
        seeded = {
            p.name.removesuffix("_grammar.json")
            for p in (DATA / "grammar").glob("*_grammar.json")
        }
        tracked = set(CHARTED_LANGUAGES) | UNCHARTED_LANGUAGES
        assert seeded <= tracked, f"untracked languages: {seeded - tracked}"


class TestAnswerLookupCoverage:
    """The lookup half: a drill's own answer must be findable in the charts.

    Mirrors `_chart_form_index` + `_form_key` against the real seed data, so a
    regression in either shows up as a coverage drop rather than as silently
    missing charts in the Gym.
    """

    @staticmethod
    def _hit_rate(code: str) -> tuple[int, int]:
        from backend.repositories.cards import (
            _chart_form_keys,
            _form_key,
            _word_tokens,
        )

        charted = _charted_words(code)
        index: dict[str, str] = {}
        for word, morph in charted.items():
            for key in (_form_key(word), *sorted(_chart_form_keys(morph))):
                if key and key not in index:
                    index[key] = word

        grammar = json.loads(
            (DATA / "grammar" / f"{code}_grammar.json").read_text(encoding="utf-8")
        )
        points = grammar if isinstance(grammar, list) else grammar.get("points", [])
        total = hits = 0
        for point in points:
            for drill in point.get("drills") or []:
                answer = (drill.get("answer") or "").strip()
                if not answer:
                    continue
                total += 1
                tokens = [t for t in _word_tokens(answer) if len(t) > 2]
                if any(_form_key(t) in index for t in tokens):
                    hits += 1
        return hits, total

    # Floors sit ~5pts under measured rates (2026-07: es 50, fr 47, ru 45,
    # pt 45, de 39, ca 38, it 38, ar 35, ro 31, el 30, tr 22) — they catch a
    # broken index, not data churn. The jump over the first measurement came
    # from _word_tokens: stressed chart forms used to split at the combining
    # mark and never enter the index.
    @pytest.mark.parametrize("code,floor_pct", [
        ("es", 45), ("fr", 40), ("de", 33), ("ca", 33), ("it", 33),
        ("pt", 40), ("ro", 26), ("el", 25), ("tr", 17), ("ru", 40),
        ("ar", 30),
    ])
    def test_answers_resolve_to_charts(self, code, floor_pct):
        hits, total = self._hit_rate(code)
        assert total > 0, f"{code}: no drills with answers in the seed data"
        pct = hits * 100 // total
        assert pct >= floor_pct, (
            f"{code}: only {pct}% of drill answers find a chart "
            f"({hits}/{total}, floor {floor_pct}%)"
        )

    def test_form_key_ignores_stress_marks(self):
        """The charts print stress ("жи́ли"); the drills don't ("жили")."""
        from backend.repositories.cards import _form_key

        assert _form_key("жи́ли") == _form_key("жили")
        assert _form_key("Preparás") == _form_key("preparas")
        assert _form_key(unicodedata.normalize("NFC", "é")) == _form_key("e")
