"""Demand-driven support-locale gloss filling, as a background loop.

The manual CLI (seeder/translate_english.py) fills English-course glosses for
one locale when an operator runs it. This is the automated, generalized
version — the "translate by demand, not by matrix" rule as running code:

  - A (course, support locale) pair is worked on ONLY while at least one real
    account has that combination in user_profiles. No learners, no spend.
  - Three lanes, in priority order, all inside one per-cycle budget:
      1. DEMAND — content a learner is looking at (or waiting on) right now.
        Always served, whatever the course's toggle says: a person on the
        wait screen outranks every configuration knob.
      2. BASELINE — a course switched OFF but in real recent use gets a
        starter corpus scaled by its active learners (150 words each,
        capped at 600), so being used and being usable stay the same thing
        while an abandoned course costs nothing.
      3. BACKLOG — `languages.auto_translate_enabled` (the admin panel
        toggle) opts a course into the full breadth-first drain. This is
        what the toggle governs — bulk spend, not whether learners are
        served.
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
from datetime import UTC, datetime, timedelta

import asyncpg

from backend.config import get_settings
from backend.services.translate import (
    generate_sentence_translations,
    generate_text_translations,
    maker_check_batch,
    translations_available,
)
from backend.services.translate_checks import safe_row

logger = logging.getLogger(__name__)

SWEEP_SECONDS = 15 * 60
# Words handed to one maker/checker call. Same default as the CLI.
BATCH_SIZE = 25
# Demand rows honoured per kind per cycle — demand is a priority lane, not a
# bypass of the budget.
DEMAND_LIMIT = 50

# How long a failed item waits before the loop tries it again, by attempt
# count. Failure is never final — the last entry repeats — because the
# alternative is what this replaced: one bad batch retiring a word, a
# grammar point or a drill permanently, with the learner reading English
# forever and nothing in the system aware of it.
#
# The curve is shaped for the two real cases. A transient failure (a
# timeout, a rate limit, a checker having an off moment) clears on the
# first or second retry, so those are minutes apart. Content the model
# genuinely cannot render keeps costing a couple of calls a day rather
# than a hot loop.
RETRY_BACKOFF = (
    timedelta(minutes=2),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=6),
    timedelta(days=1),
)

# ---------------------------------------------------------------------------
# Demand: "a learner just saw this in English". Card reads record what was
# missing (translation_demand) and wake the loop, which serves those rows
# before its breadth-first sweep — so the card a learner is looking at fills
# in minutes, not whenever A1-first ordering reaches it.
# ---------------------------------------------------------------------------

_wake = asyncio.Event()

# Proof of life for the sweep, in this process.
#
# Every failure mode of this feature used to look identical from outside:
# a bar stuck at zero. The status readout could say the course was on, the
# provider was ready and the backlog was N — and still not answer the first
# question anyone actually has, which is "is the thing running at all?".
# A loop that never started, a task that died, or a worker that simply
# isn't the one running it all present as "nothing is translating", and
# each has a completely different fix.
_HEARTBEAT: dict = {
    "started": False,
    "last_cycle_at": None,
    "last_stats": None,
    "last_error": None,
    "cycles": 0,
}


def heartbeat() -> dict:
    """What the sweep has done in THIS process. Copied, not shared."""
    return dict(_HEARTBEAT)


def kick() -> None:
    """Wake the loop now (called after demand is recorded).

    Best-effort ONLY, and known to miss in production: the event is
    in-process, and under multiple workers/replicas the process serving
    the request need not be the one whose sweep does the work. The owner's
    panel showed 18 cycles in ~4.5 h — the bare 15-minute cadence, not one
    extra cycle from a kick — while wait screens sat at 0 of 3 the whole
    time and filled "eventually" (the next timer sweep). Anything a
    learner is actively waiting on must NOT rely on this reaching a loop;
    that is what fill_start_batch below is for.
    """
    _wake.set()


# One inline fill at a time per (user, language), and few across the
# process: this runs on the web worker, so it must be impossible for an
# impatient refresher to stack model calls.
_INLINE_FILLS: dict[tuple[str, str], float] = {}
_INLINE_COOLDOWN_S = 90
_INLINE_CONCURRENCY = asyncio.Semaphore(2)
# Enough for the start gate (START_CARDS=3) plus the next few cards, small
# enough that one maker–checker round trip covers it.
INLINE_FILL_WORDS = 8
INLINE_FILL_POINTS = 3
INLINE_FILL_SENTENCES = 8


async def fill_start_batch(
    user_id: str, language_id: str,
    vocab_ids: list, grammar_ids: list,
) -> None:
    """Translate the learner's first cards NOW, in the process they are
    talking to.

    The wait screen used to record demand and kick() the sweep — which
    works only when the kicked process is the one that sweeps. In the
    deployed topology it demonstrably is not, so a learner watched
    "0 of 3" until some other process's quarter-hour timer fired. This
    path owns the wait screen's promise directly: the handful of glosses
    and explanations the start gate needs, plus the sentence layer under
    them (example sentences, drill translations/hints) — without it the
    first cards opened with translated bodies over English "in context"
    lines, which read as another failure. A few bounded round trips,
    written by the web worker itself. The loop remains the bulk engine
    for everything else; this is the espresso shot, not the pot.

    Fire-and-forget safe: never raises, cooldown per (user, language),
    process-wide concurrency cap of 2.
    """
    key = (str(user_id), str(language_id))
    now = asyncio.get_event_loop().time()
    last = _INLINE_FILLS.get(key)
    if last is not None and now - last < _INLINE_COOLDOWN_S:
        return
    _INLINE_FILLS[key] = now
    if not translations_available():
        return
    try:
        async with _INLINE_CONCURRENCY:
            from backend.repositories.pool import privileged_connection

            async with privileged_connection() as conn:
                locale = await conn.fetchval(
                    "SELECT COALESCE(support_locale, NULLIF(ui_language, 'en')) "
                    "FROM user_profiles WHERE id = $1",
                    user_id)
                if not locale or locale == "en":
                    return
                pair = await conn.fetchrow(
                    """SELECT l.id AS language_id, l.code AS language_code,
                              l.name AS language_name,
                              loc.code AS locale, loc.name AS locale_name
                       FROM languages l
                       LEFT JOIN languages loc ON loc.code = $2
                       WHERE l.id = $1""", language_id, locale)
                if pair is None:
                    return
                pair = dict(pair)
                # A support locale with no languages row still deserves a
                # readable name in the prompt.
                pair["locale"] = locale
                pair["locale_name"] = pair["locale_name"] or locale

                # Words first: the start gate counts glossed words, and one
                # batch covers it.
                rows = await pending_words(
                    conn, language_id, locale, INLINE_FILL_WORDS,
                    ids=list(vocab_ids) or None)
                if rows:
                    items = [{"i": i, "word": r["word"], "pos": r["pos"],
                              "definition": r["definition"],
                              "example": r["example"]}
                             for i, r in enumerate(rows)]
                    results = await maker_check_batch(
                        pair["locale_name"], items,
                        source_language=pair["language_name"])
                    by_i = {b["i"]: b for b in results}
                    merged = [{**by_i[i], "id": rows[i]["id"]}
                              for i in range(len(rows)) if i in by_i]
                    applied, _ = await _apply(conn, locale, merged)
                    await _settle(conn, "word", pair,
                                  [r["id"] for r in rows])
                    logger.info(
                        "inline fill %s→%s: %d/%d words for a waiting learner",
                        pair["language_code"], locale, applied, len(rows))

                # The example sentences under those words — the "in context"
                # block a learner reads in the same first minute. The start
                # gate doesn't count them, but a card that opens with a
                # translated gloss over English sentences reads as
                # half-loaded. Skipped on the self-pair, where a rendering
                # would just restate the sentence.
                if vocab_ids and not self_pair(pair):
                    rows = await pending_examples(
                        conn, language_id, locale, INLINE_FILL_SENTENCES,
                        vocab_ids=list(vocab_ids))
                    if rows:
                        done = await _translate_examples(conn, pair, rows)
                        await _settle(conn, "example", pair,
                                      list({r["vocabulary_id"] for r in rows}))
                        logger.info(
                            "inline fill %s→%s: %d/%d example sentences",
                            pair["language_code"], locale, done, len(rows))

                # Then the explanations of the batch's grammar points — a
                # grammar card's body, and what its readiness counts.
                if grammar_ids:
                    rows = await pending_explanations(
                        conn, language_id, locale, INLINE_FILL_POINTS,
                        ids=list(grammar_ids))
                    if rows:
                        done = await _translate_explanations(conn, pair, rows)
                        await _settle(conn, "explanation", pair,
                                      [r["id"] for r in rows])
                        logger.info(
                            "inline fill %s→%s: %d/%d explanations",
                            pair["language_code"], locale, done, len(rows))

                    # And those points' drill sentences — the "in context"
                    # lines of a grammar card. pending_drills is keyed by
                    # drill id, so map the batch's points to their drills
                    # first. On the self-pair _translate_drills renders
                    # hints only (the translation would spell out the
                    # cloze answer).
                    drill_ids = [r["id"] for r in await conn.fetch(
                        """SELECT id FROM drill_sentences
                           WHERE grammar_point_id = ANY($1::uuid[])""",
                        list(grammar_ids))]
                    if drill_ids:
                        rows = await pending_drills(
                            conn, language_id, locale, INLINE_FILL_SENTENCES,
                            ids=drill_ids)
                        if rows:
                            done = await _translate_drills(conn, pair, rows)
                            await _settle(conn, "drill", pair,
                                          [r["id"] for r in rows])
                            logger.info(
                                "inline fill %s→%s: %d/%d drills",
                                pair["language_code"], locale, done, len(rows))
    except Exception as exc:  # noqa: BLE001 — a wait-screen helper, never a page
        logger.warning("inline start-batch fill failed: %s", exc)


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


async def column_present(conn, table: str, column: str) -> bool:
    """Whether *table.column* exists. Same discipline as table_present, and
    same reason: a query naming a missing COLUMN raises too, and that throw
    aborts the whole pooled transaction. Reads a catalog view, so it never
    raises even when the table itself is absent."""
    return bool(await conn.fetchval(
        """SELECT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = $1 AND column_name = $2)""",
        table, column,
    ))


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


def _backoff_sql(alias: str, kind: str) -> str:
    """A NOT EXISTS clause that hides items still inside their retry window.

    Written as SQL rather than a post-filter because every pending_* query
    has a LIMIT: filtering afterwards would let a batch of backed-off rows
    fill the limit and starve everything behind them.

    Only ever spliced in when the caller has PROBED that the table exists
    (see table_present) — naming a missing table would abort the sweep's
    single transaction and take every kind down with it.
    """
    cases = " ".join(
        f"WHEN a.attempts <= {i + 1} THEN interval '{int(d.total_seconds())} seconds'"
        for i, d in enumerate(RETRY_BACKOFF)
    )
    last = int(RETRY_BACKOFF[-1].total_seconds())
    return f"""
        AND NOT EXISTS (
          SELECT 1 FROM translation_attempts a
           WHERE a.kind = '{kind}' AND a.ref_id = {alias} AND a.locale = $2
             AND a.last_attempt_at > now() - (CASE {cases}
                   ELSE interval '{last} seconds' END))"""


async def record_attempts(
    conn: asyncpg.Connection, kind: str, ref_ids, locale: str,
    error: str | None = None,
) -> None:
    """Mark these items as tried-and-not-landed, so they come back later.

    Best-effort by design: if the ledger can't be written the worst case is
    that the item is retried sooner than the backoff intended, which is the
    right way to fail. Never raises into the sweep.
    """
    ids = [r for r in ref_ids if r]
    if not ids:
        return
    try:
        if not await table_present(conn, "translation_attempts"):
            return
        await conn.execute(
            """INSERT INTO translation_attempts
                   (kind, ref_id, locale, attempts, last_attempt_at, last_error)
               SELECT $1, unnest($2::uuid[]), $3, 1, now(), $4
               ON CONFLICT (kind, ref_id, locale) DO UPDATE
                 SET attempts = translation_attempts.attempts + 1,
                     last_attempt_at = now(),
                     last_error = EXCLUDED.last_error""",
            kind, ids, locale, (error or "")[:500] or None,
        )
    except Exception as exc:  # noqa: BLE001 — a ledger, never the sweep
        logger.debug("attempt not recorded for %s/%s: %s", kind, locale, exc)


async def clear_attempts(
    conn: asyncpg.Connection, kind: str, ref_ids, locale: str
) -> None:
    """Forget the failures for content that has now landed, so the table
    holds outstanding problems rather than history."""
    ids = [r for r in ref_ids if r]
    if not ids:
        return
    try:
        if not await table_present(conn, "translation_attempts"):
            return
        await conn.execute(
            """DELETE FROM translation_attempts
                WHERE kind = $1 AND ref_id = ANY($2::uuid[]) AND locale = $3""",
            kind, ids, locale,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("attempts not cleared for %s/%s: %s", kind, locale, exc)


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
            JOIN languages loc
                 ON loc.code = COALESCE(p.support_locale, p.ui_language)
            WHERE l.auto_translate_enabled
              AND COALESCE(p.support_locale, p.ui_language) IS NOT NULL
              AND COALESCE(p.support_locale, p.ui_language) <> 'en'
            GROUP BY l.id, l.code, l.name, loc.code, loc.name
            ORDER BY count(*) DESC, l.name, loc.code
            """
        )
        return [dict(r) for r in rows]
    except asyncpg.exceptions.UndefinedColumnError:
        return []


