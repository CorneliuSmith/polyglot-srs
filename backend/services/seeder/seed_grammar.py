"""Grammar curriculum seeder — loads grammar points + drill sentences.

Reads a per-language curriculum file (data/grammar/{code}_grammar.json) and
populates grammar_points (with explanation, culture note, provenance), their
fill-in-the-blank drill_sentences (sentence + answer + translation + hint),
and a grammar content_list per level so the points are subscribable and
learnable. Re-running updates in place (UPSERT by language + title; drills are
replaced).

Curriculum file shape:
    {
      "lists":  [{"level": "A1", "title": "...", "description": "..."}],
      "points": [{
        "title": "...", "level": "A1", "display_order": 1,
        "explanation": "...", "culture_note": "",
        "source": "contributor", "reviewed": true,
        "drills": [{"sentence": "... {{answer}} ...", "answer": "...",
                    "translation": "...", "hint": "...", "display_order": 1}]
      }]
    }

CLI:
    python -m backend.services.seeder.seed_grammar --language ru
    python -m backend.services.seeder.seed_grammar --language all
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

import asyncpg

from backend.services.references import clean_references

from .base import DATA_DIR

GRAMMAR_DIR = DATA_DIR / "grammar"

logger = logging.getLogger("seed_grammar")

VALID_SOURCES = {"contributor", "ai", "wiktionary", "pending"}


class GrammarSeeder:
    """Loads a grammar curriculum JSON for one language into the DB."""

    def __init__(self, db_url: str, language_code: str):
        self.db_url = db_url
        self.language_code = language_code

    def transform(self) -> dict:
        """Parse and validate the curriculum file. No DB access (testable)."""
        path = GRAMMAR_DIR / f"{self.language_code}_grammar.json"
        if not path.exists():
            raise FileNotFoundError(f"No grammar curriculum at {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        points = []
        for p in data.get("points", []):
            title = (p.get("title") or "").strip()
            if not title:
                continue
            source = p.get("source") or "pending"
            if source not in VALID_SOURCES:
                source = "pending"
            drills = []
            for d in p.get("drills", []):
                sentence = (d.get("sentence") or "").strip()
                answer = (d.get("answer") or "").strip()
                if not sentence or not answer or "{{answer}}" not in sentence:
                    continue
                drills.append({
                    "sentence": sentence,
                    "answer": answer,
                    "translation": (d.get("translation") or "").strip() or None,
                    "hint": (d.get("hint") or "").strip() or None,
                    "gloss": (d.get("gloss") or "").strip() or None,
                    "transliteration": (d.get("transliteration") or "").strip() or None,
                    "display_order": int(d.get("display_order") or 0),
                })
            points.append({
                "title": title,
                "level": p.get("level"),
                "function": (p.get("function") or "").strip() or None,
                "explanation": (p.get("explanation") or "").strip() or None,
                "culture_note": (p.get("culture_note") or "").strip() or None,
                "source": source,
                "reviewed": bool(p.get("reviewed", False)),
                "display_order": int(p.get("display_order") or 0),
                "references": clean_references(p.get("references")),
                "drills": drills,
            })
        return {"lists": data.get("lists", []), "points": points}

    async def load(self, data: dict) -> int:
        """Write lists, points, and drills. Returns the number of points loaded."""
        conn = await asyncpg.connect(self.db_url)
        try:
            language_id = await conn.fetchval(
                "SELECT id FROM languages WHERE code = $1", self.language_code
            )
            if not language_id:
                raise ValueError(f"Language '{self.language_code}' not found in DB")

            for lst in data.get("lists", []):
                await conn.execute(
                    """
                    INSERT INTO content_lists (language_id, list_type, level, title, description)
                    VALUES ($1, 'grammar', $2, $3, $4)
                    ON CONFLICT (language_id, list_type, level) DO UPDATE SET
                        title = EXCLUDED.title, description = EXCLUDED.description
                    """,
                    language_id, lst.get("level"), lst.get("title", "Grammar"),
                    lst.get("description"),
                )

            count = 0
            for point in data["points"]:
                gp_id = await conn.fetchval(
                    """
                    INSERT INTO grammar_points
                        (language_id, title, function_note, explanation, culture_note,
                         level, display_order, explanation_source, reviewed, reference_links)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
                    ON CONFLICT (language_id, title) DO UPDATE SET
                        function_note = EXCLUDED.function_note,
                        explanation = EXCLUDED.explanation,
                        culture_note = EXCLUDED.culture_note,
                        level = EXCLUDED.level,
                        display_order = EXCLUDED.display_order,
                        explanation_source = EXCLUDED.explanation_source,
                        reviewed = EXCLUDED.reviewed,
                        reference_links = EXCLUDED.reference_links
                    RETURNING id
                    """,
                    language_id, point["title"], point.get("function"),
                    point["explanation"], point["culture_note"], point["level"],
                    point["display_order"], point["source"], point["reviewed"],
                    json.dumps(point.get("references") or [], ensure_ascii=False),
                )
                # Replace drills so re-seeding is idempotent.
                await conn.execute(
                    "DELETE FROM drill_sentences WHERE grammar_point_id = $1", gp_id
                )
                for d in point["drills"]:
                    await conn.execute(
                        """
                        INSERT INTO drill_sentences
                            (grammar_point_id, sentence, answer, translation, hint,
                             gloss, transliteration, display_order)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        gp_id, d["sentence"], d["answer"], d["translation"],
                        d["hint"], d.get("gloss"), d.get("transliteration"),
                        d["display_order"],
                    )
                count += 1

            logger.info("Loaded %d grammar points for %s", count, self.language_code)
            return count
        finally:
            await conn.close()

    async def run(self) -> int:
        return await self.load(self.transform())


def _available_languages() -> list[str]:
    if not GRAMMAR_DIR.exists():
        return []
    return sorted(
        p.name.removesuffix("_grammar.json")
        for p in GRAMMAR_DIR.glob("*_grammar.json")
    )


async def _main() -> None:
    import os

    parser = argparse.ArgumentParser(description="Seed grammar curricula")
    parser.add_argument("--language", "-l", default="all")
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        return

    languages = _available_languages() if args.language == "all" else [args.language]
    for lang in languages:
        try:
            n = await GrammarSeeder(args.db_url, lang).run()
            print(f"OK {lang}: {n} grammar points loaded")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {lang}: {e}")


if __name__ == "__main__":
    asyncio.run(_main())
