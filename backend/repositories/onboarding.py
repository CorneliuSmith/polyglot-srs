"""Onboarding repository — placement sampling and first-run setup.

Completing onboarding is what actually gives a learner something to study:
it subscribes them to the grammar + vocabulary content lists at and below their
starting level (so "Learn" has cards to draw from) and records their active
language. All writes are RLS-scoped to the user.
"""
from __future__ import annotations

import re

import asyncpg

from backend.services.extract import ANSWER_MARKER

# CEFR ladder, easiest first.
CEFR_ORDER: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

# Shown in a grammar cloze where the answer goes.
_BLANK = "____"


def levels_at_or_below(level: str) -> list[str]:
    """Return the CEFR levels up to and including *level* (A1..level)."""
    if level not in CEFR_ORDER:
        return ["A1"]
    return list(CEFR_ORDER[: CEFR_ORDER.index(level) + 1])


def estimate_level(per_level: dict[str, tuple[int, int]], *, threshold: float = 0.6) -> str:
    """Estimate a starting level from per-level (correct, total) results.

    The estimate is the highest level the learner answered at or above the pass
    threshold; defaults to A1 when nothing is passed.
    """
    best = "A1"
    for level in CEFR_ORDER:
        if level in per_level:
            correct, total = per_level[level]
            if total > 0 and correct / total >= threshold:
                best = level
    return best


# ── Adaptive placement (WP11) ────────────────────────────────────────────────
# A deterministic level staircase: probe at a level, step up on a correct
# answer and down on a miss, and stop as soon as the estimate is stable —
# most learners finish in 5–8 items instead of a fixed batch.

MAX_ADAPTIVE_ITEMS = 12
MIN_ADAPTIVE_ITEMS = 6    # beta fix: don't let oscillation end the test early —
                          # with 1–3 samples per level, one unlucky item was
                          # deciding the placement. Floor/ceiling stops are
                          # unambiguous and stay immediate.
_START_PROBE = 1          # A2 — assumes a little knowledge, falls fast if not
_STOP_REVERSALS = 4       # direction changes = oscillating around the level
_STOP_BOUNDARY = 2        # consecutive misses at A1 / passes at C2
_GRAMMAR_WEIGHT = 0.6     # grammar levels are the better-calibrated signal


def adaptive_next(
    pool: list[dict], history: list[tuple[dict, bool]]
) -> dict | None:
    """Pick the next placement item, or None when the estimate is stable.

    *pool* holds sampled items ({id, kind, level}); *history* is the graded
    answers so far in order ((item, correct)). Pure and deterministic: the
    same inputs always walk the same staircase, so the endpoint can stay
    stateless (the client replays its answer history each round).
    """
    probe = _START_PROBE
    reversals = 0
    last_dir: int | None = None
    floor_misses = ceiling_passes = 0

    for item, correct in history:
        direction = 1 if correct else -1
        if last_dir is not None and direction != last_dir:
            reversals += 1
        last_dir = direction
        if probe == 0 and not correct:
            floor_misses += 1
        elif probe == len(CEFR_ORDER) - 1 and correct:
            ceiling_passes += 1
        else:
            floor_misses = ceiling_passes = 0
        probe = max(0, min(len(CEFR_ORDER) - 1, probe + direction))

    if (
        len(history) >= MAX_ADAPTIVE_ITEMS
        or (reversals >= _STOP_REVERSALS and len(history) >= MIN_ADAPTIVE_ITEMS)
        or floor_misses >= _STOP_BOUNDARY
        or ceiling_passes >= _STOP_BOUNDARY
    ):
        return None

    used = {item["id"] for item, _ in history}
    unused = [it for it in pool if it["id"] not in used]
    if not unused:
        return None

    # Grammar/vocab weighting: keep grammar at ~60% of what's been asked.
    asked = len(history)
    grammar_asked = sum(1 for item, _ in history if item["kind"] == "grammar")
    want = (
        "grammar"
        if grammar_asked < _GRAMMAR_WEIGHT * (asked + 1)
        else "vocabulary"
    )

    def rank(it: dict) -> tuple:
        lvl = (
            CEFR_ORDER.index(it["level"])
            if it["level"] in CEFR_ORDER else len(CEFR_ORDER)
        )
        return (
            abs(lvl - probe),   # closest to the probe level first
            lvl,                # tie → easier level
            it["kind"] != want, # preferred kind first
            it["id"],           # deterministic tiebreak
        )

    return min(unused, key=rank)


