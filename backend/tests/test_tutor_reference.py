"""REFERENCE.md is generated, and the generated files are what is committed.

The drift this guards against was real: 22 of the 27 bundles were missing
the grammar points added since their file was hand-written, so the tutor
sequenced a course the deck no longer taught (brief item 6, 3 Sep 2026).
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.services import tutor_reference as tr


class TestRender:
    def test_groups_points_by_level_in_display_order(self, tmp_path):
        (tmp_path / "zz_grammar.json").write_text(json.dumps({"points": [
            {"title": "Later", "level": "A2", "function": "second", "display_order": 2},
            {"title": "First", "level": "A1", "function": "one", "display_order": 1},
            {"title": "Third", "level": "A1", "function": "", "display_order": 3},
        ]}), encoding="utf-8")
        text = tr.render_reference("zz", grammar_dir=tmp_path)
        assert text.startswith("# Curriculum reference — zz (zz)\n\n")
        assert tr.INTRO in text
        a1 = text.index("## A1")
        a2 = text.index("## A2")
        assert a1 < a2
        # Display order within a level, function joined with an em dash,
        # and no dangling dash when a point has no function line.
        assert "- First — one\n- Third\n" in text
        assert "- Later — second" in text

    def test_unknown_levels_follow_the_known_ones(self, tmp_path):
        (tmp_path / "zz_grammar.json").write_text(json.dumps({"points": [
            {"title": "Odd", "level": "X", "function": "", "display_order": 1},
            {"title": "Normal", "level": "C2", "function": "", "display_order": 2},
        ]}), encoding="utf-8")
        text = tr.render_reference("zz", grammar_dir=tmp_path)
        assert text.index("## C2") < text.index("## X")


class TestCommittedFiles:
    def test_every_bundle_is_current(self):
        # The one that matters. A grammar edit without a regenerate lands
        # here, naming the language, with the command to run.
        stale = tr.stale_references()
        assert stale == [], (
            f"REFERENCE.md out of date for {stale}: run "
            "`python -m backend.services.tutor_reference`"
        )

    def test_every_course_is_named(self):
        for code in tr.reference_codes():
            assert code in tr.LANGUAGE_NAMES, f"add {code} to LANGUAGE_NAMES"

    def test_check_mode_reports_and_writes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tr, "SKILLS_DIR", tmp_path)
        (tmp_path / "fr").mkdir()
        (tmp_path / "fr" / "REFERENCE.md").write_text("old", encoding="utf-8")
        assert tr.main(["--check", "fr"]) == 1
        assert (tmp_path / "fr" / "REFERENCE.md").read_text(encoding="utf-8") == "old"
        assert tr.main(["fr"]) == 0
        assert (tmp_path / "fr" / "REFERENCE.md").read_text(encoding="utf-8") == \
            tr.render_reference("fr")
        assert tr.main(["--check", "fr"]) == 0

    def test_generated_files_stay_within_the_on_demand_bound(self):
        # test_tutor bounds the on-demand files at 20k chars. A course
        # that outgrows the bound needs it raised deliberately, not a
        # silently truncated map.
        for code in tr.reference_codes():
            text = (Path(tr.SKILLS_DIR) / code / "REFERENCE.md").read_text(encoding="utf-8")
            assert len(text) < 20000, code
