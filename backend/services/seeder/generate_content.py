"""CLI: maker–checker generation to fill example-sentence / drill gaps.

The same engine the admin panel uses (WP42), from the terminal. For each item
under its target, the maker drafts candidates and the checker verifies every
one before it's stored. Idempotent: only under-target items are touched and
inserts dedupe on the sentence text, so re-running continues rather than
duplicating — no wasted spend.

Generated content lands source='ai', reviewed=false — HIDDEN from learners
until a reviewer approves it (Contributor › Review). This command fills the
pool; approval is a separate, human step.

Environment:
  ANTHROPIC_API_KEY   real generation (omit + set TUTOR_DEV_MOCK=1 for a mock)
  DATABASE_URL        the target database
  SUPABASE_URL, SUPABASE_JWT_SECRET   required to construct app settings

Usage:
  # Dry run — show the work-list and a cost ESTIMATE, no model call:
  python -m backend.services.seeder.generate_content -l en -k vocab --dry-run

  # Generate 3 example sentences per under-covered English word (up to 200 words):
  python -m backend.services.seeder.generate_content -l en -k vocab --target 3 --max 200

  # Fill each thin grammar cell to 2 drills (up to 100 points):
  python -m backend.services.seeder.generate_content -l en -k grammar --target 2 --max 100
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

from backend.config import get_settings
from backend.repositories.pool import close_pool, init_pool, privileged_connection
from backend.services.generate import generation_available
from backend.services.generation_admin import plan_run, run_generation

logger = logging.getLogger("generate_content")


async def _run(args: argparse.Namespace) -> None:
    async with privileged_connection() as conn:
        lang = await conn.fetchrow(
            "SELECT id, code, name FROM languages WHERE code = $1", args.language
        )
        if lang is None:
            print(f"ERROR: no language with code {args.language!r}.")
            return
        lang_id = str(lang["id"])

        if args.dry_run:
            plan = await plan_run(
                conn, kind=args.kind, language_id=lang_id,
                language_code=lang["code"],
                target_per_item=args.target, max_items=args.max,
            )
            plan.pop("_items", None)
            print(json.dumps({"dry_run": True, **plan}, indent=2, default=str))
            return

        if not generation_available():
            print(
                "ERROR: real generation needs ANTHROPIC_API_KEY on the environment "
                "(or set TUTOR_DEV_MOCK=1 for a deterministic mock run)."
            )
            return

        print(
            f"Generating {args.kind} for {lang['name']} "
            f"(target {args.target}, up to {args.max} items)…"
        )
        result = await run_generation(
            conn, kind=args.kind, language_id=lang_id,
            language_code=lang["code"], language_name=lang["name"],
            target_per_item=args.target, max_items=args.max,
        )
        print(json.dumps({"dry_run": False, **result}, indent=2, default=str))
        print(
            "\nGenerated content is pending review (source='ai', reviewed=false). "
            "Approve it in Contributor › Review before learners see it."
        )


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Maker-checker generation for example sentences / drills."
    )
    parser.add_argument("--language", "-l", required=True, help="language code, e.g. en")
    parser.add_argument("--kind", "-k", choices=["vocab", "grammar"], required=True)
    parser.add_argument(
        "--target", type=int, default=3,
        help="target example sentences per word (vocab) / drills per grammar cell",
    )
    parser.add_argument(
        "--max", type=int, default=200,
        help="maximum gap items to touch in this run",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="resolve the work-list and cost estimate only; no model call",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    settings = get_settings()
    await init_pool(settings.database_url)
    try:
        await _run(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
