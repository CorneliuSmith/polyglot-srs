"""Grammar-content pipeline — populate grammar_points explanations 3 ways.

A learner who answers a grammar card can open the review panel to see a broad
explanation, a culture note, and examples. That text comes from one of three
sources, tracked in grammar_points.explanation_source:

  - contributor  : hand-authored by a language specialist. Highest trust;
                   imported via import_grammar_notes() and marked reviewed.
  - ai           : generated here by Claude, grounded on the language's
                   linguistics brief + the point's drill sentences, cached in
                   the DB. Starts unreviewed; a specialist can promote it.
  - wiktionary   : open-source usage notes (future; pulled from kaikki).

The AI generator never overwrites contributor/reviewed content. A dev mock
mode (TUTOR_DEV_MOCK) produces canned text so the panel can be populated and
tested with no API key.

CLI:
    # Generate AI explanations for grammar points that have none yet:
    python -m backend.services.seeder.generate_grammar --language ru --generate
    # Import hand-authored notes from a specialist:
    python -m backend.services.seeder.generate_grammar --language ru \
        --import-file data/ru_grammar_notes.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.tutor import _load_skill

logger = logging.getLogger("generate_grammar")

_CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {
            "type": "string",
            "description": (
                "A clear, learner-facing explanation of this grammar point: "
                "what it is, when to use it, and the rule, in a short paragraph. "
                "Use contrastive examples where helpful."
            ),
        },
        "culture_note": {
            "type": "string",
            "description": (
                "An optional note on register, regional variation, or cultural "
                "context a learner should know. Empty string if none applies."
            ),
        },
    },
    "required": ["explanation", "culture_note"],
    "additionalProperties": False,
}


def _mock_content(title: str) -> dict:
    return {
        "explanation": f"[dev mock] Explanation of '{title}'. Turn off "
                       "TUTOR_DEV_MOCK and set ANTHROPIC_API_KEY for real content.",
        "culture_note": "",
    }


async def generate_grammar_content(
    language_code: str,
    title: str,
    examples: list[str] | None = None,
    level: str | None = None,
) -> dict:
    """Generate {explanation, culture_note} for one grammar point via Claude."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_content(title)

    brief = _load_skill(language_code) or f"Language code: {language_code}."
    ex_text = "\n".join(f"- {e}" for e in (examples or [])) or "(none provided)"
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.tutor_summary_model,
        max_tokens=1024,
        system=(
            "You write concise, accurate grammar explanations for language "
            "learners. Ground every claim in the language's real grammar.\n\n"
            + brief
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Grammar point: {title}\n"
                f"CEFR level: {level or 'unknown'}\n"
                f"Example sentences:\n{ex_text}\n\n"
                "Write the explanation and an optional culture note."
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": _CONTENT_SCHEMA}},
    )
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {"explanation": "", "culture_note": ""}
    return {
        "explanation": data.get("explanation") or "",
        "culture_note": data.get("culture_note") or "",
    }


def parse_grammar_notes_file(path: str) -> list[dict]:
    """Parse a contributor JSON file: [{title, explanation, culture_note?}]."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    notes = []
    for row in data:
        title = (row.get("title") or "").strip()
        explanation = (row.get("explanation") or "").strip()
        if title and explanation:
            notes.append({
                "title": title,
                "explanation": explanation,
                "culture_note": (row.get("culture_note") or "").strip(),
            })
    return notes


async def import_grammar_notes(db_url: str, language_code: str, path: str) -> int:
    """Import hand-authored grammar notes; marks them contributor + reviewed."""
    import asyncpg

    notes = parse_grammar_notes_file(path)
    conn = await asyncpg.connect(db_url)
    try:
        language_id = await conn.fetchval(
            "SELECT id FROM languages WHERE code = $1", language_code
        )
        if not language_id:
            raise ValueError(f"Language '{language_code}' not found in DB")
        count = 0
        for note in notes:
            result = await conn.execute(
                """
                UPDATE grammar_points
                SET explanation = $3,
                    culture_note = NULLIF($4, ''),
                    explanation_source = 'contributor',
                    reviewed = true
                WHERE language_id = $1 AND title = $2
                """,
                language_id, note["title"], note["explanation"], note["culture_note"],
            )
            if result.endswith("1"):
                count += 1
        logger.info("Imported %d contributor grammar notes for %s", count, language_code)
        return count
    finally:
        await conn.close()


async def generate_for_language(db_url: str, language_code: str) -> int:
    """Generate AI explanations for grammar points lacking trusted content."""
    import asyncpg

    conn = await asyncpg.connect(db_url)
    try:
        language_id = await conn.fetchval(
            "SELECT id FROM languages WHERE code = $1", language_code
        )
        if not language_id:
            raise ValueError(f"Language '{language_code}' not found in DB")
        # Never overwrite contributor/reviewed content.
        points = await conn.fetch(
            """
            SELECT id, title, level
            FROM grammar_points
            WHERE language_id = $1
              AND explanation_source IN ('pending', 'ai')
              AND reviewed = false
            ORDER BY display_order
            """,
            language_id,
        )
        count = 0
        for p in points:
            examples = await conn.fetch(
                "SELECT sentence FROM drill_sentences WHERE grammar_point_id = $1 "
                "ORDER BY display_order LIMIT 5",
                p["id"],
            )
            content = await generate_grammar_content(
                language_code, p["title"],
                [e["sentence"] for e in examples], p["level"],
            )
            if not content["explanation"]:
                continue
            await conn.execute(
                """
                UPDATE grammar_points
                SET explanation = $2,
                    culture_note = NULLIF($3, ''),
                    explanation_source = 'ai'
                WHERE id = $1
                """,
                p["id"], content["explanation"], content["culture_note"],
            )
            count += 1
        logger.info("Generated %d AI grammar explanations for %s", count, language_code)
        return count
    finally:
        await conn.close()


async def _main() -> None:
    import os

    parser = argparse.ArgumentParser(description="Populate grammar explanations")
    parser.add_argument("--language", "-l", required=True)
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--generate", action="store_true", help="AI-generate missing explanations")
    parser.add_argument("--import-file", help="Import contributor notes (JSON)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        return
    if args.import_file:
        n = await import_grammar_notes(args.db_url, args.language, args.import_file)
        print(f"Imported {n} contributor notes for {args.language}")
    if args.generate:
        n = await generate_for_language(args.db_url, args.language)
        print(f"Generated {n} AI explanations for {args.language}")


if __name__ == "__main__":
    asyncio.run(_main())