async def get_status(conn: asyncpg.Connection, user_id: str) -> dict:
    """Return the user's onboarding status for routing decisions."""
    row = await conn.fetchrow(
        "SELECT onboarded_at, active_language_id FROM user_profiles WHERE id = $1",
        user_id,
    )
    has_subs = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM user_content_subscriptions WHERE user_id = $1)",
        user_id,
    )
    return {
        "onboarded": bool(row and row["onboarded_at"]),
        "active_language_id": str(row["active_language_id"])
        if row and row["active_language_id"] else None,
        "has_subscriptions": bool(has_subs),
    }


# Dictionary-derived definitions for the MOST frequent words are exactly the
# ones written in grammarese ("initial interrogative particle", "feminine
# singular of o") — a beta tester rightly flagged that a placement test is no
# place for linguistics vocabulary. Prompts matching this are skipped in
# favour of the next-most-frequent word with a plain, concrete definition.
_JARGON_RE = re.compile(
    r"inflection of|indicative|subjunctive|participle|particle\b|conjunction"
    r"|preposition|genitive|dative|accusative|nominative|vocative|oblique"
    r"|singular of|plural of|feminine|masculine|diminutive|auxiliary"
    r"|clitic|copula|interrogative|grammatical|denotes|comitative|ergative"
    r"|postposition|definite article|indefinite article|conjugat",
    re.IGNORECASE,
)
_MAX_PROMPT_LEN = 60  # long dictionary entries make bad type-the-word prompts


def _plain_prompt(definition: str) -> bool:
    d = definition.strip()
    return bool(d) and len(d) <= _MAX_PROMPT_LEN and not _JARGON_RE.search(d)


async def sample_placement_items(
    conn: asyncpg.Connection, language_id: str, *, per_level: int = 3
) -> list[dict]:
    """Sample graded placement prompts across vocabulary and grammar.

    Vocabulary items show an English definition (type the word); grammar items
    show a reviewed cloze sentence with a blank (type the missing form). Both
    pick the most representative items per CEFR level. Answers are not returned.
    """
    # Over-fetch per level, then keep the first plain-language definitions —
    # frequency order is preserved, jargon rows just fall through.
    vocab_pool = await conn.fetch(
        """
        SELECT id, level, prompt FROM (
            SELECT
                v.id,
                v.level,
                t.definition AS prompt,
                row_number() OVER (
                    PARTITION BY v.level ORDER BY v.frequency_rank ASC NULLS LAST
                ) AS rn
            FROM vocabulary v
            JOIN translations t ON v.id = t.vocabulary_id AND t.locale = 'en'
            WHERE v.language_id = $1
              AND v.level IS NOT NULL
              AND t.definition IS NOT NULL
        ) ranked
        WHERE rn <= $2
        ORDER BY level, rn
        """,
        language_id,
        per_level * 8,
    )
    vocab: list = []
    taken: dict[str, int] = {}
    for r in vocab_pool:
        if taken.get(r["level"], 0) >= per_level:
            continue
        if not _plain_prompt(r["prompt"]):
            continue
        taken[r["level"]] = taken.get(r["level"], 0) + 1
        vocab.append(r)
    # A level whose every candidate is jargon still gets its plain-limit
    # fallback rows rather than vanishing from the staircase.
    for level in {r["level"] for r in vocab_pool}:
        if taken.get(level, 0) == 0:
            for r in vocab_pool:
                if r["level"] == level:
                    vocab.append(r)
                    taken[level] = taken.get(level, 0) + 1
                    if taken[level] >= per_level:
                        break
    grammar = await conn.fetch(
        """
        SELECT id, level, sentence, translation FROM (
            SELECT
                ds.id,
                gp.level,
                ds.sentence,
                ds.translation,
                row_number() OVER (
                    PARTITION BY gp.level ORDER BY gp.display_order, ds.display_order
                ) AS rn
            FROM drill_sentences ds
            JOIN grammar_points gp ON ds.grammar_point_id = gp.id
            WHERE gp.language_id = $1
              AND gp.level IS NOT NULL
              AND gp.reviewed = true
              AND ds.reviewed
              AND ds.sentence LIKE '%' || $3 || '%'
        ) ranked
        WHERE rn <= $2
        ORDER BY level, rn
        """,
        language_id,
        per_level,
        ANSWER_MARKER,
    )

    items = [
        {"id": str(r["id"]), "kind": "vocabulary", "level": r["level"],
         "prompt": r["prompt"], "translation": None}
        for r in vocab
    ] + [
        {"id": str(r["id"]), "kind": "grammar", "level": r["level"],
         "prompt": r["sentence"].replace(ANSWER_MARKER, _BLANK),
         "translation": r["translation"]}
        for r in grammar
    ]
    # Interleave by level so a short test still spans the difficulty range.
    items.sort(key=lambda it: (
        CEFR_ORDER.index(it["level"]) if it["level"] in CEFR_ORDER else len(CEFR_ORDER),
        it["kind"],
    ))
    return items


