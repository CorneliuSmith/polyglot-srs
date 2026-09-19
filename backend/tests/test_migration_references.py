"""Every migration a source file names must exist on disk.

A migration's version is not stable. Supabase keys `schema_migrations` on the
timestamp digits, so two branches that pick the same stamp collide, and the
push fails with "Found local migration files to be inserted before the last
migration on remote database" — which reads like an ordering problem and is
really a taken version. The fix is to re-stamp the file, and on 19 Sep 2026
that happened to two telemetry migrations mid-review.

What it left behind is the reason for this test. Nineteen places still named
`20261029`, including the 503 detail the API returns, the Deployment panel's
copy and the Quality settings panel's disabled-state message — every one of
them telling the owner to apply a migration that is no longer the one they
need, at the exact moment they were trying to apply it. A stale comment is a
nuisance; a stale instruction in a user-facing error is a wrong answer to
"what do I do now".

**And the obvious guard would not have caught it.** `20261029` and `20261030`
were not freed by the rename — they are still on disk, now held by two
`provisional_strokes_*` migrations. So a test that only asks "does this stamp
exist" passes on a reference that has come to name a completely different
migration, which is worse than a dangling one. That is why the third test
below resolves each table to the file that actually creates it, and the first
two are the cheap net underneath it.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "supabase" / "migrations"

# A migration stamp is 14 digits. Four- and six-digit years are not, and
# neither is a rank, a count or a date written any other way.
STAMP = re.compile(r"\b(20\d{12})\b")
# `migration 20261107` — the shorthand the prose uses: eight digits, no file.
SHORT = re.compile(r"\bmigrations?\s+(20\d{6})\b", re.IGNORECASE)

# The tables and columns whose migration the code names in a message an OWNER
# reads, mapped to the text that creates them. The third test below finds which
# file actually defines each and checks the code agrees — which is the only one
# of the three that could have caught 19 Sep.
OWNED: dict[str, str] = {
    "quality_runs": "CREATE TABLE IF NOT EXISTS quality_runs",
    "content_verdicts": "CREATE TABLE IF NOT EXISTS content_verdicts",
    "quality_settings": "CREATE TABLE IF NOT EXISTS quality_settings",
}

SEARCHED = ("backend", "frontend/src", "docs", "scripts")
SUFFIXES = {".py", ".ts", ".tsx", ".md", ".sql"}
SKIP_PARTS = {"node_modules", "__pycache__", ".venv", "dist", "migrations"}


def _sources() -> list[Path]:
    out = []
    for where in SEARCHED:
        root = REPO / where
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix not in SUFFIXES or not p.is_file():
                continue
            if SKIP_PARTS & set(p.parts):
                continue
            out.append(p)
    return out


def _stamps_on_disk() -> set[str]:
    return {m.name.split("_", 1)[0] for m in MIGRATIONS.glob("*.sql")}


def test_every_full_stamp_named_in_source_exists():
    """A 14-digit stamp is a filename. If it is not on disk, the reference is
    pointing at a migration that was renamed or never landed."""
    on_disk = _stamps_on_disk()
    assert on_disk, "no migrations found — run from the repo"
    dangling: dict[str, list[str]] = {}
    for path in _sources():
        for stamp in set(STAMP.findall(path.read_text(encoding="utf-8", errors="ignore"))):
            if stamp not in on_disk:
                dangling.setdefault(stamp, []).append(str(path.relative_to(REPO)))
    assert not dangling, (
        "these full migration stamps are named in source and do not exist: "
        f"{ {k: v[:3] for k, v in dangling.items()} }"
    )


def test_every_migration_shorthand_matches_a_real_one():
    """The prose and the UI say "migration 20261107" rather than the whole
    filename. That shorthand has to prefix something real — this is the form
    that went stale on 19 Sep and reached the API's 503 body."""
    prefixes = {s[:8] for s in _stamps_on_disk()}
    assert prefixes, "no migrations found — run from the repo"
    dangling: dict[str, list[str]] = {}
    for path in _sources():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for short in set(SHORT.findall(text)):
            if short not in prefixes:
                dangling.setdefault(short, []).append(str(path.relative_to(REPO)))
    assert not dangling, (
        'these "migration <stamp>" references name no migration on disk: '
        f"{ {k: v[:3] for k, v in dangling.items()} }"
    )


def _defining_stamp(needle: str) -> str | None:
    """The stamp of the migration whose text creates *needle*."""
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if needle in path.read_text(encoding="utf-8", errors="ignore"):
            return path.name.split("_", 1)[0]
    return None


def _quality_503_body() -> str:
    """The telemetry feature's own 503 helper, not the whole router.

    `contribute.py` is four thousand lines and carries a dozen features'
    migration messages, each correctly naming its own. Only this helper speaks
    for the telemetry tables.
    """
    text = (REPO / "backend" / "routers" / "contribute.py").read_text(encoding="utf-8")
    start = text.index("def _quality_503(")
    end = text.index("\ndef ", start + 1)
    return text[start:end]


def test_the_instruction_the_owner_reads_names_the_right_migration():
    """The one that would have caught 19 Sep.

    A stamp existing is not enough — `20261029` still exists and now holds a
    stroke migration, so a reference to it is not dangling, it is confidently
    wrong. This resolves `quality_runs` to the file that CREATES it and
    requires every place that tells the owner WHICH MIGRATION TO APPLY for the
    telemetry feature to name that one.

    Scoped to those instructions on purpose. A module may legitimately cite
    several migrations — `verdicts.py` names the one that added
    `vocabulary.retired_at` because it filters on that column — and a router
    shared by a dozen features names a dozen migrations. What must never be
    wrong is the sentence an owner acts on.
    """
    want = _defining_stamp(OWNED["quality_runs"])
    assert want, "no migration creates quality_runs"
    sources = {
        "backend/routers/contribute.py::_quality_503": _quality_503_body(),
    }
    for rel in ("backend/services/quality_loop.py",
                "frontend/src/features/contribute/QualitySettingsPanel.tsx",
                "frontend/src/features/contribute/ContentHealthPanel.tsx",
                "frontend/src/features/settings/DeploymentPanel.tsx"):
        path = REPO / rel
        if path.exists():
            sources[rel] = path.read_text(encoding="utf-8")
    named = re.compile(r"migration\s+(20\d{6,12})", re.IGNORECASE)
    wrong: dict[str, list[str]] = {}
    seen = 0
    for where, text in sources.items():
        for stamp in named.findall(text):
            seen += 1
            if stamp[:8] != want[:8]:
                wrong.setdefault(where, []).append(stamp)
    assert seen, "found no migration instruction to check — the shapes moved"
    assert not wrong, (
        f"quality_runs is created by {want}; these tell the owner to apply "
        f"something else: {wrong}"
    )
