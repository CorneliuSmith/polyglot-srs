"""Content verdicts: the rows the nightly judge reads next and the rows it
writes back (migration 20261107000000, `content_verdicts`).

Why a second repository beside `quality.py`: `quality_runs` is a ledger of
numbers and this table is a ledger of judgements — one row per judged
(row, question, locale, run) carrying the evidence, the rewrite and a
disposition a reviewer sets. The two join on `run_id`, so "what did the
judge say the night it spent 40k tokens on Arabic" is one query.

Two rules, both `quality.py`'s:

* **Every function degrades on an absent table**, under a savepoint,
  because migrations are the owner's to apply and the loop runs inside one
  privileged transaction where a failed statement poisons everything after
  it (LEARN.md, "try/except a SQL error inside a transaction is a no-op").
* **The writes are the judge's only.** A verdict is a queue item, never a
  change to content (plan §3, principle 5). Routing one into
  `card_change_requests` needs a service account — owner decision #2 — and
  is not here.

Row selection is the plan's priority order made SQL (`candidates`): rows
never judged for this question first, the top of the frequency band first
within them, and only then the rows judged longest ago — so a 200-row night
reaches the cards most learners hold before it re-reads anything. The SQL
for each question's scope is `register_pass.load_db_store`'s, copied rather
than imported: that function opens its own connection over `DATABASE_URL`
and reads one course (`CODE`), and the loop already holds a connection and
walks 27.
"""
from __future__ import annotations

from decimal import Decimal

import asyncpg

from backend.repositories.pool import savepoint
from backend.services.auto_translate import column_present

_MISSING = (asyncpg.exceptions.UndefinedTableError, asyncpg.exceptions.UndefinedColumnError)

# Where a judge item keeps the row it came from. `content_judge.run_items`
# sends every key but `id` to the model, so the step strips this one before
# the call and `record_verdicts` reads it after — the judge sees the item
# shape it was calibrated on, and the verdict still finds its row.
ENTITY_KEY = "entity"

# Each question's scope: one SELECT, `$1` = language_id, yielding the four
# entity columns the verdict is written back to, `frequency_rank` for the
# ordering, and the item columns `_item` reads. Column names are the
# schema's (20260312 initial, 20260613000002 example_sentences).
#
# `str.format` templates, not SQL: `{v_retired}` and `{gp_retired}` are the
# `retired_at IS NULL` predicates `_scope` fills in after probing for the
# column (see there), and the drill marker is written `{{{{answer}}}}` so
# the format halves it to the literal `{{answer}}` the rows hold.
#
# Register reads sentences the way `register_pass --store db-sentences`
# did — text, translation and headword, NO rank: REGISTER_RULES says "an
# item with a rank is a headword from a frequency list" and judges it as an
# entry, so a rank on a sentence would send the judge down the wrong branch
# of the question it was calibrated on. A drill is sent with `{{answer}}`
# filled in, because the judge reads a sentence and the marker is not one.
_SCOPE: dict[str, str] = {
    "register": """
        SELECT 'example_sentence' AS entity_type, es.id AS entity_id,
               'sentence' AS field, NULL::text AS locale, v.frequency_rank,
               'sentence' AS item_field, es.sentence AS text, es.translation,
               v.word AS headword
          FROM example_sentences es
          JOIN vocabulary v ON v.id = es.vocabulary_id
         WHERE es.language_id = $1::uuid
           {v_retired}
        UNION ALL
        SELECT 'drill', d.id, 'sentence', NULL::text, NULL::int,
               'drill', replace(d.sentence, '{{{{answer}}}}', COALESCE(d.answer, '')),
               d.translation, d.answer
          FROM drill_sentences d
          JOIN grammar_points gp ON gp.id = d.grammar_point_id
         WHERE gp.language_id = $1::uuid
           {gp_retired}
    """,
    "sense": """
        SELECT 'vocabulary' AS entity_type, v.id AS entity_id,
               'definition' AS field, NULL::text AS locale, v.frequency_rank,
               v.word, v.part_of_speech AS pos, t.definition
          FROM vocabulary v
          JOIN translations t ON t.vocabulary_id = v.id AND t.locale = 'en'
         WHERE v.language_id = $1::uuid
           AND COALESCE(t.definition, '') <> ''
           {v_retired}
    """,
    "gloss": """
        SELECT 'translation' AS entity_type, t.id AS entity_id,
               'definition' AS field, t.locale, v.frequency_rank,
               v.word, v.part_of_speech AS pos, en.definition, t.definition AS gloss
          FROM translations t
          JOIN vocabulary v ON v.id = t.vocabulary_id
          JOIN translations en ON en.vocabulary_id = v.id AND en.locale = 'en'
         WHERE v.language_id = $1::uuid
           AND t.locale <> 'en'
           {v_retired}
    """,
    "scripture": """
        SELECT 'example_sentence' AS entity_type, es.id AS entity_id,
               'sentence' AS field, NULL::text AS locale, v.frequency_rank,
               es.sentence, es.translation
          FROM example_sentences es
          JOIN vocabulary v ON v.id = es.vocabulary_id
         WHERE es.language_id = $1::uuid
           {v_retired}
    """,
    "card_shape": """
        SELECT 'vocabulary' AS entity_type, v.id AS entity_id,
               'card' AS field, NULL::text AS locale, v.frequency_rank,
               v.word, v.part_of_speech AS pos, t.definition
          FROM vocabulary v
          LEFT JOIN translations t ON t.vocabulary_id = v.id AND t.locale = 'en'
         WHERE v.language_id = $1::uuid
           {v_retired}
    """,
}


