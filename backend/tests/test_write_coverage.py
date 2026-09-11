"""The baseline's coverage set: what a script's baseline must show, and
the greedy pick that shows it (docs/plans/handwriting.md, §12.2)."""

from __future__ import annotations

from backend.services.write_coverage import (
    pick_coverage,
    targets,
    units_shown,
)


def _pool(*answers: str) -> list[dict]:
    return [{"answer": a, "prompt": f"meaning of {a}"} for a in answers]


class TestUnits:
    def test_arabic_units_are_letter_and_form(self):
        # ب starts, ي is medial, ت ends; the space breaks joining.
        assert units_shown("ar", "بيت") == {"ب:initial", "ي:medial", "ت:final"}
        # Alif never joins left: the letter after it is initial, not medial.
        assert "ن:initial" in units_shown("ar", "أنا")
        assert "أ:isolated" in units_shown("ar", "أنا")
        assert "ا:final" in units_shown("ar", "أنا")

    def test_cased_scripts_fold_case(self):
        assert units_shown("ru", "Фёдор") == {"ф", "ё", "д", "о", "р"}
        assert "ф" in targets("ru")

    def test_hangul_blocks_decompose_to_jamo(self):
        # ㅎ at the top and ㄴ at the bottom of 한 are the letters ㅎ and
        # ㄴ — one unit each, whatever the position.
        u = units_shown("ko", "한")
        assert u == {"HIEUH", "A", "NIEUN"}
        assert u <= targets("ko")
        assert units_shown("ko", "난") & u == {"A", "NIEUN"}

    def test_arabic_targets_skip_forms_a_letter_cannot_take(self):
        t = targets("ar")
        assert "ب:medial" in t and "د:medial" not in t and "د:final" in t

    def test_a_latin_course_is_covered_by_its_own_pool(self):
        assert targets("es", ["Hola", "niño"]) == {"h", "o", "l", "a", "n", "i", "ñ"}


class TestPick:
    def test_picks_the_sentences_that_add_the_most(self):
        pool = _pool("аб", "вгд", "абв", "ежз")
        out = pick_coverage("ru", pool, n=2)
        # "вгд" (3 new) then "ежз" (3 new) beat "абв" (only а,б new after them).
        assert [s["answer"] for s in out["items"]] == ["вгд", "ежз"]
        assert out["total"] == 33 and out["covered"] == 6

    def test_fills_to_eight_with_the_shortest_when_coverage_runs_out(self):
        pool = _pool("аб", "аб аб", "а", "б", "в", "г", "д", "е", "ж", "з")
        out = pick_coverage("ru", pool, n=8)
        assert len(out["items"]) == 8
        assert out["items"][0]["answer"] == "аб"   # shorter tie-break

    def test_an_empty_pool_is_an_empty_set(self):
        assert pick_coverage("ar", []) == {"items": [], "covered": 0, "total": len(targets("ar"))}
