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
    generate_text_translations,
    maker_check_batch,
    translations_available,
)

logger = logging.getLogger(__name__)

SWEEP_SECONDS = 15 * 60
# Words handed to one maker/checker call. Same default as the CLI.
BATCH_SIZE = 25
# Demand rows honoured per kind per cycle — demand is a priority lane, not a
# bypass of the budget.
DEMAND_LIMIT = 50

# ---------------------------------------------------------------------------
# Demand: "a learner just saw this in English". Card reads record what was
# missing (translation_demand) and wake the loop, which serves those rows
# before its breadth-first sweep — so the card a learner is looking at fills
# in minutes, not whenever A1-first ordering reaches it.
# ---------------------------------------------------------------------------

_wake = asyncio.Event()


def kick() -> None:
    """Wake the loop now (called after demand is recorded)."""
    _wake.set()


async def table_present(conn, table: str) -> bool:
    """Whether *table*'s migration has landed — probed with to_regclass,
    which NEVER raises. This matters more than it looks: every pooled
    connection here runs inside one transaction (pool.py), so a thrown
    UndefinedTableError doesn't just fail its own query — it aborts the
    transaction and every later query in the same request/sweep dies with
    it. That took the whole Gym manifest down (and killed entire sweeps)
    when the 20260914 migration wasn't applied yet. Probe first; never let
    a query against a maybe-missing table reach the server."""
    return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table))


async def note_demand(conn, kind: str, ref_ids, locale: str | None) -> None:
    """Record that content was served with an English fallback for *locale*.

    Fire-and-forget semantics: any failure degrades to 'no demand
    recorded' — the sweep still fills the row eventually. Never raises
    into the read path, and (see table_present) never poisons its
    transaction either.
    """
    ids = [r for r in ref_ids if r]
    if not ids or not locale or locale == "en":
        return
    try:
        if not await table_present(conn, "translation_demand"):
            return
        await conn.execute(
            """INSERT INTO translation_demand (kind, ref_id, locale)
               SELECT $1, unnest($2::uuid[]), $3
               ON CONFLICT DO NOTHING""",
            kind, ids, locale,
        )
    except Exception as exc:  # noqa: BLE001 — never break a card read
        logger.debug("translation demand not recorded: %s", exc)
        return
    kick()


# Detection mirrors the loop's pending_* queries exactly: a kind is demanded
# only when the overlay row genuinely doesn't exist (attempted/rejected rows
# count as covered, same as the sweep).
_DEMAND_DETECTORS = {
    "word": """
        SELECT 'word', v.id, $2 FROM vocabulary v
        WHERE v.id = ANY($1::uuid[])
          AND NOT EXISTS (SELECT 1 FROM translations t
                           WHERE t.vocabulary_id = v.id AND t.locale = $2)
          AND NOT EXISTS (SELECT 1 FROM translation_reviews r
                           WHERE r.vocabulary_id = v.id AND r.locale = $2)""",
    "example": """
        SELECT DISTINCT 'example', es.vocabulary_id, $2 FROM example_sentences es
        WHERE es.vocabulary_id = ANY($1::uuid[])
          AND es.translation_locale = 'en' AND es.reviewed
          AND es.translation IS NOT NULL AND es.translation <> ''
          AND NOT EXISTS (SELECT 1 FROM example_sentences es2
                           WHERE es2.vocabulary_id = es.vocabulary_id
                             AND es2.sentence = es.sentence
                             AND es2.translation_locale = $2)""",
    "drill": """
        SELECT 'drill', ds.id, $2 FROM drill_sentences ds
        WHERE ds.grammar_point_id = ANY($1::uuid[])
          AND (ds.translation IS NOT NULL OR ds.hint IS NOT NULL)
          AND NOT EXISTS (SELECT 1 FROM drill_hint_translations dht
                           WHERE dht.drill_id = ds.id AND dht.locale = $2)""",
    "explanation": """
        SELECT 'explanation', gp.id, $2 FROM grammar_points gp
        WHERE gp.id = ANY($1::uuid[])
          AND gp.explanation IS NOT NULL AND gp.explanation <> ''
          AND NOT EXISTS (SELECT 1 FROM explanation_translations et
                           WHERE et.grammar_point_id = gp.id
                             AND et.locale = $2)""",
    "grammar_meta": """
        SELECT 'grammar_meta', gp.id, $2 FROM grammar_points gp
        WHERE gp.id = ANY($1::uuid[])
          AND NOT EXISTS (SELECT 1 FROM grammar_point_translations gpt
                           WHERE gpt.grammar_point_id = gp.id
                             AND gpt.locale = $2)""",
}