def _item(question_name: str, row, code: str) -> dict:
    """The row as the judge item its question was calibrated on
    (`content_judge.Question.item_fields`, `data/eval/README.md`)."""
    if question_name == "register":
        return {"field": row["item_field"], "text": row["text"] or "",
                "translation": row["translation"] or "", "headword": row["headword"] or ""}
    if question_name == "sense":
        item = {"word": row["word"] or "", "pos": row["pos"] or "",
                "definition": row["definition"] or ""}
        if row["frequency_rank"] is not None:
            item["rank"] = int(row["frequency_rank"])
        return item
    if question_name == "gloss":
        return {"word": row["word"] or "", "pos": row["pos"] or "",
                "definition": row["definition"] or "", "gloss": row["gloss"] or "",
                "locale": row["locale"] or ""}
    if question_name == "scripture":
        return {"sentence": row["sentence"] or "", "translation": row["translation"] or "",
                "language": code}
    if question_name == "card_shape":
        return {"word": row["word"] or "", "pos": row["pos"] or "",
                "definition": row["definition"] or "", "language": code}
    raise ValueError(f"no row source for question {question_name!r}")


async def _retired_clause(conn: asyncpg.Connection, table: str, alias: str) -> str:
    """`AND <alias>.retired_at IS NULL`, or nothing on a database that has
    not had the column's migration — `cards._retired_clause`'s probe, for a
    different reason: there a thrown error aborts the request's transaction;
    here the scope runs under a savepoint and would merely fail, which for a
    scope means the judge reads NOTHING for the course and coverage says 0
    of 0, when the alternative is a few retired rows in scope."""
    if await column_present(conn, table, "retired_at"):
        return f"AND {alias}.retired_at IS NULL"
    return ""


async def _scope(conn: asyncpg.Connection, question) -> str:
    """The question's scope SQL, retired rows out where the column exists.

    A retired word (`vocabulary.retired_at`, migration 20261016, applied 7
    Sep 2026) is off every card and out of every count, so judging its
    definition, its card or its sentences is spend on nothing a learner
    sees. `grammar_points.retired_at` (20261017) is still owed, so the drill
    branch probes separately and includes retired points' drills until it
    lands. Probed per call, not cached: the loop is nightly and a catalog
    read is nothing next to the model call it precedes."""
    try:
        template = _SCOPE[question.name]
    except KeyError:
        raise ValueError(f"no row source for question {question.name!r}") from None
    clauses = {"v_retired": await _retired_clause(conn, "vocabulary", "v")}
    if "{gp_retired}" in template:
        clauses["gp_retired"] = await _retired_clause(conn, "grammar_points", "gp")
    return template.format(**clauses)


async def candidates(conn: asyncpg.Connection, question, language_id, code: str,
                     limit: int) -> list[dict]:
    """The next *limit* rows this question should read for the course, in
    the plan's priority order. Each item is `{id, entity: {type, id, field,
    locale}, **item_fields}`; the step strips `entity` before the model sees
    it and `record_verdicts` reads it back. Empty when the table is absent."""
    if limit <= 0:
        return []
    try:
        async with savepoint(conn):
            sql = f"""
                WITH scope AS ({await _scope(conn, question)})
                SELECT s.*
                  FROM scope s
                  LEFT JOIN LATERAL (
                       -- NULL here is NOT EXISTS a content_verdicts row for
                       -- (entity_type, entity_id, field, question, locale); the
                       -- max is what orders the rows that do have one.
                       SELECT max(cv.judged_at) AS at
                         FROM content_verdicts cv
                        WHERE cv.entity_type = s.entity_type
                          AND cv.entity_id   = s.entity_id
                          AND cv.field       = s.field
                          AND cv.question    = $2
                          AND cv.locale IS NOT DISTINCT FROM s.locale
                  ) judged ON true
                 ORDER BY (judged.at IS NULL) DESC,     -- never judged first
                          s.frequency_rank NULLS LAST,  -- top band first
                          judged.at,                    -- then the oldest verdict
                          s.entity_id
                 LIMIT $3
            """
            rows = await conn.fetch(sql, str(language_id), question.name, int(limit))
    except _MISSING:
        return []
    items = []
    for row in rows:
        entity = {"type": row["entity_type"], "id": str(row["entity_id"]),
                  "field": row["field"], "locale": row["locale"]}
        items.append({"id": f"{entity['type']}:{entity['id']}", ENTITY_KEY: entity,
                      **_item(question.name, row, code)})
    return items


