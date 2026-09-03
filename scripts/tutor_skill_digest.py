#!/usr/bin/env python3
"""Digest a language's quality standard (and open review notes) into
`tutor_skills/<code>/ERRORS.extracted.md` for a human to fold into ERRORS.md.

    .venv/bin/python scripts/tutor_skill_digest.py fr
    .venv/bin/python scripts/tutor_skill_digest.py fr --db-url "$DATABASE_URL"
    .venv/bin/python scripts/tutor_skill_digest.py fr --no-model   # cue-based, no key
    .venv/bin/python scripts/tutor_skill_digest.py --status         # every language

Prints a unified diff of the digest against the current ERRORS.md. Nothing
here rewrites ERRORS.md: the tutor's brief stays a human's document, and the
stamp line in the digest is what you carry across when you fold it in (the
test suite checks it against the standard's current content).
"""
from __future__ import annotations

import argparse
import asyncio
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import tutor_skill_digest as d  # noqa: E402
from backend.services.tutor_reference import LANGUAGE_NAMES  # noqa: E402


def _status_table() -> int:
    codes = sorted(p.stem for p in d.QUALITY_DIR.glob("*.md")
                   if (d.SKILLS_DIR / p.stem).is_dir())
    for code in codes:
        print(f"{code:4} {d.digest_status(code)}")
    return 0


async def _run(args: argparse.Namespace) -> int:
    code = args.code
    standard_path = d.quality_path(code)
    if not standard_path.is_file():
        print(f"no standard at {standard_path}", file=sys.stderr)
        return 2
    bundle = d.SKILLS_DIR / code
    if not bundle.is_dir():
        print(f"no tutor bundle at {bundle}", file=sys.stderr)
        return 2
    standard = standard_path.read_text(encoding="utf-8")
    errors_path = bundle / "ERRORS.md"
    existing = errors_path.read_text(encoding="utf-8") if errors_path.is_file() else ""
    sources = [f"docs/quality/{code}.md"]
    notes: list[str] = []
    if args.db_url:
        notes = await d.open_notes(args.db_url, code)
        sources.append(f"{len(notes)} open review notes")
    name = LANGUAGE_NAMES.get(code, code)
    if args.no_model:
        bullets = d.mechanical_digest(standard, notes)
    else:
        bullets = await d.model_digest(code, name, standard, notes, existing,
                                       model=args.model)
    digest = d.quality_hash(code) or ""
    text = d.render_extracted(code, name, bullets, digest, sources)
    out = bundle / "ERRORS.extracted.md"
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(bullets)} bullets)\n")
    sys.stdout.writelines(difflib.unified_diff(
        existing.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=str(errors_path), tofile=str(out)))
    print(f"\nWhen folded in, ERRORS.md must carry:\n  {d.stamp_line(code, digest)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("code", nargs="?", help="language code, e.g. fr")
    p.add_argument("--db-url", help="include the language's open review notes")
    p.add_argument("--model", help="override the summary model")
    p.add_argument("--no-model", action="store_true",
                   help="cue-based extraction only; needs no API key")
    p.add_argument("--status", action="store_true",
                   help="print each language's digest status and exit")
    args = p.parse_args()
    if args.status:
        return _status_table()
    if not args.code:
        p.error("a language code is required (or --status)")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
