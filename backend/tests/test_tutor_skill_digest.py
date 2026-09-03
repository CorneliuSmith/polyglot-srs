"""The tutor bundles track the language standards (brief item 6).

The check that matters is the last class: a standard edited after its
tutor's last digest fails the build by name. Everything else pins the
plumbing the script relies on.
"""
from __future__ import annotations

from pathlib import Path

from backend.services import tutor_skill_digest as d

STANDARD = """# French (fr) — Content Quality Standards

## Language profile

Latin script. Learners drop the accents. Three features dominate drill
quality: elision, which makes one blank hard; gender agreement. The file
uses ASCII apostrophes.

## Hint standards

Hints never quote the answer. Learners confuse tu and vous.
"""


class TestStamps:
    def test_hash_is_twelve_hex_chars_of_the_standard(self, tmp_path):
        (tmp_path / "fr.md").write_text(STANDARD, encoding="utf-8")
        h = d.quality_hash("fr", quality_dir=tmp_path)
        assert len(h) == 12 and int(h, 16) >= 0
        (tmp_path / "fr.md").write_text(STANDARD + "\nmore\n", encoding="utf-8")
        assert d.quality_hash("fr", quality_dir=tmp_path) != h
        assert d.quality_hash("zz", quality_dir=tmp_path) is None

    def test_stamp_round_trips(self):
        line = d.stamp_line("fr", "0123456789ab")
        assert d.stamped_hash(f"# Errors\n\n{line}\n- **X.** y") == "0123456789ab"
        assert d.stamped_hash("# Errors\n- **X.** y") is None

    def test_status_names_every_case(self, tmp_path):
        q, s = tmp_path / "q", tmp_path / "s"
        q.mkdir(), s.mkdir()
        assert d.digest_status("fr", q, s) == "no-standard"
        (q / "fr.md").write_text(STANDARD, encoding="utf-8")
        assert d.digest_status("fr", q, s) == "no-tutor"
        (s / "fr").mkdir()
        (s / "fr" / "ERRORS.md").write_text("# Errors\n", encoding="utf-8")
        assert d.digest_status("fr", q, s) == "never"
        h = d.quality_hash("fr", q)
        (s / "fr" / "ERRORS.md").write_text(
            f"# Errors\n{d.stamp_line('fr', h)}\n", encoding="utf-8")
        assert d.digest_status("fr", q, s) == "current"
        (q / "fr.md").write_text(STANDARD + "\nedited\n", encoding="utf-8")
        assert d.digest_status("fr", q, s) == "stale"


class TestMechanicalDigest:
    def test_takes_the_profile_sentences_about_learners_and_the_notes(self):
        bullets = d.mechanical_digest(STANDARD, notes=["Passé composé: drill agreement"])
        # From the profile: the sentences with a learner-error cue…
        assert any("drop the accents" in b for b in bullets)
        assert any("one blank hard" in b for b in bullets)
        # …not the one about file formatting…
        assert not any("ASCII" in b for b in bullets)
        # …and nothing from later sections, which are about the data.
        assert not any("tu and vous" in b for b in bullets)
        assert bullets[-1] == "Passé composé: drill agreement"

    def test_render_carries_the_stamp_and_bullets(self):
        text = d.render_extracted("fr", "French", ["**A.** b", "- **C.** d"],
                                  "0123456789ab", ["docs/quality/fr.md"])
        assert text.startswith("# Common learner errors — French (fr)\n")
        assert d.stamped_hash(text) == "0123456789ab"
        assert "\n- **A.** b\n- **C.** d\n" in text


class TestThePersonasTrackTheStandards:
    def test_every_standard_has_a_current_digest_or_a_listed_exemption(self):
        """The 'have they been updated' check, made mechanical."""
        codes = sorted(
            p.stem for p in Path(d.QUALITY_DIR).glob("*.md")
            if (Path(d.SKILLS_DIR) / p.stem).is_dir()
        )
        assert codes, "no standards found — paths moved?"
        for code in codes:
            status = d.digest_status(code)
            if code in d.NEVER_DIGESTED:
                assert status == "never", (
                    f"{code}: ERRORS.md is stamped now — remove it from "
                    "NEVER_DIGESTED so the check applies"
                )
            else:
                assert status == "current", (
                    f"{code}: docs/quality/{code}.md changed since the tutor's "
                    f"last digest — run `scripts/tutor_skill_digest.py {code}` "
                    "and fold the result into ERRORS.md (stamp included)"
                )

    def test_exemptions_name_real_languages(self):
        for code in d.NEVER_DIGESTED:
            assert (Path(d.SKILLS_DIR) / code).is_dir(), code