# How much of a switched-OFF course the loop will still fill, per learner
# who has actually been here lately. The toggle stops the backlog drain —
# it must not stop the course being usable — so a pair with real recent
# accounts gets a starter corpus sized by that usage and nothing more.
# 150 words is roughly a first couple of weeks of study; the cap keeps a
# course with one enthusiastic classroom from quietly becoming a full
# drain the admin thought they had switched off.
BASELINE_WORDS_PER_ACTIVE_LEARNER = 150
BASELINE_WORDS_MAX = 600
BASELINE_ACTIVE_DAYS = 14


async def baseline_pairs(conn: asyncpg.Connection) -> list[dict]:
    """(course, locale) pairs whose course is switched OFF but which real,
    recently active accounts are using — plus how much starter corpus each
    is still owed.

    "Active" is either of the two signals we actually have: a review logged
    in the window, or the profile touched in the window (login/settings).
    A pair whose learners have all drifted away gets nothing: the spend
    follows the people, not the configuration.

    Returns the same keys discover_pairs does, plus `allowance` — how many
    more items the baseline is willing to buy for this pair, ever, at the
    current usage level. Empty when the toggle column's migration hasn't
    landed (same fail-closed rule as discover_pairs).
    """
    try:
        rows = await conn.fetch(
            f"""
            SELECT l.id   AS language_id,
                   l.code AS language_code,
                   l.name AS language_name,
                   loc.code AS locale,
                   loc.name AS locale_name,
                   count(*) AS learners,
                   count(*) FILTER (
                     WHERE p.updated_at > now() - interval '{BASELINE_ACTIVE_DAYS} days'
                        OR EXISTS (
                          SELECT 1 FROM review_log rl
                            JOIN user_cards uc ON uc.id = rl.card_id
                           WHERE rl.user_id = p.id
                             AND uc.language_id = l.id
                             AND rl.created_at > now() - interval '{BASELINE_ACTIVE_DAYS} days')
                   ) AS active_learners,
                   (SELECT count(*) FROM translations t
                      JOIN vocabulary v ON v.id = t.vocabulary_id
                     WHERE v.language_id = l.id AND t.locale = loc.code)
                     AS translated_words
            FROM user_profiles p
            JOIN languages l   ON l.id = p.active_language_id
            JOIN languages loc
                 ON loc.code = COALESCE(p.support_locale, p.ui_language)
            WHERE NOT l.auto_translate_enabled
              AND COALESCE(p.support_locale, p.ui_language) IS NOT NULL
              AND COALESCE(p.support_locale, p.ui_language) <> 'en'
            GROUP BY l.id, l.code, l.name, loc.code, loc.name
            ORDER BY count(*) DESC, l.name, loc.code
            """
        )
    except (asyncpg.exceptions.UndefinedColumnError,
            asyncpg.exceptions.UndefinedTableError):
        return []
    out = []
    for r in rows:
        active = int(r["active_learners"])
        if active <= 0:
            continue
        ceiling = min(BASELINE_WORDS_PER_ACTIVE_LEARNER * active,
                      BASELINE_WORDS_MAX)
        allowance = ceiling - int(r["translated_words"])
        if allowance <= 0:
            continue
        out.append({**{k: r[k] for k in
                       ("language_id", "language_code", "language_name",
                        "locale", "locale_name", "learners")},
                    "allowance": allowance})
    return out