async def note_missing_content(
    conn, locale: str | None,
    vocab_ids: list | None = None,
    grammar_ids: list | None = None,
) -> None:
    """Record every English fallback a card read just served: missing glosses
    and example translations for *vocab_ids*, missing drill/explanation/
    title translations for *grammar_ids*. One cheap INSERT..SELECT per kind;
    any failure degrades to 'no demand recorded'. Never raises, never
    poisons the read's transaction (see table_present)."""
    if not locale or locale == "en":
        return
    recorded = 0
    try:
        if not await table_present(conn, "translation_demand"):
            return
        plan = []
        if vocab_ids:
            plan += [("word", vocab_ids), ("example", vocab_ids)]
        if grammar_ids:
            plan += [("drill", grammar_ids), ("explanation", grammar_ids)]
            # The grammar_meta detector reads its own overlay table — same
            # migration as translation_demand, but probe anyway so a partial
            # application can't abort the read.
            if await table_present(conn, "grammar_point_translations"):
                plan += [("grammar_meta", grammar_ids)]
        for kind, ids in plan:
            status = await conn.execute(
                "INSERT INTO translation_demand (kind, ref_id, locale)"
                + _DEMAND_DETECTORS[kind]
                + " ON CONFLICT DO NOTHING",
                list(ids), locale,
            )
            recorded += int(status.rsplit(" ", 1)[-1] or 0)
    except Exception as exc:  # noqa: BLE001 — never break a card read
        logger.debug("translation demand not recorded: %s", exc)
    if recorded:
        kick()

# A1 first: the loop fills what a beginner meets before what a C2 reader
# might. NULL levels (unleveled imports) go last.
_LEVEL_ORDER = "array_position(ARRAY['A1','A2','B1','B2','C1','C2'], v.level)"


async def discover_pairs(conn: asyncpg.Connection) -> list[dict]:
    """Live (course, locale) pairs the loop should serve, most learners first.

    A pair exists only when a real account is learning the course WITH that
    support locale. English support is the always-present spine (nothing to
    fill). The SELF-pair (learning Spanish with Spanish support) is a real
    pair: the content is English text ABOUT the course language — hints,
    explanations, titles — and a Spanish-UI learner wants it in Spanish.
    Only word glosses become monolingual definitions, which is fine.
    Fails closed (empty) when the toggle column's migration hasn't landed.
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
            GROUP BY l.id, l.code, l.name, loc.code, loc.name
            ORDER BY count(*) DESC, l.name, loc.code
            """
        )
        return [dict(r) for r in rows]
    except asyncpg.exceptions.UndefinedColumnError:
        return []


