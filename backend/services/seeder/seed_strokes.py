"""Seed the stroke library from data/strokes/{script}.json — a reviewed set
authored elsewhere lands without touching code, the same pattern as
data/alphabet/{code}.json for the alphabet decks.

File shape:
  {"script": "cyrillic",
   "glyphs": [{"glyph": "а", "form": "lower", "style": "cursive",
               "strokes": [[[x, y], ...], ...], "joins": {...}, "hints": [...],
               "reviewed": true}],
   "exemplars": [{"language_code": "ru", "style": "cursive",
                  "text": "...", "strokes": [...], "reviewed": true}]}

Idempotent: glyphs upsert on (script, glyph, form, style); exemplars are
skipped when the same (script, style, text) already exists.

CLI: python -m backend.services.seeder.seed_strokes --script cyrillic
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

import asyncpg

from backend.repositories.strokes import add_exemplar, upsert_glyph

from .base import COMMAND_TIMEOUT, DATA_DIR, close_quietly

logger = logging.getLogger("seed_strokes")
STROKES_DIR = DATA_DIR / "strokes"


def load_file(script: str) -> dict | None:
    path = STROKES_DIR / f"{script}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


async def seed(db_url: str, script: str) -> dict:
    data = load_file(script)
    if not data:
        return {"glyphs": 0, "exemplars": 0}
    conn = await asyncpg.connect(db_url, command_timeout=COMMAND_TIMEOUT)
    try:
        glyphs = 0
        for g in data.get("glyphs", []):
            row = await upsert_glyph(
                conn, script=script, glyph=g["glyph"], form=g.get("form", "letter"),
                style=g.get("style", "print"), strokes=g["strokes"],
                joins=g.get("joins"), hints=g.get("hints"), user_id=None,
                source="file", reviewed=bool(g.get("reviewed", False)))
            glyphs += 1 if row else 0
        exemplars = 0
        for e in data.get("exemplars", []):
            exists = await conn.fetchval(
                "SELECT 1 FROM script_exemplars WHERE script = $1 AND style = $2 AND text = $3",
                script, e.get("style", "print"), e["text"].strip())
            if exists:
                continue
            row = await add_exemplar(
                conn, script=script, language_code=e["language_code"],
                style=e.get("style", "print"), text=e["text"], strokes=e["strokes"],
                user_id=None, source="file", reviewed=bool(e.get("reviewed", False)))
            exemplars += 1 if row else 0
        return {"glyphs": glyphs, "exemplars": exemplars}
    finally:
        await close_quietly(conn)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", required=True)
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    if not args.db_url:
        raise SystemExit("DATABASE_URL (or --db-url) is required")
    print(await seed(args.db_url, args.script))


if __name__ == "__main__":
    asyncio.run(main())
