"""Demand-driven support-locale gloss filling, as a background loop.

The manual CLI (seeder/translate_english.py) fills English-course glosses for
one locale when an operator runs it. This is the automated, generalized
version — the "translate by demand, not by matrix" rule as running code:

  - A (course, support locale) pair is worked on ONLY while at least one real
    account has that combination in user_profiles. No learners, no spend.
  - The course must have `languages.auto_translate_enabled` switched on by an
    admin (the language-management panel) — the loop's on/off switch, per
    learning language. Default off.
  - Each sweep translates a bounded number of words (settings
    .auto_translate_words_per_cycle), most-subscribed pair first, A1 before
    C2, frequent before rare — so cost per hour is capped and the content
    real learners face soonest fills first.

Every gloss goes through the same maker–checker as the CLI: approved ones
land in `translations` (the COALESCE overlay learners read), rejected ones in
`translation_reviews` for a human — never auto-applied. English is the pivot:
for a non-English course the maker renders the word's English definition into
the locale, so the English spine is a prerequisite, never replaced.

The loop runs under no user account and draws from NO learner's usage
allowance — the API cost lands on the operator's Anthropic key, on the cheap
translate-task model (resolve_model("translate")).

If migration 20260913 (the toggle column) hasn't been applied, the sweep
treats every language as switched off and does nothing — failing closed on
spend, per the missing-migrations-degrade rule.
"""
from __future__ import annotations

import asyncio
import logging

import asyncpg

from backend.config import get_settings
from backend.services.translate import (
    generate_sentence_translations,
    maker_check_batch,
    translations_available,
)

logger = logging.getLogger(__name__)

SWEEP_SECONDS = 15 * 60
# Words handed to one maker/checker call. Same default as the CLI.
BATCH_SIZE = 25

# A1 first: the loop fills what a beginner meets before what a C2 reader
# might. NULL levels (unleveled imports) go last.
_LEVEL_ORDER = "array_position(ARRAY['A1','A2','B1','B2','C1','C2'], v.level)"


async def discover_pairs(conn: asyncpg.Connection) -> list[dict]:
    """Live (course, locale) pairs the loop should serve, most learners first.

    A pair exists only when a real account is learning the course WITH that
    support locale. English support is the always-present spine (nothing to
    fill), and a locale equal to the course's own language would be a
    self-translation — both excluded. Fails closed (empty) when the toggle
    column's migration hasn't landed.
    """
    try:
        rows = await conn.fetch(
            """
            SELECT l.id   AS language_id,
                   l.code AS language_code,
                   l.name AS language_name,
                   loc.code AS locale,
                   loc.name AS locale_name,
                   count(*) AS learners
            FROM user_profiles p
            JOIN languages l   ON l.id = p.active_language_id
            JOIN languages loc ON loc.code = p.support_locale
            WHERE l.auto_translate_enabled
              AND p.support_locale IS NOT NULL
              AND p.support_locale <> 'en'
              AND loc.code <> l.code
            GROUP BY l.id, l.code, l.name, loc.code, loc.name
            ORDER BY count(*) DESC, l.name, loc.code
            """
        )
        return [dict(r) for r in rows]
    except asyncpg.exceptions.UndefinedColumnError:
        return []


async def pending_words(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int
) -> list[dict]:
    """Words of the course still lacking a *locale* gloss, in the order a
    learner meets them. Mirrors the CLI's query, plus: a non-English course
    word must HAVE an English gloss (the pivot the maker disambiguates with);
    for the English course the headword itself is the English."""
    rows = await conn.fetch(
        f"""
        SELECT v.id, v.word, v.part_of_speech AS pos,
               (SELECT definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                   AS definition,
               (SELECT sentence FROM example_sentences es
                 WHERE es.vocabulary_id = v.id
                 ORDER BY es.difficulty_rank NULLS LAST LIMIT 1) AS example
        FROM vocabulary v
        JOIN languages l ON l.id = v.language_id
        WHERE v.language_id = $1
          AND NOT EXISTS (
            SELECT 1 FROM translations t
             WHERE t.vocabulary_id = v.id AND t.locale = $2)
          AND NOT EXISTS (
            SELECT 1 FROM translation_reviews r
             WHERE r.vocabulary_id = v.id AND r.locale = $2)
          AND (l.code = 'en' OR EXISTS (
            SELECT 1 FROM translations t
             WHERE t.vocabulary_id = v.id AND t.locale = 'en'))
        ORDER BY {_LEVEL_ORDER} NULLS LAST, v.frequency_rank NULLS LAST
        LIMIT $3
        """,
        language_id, locale, limit,
    )
    return [dict(r) for r in rows]