async def pending_words(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int,
    ids: list | None = None,
) -> list[dict]:
    """Words of the course still lacking a *locale* gloss, in the order a
    learner meets them. Mirrors the CLI's query, plus: a non-English course
    word must HAVE an English gloss (the pivot the maker disambiguates with);
    for the English course the headword itself is the English. *ids*
    restricts to specific words (the demand lane)."""
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
          AND ($4::uuid[] IS NULL OR v.id = ANY($4::uuid[]))
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
        language_id, locale, limit, ids,
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
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int,
    ids: list | None = None,
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
          AND ($4::uuid[] IS NULL OR ds.id = ANY($4::uuid[]))
          AND (ds.translation IS NOT NULL OR ds.hint IS NOT NULL)
          AND NOT EXISTS (
            SELECT 1 FROM drill_hint_translations dht
             WHERE dht.drill_id = ds.id AND dht.locale = $2)
        ORDER BY {_LEVEL_ORDER.replace('v.level', 'gp.level')} NULLS LAST,
                 gp.display_order NULLS LAST, ds.display_order NULLS LAST, ds.id
        LIMIT $3
        """,
        language_id, locale, limit, ids,
    )
    return [dict(r) for r in rows]


async def pending_explanations(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int,
    ids: list | None = None,
) -> list[dict]:
    """Grammar points whose explanation has no *locale* rendering yet."""
    rows = await conn.fetch(
        f"""
        SELECT gp.id, gp.explanation
        FROM grammar_points gp
        WHERE gp.language_id = $1
          AND ($4::uuid[] IS NULL OR gp.id = ANY($4::uuid[]))
          AND gp.explanation IS NOT NULL AND gp.explanation <> ''
          AND NOT EXISTS (
            SELECT 1 FROM explanation_translations et
             WHERE et.grammar_point_id = gp.id AND et.locale = $2)
        ORDER BY {_LEVEL_ORDER.replace('v.level', 'gp.level')} NULLS LAST,
                 gp.display_order NULLS LAST, gp.id
        LIMIT $3
        """,
        language_id, locale, limit, ids,
    )
    return [dict(r) for r in rows]


async def pending_grammar_meta(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int,
    ids: list | None = None,
) -> list[dict]:
    """Grammar points whose title/notes have no *locale* row yet — the name a
    learner sees on cards, the grammar path and search. A row with NULL
    fields counts as attempted (rejections converge, COALESCE keeps
    English)."""
    rows = await conn.fetch(
        f"""
        SELECT gp.id, gp.title, gp.culture_note, gp.function_note
        FROM grammar_points gp
        WHERE gp.language_id = $1
          AND ($4::uuid[] IS NULL OR gp.id = ANY($4::uuid[]))
          AND NOT EXISTS (
            SELECT 1 FROM grammar_point_translations gpt
             WHERE gpt.grammar_point_id = gp.id AND gpt.locale = $2)
        ORDER BY {_LEVEL_ORDER.replace('v.level', 'gp.level')} NULLS LAST,
                 gp.display_order NULLS LAST, gp.id
        LIMIT $3
        """,
        language_id, locale, limit, ids,
    )
    return [dict(r) for r in rows]


async def pending_gym_labels(
    conn: asyncpg.Connection, language_code: str, locale: str
) -> list[dict]:
    """Gym picker entries (from data/gym/{code}.json) with no *locale* row.
    The whole manifest is one small batch — a language has a few dozen
    entries, translated once per locale ever."""
    from backend.services.gym_manifest import load_manifest

    manifest = load_manifest(language_code)
    if not manifest:
        return []
    entries = [
        {"point": e["point"], "label": e.get("label"),
         "usage": e.get("usage")}
        for col in manifest.get("columns", [])
        for e in col.get("entries", [])
    ]
    if not entries:
        return []
    have = {
        r["point"] for r in await conn.fetch(
            """SELECT point FROM gym_label_translations
               WHERE language_code = $1 AND locale = $2""",
            language_code, locale,
        )
    }
    return [e for e in entries if e["point"] not in have]


async def pending_examples(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int,
    vocab_ids: list | None = None,
) -> list[dict]:
    """Reviewed English example sentences whose *locale* sibling row doesn't
    exist yet. The sibling is a full example_sentences row (same sentence,
    translation_locale = locale); the CLI's -k translations fills these by
    hand, this is the loop's lane. Unreviewed rows are skipped — no point
    translating content a learner can't see."""
    rows = await conn.fetch(
        """
        SELECT es.id, es.vocabulary_id, es.language_id, es.sentence,
               es.translation
        FROM example_sentences es
        WHERE es.language_id = $1
          AND ($4::uuid[] IS NULL OR es.vocabulary_id = ANY($4::uuid[]))
          AND es.translation_locale = 'en'
          AND es.reviewed
          AND es.translation IS NOT NULL AND es.translation <> ''
          AND NOT EXISTS (
            SELECT 1 FROM example_sentences es2
             WHERE es2.vocabulary_id = es.vocabulary_id
               AND es2.sentence = es.sentence
               AND es2.translation_locale = $2)
        ORDER BY es.difficulty_rank NULLS LAST, es.id
        LIMIT $3
        """,
        language_id, locale, limit, vocab_ids,
    )
    return [dict(r) for r in rows]