async def pending_words(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int,
    ids: list | None = None, backoff: bool = False,
    skip_reviewed: bool = True,
) -> list[dict]:
    """Words of the course still lacking a *locale* gloss, in the order a
    learner meets them. Mirrors the CLI's query, plus: a non-English course
    word must HAVE an English gloss (the pivot the maker disambiguates with);
    for the English course the headword itself is the English. *ids*
    restricts to specific words (the demand lane).

    Two independent gates, because "has this landed?" and "should I try it
    now?" are different questions and conflating them cost a real bug:

    *skip_reviewed* excludes words whose gloss was rejected into the human
    queue. It is the only brake available without the attempt ledger, so it
    stays on by default — retrying every cycle with nothing pacing it would
    burn the budget on the same few words forever. Turn it OFF to ask the
    pure content question, "is there a gloss yet", which is what deciding
    whether an attempt failed requires. Leaving it on there made a rejected
    word look successful, so no attempt was recorded, so nothing was ever
    paced — and the loop retried it on every single cycle.

    *backoff* is the ledger's own gate: a rejected gloss waits out its retry
    window and then gets another go, because a checker that rejected once is
    not an oracle and the alternative was a word stuck in English forever.
    """
    gate = ""
    if backoff:
        gate += _backoff_sql("v.id", "word")
    if skip_reviewed and not backoff:
        gate += """
          AND NOT EXISTS (
            SELECT 1 FROM translation_reviews r
             WHERE r.vocabulary_id = v.id AND r.locale = $2)"""
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
          {gate}
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
    ids: list | None = None, backoff: bool = False,
) -> list[dict]:
    """Drill sentences whose translation or hint still reads in English —
    the strings a learner sees on every grammar card.

    A row used to count as attempted even when both fields came back NULL,
    which converged the sweep by declaring the drill finished in English.
    Now a drill is pending while a field with English source text has no
    rendering, and the attempt ledger (not a hollow row) is what stops the
    loop re-spending on it every cycle."""
    rows = await conn.fetch(
        f"""
        SELECT ds.id, ds.sentence, ds.translation, ds.hint, ds.answer
        FROM drill_sentences ds
        JOIN grammar_points gp ON gp.id = ds.grammar_point_id
        LEFT JOIN drill_hint_translations dht
               ON dht.drill_id = ds.id AND dht.locale = $2
        WHERE gp.language_id = $1
          AND ($4::uuid[] IS NULL OR ds.id = ANY($4::uuid[]))
          AND (ds.translation IS NOT NULL OR ds.hint IS NOT NULL)
          AND (
            (COALESCE(ds.translation, '') <> '' AND dht.translation IS NULL)
            OR (COALESCE(ds.hint, '') <> '' AND dht.hint IS NULL)
          )
          {_backoff_sql("ds.id", "drill") if backoff else ""}
        ORDER BY {_LEVEL_ORDER.replace('v.level', 'gp.level')} NULLS LAST,
                 gp.display_order NULLS LAST, ds.display_order NULLS LAST, ds.id
        LIMIT $3
        """,
        language_id, locale, limit, ids,
    )
    return [dict(r) for r in rows]


