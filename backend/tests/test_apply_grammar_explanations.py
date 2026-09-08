"""The gate on the markdown/editorial pass over grammar explanations.

`docs/plans/markdown-explanations.md`. An explanation that carries markdown
now RENDERS as markdown on the card, and `CardMarkdown`'s sanitiser allows a
narrow set of tags — so a construct outside that set is not "slightly off",
it is silently dropped or printed literally for every learner. This gate
decides only that what an editorial pass returns CAN be rendered; taste is
the reader's job.

Rule 47: a gate is tested against the corpus it governs, not against
examples chosen to make it pass.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.apply_grammar_explanations import GRAMMAR, check, has_markdown

PLAIN = "Turkish has no separate verb 'to be' in the present tense here."


class TestWhatItRefuses:
    def test_a_heading_the_renderer_cannot_show(self):
        why = check(PLAIN, "## Forms\n\nTurkish has no separate verb to be here.")
        assert why and "heading" in why

    def test_raw_html(self):
        why = check(PLAIN, "Turkish has <b>no</b> separate verb to be in the present.")
        assert why and "HTML" in why

    def test_an_unsafe_link_destination(self):
        why = check(PLAIN, "Turkish [has](javascript:alert(1)) no separate verb here.")
        assert why and "HTML" in why or "link" in why

    def test_an_image(self):
        why = check(PLAIN, "Turkish has no separate verb ![chart](https://x/y.png) here.")
        assert why and "image" in why

    def test_a_horizontal_rule(self):
        why = check(PLAIN, "Turkish has no separate verb to be.\n\n---\n\nIt suffixes.")
        assert why and "rule" in why

    def test_a_table_whose_rows_disagree_with_its_header(self):
        bad = ("Turkish suffixes the person here:\n\n"
               "| person | form |\n| --- | --- |\n| ben | -im | extra |")
        why = check(PLAIN, bad)
        assert why and "table" in why

    def test_a_blank_inside_a_markdown_block(self):
        why = check(PLAIN, "**Turkish** has no separate verb: ben ___ here.")
        assert why and "___" in why

    def test_an_empty_replacement(self):
        assert check(PLAIN, "   ") == "empty"

    def test_a_replacement_that_shares_no_word(self):
        why = check(PLAIN, "Completely different subject matter entirely, yes.")
        assert why and "wrong point" in why

    def test_a_replacement_that_ballooned(self):
        why = check(PLAIN, PLAIN + " Turkish " * 200)
        assert why and "longer" in why

    def test_a_truncated_replacement(self):
        why = check(PLAIN, "Turkish")
        assert why and ("truncated" in why or "of the text" in why)


class TestWhatItAccepts:
    def test_bold_a_list_and_a_table(self):
        good = ("**Turkish** has no separate verb 'to be' in the present here.\n\n"
                "- ben\n- sen\n\n| person | form |\n| --- | --- |\n| ben | -im |")
        assert check(PLAIN, good) is None

    def test_inline_code_and_a_safe_link(self):
        good = ("Turkish suffixes the person, `-im`, in the present tense, "
                "see [TDK](https://sozluk.gov.tr) here.")
        assert check(PLAIN, good) is None

    def test_plain_prose_unchanged_in_shape(self):
        assert check(PLAIN, PLAIN.replace("present", "present tense")) is None

    def test_a_first_text_with_no_predecessor(self):
        assert check("", "**Bold** opening line for a brand new explanation.") is None


class TestAgainstTheCorpus:
    @pytest.mark.parametrize(
        "path", sorted(GRAMMAR.glob("*_grammar.json")), ids=lambda p: p.stem)
    def test_every_shipped_explanation_passes_its_own_gate(self, path):
        """The corpus is the gate's first test set: a rule that would refuse
        text already shipped is a rule that is wrong, not a corpus that is."""
        data = json.loads(path.read_text(encoding="utf-8"))
        points = data["points"] if isinstance(data, dict) else data
        bad = []
        for p in points:
            text = (p.get("explanation") or "").strip()
            if text:
                why = check(text, text)
                if why:
                    bad.append((p.get("title"), why))
        assert bad == [], f"{path.name}: the gate refuses shipped text: {bad[:5]}"

    def test_only_the_courses_the_pass_has_reached_carry_markdown(self):
        """A ratchet, not a zero. The editorial pass runs course by course
        (`docs/plans/markdown-explanations.md`), so this names the ones it
        has reached. A course that gains markdown without being listed here
        gained it by accident — a copied paragraph, an AI-written row — and
        that is what this catches. Add a code when its pass ships."""
        formatted = {"ca", "de", "el", "es", "fr", "it", "nl", "pt", "ro", "ru"}
        by_course = {}
        for path in sorted(GRAMMAR.glob("*_grammar.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            points = data["points"] if isinstance(data, dict) else data
            n = sum(1 for p in points
                    if has_markdown(p.get("explanation") or ""))
            if n:
                by_course[path.stem.replace("_grammar", "")] = n
        assert set(by_course) == formatted, (
            f"formatted courses are {sorted(by_course)}, expected "
            f"{sorted(formatted)} — add the code above when a pass ships, or "
            f"find out how markdown got in")

    def test_a_finished_course_did_not_format_for_its_own_sake(self):
        """Restraint, measured on the right signal.

        The first version of this bounded the SHARE of formatted points, and
        Greek tripped it at 83%. Greek is not over-formatted; it is inflected
        — 21 of its 41 points hold a real case-by-gender or person-by-form
        paradigm, against 12 in French. Share measures the language, not the
        pass.

        What measures the pass is how many points got ONLY bold: the cheap
        edit, no table and no list. Across the ten courses done on 7 Sep 2026
        that runs 2% (ca, fr, it, ro) to 20% (el), while the overall share
        runs 48% to 83%. A pass whose bold-only share climbs is one reaching
        for something to do.
        """
        table = re.compile(r"(^|\n)\s*\|.*\|")
        bullet = re.compile(r"(^|\n)\s*([-*+]|\d+\.)\s+")
        bad = []
        for code in ("ca", "de", "el", "es", "fr", "it", "nl", "pt", "ro", "ru"):
            data = json.loads(
                (GRAMMAR / f"{code}_grammar.json").read_text(encoding="utf-8"))
            points = data["points"] if isinstance(data, dict) else data
            texts = [p["explanation"] for p in points
                     if (p.get("explanation") or "").strip()]
            done = [t for t in texts if has_markdown(t)]
            structured = [t for t in done if table.search(t) or bullet.search(t)]
            bold_only = len(done) - len(structured)
            if not 0.35 <= len(done) / len(texts) <= 0.90:
                bad.append((code, "share", f"{len(done)}/{len(texts)}"))
            if bold_only / len(texts) > 0.30:
                bad.append((code, "bold-only", f"{bold_only}/{len(texts)}"))
        assert bad == [], (
            f"{bad} — a low share means the pass did nothing; a high bold-only "
            "share means it formatted to look busy")


def test_has_markdown_mirrors_the_renderer():
    """Its six signals are `hasMarkdown` in ExplanationView.tsx. If that list
    changes, this gate is deciding with the wrong one."""
    tsx = (Path(__file__).resolve().parents[2] / "frontend" / "src" /
           "components" / "ExplanationView.tsx").read_text(encoding="utf-8")
    body = tsx[tsx.index("export function hasMarkdown"):]
    body = body[:body.index("\n}")]
    for signal in ("`[^`\\n]+`", "\\*\\*[^*\\n]+\\*\\*", "|.*\\|", "#{1,3}"):
        assert signal in body, f"the renderer no longer tests {signal!r}"
    assert has_markdown("**bold**") and not has_markdown("plain prose here")