async def _apply(conn: asyncpg.Connection, locale: str,
                 results: list[dict]) -> tuple[int, int]:
    """Store one batch's outcome — same writes as the CLI's apply step:
    approved → translations overlay, rejected → the human review queue."""
    applied = queued = 0
    for r in results:
        if r["verdict"] in ("ok", "fixed") and r["gloss"]:
            await conn.execute(
                """INSERT INTO translations (vocabulary_id, locale, definition)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (vocabulary_id, locale)
                     DO UPDATE SET definition = EXCLUDED.definition""",
                r["id"], locale, r["gloss"])
            applied += 1
        else:
            await conn.execute(
                """INSERT INTO translation_reviews
                       (vocabulary_id, locale, proposed, reason)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (vocabulary_id, locale) DO NOTHING""",
                r["id"], locale, r.get("proposed") or "", r["note"])
            queued += 1
    return applied, queued


async def pending_drills(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int
) -> list[dict]:
    """Drill sentences of the course with no *locale* row yet — the strings a
    learner reads on every grammar card (the translation under the cloze and
    the hint). A row with NULL fields counts as attempted: rejected renderings
    are recorded as NULLs so the sweep converges instead of re-spending, and
    the card COALESCEs to English exactly as before."""
    rows = await conn.fetch(
        f"""
        SELECT ds.id, ds.sentence, ds.translation, ds.hint
        FROM drill_sentences ds
        JOIN grammar_points gp ON gp.id = ds.grammar_point_id
        WHERE gp.language_id = $1
          AND (ds.translation IS NOT NULL OR ds.hint IS NOT NULL)
          AND NOT EXISTS (
            SELECT 1 FROM drill_hint_translations dht
             WHERE dht.drill_id = ds.id AND dht.locale = $2)
        ORDER BY {_LEVEL_ORDER.replace('v.level', 'gp.level')} NULLS LAST,
                 gp.display_order NULLS LAST, ds.display_order NULLS LAST, ds.id
        LIMIT $3
        """,
        language_id, locale, limit,
    )
    return [dict(r) for r in rows]


async def pending_explanations(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int
) -> list[dict]:
    """Grammar points whose explanation has no *locale* rendering yet."""
    rows = await conn.fetch(
        f"""
        SELECT gp.id, gp.explanation
        FROM grammar_points gp
        WHERE gp.language_id = $1
          AND gp.explanation IS NOT NULL AND gp.explanation <> ''
          AND NOT EXISTS (
            SELECT 1 FROM explanation_translations et
             WHERE et.grammar_point_id = gp.id AND et.locale = $2)
        ORDER BY {_LEVEL_ORDER.replace('v.level', 'gp.level')} NULLS LAST,
                 gp.display_order NULLS LAST, gp.id
        LIMIT $3
        """,
        language_id, locale, limit,
    )
    return [dict(r) for r in rows]


async def _translate_drills(conn, pair, rows) -> int:
    """English drill translation + hint → the locale, one maker–checker pass
    per field. Approved renderings are stored as draft rows (reviewed=false —
    live immediately, the read path COALESCEs with no reviewed gate, and a
    reviewer can amend later); rejected ones store NULL, which both records
    the attempt and leaves the card on its English fallback."""
    out: dict[str, dict] = {str(r["id"]): {"translation": None, "hint": None}
                            for r in rows}
    for field in ("translation", "hint"):
        items = [{"i": i, "sentence": r[field]}
                 for i, r in enumerate(rows) if r[field]]
        if not items:
            continue
        results = await generate_sentence_translations(pair["locale_name"], items)
        for res in results:
            if res["translation"]:
                out[str(rows[res["i"]]["id"])][field] = res["translation"]
    applied = 0
    for r in rows:
        vals = out[str(r["id"])]
        await conn.execute(
            """INSERT INTO drill_hint_translations
                   (drill_id, locale, hint, translation, reviewed)
               VALUES ($1, $2, $3, $4, false)
               ON CONFLICT (drill_id, locale) DO NOTHING""",
            r["id"], pair["locale"], vals["hint"], vals["translation"])
        if vals["translation"] or vals["hint"]:
            applied += 1
    return applied


