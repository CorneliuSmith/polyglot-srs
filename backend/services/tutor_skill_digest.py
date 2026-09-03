"""Fold what the cleaning work learned about a language into its tutor.

Each tutor bundle carries `ERRORS.md` — the interference errors and
coaching moves the tutor consults on demand. It is hand-written, and until
3 Sep 2026 nothing connected it to the place the language insights actually
accumulate: `docs/quality/<code>.md`, the per-language standard the cleaning
passes maintain, and the open review notes. The one documented bridge was a
habit ("a human folds `ERRORS.extracted.md` into `ERRORS.md`") that only
French ever exercised. So the tutors were not getting the insights, and
there was no mechanism by which they would (brief item 6).

This module is the mechanism, in two parts:

1. **The digest** (`scripts/tutor_skill_digest.py <code>`): reads the
   standard (its "Language profile" section — the part about the language,
   not about the data files) and, with a database URL, the open review
   notes; asks the summary model for learner-error bullets in ERRORS.md's
   own style; writes them to `ERRORS.extracted.md` with a stamp naming the
   standard's content hash; prints the diff against `ERRORS.md`. A human
   folds it in — the tutor's brief is never rewritten by a script — and
   carries the stamp across.

2. **The check** (`tests/test_tutor_skill_digest.py`): every language with a
   standard must have an `ERRORS.md` stamped with the standard's CURRENT
   hash, or be listed in NEVER_DIGESTED. A standard that changes after its
   last digest fails the build naming the language and the command. That is
   "have the personas been updated with the language insights", made
   mechanical.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
QUALITY_DIR = REPO / "docs" / "quality"
SKILLS_DIR = Path(__file__).parent / "tutor_skills"

STAMP_RE = re.compile(r"<!-- digest: docs/quality/([a-z]+)\.md@([0-9a-f]{12}) -->")

# Languages whose ERRORS.md predates the digest and has never been through
# it. The check tolerates the missing stamp for these, and ONLY these; the
# first digest for a language removes it from this set (the test fails if
# a listed language is stamped, so the list cannot go stale). Every course
# started here on 3 Sep 2026: the digest needs a model key, and running it
# 27 times is the owner's spend to authorise, not a test's.
NEVER_DIGESTED = frozenset({
    "ar", "ca", "de", "el", "en", "es", "fa", "fr", "ha", "he", "hi", "id",
    "it", "jam", "ko", "la", "mi", "nl", "pt", "ro", "ru", "sw", "th", "tl",
    "tr", "xh", "yo",
})

# Sentences worth a tutor's attention, when no model is available: the
# standard is written for content cleaners, and only some of it is about
# what learners get wrong.
_ERROR_CUES = re.compile(
    r"\b(learner|learners|error|errors|mistake|mistakes|confus\w*|wrong|"
    r"tempt\w*|forget\w*|drop\w*|hard\b|hardest|trap|pitfall|interferen\w*)\b",
    re.IGNORECASE,
)


def quality_path(code: str, quality_dir: Path = QUALITY_DIR) -> Path:
    return quality_dir / f"{code}.md"


def quality_hash(code: str, quality_dir: Path = QUALITY_DIR) -> str | None:
    """Twelve hex chars of the standard's content — the stamp's value."""
    path = quality_path(code, quality_dir)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def stamp_line(code: str, digest: str) -> str:
    return f"<!-- digest: docs/quality/{code}.md@{digest} -->"


def stamped_hash(text: str) -> str | None:
    """The hash an ERRORS.md / ERRORS.extracted.md was digested from."""
    m = STAMP_RE.search(text)
    return m.group(2) if m else None


def digest_status(code: str, quality_dir: Path = QUALITY_DIR,
                  skills_dir: Path = SKILLS_DIR) -> str:
    """'current' | 'stale' | 'never' | 'no-standard' | 'no-tutor'."""
    want = quality_hash(code, quality_dir)
    if want is None:
        return "no-standard"
    errors = skills_dir / code / "ERRORS.md"
    if not errors.is_file():
        return "no-tutor"
    have = stamped_hash(errors.read_text(encoding="utf-8"))
    if have is None:
        return "never"
    return "current" if have == want else "stale"


def profile_section(standard: str) -> str:
    """The '## Language profile' body — the part of the standard that is
    about the language rather than about the files."""
    m = re.search(r"^## Language profile\s*$(.*?)(?=^## |\Z)", standard,
                  re.MULTILINE | re.DOTALL)
    return (m.group(1) if m else standard).strip()


def mechanical_digest(standard: str, notes: list[str] = ()) -> list[str]:
    """No-model fallback: the profile's sentences that talk about what
    learners do, plus every open note, as plain bullets. Good enough to
    show a human where to look; not good enough to paste into ERRORS.md."""
    body = profile_section(standard)
    body = re.sub(r"`[^`]*`", lambda m: m.group(0), body)
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(body.split()))
    out = [s.strip() for s in sentences if _ERROR_CUES.search(s)]
    out += [n.strip() for n in notes if n.strip()]
    return out[:25]


def render_extracted(code: str, name: str, bullets: list[str],
                     digest: str, sources: list[str]) -> str:
    lines = [
        f"# Common learner errors — {name} ({code})",
        "",
        "_Digest of " + ", ".join(sources) + "; review before folding into "
        "ERRORS.md, and carry the stamp below across when you do._",
        "",
        stamp_line(code, digest),
        "",
    ]
    for b in bullets:
        b = b.strip()
        lines.append(b if b.startswith("- ") else f"- {b}")
    lines.append("")
    return "\n".join(lines)


_MODEL_SYSTEM = (
    "You maintain the coaching notes a language tutor consults about common "
    "learner errors. You are given the language's content-quality standard "
    "(written for the people cleaning the course data — much of it is about "
    "files, not learners) and open reviewer notes. Extract ONLY what a tutor "
    "should know about the mistakes learners of this language make and how "
    "to coach them. Write markdown bullets in this exact style:\n"
    "- **Short name of the error.** One to three sentences: the mistake, "
    "why it happens, the coaching move.\n"
    "Six to twelve bullets. Do not describe the data files, the app, or "
    "the standard itself. Do not repeat a point already in the existing "
    "notes unless the sources add something to it."
)


async def model_digest(code: str, name: str, standard: str, notes: list[str],
                       existing_errors: str, model: str | None = None) -> list[str]:
    """Ask the summary model for the bullets. Import-local so the module
    (and its tests) never need the SDK."""
    from anthropic import AsyncAnthropic

    from backend.config import get_settings

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    notes_text = "\n".join(f"- {n}" for n in notes) or "(none)"
    content = (
        f"Language: {name} ({code})\n\n"
        f"## Existing ERRORS.md\n{existing_errors.strip() or '(empty)'}\n\n"
        f"## Language profile (from docs/quality/{code}.md)\n"
        f"{profile_section(standard)}\n\n"
        f"## Open reviewer notes\n{notes_text}"
    )
    resp = await client.messages.create(
        model=model or settings.tutor_summary_model,
        max_tokens=2048,
        system=_MODEL_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return [ln.strip() for ln in text.splitlines() if ln.strip().startswith("- ")]


OPEN_NOTES_SQL = """
    SELECT COALESCE(gp.title, v.word) AS about, n.note
      FROM point_review_notes n
      LEFT JOIN grammar_points gp ON n.grammar_point_id = gp.id
      LEFT JOIN vocabulary v ON n.vocabulary_id = v.id
      JOIN languages l ON l.id = COALESCE(gp.language_id, v.language_id)
     WHERE n.status = 'open' AND l.code = $1
     ORDER BY n.created_at
     LIMIT 200
"""


async def open_notes(db_url: str, code: str) -> list[str]:
    """The language's open review notes, as '<card>: <note>' lines."""
    import asyncpg

    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(OPEN_NOTES_SQL, code)
    finally:
        await conn.close()
    return [f"{r['about']}: {r['note']}" if r["about"] else r["note"] for r in rows]
