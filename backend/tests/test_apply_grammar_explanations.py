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
import unicodedata
from pathlib import Path

import pytest

from scripts.apply_grammar_explanations import GRAMMAR, check, has_markdown

# Courses the editorial pass has finished. Korean is held for its
# duplicate-point decision (docs/plans/quality-parity.md). Add a code when
# its pass ships.
FORMATTED = {"ar", "ca", "de", "el", "en", "es", "fa", "fr", "ha", "he",
             "hi", "id", "it", "jam", "ko", "la", "mi", "nl", "pt", "ro",
             "ru", "sw", "th", "tl", "tr", "xh", "yo"}

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
        formatted = FORMATTED
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
        """Restraint, measured on the signal that survived two calibrations.

        First try bounded the SHARE of formatted points at 80%. Greek tripped
        it at 83% — and Greek is not over-formatted, it is inflected: 21 of
        its 41 points hold a real paradigm against 12 in French. Share
        measures the language.

        Second try bounded the share of points that got ONLY bold. Jamaican
        tripped it at 38% and Yoruba at 38% — and their bolds are all correct:
        both languages teach particles, so a point is often one sentence
        naming one form (`**dem**` after the noun for the plural, `**Kò**`
        before the verb for negation) with no paradigm to table. Bold-only
        share measures the language too.

        What measures the PASS is whether a bold names the form the point
        actually teaches. Across the 26 finished courses, 208 of 238 bolds
        (87%) match a string in the point's title or one of its drill
        answers. Decoration would not.
        """
        def fold(text):
            return "".join(c for c in unicodedata.normalize("NFD", text.casefold())
                           if not unicodedata.category(c).startswith("M"))

        bold = re.compile(r"\*\*([^*\n]+)\*\*")
        total = named = 0
        thin = []
        per_course = []
        for code in FORMATTED:
            data = json.loads(
                (GRAMMAR / f"{code}_grammar.json").read_text(encoding="utf-8"))
            points = data["points"] if isinstance(data, dict) else data
            texts = [p for p in points if (p.get("explanation") or "").strip()]
            done = [p for p in texts if has_markdown(p["explanation"])]
            if len(done) / len(texts) < 0.35:
                thin.append((code, f"{len(done)}/{len(texts)}"))
            hits = misses = 0
            for point in points:
                pool = fold(point.get("title") or "") + " " + " ".join(
                    fold(d.get("answer") or "") for d in (point.get("drills") or []))
                for match in bold.findall(point.get("explanation") or ""):
                    if fold(match.strip()) in pool:
                        hits += 1
                    else:
                        misses += 1
            total += hits + misses
            named += hits
            if hits + misses >= 8 and hits / (hits + misses) < 0.5:
                per_course.append((code, f"{hits}/{hits + misses}"))
        assert thin == [], f"{thin} — the pass barely formatted these courses"
        assert per_course == [], (
            f"{per_course} — most of these courses' bolds do not name a form "
            "the point teaches, which is decoration")
        assert named / total >= 0.80, (
            f"only {named}/{total} bolds name the taught form; the measured "
            "state on 8 Sep 2026 was 208/238")


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
