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

  # Quality-audit EXISTING English sentences: an LLM judge flags bad ones for
  # review, backfills missing translations, and tops each word back up to 3
  # good sentences with fresh alternatives (up to 100 words):
  python -m backend.services.seeder.generate_content -l en -k vocab --recheck --target 3 --max 100

  # Fill missing English definitions for a low-density language (Swahili),
  # gated for review (or applied live if the language is 'ai_ok'):
  python -m backend.services.seeder.generate_content -l sw -k definitions --max 200

  # Translate existing English example sentences into a support locale (for a
  # non-English speaker learning English), gated for review:
  python -m backend.services.seeder.generate_content -l en -k translations --locale ru --max 200
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

from backend.config import get_settings
from backend.repositories.contributor import (
    add_example_sentence,
    apply_definition,
    ensure_vocab_content_list,
    get_language_policy,
    queue_definition_review,
    sentences_needing_locale,
    set_vocab_ai_level,
    vocab_needing_definition,
    vocab_needing_level,
)
from backend.repositories.pool import close_pool, init_pool, privileged_connection
from backend.services.define import definitions_available, generate_definitions
from backend.services.generate import generation_available
from backend.services.generation_admin import (
    plan_recheck,
    plan_run,
    recheck_examples,
    run_generation,
)
from backend.services.level_estimate import estimate_levels
from backend.services.translate import (
    generate_sentence_translations,
    translations_available,
)

logger = logging.getLogger("generate_content")


async def _run_levels(conn, lang, args) -> None:
    """AI-estimate a CEFR level for words that have none, so they can enter a
    deck (level_source='ai', pending a reviewer's confirm)."""
    words = await vocab_needing_level(conn, str(lang["id"]), args.max)
    if not words:
        print(f"No un-leveled {lang['name']} words — nothing to do.")
        return
    if args.dry_run:
        print(json.dumps({
            "dry_run": True, "kind": "levels",
            "words_without_level": len(words),
        }, indent=2))
        return
    if not generation_available():
        print("ERROR: real estimation needs ANTHROPIC_API_KEY (or TUTOR_DEV_MOCK=1).")
        return
    print(f"Estimating levels for {len(words)} {lang['name']} words…")
    levels = await estimate_levels(words, lang["name"], lang["code"])
    applied = 0
    for w in words:
        level = levels.get(w["word"])
        if not level:
            continue
        if await set_vocab_ai_level(conn, w["vocabulary_id"], level):
            await ensure_vocab_content_list(conn, str(lang["id"]), level, lang["code"])
            applied += 1
    print(json.dumps({
        "dry_run": False, "kind": "levels",
        "words_without_level": len(words), "levels_applied": applied,
    }, indent=2))
    print(
        "\nEstimated levels are provisional (level_source='ai'). Confirm them in "
        "Contributor › Review; under Strict policy they stay out of learners' "
        "decks until confirmed."
    )


async def _locale_language_name(conn, locale: str) -> str:
    """Human name of a locale for the maker/checker prompts ('en' → English)."""
    if locale == "en":
        return "English"
    name = await conn.fetchval("SELECT name FROM languages WHERE code = $1", locale)
    return name or locale


async def _run_definitions(conn, lang, args) -> None:
    """Maker-check a DEFINITION for words that have none in --locale (English by
    default). Gated: definitions land in the translation-review queue for a human
    unless the language policy is 'ai_ok', in which case they apply directly."""
    lang_id = str(lang["id"])
    locale = args.locale
    words = await vocab_needing_definition(conn, lang_id, locale, args.max)
    if not words:
        print(f"No {lang['name']} words missing a '{locale}' definition — nothing to do.")
        return
    if args.dry_run:
        print(json.dumps({
            "dry_run": True, "kind": "definitions", "locale": locale,
            "words_without_definition": len(words),
        }, indent=2))
        return
    if not definitions_available():
        print("ERROR: real generation needs ANTHROPIC_API_KEY (or TUTOR_DEV_MOCK=1).")
        return

    locale_language = await _locale_language_name(conn, locale)
    policy = await get_language_policy(conn, lang_id)
    items = [
        {"i": n, "word": w["word"], "pos": w["part_of_speech"], "example": w["example"]}
        for n, w in enumerate(words)
    ]
    print(
        f"Defining {len(items)} {lang['name']} words in {locale_language} "
        f"(policy: {policy})…"
    )
    results = await generate_definitions(lang["name"], locale_language, items)
    by_i = {w_i["i"]: w for w_i, w in zip(items, words)}

    applied = queued = 0
    for r in results:
        word = by_i[r["i"]]
        vid = word["vocabulary_id"]
        if r["verdict"] in ("ok", "fixed") and r["definition"]:
            if policy == "ai_ok":
                if await apply_definition(conn, vid, locale, r["definition"]):
                    applied += 1
                continue
            await queue_definition_review(conn, vid, locale, r["definition"], r["note"])
            queued += 1
        else:
            # Checker rejected — queue for a human with the reason, no definition.
            await queue_definition_review(conn, vid, locale, "", r["note"])
            queued += 1

    print(json.dumps({
        "dry_run": False, "kind": "definitions", "locale": locale,
        "words_processed": len(results), "applied_live": applied,
        "queued_for_review": queued,
    }, indent=2))
    print(
        "\nDefinitions applied 'live' only on an 'ai_ok' language. Otherwise they "
        "wait in Contributor › Review (translation reviews) for approval."
        if policy != "ai_ok" else
        "\nThis language is 'ai_ok', so checker-passed definitions went live; "
        "rejects are queued for review."
    )