def self_pair(pair) -> bool:
    """Learning a language THROUGH itself (Spanish course, Spanish support).

    Most kinds are better for it — a gloss becomes a monolingual learner's
    dictionary entry, and hints/explanations/titles are English text ABOUT
    the language that clearly should be Spanish. But a sentence TRANSLATION
    is different: rendering "The house is big" into the course language
    reproduces the drill sentence itself — with the blank filled in. That
    hands over the answer. Those kinds stay on their English source here.
    """
    return pair["locale"] == pair["language_code"]


async def _translate_drills(conn, pair, rows) -> int:
    """English drill translation + hint → the locale, one maker–checker pass
    per field. Approved renderings are stored as draft rows (reviewed=false —
    live immediately, the read path COALESCEs with no reviewed gate, and a
    reviewer can amend later); rejected ones store NULL, which both records
    the attempt and leaves the card on its English fallback.

    On the self-pair only the HINT is rendered: the translation would spell
    out the cloze answer (see self_pair)."""
    out: dict[str, dict] = {str(r["id"]): {"translation": None, "hint": None}
                            for r in rows}
    fields = ("hint",) if self_pair(pair) else ("translation", "hint")
    for field in fields:
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
    """Grammar explanations → the locale, through the prose charter (an
    explanation is a lesson, not an example sentence). The table requires
    NOT NULL text, so only approved renderings are stored; a rejected one
    simply retries on a later sweep (rare, and the budget caps the spend
    either way)."""
    items = [{"i": i, "sentence": r["explanation"]} for i, r in enumerate(rows)]
    results = await generate_text_translations(pair["locale_name"], items,
                                               kind="prose")
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


async def _translate_grammar_meta(conn, pair, rows) -> int:
    """Grammar point titles (label charter) and culture/function notes (prose
    charter) → the locale. One row per point; a field whose rendering was
    rejected stays NULL and the read path keeps its English fallback."""
    out: dict[str, dict] = {
        str(r["id"]): {"title": None, "culture_note": None, "function_note": None}
        for r in rows
    }
    for field, kind in (("title", "label"), ("culture_note", "prose"),
                        ("function_note", "prose")):
        items = [{"i": i, "sentence": r[field]}
                 for i, r in enumerate(rows) if r[field]]
        if not items:
            continue
        results = await generate_text_translations(pair["locale_name"], items,
                                                   kind=kind)
        for res in results:
            if res["translation"]:
                out[str(rows[res["i"]]["id"])][field] = res["translation"]
    applied = 0
    for r in rows:
        vals = out[str(r["id"])]
        await conn.execute(
            """INSERT INTO grammar_point_translations
                   (grammar_point_id, locale, title, culture_note,
                    function_note, reviewed)
               VALUES ($1, $2, $3, $4, $5, false)
               ON CONFLICT (grammar_point_id, locale) DO NOTHING""",
            r["id"], pair["locale"], vals["title"], vals["culture_note"],
            vals["function_note"])
        if any(vals.values()):
            applied += 1
    return applied


async def _translate_gym_labels(conn, pair, rows) -> int:
    """Gym picker labels and usage lines → the locale. The `example` field is
    course-language text and is never translated. Keyed by manifest point
    title, so re-seeded grammar keeps its picker translations."""
    out: dict[str, dict] = {r["point"]: {"label": None, "usage": None}
                            for r in rows}
    for field in ("label", "usage"):
        items = [{"i": i, "sentence": r[field]}
                 for i, r in enumerate(rows) if r[field]]
        if not items:
            continue
        results = await generate_text_translations(pair["locale_name"], items,
                                                   kind="label")
        for res in results:
            if res["translation"]:
                out[rows[res["i"]]["point"]][field] = res["translation"]
    applied = 0
    for r in rows:
        vals = out[r["point"]]
        await conn.execute(
            """INSERT INTO gym_label_translations
                   (language_code, locale, point, label, usage_note, reviewed)
               VALUES ($1, $2, $3, $4, $5, false)
               ON CONFLICT (language_code, locale, point) DO NOTHING""",
            pair["language_code"], pair["locale"], r["point"], vals["label"],
            vals["usage"])
        if any(vals.values()):
            applied += 1
    return applied


