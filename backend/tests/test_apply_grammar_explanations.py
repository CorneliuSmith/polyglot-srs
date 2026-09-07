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

    def test_the_corpus_carries_no_markdown_yet(self):
        """Pins the starting point the plan measured, so the first course to
        be formatted shows up as a real change rather than as drift."""
        formatted = [
            (path.stem, p.get("title"))
            for path in sorted(GRAMMAR.glob("*_grammar.json"))
            for p in (lambda d: d["points"] if isinstance(d, dict) else d)(
                json.loads(path.read_text(encoding="utf-8")))
            if has_markdown(p.get("explanation") or "")
        ]
        assert formatted == [], f"already formatted: {formatted[:5]}"


class TestTheRoundTrip:
    def test_export_then_apply_is_a_no_op(self, tmp_path, capsys):
        from scripts import apply_grammar_explanations as mod
        mod.export("mi", tmp_path / "mi.json")
        mod.apply([tmp_path / "mi.json"], dry_run=True)
        out = capsys.readouterr().out
        assert "accepted 0" in out, out

    def test_a_wrong_title_at_the_index_is_refused(self, tmp_path, capsys):
        from scripts import apply_grammar_explanations as mod
        blob = {"code": "mi", "points": [
            {"index": 0, "title": "Not the point that is there",
             "explanation": "Anything at all goes here for the test."}]}
        (tmp_path / "x.json").write_text(json.dumps(blob), encoding="utf-8")
        mod.apply([tmp_path / "x.json"], dry_run=True)
        assert "title does not match" in capsys.readouterr().out

    def test_it_writes_nothing_on_a_dry_run(self, tmp_path):
        from scripts import apply_grammar_explanations as mod
        path = GRAMMAR / "mi_grammar.json"
        before = path.read_bytes()
        mod.export("mi", tmp_path / "mi.json")
        blob = json.loads((tmp_path / "mi.json").read_text(encoding="utf-8"))
        blob["points"][0]["explanation"] = (
            "**" + blob["points"][0]["explanation"][:60] + "** and the rest follows.")
        (tmp_path / "mi.json").write_text(json.dumps(blob, ensure_ascii=False),
                                          encoding="utf-8")
        mod.apply([tmp_path / "mi.json"], dry_run=True)
        assert path.read_bytes() == before


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
