"""Harvest example sentences from app-generated Reader passages (WP25d).

The cheapest corpus growth there is: these sentences were already
generated (and paid for) at the learner's level — this recycles them
into the shared example pool for vocabulary that still lacks variety.

PRIVACY RULE (structural, absolute): only readings with
``source = 'generated'`` are read. The learner-typed *topic* is never
touched, and a future paste-a-passage mode (``source = 'pasted'``) is
excluded by the same predicate. Because topics can be personal and the
generated text inherits them, every candidate ALSO passes a checker
model that screens for references to private individuals, on top of
vulgarity/slurs, grammaticality, and word-sense fit.

Matching is accent-sensitive (the él/el lesson): a sentence exemplifies
a word only when the exact surface form appears.

Accepted rows land in example_sentences as ``source='harvested'`` with
an undo journal in data/backups. Idempotent: the (vocabulary_id,
sentence, translation_locale) unique key makes re-runs no-ops.

CLI:
    python -m backend.services.seeder.harvest_sentences --language es --dry-run
    python -m backend.services.seeder.harvest_sentences --language es
    python -m backend.services.seeder.harvest_sentences --all
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import asyncpg
from anthropic import AsyncAnthropic

from backend.config import get_settings

logger = logging.getLogger("harvest_sentences")

BACKUP_DIR = Path(__file__).resolve().parents[3] / "data" / "backups"

# A word stops collecting once it has this many examples; one run adds
# at most PER_RUN_CAP sentences per word so no single harvest floods it.
TARGET_EXAMPLES = 8
PER_RUN_CAP = 3

CHECKER_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["ok", "reject"]},
                    "reason": {"type": "string"},
                },
                "required": ["index", "verdict"],
            },
        }
    },
    "required": ["verdicts"],
}

CHECKER_PROMPT = """You are quality-gating sentences harvested from \
AI-generated readings before they become shared example sentences in a \
{language} course. For each numbered candidate, verdict "ok" only if ALL \
hold:
1. The sentence is natural, grammatical {language}.
2. It uses the word '{{word}}' in a common, teachable sense that matches \
its dictionary meaning.
3. No vulgarity, slurs, or adult content.
4. No references to specific private individuals (personal names in \
private contexts). Well-known public figures and place names are fine.
5. The English translation is faithful.
Reject anything doubtful — rejected sentences are simply dropped."""


def fold_free_present(word: str, sentence: str) -> bool:
    """Exact surface match, accent-sensitive, word-boundary."""
    w = re.escape(unicodedata.normalize("NFC", word.lower()))
    s = unicodedata.normalize("NFC", sentence.lower())
    return re.search(rf"(?<![^\W\d_]){w}(?![^\W\d_])", s) is not None


def collect_candidates(
    needy_words: dict[str, dict],
    readings_sentences: list[dict],
    existing: set[tuple[str, str]],
) -> list[dict]:
    """Pick sentences from generated readings for words short on examples.

    *needy_words*: lower word -> {"id": vocab_id, "have": count}
    *readings_sentences*: [{"text": ..., "translation": ...}]
    *existing*: {(lower word, sentence)} already in example_sentences
    """
    picked: list[dict] = []
    taken: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for s in readings_sentences:
        text = (s.get("text") or "").strip()
        translation = (s.get("translation") or "").strip()
        if not text or not translation:
            continue
        for word, info in needy_words.items():
            room = min(PER_RUN_CAP, TARGET_EXAMPLES - info["have"])
            if taken.get(word, 0) >= room:
                continue
            key = (word, text)
            if key in existing or key in seen:
                continue
            if not fold_free_present(word, text):
                continue
            seen.add(key)
            taken[word] = taken.get(word, 0) + 1
            picked.append({
                "word": word,
                "vocabulary_id": info["id"],
                "sentence": text,
                "translation": translation,
            })
    return picked


async def check_candidates(
    language_name: str, items: list[dict], model: str
) -> list[dict]:
    """Checker gate. Returns the accepted subset of *items*."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return items  # dev mock: accept everything
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    lines = [
        f"{i}. word='{it['word']}' sentence={it['sentence']!r} "
        f"translation={it['translation']!r}"
        for i, it in enumerate(items)
    ]
    resp = await client.messages.create(
        model=model,
        max_tokens=2048,
        system=CHECKER_PROMPT.format(language=language_name),
        messages=[{"role": "user", "content": "\n".join(lines)}],
        output_config={"format": {"type": "json_schema", "schema": CHECKER_SCHEMA}},
    )
    data = json.loads(resp.content[0].text)
    accepted = []
    for v in data.get("verdicts", []):
        i = v.get("index")
        if v.get("verdict") == "ok" and isinstance(i, int) and 0 <= i < len(items):
            accepted.append(items[i])
        elif v.get("verdict") == "reject":
            logger.info(
                "reject %s: %s", items[i]["word"] if isinstance(i, int) else "?",
                v.get("reason", ""),
            )
    return accepted