async def _run_translations(conn, lang, args) -> None:
    """Translate existing English example sentences into --locale (a support
    locale for a non-English speaker learning English). New locale rows land
    source='ai', reviewed=false — gated like other AI content, and the learner
    keeps seeing the English fallback until each is approved."""
    lang_id = str(lang["id"])
    locale = args.locale
    sents = await sentences_needing_locale(conn, lang_id, locale, args.max)
    if not sents:
        print(f"No {lang['name']} sentences missing a '{locale}' translation.")
        return
    if args.dry_run:
        print(json.dumps({
            "dry_run": True, "kind": "translations", "locale": locale,
            "sentences_without_translation": len(sents),
        }, indent=2))
        return
    if not translations_available():
        print("ERROR: real generation needs ANTHROPIC_API_KEY (or TUTOR_DEV_MOCK=1).")
        return

    locale_language = await _locale_language_name(conn, locale)
    items = [{"i": n, "sentence": s["sentence"]} for n, s in enumerate(sents)]
    print(f"Translating {len(items)} {lang['name']} sentences into {locale_language}…")
    results = await generate_sentence_translations(locale_language, items)
    by_i = {n: s for n, s in enumerate(sents)}

    stored = queued_reject = 0
    for r in results:
        s = by_i[r["i"]]
        if r["verdict"] in ("ok", "fixed") and r["translation"]:
            row_id = await add_example_sentence(
                conn, s["vocabulary_id"], lang_id, s["sentence"], r["translation"],
                source="ai", origin_detail=f"translate:{locale}",
                translation_locale=locale,
            )
            if row_id:
                stored += 1
        else:
            queued_reject += 1

    print(json.dumps({
        "dry_run": False, "kind": "translations", "locale": locale,
        "sentences_processed": len(results),
        "translations_stored": stored, "rejected": queued_reject,
    }, indent=2))
    print(
        "\nStored translations are pending review (source='ai') — approve them in "
        "the generation panel. Learners see the English fallback until then."
    )


async def _run_recheck(conn, lang, args) -> None:
    """Quality-audit EXISTING example sentences: an LLM judge flags bad ones for
    reviewers, missing translations are backfilled, and each word is topped back
    up to --target with fresh alternatives (source='ai', pending review)."""
    lang_id = str(lang["id"])
    if args.dry_run:
        plan = await plan_recheck(
            conn, language_id=lang_id, language_code=lang["code"],
            max_items=args.max,
        )
        plan.pop("_items", None)
        print(json.dumps({"dry_run": True, **plan}, indent=2, default=str))
        return
    if not generation_available():
        print("ERROR: real recheck needs ANTHROPIC_API_KEY (or TUTOR_DEV_MOCK=1).")
        return
    print(
        f"Rechecking {lang['name']} example sentences "
        f"(target {args.target} good per word, up to {args.max} words)…"
    )
    result = await recheck_examples(
        conn, language_id=lang_id, language_code=lang["code"],
        language_name=lang["name"], target_per_item=args.target,
        max_items=args.max,
    )
    print(json.dumps({"dry_run": False, **result}, indent=2, default=str))
    print(
        "\nFlagged sentences (weak or too simple) are marked for reviewers "
        "(Contributor › Review) — not deleted. Weak translations get a suggested "
        "replacement to accept/dismiss. New alternatives are pending review "
        "(source='ai')."
    )


async def _run(args: argparse.Namespace) -> None:
    async with privileged_connection() as conn:
        lang = await conn.fetchrow(
            "SELECT id, code, name FROM languages WHERE code = $1", args.language
        )
        if lang is None:
            print(f"ERROR: no language with code {args.language!r}.")
            return
        lang_id = str(lang["id"])

        if args.kind == "levels":
            await _run_levels(conn, lang, args)
            return

        if args.kind == "definitions":
            await _run_definitions(conn, lang, args)
            return

        if args.kind == "translations":
            await _run_translations(conn, lang, args)
            return

        if args.recheck:
            await _run_recheck(conn, lang, args)
            return

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
    parser.add_argument(
        "--kind", "-k",
        choices=["vocab", "grammar", "levels", "definitions", "translations"],
        required=True,
    )
    parser.add_argument(
        "--target", type=int, default=3,
        help="target example sentences per word (vocab) / drills per grammar cell",
    )
    parser.add_argument(
        "--max", type=int, default=200,
        help="maximum gap items to touch in this run",
    )
    parser.add_argument(
        "--locale", default="en",
        help="definitions only: locale the definition is written IN (default en)",
    )
    parser.add_argument(
        "--recheck", action="store_true",
        help="vocab only: LLM-audit EXISTING sentences, flag bad ones for "
        "review, backfill missing translations, top each word back up to "
        "--target with fresh alternatives",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="resolve the work-list and cost estimate only; no model call",
    )
    args = parser.parse_args()
    if args.recheck and args.kind != "vocab":
        parser.error("--recheck applies to -k vocab only")
    if args.kind == "translations":
        if args.locale == "en":
            parser.error("-k translations needs a non-English --locale (e.g. --locale ru)")
        if args.language != "en":
            parser.error(
                "-k translations serves the English course only — use -l en "
                "(support-locale translations aren't served for other languages)"
            )
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    settings = get_settings()
    await init_pool(settings.database_url)
    try:
        await _run(args)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