async def scope_size(conn: asyncpg.Connection, question, language_id) -> int:
    """How many rows the question applies to for the course: the coverage
    denominator. Reads content tables only, so it does not depend on the
    migration; 0 when a content table is somehow absent."""
    try:
        async with savepoint(conn):
            total = await conn.fetchval(
                f"SELECT count(*) FROM ({await _scope(conn, question)}) s", str(language_id),
            )
    except _MISSING:
        return 0
    return int(total or 0)


async def judged_count(conn: asyncpg.Connection, question, language_id) -> int:
    """Distinct rows IN SCOPE with a verdict for the question: the coverage
    numerator. A translation is one row per locale, so the locale is part of
    the identity, folded the way the unique index folds it.

    It joins `_scope` rather than counting `content_verdicts` alone, because
    the denominator (`scope_size`) counts that scope and a numerator over a
    different row set is not a percentage. `content_verdicts.entity_id` has
    no foreign key, so a verdict outlives the row it judged: a word retired
    since (the scopes exclude `retired_at IS NOT NULL`) or a sentence
    deleted by a re-seed both leave a verdict counting toward a coverage it
    is no longer part of. Measured on a three-row fixture, one verdict on a
    retired word's sentence: 3 in scope, 4 "judged", 133% covered — and the
    panel renders that number straight.
    """
    try:
        async with savepoint(conn):
            total = await conn.fetchval(
                f"""
                SELECT count(DISTINCT (s.entity_type, s.entity_id, s.field,
                                       COALESCE(s.locale, '')))
                  FROM ({await _scope(conn, question)}) s
                  JOIN content_verdicts cv
                    ON cv.entity_type = s.entity_type
                   AND cv.entity_id = s.entity_id
                   AND cv.field = s.field
                   AND cv.locale IS NOT DISTINCT FROM s.locale
                   AND cv.question = $2
                 WHERE cv.language_id = $1::uuid
                """,
                str(language_id), question.name,
            )
    except _MISSING:
        return 0
    return int(total or 0)


def stored_confidence(value) -> Decimal:
    """A verdict's confidence as the table holds it — and as
    `judge_step.is_flagged` compares it, so the flagged.<question> ledger
    and `WHERE confidence >= 0.7` on the table agree at the threshold.

    Clamped to the CHECK's 0..1, because a model's number is not guaranteed
    to be in it and a verdict outside it must be stored clamped, not lost
    with its batch. A Decimal from the SHORT string, never the float: asyncpg
    binds a float to `numeric` as Decimal(float), the full binary expansion,
    and 0.7 reached a real Postgres as 0.6999999999999999555910790149937…,
    which `>= 0.7` excludes — the checker's drill-down found none of the
    rows the ledger had counted at exactly the threshold. Four places is
    more than any question's rules ask a model to report."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    if number != number:  # NaN
        number = 0.0
    return Decimal(str(round(max(0.0, min(1.0, number)), 4)))


def _evidence(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [str(e) for e in (value or []) if e is not None]


async def record_verdicts(conn: asyncpg.Connection, run_id, language_id, question,
                          items: list[dict], verdicts: list[dict], judge: str) -> int | None:
    """One row per verdict, matched to its item by `id`, tagged with the
    `quality_runs` row that paid for it. Returns how many were inserted, or
    None when the table is absent so the caller can count them as dropped.

    `ON CONFLICT DO NOTHING` with no target: the only unique index is
    `uq_content_verdicts_row_question_run` (entity_type, entity_id, field,
    question, COALESCE(locale, ''), run_id), and naming an expression index
    as the target has to match its parse exactly or every insert fails —
    a mistake this code could not test without the migration applied.
    A verdict the judge did not return (no `id` match) is not written:
    `run_items` already turned it into `unsure`, so a missing one here is a
    caller bug, not a silent clean row."""
    by_id = {v.get("id"): v for v in verdicts if isinstance(v, dict)}
    inserted = 0
    try:
        async with savepoint(conn):
            for item in items:
                verdict = by_id.get(item.get("id"))
                entity = item.get(ENTITY_KEY)
                if verdict is None or not entity:
                    continue
                row_id = await conn.fetchval(
                    """
                    INSERT INTO content_verdicts
                        (run_id, language_id, locale, entity_type, entity_id, field,
                         question, verdict, category, evidence, confidence, expected,
                         note, judge)
                    VALUES ($1::uuid, $2::uuid, $3, $4, $5::uuid, $6, $7, $8, $9,
                            $10::text[], $11::numeric, $12, $13, $14)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    str(run_id) if run_id is not None else None, str(language_id),
                    entity.get("locale"), entity["type"], entity["id"], entity["field"],
                    question.name, str(verdict.get("verdict") or "unsure"),
                    verdict.get(question.category_field),
                    _evidence(verdict.get("evidence")),
                    stored_confidence(verdict.get("confidence")),
                    verdict.get(question.expected_field), verdict.get("note"), judge,
                )
                if row_id is not None:
                    inserted += 1
    except _MISSING:
        return None
    return inserted
