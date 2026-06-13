"""AI grammar-curriculum generator.

Generates grammar points and fill-in-the-blank drill sentences for a language
(the structural layer the explanation generator and contributor tools can't
produce), then SELF-VALIDATES every generated drill through that language's
own NLP backend before keeping it. A drill survives only if:

  1. its sentence contains the literal {{answer}} blank,
  2. filling the blank with `answer` reproduces the model's full_sentence
     (so the blank and the answer actually agree), and
  3. the answer validates as CORRECT through the exact same NLP path the
     review screen uses — i.e. the card is guaranteed answerable.

This catches mechanical failures (missing blank, mismatched answer, wrong
script) automatically. Semantic correctness — is this actually good grammar?
— still needs a human, so everything is written as source='ai', reviewed=
false for a specialist to approve in the contributor tool.

A dev mock mode (TUTOR_DEV_MOCK) produces a canned, structurally-valid
curriculum so the pipeline (including NLP validation) is testable with no key.

CLI:
    python -m backend.services.seeder.generate_curriculum --language sw --generate
    python -m backend.services.seeder.generate_curriculum --language yo --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import unicodedata

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.drills import is_answerable
from backend.services.nlp import init_nlp_backends
from backend.services.seeder.seed_grammar import GrammarSeeder
from backend.services.tutor import _LANGUAGE_BRIEFS

logger = logging.getLogger("generate_curriculum")

_CURRICULUM_SCHEMA = {
    "type": "object",
    "properties": {
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "explanation": {"type": "string"},
                    "culture_note": {"type": "string"},
                    "drills": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sentence": {
                                    "type": "string",
                                    "description": "A natural sentence with the target form replaced by the literal token {{answer}}.",
                                },
                                "answer": {
                                    "type": "string",
                                    "description": "The exact inflected form that fills the {{answer}} blank.",
                                },
                                "full_sentence": {
                                    "type": "string",
                                    "description": "The sentence with {{answer}} replaced by the answer (used to verify consistency).",
                                },
                                "translation": {"type": "string"},
                                "hint": {"type": "string"},
                            },
                            "required": ["sentence", "answer", "full_sentence", "translation", "hint"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "explanation", "culture_note", "drills"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["points"],
    "additionalProperties": False,
}


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


def _mock_curriculum(language_code: str, level: str) -> dict:
    return {
        "points": [
            {
                "title": f"[dev mock] {language_code} {level} point",
                "explanation": "[dev mock] explanation — set ANTHROPIC_API_KEY for real content.",
                "culture_note": "",
                "drills": [
                    {
                        "sentence": "Kitap {{answer}}.",
                        "answer": "masada",
                        "full_sentence": "Kitap masada.",
                        "translation": "The book is on the table.",
                        "hint": "masa + -da",
                    },
                    {
                        # Deliberately broken (blank/answer mismatch) — validation must drop it.
                        "sentence": "Araba {{answer}}.",
                        "answer": "evde",
                        "full_sentence": "Araba garajda.",
                        "translation": "The car is in the garage.",
                        "hint": "",
                    },
                ],
            }
        ]
    }


async def generate_curriculum(
    language_code: str, level: str = "A1", num_points: int = 6
) -> dict:
    """Generate a raw curriculum (points + drills) via Claude, or mock."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_curriculum(language_code, level)

    brief = _LANGUAGE_BRIEFS.get(language_code, f"Language code: {language_code}.")
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.tutor_model,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=(
            "You design beginner language-learning grammar curricula. Produce "
            "accurate, foundational grammar points with fill-in-the-blank drills. "
            "Every drill sentence must contain the literal token {{answer}} where "
            "the target form goes, `answer` must be the exact inflected form that "
            "fills it, and `full_sentence` must equal the sentence with {{answer}} "
            "replaced by `answer`. Keep sentences short and unambiguous.\n\n" + brief
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Create {num_points} essential {level}-level grammar points for "
                "this language, each with 2 drill sentences."
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": _CURRICULUM_SCHEMA}},
    )
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {"points": []}


async def validate_drill(language_code: str, drill: dict) -> bool:
    """True if a drill is structurally sound AND answerable via the NLP backend."""
    sentence = (drill.get("sentence") or "").strip()
    answer = (drill.get("answer") or "").strip()
    full = (drill.get("full_sentence") or "").strip()
    if "{{answer}}" not in sentence or not answer:
        return False
    # The model's full_sentence must equal the sentence with the blank filled,
    # so the blank and the answer actually agree.
    if _nfc(sentence.replace("{{answer}}", answer)) != _nfc(full):
        return False
    return await is_answerable(language_code, answer)


async def validate_curriculum(
    language_code: str, raw: dict, level: str = "A1"
) -> dict:
    """Filter a raw curriculum to answerable drills, in GrammarSeeder.load shape.

    Drops invalid drills and any point left with no valid drill. Marks
    everything source='ai', reviewed=false (pending specialist approval).
    """
    points_out = []
    for i, p in enumerate(raw.get("points", []), start=1):
        title = (p.get("title") or "").strip()
        if not title:
            continue
        drills = []
        for d in p.get("drills", []):
            if await validate_drill(language_code, d):
                drills.append({
                    "sentence": d["sentence"].strip(),
                    "answer": d["answer"].strip(),
                    "translation": (d.get("translation") or "").strip() or None,
                    "hint": (d.get("hint") or "").strip() or None,
                    "display_order": len(drills) + 1,
                })
        if not drills:
            continue
        points_out.append({
            "title": title,
            "level": level,
            "explanation": (p.get("explanation") or "").strip() or None,
            "culture_note": (p.get("culture_note") or "").strip() or None,
            "source": "ai",
            "reviewed": False,
            "display_order": i,
            "references": [],
            "drills": drills,
        })
    lists = [{
        "level": level,
        "title": f"{language_code.upper()} {level} Grammar",
        "description": "AI-generated grammar curriculum (pending review).",
    }]
    return {"lists": lists, "points": points_out}


async def generate_and_load(
    db_url: str, language_code: str, level: str, num_points: int, dry_run: bool
) -> dict:
    """Full pipeline: generate -> NLP-validate -> (load or report)."""
    init_nlp_backends()
    raw = await generate_curriculum(language_code, level, num_points)
    raw_drills = sum(len(p.get("drills", [])) for p in raw.get("points", []))
    cleaned = await validate_curriculum(language_code, raw, level)
    kept_drills = sum(len(p["drills"]) for p in cleaned["points"])

    report = {
        "raw_points": len(raw.get("points", [])),
        "raw_drills": raw_drills,
        "kept_points": len(cleaned["points"]),
        "kept_drills": kept_drills,
    }
    if not dry_run and cleaned["points"]:
        await GrammarSeeder(db_url, language_code).load(cleaned)
        report["loaded"] = True
    return report


async def _main() -> None:
    import os

    parser = argparse.ArgumentParser(description="AI-generate a grammar curriculum")
    parser.add_argument("--language", "-l", required=True)
    parser.add_argument("--level", default="A1")
    parser.add_argument("--num-points", type=int, default=6)
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--generate", action="store_true", help="Write to the DB")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report only")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    dry = args.dry_run or not args.generate
    if not dry and not args.db_url:
        print("ERROR: DATABASE_URL not set (or use --dry-run).")
        return
    report = await generate_and_load(
        args.db_url, args.language, args.level, args.num_points, dry
    )
    print(json.dumps(report, indent=2))
    if dry:
        print("(dry run — nothing written; re-run with --generate to load)")


if __name__ == "__main__":
    asyncio.run(_main())