async def harvest(
    conn: asyncpg.Connection,
    code: str,
    model: str,
    limit: int | None = None,
    dry_run: bool = False,
    journal=None,
) -> tuple[int, int]:
    lang = await conn.fetchrow(
        "SELECT id, name FROM languages WHERE code = $1", code
    )
    if not lang:
        raise SystemExit(f"unknown language {code}")

    vocab = await conn.fetch(
        """
        SELECT v.id, v.word,
               (SELECT count(*) FROM example_sentences es
                 WHERE es.vocabulary_id = v.id) AS have
        FROM vocabulary v
        WHERE v.language_id = $1
        """,
        lang["id"],
    )
    needy = {
        r["word"].lower(): {"id": r["id"], "have": r["have"]}
        for r in vocab if r["have"] < TARGET_EXAMPLES
    }

    readings = await conn.fetch(
        """
        SELECT content FROM readings
        WHERE language_id = $1 AND source = 'generated'
        ORDER BY created_at DESC
        """,
        lang["id"],
    )
    sentences: list[dict] = []
    for r in readings:
        content = r["content"]
        if isinstance(content, str):
            content = json.loads(content)
        sentences.extend(content.get("sentences") or [])

    existing_rows = await conn.fetch(
        """
        SELECT lower(v.word) AS w, es.sentence
        FROM example_sentences es
        JOIN vocabulary v ON v.id = es.vocabulary_id
        WHERE es.language_id = $1
        """,
        lang["id"],
    )
    existing = {(r["w"], r["sentence"]) for r in existing_rows}

    candidates = collect_candidates(needy, sentences, existing)
    if limit:
        candidates = candidates[:limit]
    print(f"{code}: {len(readings)} generated readings, "
          f"{len(candidates)} candidates for {len(needy)} needy words")
    if dry_run or not candidates:
        for c in candidates[:10]:
            print(f"  {c['word']}: {c['sentence']}")
        return len(candidates), 0

    accepted = await check_candidates(lang["name"], candidates, model)
    inserted = 0
    for c in accepted:
        result = await conn.execute(
            """
            INSERT INTO example_sentences
                (language_id, vocabulary_id, sentence, translation,
                 difficulty_rank, source, license)
            VALUES ($1, $2, $3, $4, 1, 'harvested', NULL)
            ON CONFLICT (vocabulary_id, sentence, translation_locale)
                DO NOTHING
            """,
            lang["id"], c["vocabulary_id"], c["sentence"], c["translation"],
        )
        if result.endswith("1"):
            inserted += 1
            if journal:
                journal.write(json.dumps(
                    {"lang": code, "word": c["word"],
                     "sentence": c["sentence"]}, ensure_ascii=False) + "\n")
    print(f"{code}: checker accepted {len(accepted)}/{len(candidates)}, "
          f"inserted {inserted}")
    return len(candidates), inserted


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", help="one language code")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="claude-sonnet-5")
    args = parser.parse_args()
    if not args.language and not args.all:
        parser.error("--language CODE or --all")

    settings = get_settings()
    if (not args.dry_run and not settings.anthropic_api_key
            and not getattr(settings, "tutor_dev_mock", False)):
        raise SystemExit(
            "ANTHROPIC_API_KEY is required to run the checker gate "
            "(use --dry-run to preview candidates without it)"
        )

    conn = await asyncpg.connect(
        os.environ["DATABASE_URL"], statement_cache_size=0
    )
    journal = None
    if not args.dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        path = BACKUP_DIR / (
            f"harvest_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.jsonl"
        )
        journal = open(path, "w", encoding="utf-8")
        print("journal:", path)
    try:
        if args.all:
            codes = [r["code"] for r in await conn.fetch(
                "SELECT code FROM languages WHERE code <> 'yo' ORDER BY code"
            )]
        else:
            codes = [args.language]
        for code in codes:
            await harvest(
                conn, code, args.model,
                limit=args.limit, dry_run=args.dry_run, journal=journal,
            )
    finally:
        if journal:
            journal.close()
        await conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