async def get_placement_answers(
    conn: asyncpg.Connection, language_id: str, item_ids: list[str]
) -> dict[str, dict]:
    """Return {item_id: {"answer", "level"}} for scoring placement answers.

    Items may be vocabulary or grammar drills; both id spaces are looked up and
    merged (UUIDs don't collide across the two tables).
    """
    if not item_ids:
        return {}
    # Alternatives matter here (beta fix): a vocab prompt is an English
    # definition, and several target words can be right ("to walk" →
    # ходить/идти). The review flow already accepts a card's recorded
    # alternatives — placement must too, or valid answers grade as misses
    # and the staircase under-places.
    vocab = await conn.fetch(
        "SELECT id, word AS answer, level, alternatives FROM vocabulary "
        "WHERE language_id = $1 AND id = ANY($2::uuid[])",
        language_id,
        item_ids,
    )
    grammar = await conn.fetch(
        """
        SELECT ds.id, ds.answer, gp.level
        FROM drill_sentences ds
        JOIN grammar_points gp ON ds.grammar_point_id = gp.id
        WHERE gp.language_id = $1 AND ds.id = ANY($2::uuid[])
        """,
        language_id,
        item_ids,
    )
    answers = {
        str(r["id"]): {
            "answer": r["answer"], "level": r["level"],
            "alternatives": list(r["alternatives"] or []),
        }
        for r in vocab
    }
    answers.update(
        {
            str(r["id"]): {
                "answer": r["answer"], "level": r["level"], "alternatives": [],
            }
            for r in grammar
        }
    )
    return answers


async def complete_onboarding(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    level: str,
    *,
    batch_size: int | None = None,
) -> dict:
    """Subscribe the user to content at/below *level* and mark them onboarded.

    Returns the number of new subscriptions created and the chosen settings.
    """
    levels = levels_at_or_below(level)
    lists = await conn.fetch(
        """
        SELECT id FROM content_lists
        WHERE language_id = $1
          AND list_type IN ('grammar', 'vocabulary')
          AND (level = ANY($2::text[]) OR level IS NULL)
        """,
        language_id,
        levels,
    )
    subscribed = 0
    for row in lists:
        result = await conn.execute(
            "INSERT INTO user_content_subscriptions (user_id, content_list_id) "
            "VALUES ($1, $2) ON CONFLICT (user_id, content_list_id) DO NOTHING",
            user_id,
            row["id"],
        )
        # asyncpg returns "INSERT 0 1" on insert, "INSERT 0 0" when skipped.
        if result.endswith(" 1"):
            subscribed += 1

    await conn.execute(
        """
        INSERT INTO user_profiles (id, batch_size, active_language_id, onboarded_at)
        VALUES ($1, COALESCE($2, 5), $3, now())
        ON CONFLICT (id) DO UPDATE SET
            active_language_id = EXCLUDED.active_language_id,
            batch_size = COALESCE($2, user_profiles.batch_size),
            onboarded_at = now(),
            updated_at = now()
        """,
        user_id,
        batch_size,
        language_id,
    )
    return {"subscribed": subscribed, "active_language_id": language_id, "level": level}
