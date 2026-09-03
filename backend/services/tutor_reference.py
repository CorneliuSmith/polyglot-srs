"""REFERENCE.md — the tutor's map of the course — generated from the cards.

Each tutor skill bundle (`tutor_skills/<code>/`) carries a REFERENCE.md: the
language's grammar path in teaching order, loaded on demand through the
`consult_reference` tool so the tutor names points exactly as the learner's
cards do. The file is DERIVED from `data/grammar/<code>_grammar.json`, but
until 3 Sep 2026 nothing in the repo derived it: the ROADMAP said "regenerate
when paths change" and nobody did — 22 of 27 files had drifted, each missing
the points added since it was written, so the tutor sequenced a course that
no longer matched the deck.

    python -m backend.services.tutor_reference            # rewrite all
    python -m backend.services.tutor_reference --check    # list the stale
    python -m backend.services.tutor_reference fr de      # just these

`tests/test_tutor_reference.py` pins every file to `render_reference`, so
a grammar edit that forgets to regenerate fails CI instead of drifting.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GRAMMAR_DIR = REPO / "data" / "grammar"
SKILLS_DIR = Path(__file__).parent / "tutor_skills"

# The display name in each file's heading. The cards carry no language
# name (the languages table does, but this must run without a database),
# so the roster lives here; a new course adds one line.
LANGUAGE_NAMES = {
    "ar": "Arabic", "ca": "Catalan", "de": "German", "el": "Greek",
    "en": "English", "es": "Spanish", "fa": "Persian", "fr": "French",
    "ha": "Hausa", "he": "Hebrew", "hi": "Hindi", "id": "Indonesian",
    "it": "Italian", "jam": "Jamaican Patois", "ko": "Korean",
    "la": "Latin", "mi": "Māori", "nl": "Dutch", "pt": "Portuguese",
    "ro": "Romanian", "ru": "Russian", "sw": "Swahili", "th": "Thai",
    "tl": "Tagalog", "tr": "Turkish", "xh": "Xhosa", "yo": "Yoruba",
}

LEVEL_ORDER = ("A0", "A1", "A2", "B1", "B2", "C1", "C2")

INTRO = (
    "The app's grammar path in teaching order. These point titles are "
    "exactly what the learner sees on their cards, and weak grammar items "
    "arrive labeled with them — use the same names when coaching, and "
    "sequence new material in this order."
)


def grammar_points(code: str, grammar_dir: Path = GRAMMAR_DIR) -> list[dict]:
    """The language's points in display order — the order the seeder gives
    the cards, so the tutor's map and the deck agree."""
    data = json.loads((grammar_dir / f"{code}_grammar.json").read_text(encoding="utf-8"))
    points = data["points"] if isinstance(data, dict) else data
    return sorted(points, key=lambda p: (p.get("display_order") or 0))


def render_reference(code: str, grammar_dir: Path = GRAMMAR_DIR) -> str:
    name = LANGUAGE_NAMES.get(code, code)
    by_level: dict[str, list[dict]] = {}
    for p in grammar_points(code, grammar_dir):
        by_level.setdefault(p.get("level") or "?", []).append(p)
    levels = [lvl for lvl in LEVEL_ORDER if lvl in by_level]
    levels += sorted(lvl for lvl in by_level if lvl not in LEVEL_ORDER)
    out = [f"# Curriculum reference — {name} ({code})", "", INTRO, ""]
    for lvl in levels:
        out.append(f"## {lvl}")
        for p in by_level[lvl]:
            function = (p.get("function") or "").strip()
            out.append(f"- {p['title']} — {function}" if function else f"- {p['title']}")
        out.append("")
    return "\n".join(out)


def reference_codes(grammar_dir: Path = GRAMMAR_DIR,
                    skills_dir: Path = SKILLS_DIR) -> list[str]:
    """Languages that have both a grammar file and a tutor bundle."""
    return sorted(
        p.name.removesuffix("_grammar.json")
        for p in grammar_dir.glob("*_grammar.json")
        if (skills_dir / p.name.removesuffix("_grammar.json")).is_dir()
    )


def stale_references(codes: list[str] | None = None) -> list[str]:
    """Codes whose committed REFERENCE.md differs from the render."""
    out = []
    for code in codes or reference_codes():
        path = SKILLS_DIR / code / "REFERENCE.md"
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current != render_reference(code):
            out.append(code)
    return out


def write_references(codes: list[str] | None = None) -> list[str]:
    """Rewrite each bundle's REFERENCE.md; returns the codes that changed."""
    changed = []
    for code in codes or reference_codes():
        path = SKILLS_DIR / code / "REFERENCE.md"
        text = render_reference(code)
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed.append(code)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("codes", nargs="*", help="language codes (default: all)")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 listing files that would change; write nothing")
    args = parser.parse_args(argv)
    codes = args.codes or None
    if args.check:
        stale = stale_references(codes)
        if stale:
            print("stale REFERENCE.md:", ", ".join(stale))
            return 1
        print("REFERENCE.md files are current")
        return 0
    changed = write_references(codes)
    print("rewrote:", ", ".join(changed) if changed else "nothing (all current)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