async def pending_explanations(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int,
    ids: list | None = None, backoff: bool = False,
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
          {_backoff_sql("gp.id", "explanation") if backoff else ""}
        ORDER BY {_LEVEL_ORDER.replace('v.level', 'gp.level')} NULLS LAST,
                 gp.display_order NULLS LAST, gp.id
        LIMIT $3
        """,
        language_id, locale, limit, ids,
    )
    return [dict(r) for r in rows]


async def pending_grammar_meta(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int,
    ids: list | None = None, backoff: bool = False,
) -> list[dict]:
    """Grammar points whose title/notes still read in English.

    "Has a row" used to mean "done", and _translate_grammar_meta wrote a row
    whether or not anything came back — so a point whose title and notes all
    failed was marked finished with every field NULL, and the read path's
    COALESCE served English forever. That is the card in the bug report: a
    Catalan point with a Spanish interface, an English title and an English
    culture note, and nothing anywhere trying to fix it.

    Now a point is pending while any field that HAS English source text
    still has no rendering, so a partial success finishes on a later pass
    instead of freezing half-translated.
    """
    rows = await conn.fetch(
        f"""
        SELECT gp.id, gp.title, gp.culture_note, gp.function_note
        FROM grammar_points gp
        LEFT JOIN grammar_point_translations gpt
               ON gpt.grammar_point_id = gp.id AND gpt.locale = $2
        WHERE gp.language_id = $1
          AND ($4::uuid[] IS NULL OR gp.id = ANY($4::uuid[]))
          AND (
            (COALESCE(gp.title, '') <> '' AND gpt.title IS NULL)
            OR (COALESCE(gp.culture_note, '') <> '' AND gpt.culture_note IS NULL)
            OR (COALESCE(gp.function_note, '') <> '' AND gpt.function_note IS NULL)
          )
          {_backoff_sql("gp.id", "grammar_meta") if backoff else ""}
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
    vocab_ids: list | None = None, backoff: bool = False,
) -> list[dict]:
    """Reviewed English example sentences whose *locale* sibling row doesn't
    exist yet. The sibling is a full example_sentences row (same sentence,
    translation_locale = locale); the CLI's -k translations fills these by
    hand, this is the loop's lane. Unreviewed rows are skipped — no point
    translating content a learner can't see."""
    rows = await conn.fetch(
        f"""
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
          {_backoff_sql("es.vocabulary_id", "example") if backoff else ""}
        ORDER BY es.difficulty_rank NULLS LAST, es.id
        LIMIT $3
        """,
        language_id, locale, limit, vocab_ids,
    )
    return [dict(r) for r in rows]