async def _translate_examples(conn, pair, rows) -> int:
    """Locale renderings of reviewed English example sentences, stored as
    sibling example_sentences rows via the same helper the CLI uses — which
    lands them reviewed=false, pending human approval (the WP42 gate).
    Learners keep the English translation until a reviewer approves; this
    lane just makes sure the queue is FULL when they look."""
    from backend.repositories.contributor import add_example_sentence

    if self_pair(pair):
        return 0  # the rendering would just restate the sentence
    items = [{"i": i, "sentence": r["translation"]} for i, r in enumerate(rows)]
    results = await generate_sentence_translations(pair["locale_name"], items)
    applied = 0
    for res in results:
        if not res["translation"]:
            continue
        r = rows[res["i"]]
        row_id = await add_example_sentence(
            conn, r["vocabulary_id"], r["language_id"], r["sentence"],
            res["translation"], source="ai",
            origin_detail=f"auto_translate:{pair['locale']}",
            translation_locale=pair["locale"],
        )
        if row_id:
            applied += 1
    return applied


# Demand rows join back to their course language per kind; 'gym' points at
# the language itself. Each query yields (ref_id, language_id) filtered to
# languages with the toggle on; the self-pair is served like any other.
_DEMAND_RESOLVERS = {
    "word": "JOIN vocabulary v ON v.id = d.ref_id "
            "JOIN languages l ON l.id = v.language_id",
    "example": "JOIN vocabulary v ON v.id = d.ref_id "
               "JOIN languages l ON l.id = v.language_id",
    "drill": "JOIN drill_sentences ds ON ds.id = d.ref_id "
             "JOIN grammar_points gp ON gp.id = ds.grammar_point_id "
             "JOIN languages l ON l.id = gp.language_id",
    "explanation": "JOIN grammar_points gp ON gp.id = d.ref_id "
                   "JOIN languages l ON l.id = gp.language_id",
    "grammar_meta": "JOIN grammar_points gp ON gp.id = d.ref_id "
                    "JOIN languages l ON l.id = gp.language_id",
    "gym": "JOIN languages l ON l.id = d.ref_id",
}


async def _demand_batches(conn: asyncpg.Connection) -> list[dict]:
    """Outstanding demand grouped into (kind, language, locale) batches,
    oldest request first. Empty when the demand migration hasn't landed."""
    batches: dict[tuple, dict] = {}
    try:
        for kind, joins in _DEMAND_RESOLVERS.items():
            rows = await conn.fetch(
                f"""
                SELECT d.ref_id, d.locale, l.id AS language_id,
                       l.code AS language_code, l.name AS language_name,
                       loc.name AS locale_name,
                       min(d.requested_at) AS first_requested
                FROM translation_demand d
                {joins}
                JOIN languages loc ON loc.code = d.locale
                WHERE d.kind = $1
                  AND l.auto_translate_enabled
                GROUP BY d.ref_id, d.locale, l.id, l.code, l.name, loc.name
                ORDER BY min(d.requested_at)
                LIMIT $2
                """,
                kind, DEMAND_LIMIT,
            )
            for r in rows:
                key = (kind, str(r["language_id"]), r["locale"])
                b = batches.setdefault(key, {
                    "kind": kind, "language_id": r["language_id"],
                    "language_code": r["language_code"],
                    "language_name": r["language_name"],
                    "locale": r["locale"], "locale_name": r["locale_name"],
                    "ref_ids": [], "first": r["first_requested"],
                })
                b["ref_ids"].append(r["ref_id"])
                b["first"] = min(b["first"], r["first_requested"])
    except (asyncpg.exceptions.UndefinedTableError,
            asyncpg.exceptions.UndefinedColumnError):
        return []
    return sorted(batches.values(), key=lambda b: b["first"])


async def _clear_demand(conn, kind: str, ref_ids, locale: str) -> None:
    """Processed (or unprocessable) demand is deleted — the per-kind
    convergence markers, not this queue, decide whether anything retries."""
    await conn.execute(
        """DELETE FROM translation_demand
           WHERE kind = $1 AND ref_id = ANY($2::uuid[]) AND locale = $3""",
        kind, list(ref_ids), locale,
    )


async def _sweep_stale_demand(conn) -> None:
    """Rows the resolvers never pick up (toggle off, self-locale, deleted
    content) must not accumulate forever."""
    await conn.execute(
        "DELETE FROM translation_demand WHERE requested_at < now() - interval '7 days'"
    )