async def _translate_explanations(conn, pair, rows) -> int:
    """Grammar explanations → the locale. The table requires NOT NULL text,
    so only approved renderings are stored; a rejected one simply retries on
    a later sweep (rare, and the budget caps the spend either way)."""
    items = [{"i": i, "sentence": r["explanation"]} for i, r in enumerate(rows)]
    results = await generate_sentence_translations(pair["locale_name"], items)
    applied = 0
    for res in results:
        if not res["translation"]:
            continue
        await conn.execute(
            """INSERT INTO explanation_translations
                   (grammar_point_id, locale, explanation, reviewed)
               VALUES ($1, $2, $3, false)
               ON CONFLICT (grammar_point_id, locale) DO NOTHING""",
            rows[res["i"]]["id"], pair["locale"], res["translation"])
        applied += 1
    return applied


async def run_translation_cycle(conn: asyncpg.Connection) -> dict:
    """One sweep: spend the cycle's word budget across the live pairs.

    Returns {"pairs", "processed", "applied", "queued"} so the loop can log
    something meaningful (and tests can assert on it).
    """
    stats = {"pairs": 0, "processed": 0, "applied": 0, "queued": 0,
             "drills": 0, "explanations": 0}
    pairs = await discover_pairs(conn)
    if not pairs:
        return stats

    budget = getattr(get_settings(), "auto_translate_words_per_cycle", 50)
    for pair in pairs:
        if budget <= 0:
            break
        rows = await pending_words(conn, pair["language_id"], pair["locale"],
                                   min(budget, BATCH_SIZE))
        if not rows:
            continue
        stats["pairs"] += 1
        budget -= len(rows)
        items = [{"i": i, "word": r["word"], "pos": r["pos"],
                  "definition": r["definition"], "example": r["example"]}
                 for i, r in enumerate(rows)]
        results = await maker_check_batch(
            pair["locale_name"], items,
            source_language=pair["language_name"],
        )
        by_i = {b["i"]: b for b in results}
        merged = [{**by_i[i], "id": rows[i]["id"], "proposed": by_i[i]["gloss"]}
                  for i in range(len(rows)) if i in by_i]
        applied, queued = await _apply(conn, pair["locale"], merged)
        stats["processed"] += len(merged)
        stats["applied"] += applied
        stats["queued"] += queued
        logger.info(
            "auto-translate %s→%s: applied %d, queued %d (%d learner(s))",
            pair["language_code"], pair["locale"], applied, queued,
            pair["learners"],
        )

    # Remaining budget flows into the other strings a card actually shows:
    # drill translations/hints first (read on every grammar review), then
    # grammar explanations (read once per point). Same demand rule — only
    # live pairs, only missing rows.
    for kind, fetch, translate, stat in (
        ("drills", pending_drills, _translate_drills, "drills"),
        ("explanations", pending_explanations, _translate_explanations,
         "explanations"),
    ):
        for pair in pairs:
            if budget <= 0:
                break
            rows = await fetch(conn, pair["language_id"], pair["locale"],
                               min(budget, BATCH_SIZE))
            if not rows:
                continue
            budget -= len(rows)
            done = await translate(conn, pair, rows)
            stats[stat] += done
            stats["processed"] += len(rows)
            logger.info("auto-translate %s→%s: %s %d/%d",
                        pair["language_code"], pair["locale"], kind, done,
                        len(rows))
    return stats


async def auto_translate_loop() -> None:
    """In-process sweep, started from the app lifespan like the email loops.
    Survives anything; a sweep failure waits for the next tick."""
    from backend.repositories.pool import privileged_connection

    logger.info("auto-translate loop started (every %ds)", SWEEP_SECONDS)
    while True:
        try:
            if translations_available():
                async with privileged_connection() as conn:
                    stats = await run_translation_cycle(conn)
                if stats["processed"]:
                    logger.info("auto-translate sweep: %s", stats)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("auto-translate sweep failed: %s", exc)
        await asyncio.sleep(SWEEP_SECONDS)