async def words_with_pending_examples(
    conn: asyncpg.Connection, language_id: str, locale: str, vocab_ids: list,
) -> set:
    """Which of *vocab_ids* still have an example sentence awaiting *locale*.

    Demand for the example kind is recorded per WORD, but the work is per
    SENTENCE, and a word commonly owns three. One ref_id is therefore not
    one unit of work, and clearing the whole batch after a row-limited pass
    deleted the demand for every word whose sentences fell past the limit —
    they then dropped to the breadth-first sweep, where examples run last,
    behind the entire untranslated word backlog. On a large course that is
    never: the readiness bar sat at exactly the fraction glosses alone can
    reach and stopped.

    Predicate identical to pending_examples, so "nothing pending" here means
    exactly "that query would return nothing".
    """
    rows = await conn.fetch(
        """
        SELECT DISTINCT es.vocabulary_id
        FROM example_sentences es
        WHERE es.language_id = $1
          AND es.vocabulary_id = ANY($3::uuid[])
          AND es.translation_locale = 'en'
          AND es.reviewed
          AND es.translation IS NOT NULL AND es.translation <> ''
          AND NOT EXISTS (
            SELECT 1 FROM example_sentences es2
             WHERE es2.vocabulary_id = es.vocabulary_id
               AND es2.sentence = es.sentence
               AND es2.translation_locale = $2)
        """,
        language_id, locale, list(vocab_ids),
    )
    return {r["vocabulary_id"] for r in rows}


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
    reviewer can amend later).

    A drill that rendered NOTHING is left with no row at all. Writing one
    used to "record the attempt", but pending_drills read a row as done, so
    a single failed batch retired the drill in English permanently. The
    attempt ledger records the try now; the row means content.

    On the self-pair only the HINT is rendered: the translation would spell
    out the cloze answer (see self_pair)."""
    out: dict[str, dict] = {str(r["id"]): {"translation": None, "hint": None}
                            for r in rows}
    fields = ("hint",) if self_pair(pair) else ("translation", "hint")
    for field in fields:
        # The HINT carries the drill's answer so the gate can refuse a
        # rendering that names it. The TRANSLATION field does not: it
        # legitimately renders the sentence's full meaning, and gating it on
        # the English answer would reject every Spanish sentence containing
        # "no" for a drill whose answer is the English word "no" — the
        # cross-language homograph phantom of quality rule 19.
        items = [{"i": i, "sentence": r[field],
                  **({"answer": r.get("answer") or ""} if field == "hint" else {})}
                 for i, r in enumerate(rows) if r[field]]
        if not items:
            continue
        results = await generate_sentence_translations(
            pair["locale_name"], items, locale=pair["locale"])
        for res in results:
            row = safe_row(rows, res["i"])
            if res["translation"] and row is not None:
                out[str(row["id"])][field] = res["translation"]
    applied = 0
    for r in rows:
        vals = out[str(r["id"])]
        if not (vals["translation"] or vals["hint"]):
            continue
        await conn.execute(
            """INSERT INTO drill_hint_translations
                   (drill_id, locale, hint, translation, reviewed)
               VALUES ($1, $2, $3, $4, false)
               ON CONFLICT (drill_id, locale) DO UPDATE SET
                 -- Fill what an earlier pass missed; never clobber a
                 -- rendering that already exists.
                 hint = COALESCE(drill_hint_translations.hint, EXCLUDED.hint),
                 translation = COALESCE(drill_hint_translations.translation,
                                        EXCLUDED.translation)""",
            r["id"], pair["locale"], vals["hint"], vals["translation"])
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
                                               kind="prose",
                                               locale=pair["locale"])
    applied = 0
    for res in results:
        row = safe_row(rows, res["i"])
        if not res["translation"] or row is None:
            continue
        await conn.execute(
            """INSERT INTO explanation_translations
                   (grammar_point_id, locale, explanation, reviewed)
               VALUES ($1, $2, $3, false)
               ON CONFLICT (grammar_point_id, locale) DO NOTHING""",
            row["id"], pair["locale"], res["translation"])
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
                                                   kind=kind,
                                                   locale=pair["locale"])
        for res in results:
            row = safe_row(rows, res["i"])
            if res["translation"] and row is not None:
                out[str(row["id"])][field] = res["translation"]
    applied = 0
    for r in rows:
        vals = out[str(r["id"])]
        if not any(vals.values()):
            # Nothing came back. Writing the row anyway is what made failure
            # permanent: pending_grammar_meta saw a row, called the point
            # done, and the learner kept the English title forever.
            continue
        await conn.execute(
            """INSERT INTO grammar_point_translations
                   (grammar_point_id, locale, title, culture_note,
                    function_note, reviewed)
               VALUES ($1, $2, $3, $4, $5, false)
               ON CONFLICT (grammar_point_id, locale) DO UPDATE SET
                 -- Fill the gaps a previous pass left; never overwrite a
                 -- rendering that already landed (a reviewer may have
                 -- corrected it).
                 title = COALESCE(grammar_point_translations.title,
                                  EXCLUDED.title),
                 culture_note = COALESCE(grammar_point_translations.culture_note,
                                         EXCLUDED.culture_note),
                 function_note = COALESCE(grammar_point_translations.function_note,
                                          EXCLUDED.function_note)""",
            r["id"], pair["locale"], vals["title"], vals["culture_note"],
            vals["function_note"])
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
                                                   kind="label",
                                                   locale=pair["locale"])
        for res in results:
            row = safe_row(rows, res["i"])
            if res["translation"] and row is not None:
                out[row["point"]][field] = res["translation"]
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
    sibling example_sentences rows via the same helper the CLI uses.

    These land reviewed=true, unlike AI-generated sentences. pending_examples
    only ever picks sources a human already approved, so the sentence and its
    meaning are signed off — the loop rewrites the meaning LINE into the
    learner's language through the same maker-checker that produces word
    glosses, and those display immediately. Landing these unreviewed meant a
    learner whose language was fully translated still read every example in
    English, with no signal that anything was pending. The WP42 gate still
    holds for sentences the AI invents."""
    from backend.repositories.contributor import add_example_sentence

    if self_pair(pair):
        return 0  # the rendering would just restate the sentence
    items = [{"i": i, "sentence": r["translation"]} for i, r in enumerate(rows)]
    results = await generate_sentence_translations(
        pair["locale_name"], items, locale=pair["locale"])
    applied = 0
    for res in results:
        r = safe_row(rows, res["i"])
        if not res["translation"] or r is None:
            continue
        row_id = await add_example_sentence(
            conn, r["vocabulary_id"], r["language_id"], r["sentence"],
            res["translation"], source="ai",
            origin_detail=f"auto_translate:{pair['locale']}",
            translation_locale=pair["locale"],
            reviewed=True,  # the English source was already approved
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
    oldest request first. Empty when the demand migration hasn't landed.

    Deliberately NOT filtered by the course's auto_translate toggle. Demand
    means a real learner is looking at English right now — usually on the
    wait screen, watching a bar that promises this exact work. The toggle
    used to gate this lane too, and since most courses ship switched off,
    every language change sat at "0 of 3 cards ready" forever while the
    loop reported itself healthy. The toggle governs the BACKLOG — whether
    the sweep drains a whole course nobody is waiting on — not whether a
    waiting learner gets their batch.
    """
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


async def _still_pending(conn, kind: str, b: dict, ids: list) -> set:
    """Which of *ids* the translator did NOT manage to land.

    Asked by re-running the kind's own pending query over the same ids, so
    "landed" means exactly what the loop's own predicate means — no second
    definition of done to drift out of sync with the first.

    Every scheduling gate is off here on purpose. This is the content
    question ("is the rendering there?"), not the scheduling one ("should I
    try it now?"): with the gates on, a word that had just been rejected —
    or one still inside its retry window — reads as landed, no attempt gets
    recorded, and nothing paces the retry.
    """
    if not ids:
        return set()
    lang, loc = b["language_id"], b["locale"]
    n = len(ids)
    if kind == "word":
        rows = await pending_words(conn, lang, loc, n, ids,
                                   skip_reviewed=False)
    elif kind == "drill":
        rows = await pending_drills(conn, lang, loc, n, ids)
    elif kind == "explanation":
        rows = await pending_explanations(conn, lang, loc, n, ids)
    elif kind == "grammar_meta":
        rows = await pending_grammar_meta(conn, lang, loc, n, ids)
    elif kind == "example":
        return await words_with_pending_examples(conn, lang, loc, ids)
    else:
        return set()
    return {r["id"] for r in rows}


# The sweep names its kinds for logging; the ledger names them the way the
# demand queue does. One map rather than two vocabularies.
_SWEEP_KIND = {
    "drills": "drill",
    "explanations": "explanation",
    "grammar-meta": "grammar_meta",
    "examples": "example",
}


class _BatchError(Exception):
    """One translate call died. Carries the reason to the ledger."""


async def _guard(coro, kind: str, pair: dict):
    """Run one translate call so that its failure costs a BATCH, not the sweep.

    Nothing between messages.create and auto_translate_loop caught anything,
    so a single provider error — a 429, a timeout, a 500 — propagated to the
    top and aborted the entire cycle. Every remaining pair and every
    remaining kind was skipped, and the next cycle started from the same
    place and hit the same wall. One rate limit could therefore stop all
    translation for everyone, indefinitely, while the logs said only
    "sweep failed".

    That is also how the trivia bank could take the loop down with it: both
    spend the same key, so the game's generation could provoke the very
    error that killed the fill the learner was waiting on.
    """
    try:
        return await coro
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 — one batch, not the cycle
        logger.warning("auto-translate %s→%s: %s batch failed: %s",
                       pair.get("language_code"), pair.get("locale"), kind,
                       exc)
        raise _BatchError(f"{type(exc).__name__}: {exc}") from exc


async def _settle(conn, kind: str, pair: dict, tried: list) -> None:
    """Record the outcome of a sweep batch in the attempt ledger.

    The sweep has no queue to leave things in, so without this a failure
    there was invisible: the next cycle re-fetched the same rows, spent the
    same budget and failed the same way, forever crowding out content that
    would have succeeded. Now a failure costs its backoff and steps aside.
    """
    if not tried:
        return
    stuck = await _still_pending(conn, kind, pair, tried)
    landed = [i for i in tried if i not in stuck]
    await clear_attempts(conn, kind, landed, pair["locale"])
    if stuck:
        await record_attempts(conn, kind, list(stuck), pair["locale"],
                              error="no rendering returned")


async def process_demand(conn: asyncpg.Connection, budget: int,
                         stats: dict) -> int:
    """The priority lane: translate exactly what learners just saw in
    English, oldest first, spending from the same cycle budget.

    Demand now survives a failed attempt. It used to be deleted whatever
    happened — "processed (or unprocessable)" — which, combined with three
    kinds recording failure as a permanent success, is why a learner who
    hit one bad batch stayed on English forever with nothing retrying.
    A row leaves this queue when its content lands, and the attempt ledger
    paces the retries in between.
    """
    have_attempts = await table_present(conn, "translation_attempts")
    batches = await _demand_batches(conn)
    if not batches:
        return budget
    await _sweep_stale_demand(conn)
    for b in batches:
        if budget <= 0:
            break
        pair = b  # same keys the translators expect
        # Attempt only what this cycle can actually pay for, and clear only
        # THAT slice. The remainder stays queued for the next pass instead
        # of being deleted unprocessed — over-clearing dropped everything
        # past the batch cap onto the breadth-first sweep, which is orders
        # of magnitude slower and starves the low-priority kinds. That is
        # what left one lesson's examples half in the learner's language
        # and half in English, permanently.
        take = min(budget, BATCH_SIZE)
        kind, ids = b["kind"], b["ref_ids"][:take]
        failure: str | None = None
        # What the model was actually handed this cycle. Filled from the
        # rows each pending_* returns, NOT from the whole batch: items
        # sitting inside their retry window are skipped by the query, and
        # counting those as fresh failures would race the backoff up to its
        # ceiling within minutes and rewrite the ledger on every pass.
        tried: list = []
        n = 0
        try:
            if kind == "word":
                rows = await pending_words(conn, b["language_id"], b["locale"],
                                           take, ids, backoff=have_attempts)
                if rows:
                    items = [{"i": i, "word": r["word"], "pos": r["pos"],
                              "definition": r["definition"], "example": r["example"]}
                             for i, r in enumerate(rows)]
                    results = await _guard(maker_check_batch(
                        b["locale_name"], items,
                        source_language=b["language_name"]), kind, b)
                    by_i = {x["i"]: x for x in results}
                    merged = [{**by_i[i], "id": rows[i]["id"]}
                              for i in range(len(rows)) if i in by_i]
                    applied, queued = await _apply(conn, b["locale"], merged)
                    stats["applied"] += applied
                    stats["queued"] += queued
                    n = len(rows)
                    tried = [r["id"] for r in rows]
            elif kind == "drill":
                rows = await pending_drills(conn, b["language_id"], b["locale"],
                                            take, ids, backoff=have_attempts)
                if rows:
                    stats["drills"] += await _guard(
                        _translate_drills(conn, pair, rows), kind, b)
                    n = len(rows)
                    tried = [r["id"] for r in rows]
            elif kind == "explanation":
                rows = await pending_explanations(conn, b["language_id"],
                                                  b["locale"],
                                                  take, ids, backoff=have_attempts)
                if rows:
                    stats["explanations"] += await _guard(
                        _translate_explanations(conn, pair, rows), kind, b)
                    n = len(rows)
                    tried = [r["id"] for r in rows]
            elif kind == "grammar_meta":
                rows = await pending_grammar_meta(conn, b["language_id"],
                                                  b["locale"],
                                                  take, ids, backoff=have_attempts)
                if rows:
                    stats["grammar_meta"] += await _guard(
                        _translate_grammar_meta(conn, pair, rows), kind, b)
                    n = len(rows)
                    tried = [r["id"] for r in rows]
            elif kind == "example":
                rows = [] if self_pair(b) else await pending_examples(
                    conn, b["language_id"], b["locale"],
                    take, ids, backoff=have_attempts)
                if rows:
                    stats["examples"] += await _guard(
                        _translate_examples(conn, pair, rows), kind, b)
                    n = len(rows)
                    # Example rows are SENTENCES; demand is per word.
                    tried = list({r["vocabulary_id"] for r in rows})
            elif kind == "gym":
                rows = await pending_gym_labels(conn, b["language_code"],
                                                b["locale"])
                if rows:
                    stats["gym_labels"] += await _guard(
                        _translate_gym_labels(conn, pair, rows[:take]), kind, b)
                    n = min(len(rows), take)
        except _BatchError as exc:
            failure = str(exc)
        # Gym labels have no per-ref pending query and no partial state:
        # one manifest, done or not. Self-pair examples are not work at all.
        if kind == "gym" or (kind == "example" and self_pair(b)):
            await _clear_demand(conn, kind, ids, b["locale"])
        else:
            # Landed or not, judged by the kind's OWN pending predicate.
            # What landed leaves the queue and loses its failure history;
            # what was tried and didn't land is one attempt older and waits
            # for its next window. Anything skipped because it is already
            # inside a window is left completely alone — still queued, no
            # attempt counted.
            stuck = await _still_pending(conn, kind, b, tried)
            landed = [i for i in tried if i not in stuck]
            await clear_attempts(conn, kind, landed, b["locale"])
            await _clear_demand(conn, kind, landed, b["locale"])
            if stuck:
                await record_attempts(
                    conn, kind, list(stuck), b["locale"],
                    error=failure or "no rendering returned")
                stats["retrying"] = stats.get("retrying", 0) + len(stuck)
                if not have_attempts:
                    # No ledger means nothing paces a retry, so drop the row
                    # rather than spin on it every cycle. The breadth-first
                    # sweep is then the only way back — slow, but bounded.
                    await _clear_demand(conn, kind, list(stuck), b["locale"])
        if n:
            budget -= n
            stats["processed"] += n
            stats["demand"] += n
            logger.info("auto-translate demand %s→%s: %s ×%d",
                        b["language_code"], b["locale"], kind, n)
    # Demand that didn't fit this cycle's budget (a big lookahead, a busy
    # hour) makes the loop go again promptly instead of sleeping a full
    # sweep interval — the budget still caps each cycle's burst.
    #
    # Conditional on having DONE something: rows now survive a failure, so
    # "demand exists" is no longer the same question as "there is work I can
    # act on". A queue holding nothing but items inside their retry windows
    # would otherwise spin the loop every 30 seconds to do nothing at all.
    if stats.get("demand") and any(await _demand_batches(conn)):
        stats["demand_left"] = True
    return budget


async def run_translation_cycle(conn: asyncpg.Connection) -> dict:
    """One sweep: spend the cycle's word budget across the live pairs.

    Returns {"pairs", "processed", "applied", "queued"} so the loop can log
    something meaningful (and tests can assert on it).
    """
    stats = {"pairs": 0, "processed": 0, "applied": 0, "queued": 0,
             "drills": 0, "explanations": 0, "grammar_meta": 0,
             "gym_labels": 0, "examples": 0, "demand": 0, "baseline": 0}
    budget = getattr(get_settings(), "auto_translate_words_per_cycle", 50)

    # Which of the 20260914 tables exist yet. Probed (never thrown): the
    # sweep runs inside one transaction, and a single UndefinedTableError
    # would abort it and kill every kind — including the ones whose tables
    # have been there for months.
    have_demand = await table_present(conn, "translation_demand")
    have_gpt = await table_present(conn, "grammar_point_translations")
    have_gym = await table_present(conn, "gym_label_translations")
    # The attempt ledger. Without it the sweep keeps its old shape, where
    # what stops a retry is the overlay row itself; with it, a failure is
    # paced and always comes back.
    have_attempts = await table_present(conn, "translation_attempts")

    # Repair translations produced BEFORE they were stored visibly. Those
    # rows are not just hidden, they're stuck: pending_examples skips any
    # sentence that already has a locale sibling, so the loop believes the
    # work is done and never retries. Idempotent, and a no-op once the
    # backfill migration lands (or after the first pass here) — but it means
    # a learner sees their sentences without waiting on a db push.
    try:
        await conn.execute(
            """UPDATE example_sentences SET reviewed = true
                WHERE reviewed = false AND translation_locale <> 'en'
                  AND (origin_detail LIKE 'auto_translate:%'
                    OR origin_detail LIKE 'translate:%')"""
        )
    except Exception as exc:  # noqa: BLE001 — never break the sweep
        logger.debug("sentence visibility repair skipped: %s", exc)

    # The demand lane first: rows learners just saw in English (any level,
    # any kind) beat the breadth-first sweep.
    if have_demand:
        budget = await process_demand(conn, budget, stats)

    # Two tiers of breadth-first work behind the demand lane:
    #  - switched-ON courses: the full backlog, as ever (cap = None);
    #  - switched-OFF courses with recently active learners: a starter
    #    corpus, capped by usage (baseline_pairs), so a course being used
    #    is never unusable but a course nobody visits costs nothing.
    pairs = await discover_pairs(conn)
    for p in pairs:
        p["cap"] = None
    for p in await baseline_pairs(conn):
        p["cap"] = p["allowance"]
        pairs.append(p)
    if not pairs or budget <= 0:
        return stats

    def take_for(pair: dict, want: int) -> int:
        return want if pair["cap"] is None else max(0, min(want, pair["cap"]))

    def spend(pair: dict, n: int) -> None:
        if pair["cap"] is not None:
            pair["cap"] -= n
            stats["baseline"] += n

    for pair in pairs:
        if budget <= 0:
            break
        take = take_for(pair, min(budget, BATCH_SIZE))
        if take <= 0:
            continue
        rows = await pending_words(conn, pair["language_id"], pair["locale"],
                                   take, backoff=have_attempts)
        if not rows:
            continue
        stats["pairs"] += 1
        budget -= len(rows)
        spend(pair, len(rows))
        items = [{"i": i, "word": r["word"], "pos": r["pos"],
                  "definition": r["definition"], "example": r["example"]}
                 for i, r in enumerate(rows)]
        try:
            results = await _guard(maker_check_batch(
                pair["locale_name"], items,
                source_language=pair["language_name"],
            ), "word", pair)
        except _BatchError as exc:
            # One pair's provider error must not end the cycle for every
            # other pair and kind behind it.
            await record_attempts(conn, "word", [r["id"] for r in rows],
                                  pair["locale"], error=str(exc))
            continue
        by_i = {b["i"]: b for b in results}
        merged = [{**by_i[i], "id": rows[i]["id"]}
                  for i in range(len(rows)) if i in by_i]
        applied, queued = await _apply(conn, pair["locale"], merged)
        stats["processed"] += len(merged)
        stats["applied"] += applied
        stats["queued"] += queued
        await _settle(conn, "word", pair, [r["id"] for r in rows])
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
            take = take_for(pair, min(budget, BATCH_SIZE))
            if take <= 0:
                continue
            rows = await fetch(conn, pair["language_id"], pair["locale"],
                               take, backoff=have_attempts)
            if not rows:
                continue
            budget -= len(rows)
            spend(pair, len(rows))
            refs = (list({r["vocabulary_id"] for r in rows})
                    if kind == "examples" else [r["id"] for r in rows])
            try:
                done = await _guard(translate(conn, pair, rows), kind, pair)
            except _BatchError as exc:
                await record_attempts(conn, _SWEEP_KIND[kind], refs,
                                      pair["locale"], error=str(exc))
                continue
            stats[stat] += done
            stats["processed"] += len(rows)
            await _settle(conn, _SWEEP_KIND[kind], pair, refs)
            logger.info("auto-translate %s→%s: %s %d/%d",
                        pair["language_code"], pair["locale"], kind, done,
                        len(rows))

    # Gym picker labels: a few dozen strings per (language, locale), once
    # ever — small enough to ride outside the row budget's ordering but
    # still bounded by it.
    for pair in pairs:
        if not have_gym or budget <= 0:
            break
        take = take_for(pair, min(budget, BATCH_SIZE))
        if take <= 0:
            continue
        rows = await pending_gym_labels(conn, pair["language_code"],
                                        pair["locale"])
        if not rows:
            continue
        rows = rows[:take]
        budget -= len(rows)
        spend(pair, len(rows))
        try:
            done = await _guard(
                _translate_gym_labels(conn, pair, rows), "gym", pair)
        except _BatchError:
            continue
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
    _HEARTBEAT["started"] = True
    while True:
        stats: dict = {}
        try:
            if translations_available():
                async with privileged_connection() as conn:
                    stats = await run_translation_cycle(conn)
                if stats["processed"]:
                    logger.info("auto-translate sweep: %s", stats)
            _HEARTBEAT["last_error"] = None
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — the loop must survive anything
            logger.warning("auto-translate sweep failed: %s", exc)
            _HEARTBEAT["last_error"] = f"{type(exc).__name__}: {exc}"
            stats = {}
        # Stamped whether or not anything was translated: "ran and found
        # nothing to do" and "never ran" are different answers, and only one
        # of them means something is broken.
        _HEARTBEAT["last_cycle_at"] = datetime.now(UTC).isoformat()
        _HEARTBEAT["last_stats"] = stats or None
        _HEARTBEAT["cycles"] += 1
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


async def diagnose_pair(
    conn: asyncpg.Connection, language_id: str, locale: str
) -> dict:
    """Why this ONE (course, support locale) pair is or isn't filling.

    translation_status answers the question for pairs the loop already
    finds. That is the wrong end: a pair that fails a precondition is
    exactly the one nobody can explain, and it is invisible there — no
    error, no log line, a bar stuck at zero and four plausible theories.

    Returns named blockers, so "it's stuck" becomes "the course is switched
    off" or "that locale isn't in the languages table" without another
    round of guessing.
    """
    blockers: list[str] = []
    detail: dict = {}

    lang = await conn.fetchrow(
        "SELECT code, name, auto_translate_enabled FROM languages WHERE id = $1",
        language_id)
    if lang is None:
        return {"blockers": ["unknown_language"], "detail": {}}
    detail["course"] = lang["code"]
    if not lang["auto_translate_enabled"]:
        # No longer fatal: the demand lane serves waiting learners and the
        # baseline lane buys a usage-scaled starter corpus regardless of the
        # toggle. Still reported, because "the backlog will not drain" is a
        # real answer to "why is most of this course still English".
        blockers.append("switched_off")

    # discover_pairs joins the locale back to `languages`; without a row the
    # pair simply does not exist as far as the loop is concerned.
    if not await conn.fetchval(
        "SELECT 1 FROM languages WHERE code = $1", locale
    ):
        blockers.append("locale_not_a_language")

    if locale == "en":
        blockers.append("english_is_the_source")

    learners = int(await conn.fetchval(
        """SELECT count(*) FROM user_profiles
            WHERE active_language_id = $1
              AND COALESCE(support_locale, ui_language) = $2""",
        language_id, locale) or 0)
    detail["learners_with_this_active"] = learners
    if not learners:
        # The sweep is demand-driven off active_language_id; a learner whose
        # ACTIVE course is a different one still generates demand rows by
        # reading cards, but the breadth-first sweep will never reach this.
        blockers.append("no_learner_has_this_course_active")

    if not translations_available():
        blockers.append("no_provider")

    for table in ("translation_demand", "translation_attempts",
                  "grammar_point_translations"):
        if not await table_present(conn, table):
            blockers.append(f"migration_missing:{table}")

    if await table_present(conn, "translation_demand"):
        detail["queued"] = int(await conn.fetchval(
            "SELECT count(*) FROM translation_demand WHERE locale = $1",
            locale) or 0)
    if await table_present(conn, "translation_attempts"):
        detail["retrying"] = int(await conn.fetchval(
            "SELECT count(*) FROM translation_attempts WHERE locale = $1",
            locale) or 0)
        detail["last_error"] = await conn.fetchval(
            """SELECT last_error FROM translation_attempts
                WHERE locale = $1 AND last_error IS NOT NULL
                ORDER BY last_attempt_at DESC LIMIT 1""", locale)

    detail["words_pending"] = await count_pending(
        conn, "words", language_id, locale)
    detail["glosses_filled"] = int(await conn.fetchval(
        """SELECT count(*) FROM translations t
            JOIN vocabulary v ON v.id = t.vocabulary_id
           WHERE v.language_id = $1 AND t.locale = $2""",
        language_id, locale) or 0)
    return {"blockers": blockers, "detail": detail}


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
        # The first question anyone asks, and the one this readout could not
        # answer: is the sweep running? Everything below describes work the
        # loop WOULD do; none of it means anything if the loop is not there.
        # loop_enabled is the settings flag; heartbeat is what this process
        # has actually done, so "enabled but never ran" is visible too.
        "loop_enabled": getattr(
            get_settings(), "auto_translate_loop_enabled", False),
        "loop": heartbeat(),
        "migrations": {},
        "pairs": [],
        "switched_off": [],
    }
    # translation_attempts belongs here even though nothing crashes without
    # it: the retry ledger is what paces a failed item instead of abandoning
    # it, so its absence is silent by design and therefore invisible unless
    # this readout names it. A green "Migrations applied" that doesn't cover
    # the table is worse than no light at all.
    for table in ("translation_demand", "translation_attempts",
                  "grammar_point_translations", "gym_label_translations"):
        status["migrations"][table] = await table_present(conn, table)

    # Learners whose course is switched OFF — the most common cause of
    # "I turned it on and nothing happened" being about a different course.
    try:
        status["switched_off"] = [
            dict(r) for r in await conn.fetch(
                """
                SELECT l.name AS language, l.code,
                       COALESCE(p.support_locale, p.ui_language) AS locale,
                       count(*) AS learners
                FROM user_profiles p
                JOIN languages l ON l.id = p.active_language_id
                WHERE NOT l.auto_translate_enabled
                  AND COALESCE(p.support_locale, p.ui_language) IS NOT NULL
                  AND COALESCE(p.support_locale, p.ui_language) <> 'en'
                GROUP BY l.name, l.code,
                         COALESCE(p.support_locale, p.ui_language)
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