async def process_demand(conn: asyncpg.Connection, budget: int,
                         stats: dict) -> int:
    """The priority lane: translate exactly what learners just saw in
    English, oldest first, spending from the same cycle budget."""
    batches = await _demand_batches(conn)
    if not batches:
        return budget
    await _sweep_stale_demand(conn)
    for b in batches:
        if budget <= 0:
            break
        pair = b  # same keys the translators expect
        kind, ids = b["kind"], b["ref_ids"][:BATCH_SIZE]
        n = 0
        if kind == "word":
            rows = await pending_words(conn, b["language_id"], b["locale"],
                                       min(budget, BATCH_SIZE), ids)
            if rows:
                items = [{"i": i, "word": r["word"], "pos": r["pos"],
                          "definition": r["definition"], "example": r["example"]}
                         for i, r in enumerate(rows)]
                results = await maker_check_batch(
                    b["locale_name"], items,
                    source_language=b["language_name"])
                by_i = {x["i"]: x for x in results}
                merged = [{**by_i[i], "id": rows[i]["id"],
                           "proposed": by_i[i]["gloss"]}
                          for i in range(len(rows)) if i in by_i]
                applied, queued = await _apply(conn, b["locale"], merged)
                stats["applied"] += applied
                stats["queued"] += queued
                n = len(rows)
        elif kind == "drill":
            rows = await pending_drills(conn, b["language_id"], b["locale"],
                                        min(budget, BATCH_SIZE), ids)
            if rows:
                stats["drills"] += await _translate_drills(conn, pair, rows)
                n = len(rows)
        elif kind == "explanation":
            rows = await pending_explanations(conn, b["language_id"],
                                              b["locale"],
                                              min(budget, BATCH_SIZE), ids)
            if rows:
                stats["explanations"] += await _translate_explanations(
                    conn, pair, rows)
                n = len(rows)
        elif kind == "grammar_meta":
            rows = await pending_grammar_meta(conn, b["language_id"],
                                              b["locale"],
                                              min(budget, BATCH_SIZE), ids)
            if rows:
                stats["grammar_meta"] += await _translate_grammar_meta(
                    conn, pair, rows)
                n = len(rows)
        elif kind == "example":
            rows = [] if self_pair(b) else await pending_examples(
                conn, b["language_id"], b["locale"],
                min(budget, BATCH_SIZE), ids)
            if rows:
                stats["examples"] += await _translate_examples(conn, pair, rows)
                n = len(rows)
        elif kind == "gym":
            rows = await pending_gym_labels(conn, b["language_code"],
                                            b["locale"])
            if rows:
                stats["gym_labels"] += await _translate_gym_labels(
                    conn, pair, rows[:min(budget, BATCH_SIZE)])
                n = min(len(rows), min(budget, BATCH_SIZE))
        await _clear_demand(conn, kind, b["ref_ids"], b["locale"])
        if n:
            budget -= n
            stats["processed"] += n
            stats["demand"] += n
            logger.info("auto-translate demand %s→%s: %s ×%d",
                        b["language_code"], b["locale"], kind, n)
    # Demand that didn't fit this cycle's budget (a big lookahead, a busy
    # hour) makes the loop go again promptly instead of sleeping a full
    # sweep interval — the budget still caps each cycle's burst.
    if any(await _demand_batches(conn)):
        stats["demand_left"] = True
    return budget


