"""What is this server running? — the answer `/api/health` gives.

Written after three rounds of "I still don't see the setting" against the
deployed app. The setting was on `main`; whether the deployed build HAD it
was unknowable, because `/api/health` said `{"status": "ok"}` and nothing
else. A health endpoint that cannot say what it is running turns every
"is it deployed yet?" into a guess.

Three facts, each from wherever it is actually available:

  * `sha` — the git commit. From `BUILD_SHA` (the Dockerfile's build arg)
    when the platform passes one; from `.git` when running from a checkout;
    otherwise null. DigitalOcean's Docker build passes no commit by default,
    so in production this is usually null and `built_at` is the
    identifying fact — say so rather than inventing one.
  * `built_at` — written by the image build itself (`/app/BUILD_TIME`), not
    by the app at boot, so a restart of last week's image does not look
    like a fresh deploy. Null outside an image.
  * `latest_migration` — the newest migration file this build SHIPS, which
    is the newest one it expects the database to have. Paired with
    `/api/health/schema` this is the whole "is the database behind?"
    conversation in two numbers.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

from backend.services.schema_check import MIGRATIONS_DIR

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_TIME_FILE = REPO_ROOT / "BUILD_TIME"


def _sha_from_env() -> str | None:
    for name in ("BUILD_SHA", "SOURCE_COMMIT", "RENDER_GIT_COMMIT", "GIT_SHA"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _sha_from_checkout() -> str | None:
    if not (REPO_ROOT / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = out.stdout.strip()
    return sha or None


def _built_at() -> str | None:
    try:
        text = BUILD_TIME_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def _latest_migration(migrations_dir: Path | None = None) -> str | None:
    directory = migrations_dir or MIGRATIONS_DIR
    if not directory.is_dir():
        return None
    names = sorted(p.name for p in directory.glob("*.sql"))
    return names[-1] if names else None


def _migrations_shipped(migrations_dir: Path | None = None) -> int:
    directory = migrations_dir or MIGRATIONS_DIR
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.glob("*.sql"))


@lru_cache(maxsize=1)
def build_info() -> dict:
    """The stamp, computed once — none of it changes while the process lives."""
    return {
        "sha": _sha_from_env() or _sha_from_checkout(),
        "built_at": _built_at(),
        "latest_migration": _latest_migration(),
        # Zero here is the "blind diagnostic" signal: the image shipped no
        # migration files, so /api/health/schema has nothing to check
        # against and its `ok: true` means nothing.
        "migrations_shipped": _migrations_shipped(),
    }
