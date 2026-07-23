"""Shared access to the Gym manifests (data/gym/{code}.json).

One loader so the router (which builds the picker) and serving (which weights
drills) agree on what a manifest says. The manifests are curated static data,
so parsing is cached per language code.
"""
from __future__ import annotations

import json
from functools import lru_cache

from backend.services.seeder.base import DATA_DIR

GYM_DIR = DATA_DIR / "gym"


def load_manifest(code: str) -> dict | None:
    """The raw manifest for a language, or None when it has no Gym."""
    path = GYM_DIR / f"{code}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def nonstandard_point_titles(code: str) -> frozenset[str]:
    """Titles of the form categories a language marks as non-standard —
    the pattern-breaking / irregular points (verbs of motion, etc.). Used to
    give those drills an adaptive-weight boost so irregulars surface more."""
    manifest = load_manifest(code)
    if not manifest:
        return frozenset()
    return frozenset(
        e["point"]
        for col in manifest.get("columns", [])
        for e in col.get("entries", [])
        if e.get("nonstandard")
    )