async def run_translation_cycle(conn: asyncpg.Connection) -> dict:
    """One sweep: spend the cycle's word budget across the live pairs.

    Returns {"pairs", "processed", "applied", "queued"} so the loop can log
    something meaningful (and tests can assert on it).
    """
    stats = {"pairs": 0, "processed": 0, "applied": 0, "queued": 0,
             "drills": 0, "explanations": 0, "grammar_meta": 0,
             "gym_labels": 0, "examples": 0, "demand": 0}
    budget = getattr(get_settings(), "auto_translate_words_per_cycle", 50)

    # Which of the 20260914 tables exist yet. Probed (never thrown): the
    # sweep runs inside one transaction, and a single UndefinedTableError
    # would abort it and kill every kind — including the ones whose tables
    # have been there for months.
    have_demand = await table_present(conn, "translation_demand")
    have_gpt = await table_present(conn, "grammar_point_translations")
    have_gym = await table_present(conn, "gym_label_translations")

    # The demand lane first: rows learners just saw in English (any level,
    # any kind) beat the breadth-first sweep.
    if have_demand:
        budget = await process_demand(conn, budget, stats)

    pairs = await discover_pairs(conn)
    if not pairs or budget <= 0:
        return stats

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
    kinds = [
        ("drills", pending_drills, _translate_drills, "drills"),
        ("explanations", pending_explanations, _translate_explanations,
         "explanations"),
    ]
    if have_gpt:
        kinds.append(("grammar-meta", pending_grammar_meta,
                      _translate_grammar_meta, "grammar_meta"))
    kinds.append(("examples", pending_examples, _translate_examples,
                  "examples"))
    for kind, fetch, translate, stat in kinds:
        for pair in pairs:
            if budget <= 0:
                break
            if kind == "examples" and self_pair(pair):
                continue
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

    # Gym picker labels: a few dozen strings per (language, locale), once
    # ever — small enough to ride outside the row budget's ordering but
    # still bounded by it.
    for pair in pairs:
        if not have_gym or budget <= 0:
            break
        rows = await pending_gym_labels(conn, pair["language_code"],
                                        pair["locale"])
        if not rows:
            continue
        rows = rows[:min(budget, BATCH_SIZE)]
        budget -= len(rows)
        done = await _translate_gym_labels(conn, pair, rows)
        stats["gym_labels"] += done
        stats["processed"] += len(rows)
        logger.info("auto-translate %s→%s: gym labels %d/%d",
                    pair["language_code"], pair["locale"], done, len(rows))
    return stats


async def auto_translate_loop() -> None:
    """In-process sweep, started from the app lifespan like the email loops.
    Survives anything; a sweep failure waits for the next tick. A kick()
    (recorded demand) wakes it early, so what a learner just saw in English
    fills within a couple of minutes instead of at the next quarter-hour."""
    from backend.repositories.pool import privileged_connection

    logger.info("auto-translate loop started (every %ds)", SWEEP_SECONDS)
    while True:
        stats: dict = {}
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
            stats = {}
        if stats.get("demand_left"):
            # Outstanding demand: pace, then go again — don't leave a learner
            # waiting out the sweep interval mid-session.
            await asyncio.sleep(30)
            continue
        try:
            await asyncio.wait_for(_wake.wait(), timeout=SWEEP_SECONDS)
            # Debounce: let a burst of reads finish recording before sweeping.
            await asyncio.sleep(5)
        except TimeoutError:
            pass
        _wake.clear()


# Backlog counts for the admin readout. Separate COUNT queries rather than
# len(pending_*(limit)) — a limited fetch reports its own cap, so a real
# backlog of 5,000 showed as a permanently frozen "1000". The predicates
# mirror each pending_* query exactly; test_status_counts_match_the_queues
# fails if the two ever drift apart.
_PENDING_COUNTS = {
    "words": """
        SELECT count(*) FROM vocabulary v
        JOIN languages l ON l.id = v.language_id
        WHERE v.language_id = $1
          AND NOT EXISTS (SELECT 1 FROM translations t
                           WHERE t.vocabulary_id = v.id AND t.locale = $2)
          AND NOT EXISTS (SELECT 1 FROM translation_reviews r
                           WHERE r.vocabulary_id = v.id AND r.locale = $2)
          AND (l.code = 'en' OR EXISTS (
                SELECT 1 FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en'))""",
    "drills": """
        SELECT count(*) FROM drill_sentences ds
        JOIN grammar_points gp ON gp.id = ds.grammar_point_id
        WHERE gp.language_id = $1
          AND (ds.translation IS NOT NULL OR ds.hint IS NOT NULL)
          AND NOT EXISTS (SELECT 1 FROM drill_hint_translations dht
                           WHERE dht.drill_id = ds.id AND dht.locale = $2)""",
    "explanations": """
        SELECT count(*) FROM grammar_points gp
        WHERE gp.language_id = $1
          AND gp.explanation IS NOT NULL AND gp.explanation <> ''
          AND NOT EXISTS (SELECT 1 FROM explanation_translations et
                           WHERE et.grammar_point_id = gp.id
                             AND et.locale = $2)""",
    "grammar_meta": """
        SELECT count(*) FROM grammar_points gp
        WHERE gp.language_id = $1
          AND NOT EXISTS (SELECT 1 FROM grammar_point_translations gpt
                           WHERE gpt.grammar_point_id = gp.id
                             AND gpt.locale = $2)""",
    "examples": """
        SELECT count(*) FROM example_sentences es
        WHERE es.language_id = $1
          AND es.translation_locale = 'en' AND es.reviewed
          AND es.translation IS NOT NULL AND es.translation <> ''
          AND NOT EXISTS (SELECT 1 FROM example_sentences es2
                           WHERE es2.vocabulary_id = es.vocabulary_id
                             AND es2.sentence = es.sentence
                             AND es2.translation_locale = $2)""",
}


async def count_pending(conn, kind: str, language_id: str, locale: str) -> int:
    """How many rows of *kind* still await translation for this pair."""
    return int(await conn.fetchval(_PENDING_COUNTS[kind], language_id, locale))


async def translation_status(conn: asyncpg.Connection) -> dict:
    """Why translation is (or isn't) happening — the admin readout.

    Every failure mode of this feature is invisible from the app: a course
    left switched off, a migration not applied, no provider key, or simply a
    backlog the per-cycle budget hasn't reached yet. All four look identical
    to a learner ("still English"), so this reports each one directly
    instead of leaving it to be guessed at.
    """
    status: dict = {
        "provider_ready": translations_available(),
        "budget_per_cycle": getattr(
            get_settings(), "auto_translate_words_per_cycle", 50),
        "sweep_seconds": SWEEP_SECONDS,
        "migrations": {},
        "pairs": [],
        "switched_off": [],
    }
    for table in ("translation_demand", "grammar_point_translations",
                  "gym_label_translations"):
        status["migrations"][table] = await table_present(conn, table)

    # Learners whose course is switched OFF — the most common cause of
    # "I turned it on and nothing happened" being about a different course.
    try:
        status["switched_off"] = [
            dict(r) for r in await conn.fetch(
                """
                SELECT l.name AS language, l.code, p.support_locale AS locale,
                       count(*) AS learners
                FROM user_profiles p
                JOIN languages l ON l.id = p.active_language_id
                WHERE NOT l.auto_translate_enabled
                  AND p.support_locale IS NOT NULL AND p.support_locale <> 'en'
                GROUP BY l.name, l.code, p.support_locale
                ORDER BY count(*) DESC
                """
            )
        ]
    except asyncpg.exceptions.UndefinedColumnError:
        status["migrations"]["languages.auto_translate_enabled"] = False
        return status

    for pair in await discover_pairs(conn):
        lang_id, locale = pair["language_id"], pair["locale"]
        pending = {
            kind: await count_pending(conn, kind, lang_id, locale)
            for kind in ("words", "drills", "explanations", "examples")
        }
        if status["migrations"]["grammar_point_translations"]:
            pending["grammar_meta"] = await count_pending(
                conn, "grammar_meta", lang_id, locale)
        if status["migrations"]["gym_label_translations"]:
            pending["gym_labels"] = len(
                await pending_gym_labels(conn, pair["language_code"], locale))
        filled = await conn.fetchrow(
            """
            SELECT (SELECT count(*) FROM translations t
                     JOIN vocabulary v ON v.id = t.vocabulary_id
                    WHERE v.language_id = $1 AND t.locale = $2) AS words,
                   (SELECT count(*) FROM drill_hint_translations dht
                     JOIN drill_sentences ds ON ds.id = dht.drill_id
                     JOIN grammar_points gp ON gp.id = ds.grammar_point_id
                    WHERE gp.language_id = $1 AND dht.locale = $2) AS drills,
                   (SELECT count(*) FROM explanation_translations et
                     JOIN grammar_points gp ON gp.id = et.grammar_point_id
                    WHERE gp.language_id = $1 AND et.locale = $2) AS explanations
            """,
            lang_id, locale,
        )
        status["pairs"].append({
            "language": pair["language_name"], "code": pair["language_code"],
            "locale": locale, "learners": pair["learners"],
            "pending": pending, "filled": dict(filled),
        })
    return status
