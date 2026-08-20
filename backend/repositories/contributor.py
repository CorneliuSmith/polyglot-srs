"""Contributor repository — roles and specialist grammar authoring.

Reads (roles, grammar listing) run under the user's RLS connection. Writes
(saving an explanation, approving, granting a role) run under a privileged
connection AFTER the router has checked the caller's role in the app layer.
"""

from __future__ import annotations

import json

import asyncpg

from backend.repositories.audit import log_change
from backend.services.references import clean_references
from backend.services.seeder.morphology_charts import strip_nominal_chips


async def get_roles(conn: asyncpg.Connection, user_id: str) -> list[dict]:
    """Return the user's contributor roles (empty if none)."""
    rows = await conn.fetch(
        "SELECT language_id, role FROM contributor_roles WHERE user_id = $1",
        user_id,
    )
    return [
        {
            "language_id": str(r["language_id"]) if r["language_id"] else None,
            "role": r["role"],
        }
        for r in rows
    ]


def is_admin(roles: list[dict]) -> bool:
    return any(r["role"] == "admin" for r in roles)


def can_add_accounts(roles: list[dict]) -> bool:
    """True if the user may CREATE accounts. Admins and ambassadors.

    Takes no language_id, unlike every other predicate here, and that is the
    point rather than an oversight: an account does not belong to a language,
    so "ambassador for Spanish" cannot mean "may create Spanish accounts" —
    there is no such object. A grant at any scope confers the same power, and
    the Roles panel says so where an admin is choosing the scope.

    Creating an account is the ONLY thing this grants. Listing accounts,
    deleting them, granting roles and changing plans all stay admin-only —
    the last of those especially, since an ambassador who could grant roles
    would reach admin in two moves.
    """
    return is_admin(roles) or any(r["role"] == "ambassador" for r in roles)


def can_contribute(roles: list[dict], language_id: str) -> bool:
    """True if the user may edit grammar for *language_id*.

    Admins everywhere; contributors and reviewers for their language (a
    reviewer who can approve content can obviously also draft fixes to it).
    """
    if is_admin(roles):
        return True
    return any(
        r["role"] in ("contributor", "reviewer")
        and (r["language_id"] is None or r["language_id"] == language_id)
        for r in roles
    )


def can_review(roles: list[dict], language_id: str) -> bool:
    """True if the user may APPROVE content for *language_id* — the human
    gate that flips reviewed = true. Admins everywhere; reviewers for their
    language (language_id None = all languages)."""
    if is_admin(roles):
        return True
    return any(
        r["role"] == "reviewer"
        and (r["language_id"] is None or r["language_id"] == language_id)
        for r in roles
    )


def can_trial_review(roles: list[dict], language_id: str) -> bool:
    """True if the user may VIEW and RECOMMEND on the review queue for
    *language_id* — trial reviewers (advisory only), plus everyone who can
    already publish (reviewers, admins). Does NOT grant publish power."""
    if can_review(roles, language_id):
        return True
    return any(
        r["role"] == "trial_reviewer"
        and (r["language_id"] is None or r["language_id"] == language_id)
        for r in roles
    )


async def list_grammar_points(
    conn: asyncpg.Connection, language_id: str
) -> list[dict]:
    """List a language's grammar points with their current explanation state."""
    rows = await conn.fetch(
        """
        SELECT id, title, level, explanation, culture_note,
               explanation_source, reviewed, reference_links,
               ai_check_status, ai_check_notes, reviewed_by, reviewed_at
        FROM grammar_points
        WHERE language_id = $1
        ORDER BY display_order ASC, title ASC
        """,
        language_id,
    )

    def _refs(raw):
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = []
        return clean_references(raw)

    return [
        {
            "id": str(r["id"]),
            "title": r["title"],
            "level": r["level"],
            "explanation": r["explanation"],
            "culture_note": r["culture_note"],
            "explanation_source": r["explanation_source"],
            "reviewed": r["reviewed"],
            "references": _refs(r["reference_links"]),
            "ai_check_status": r["ai_check_status"],
            "ai_check_notes": r["ai_check_notes"],
            "reviewed_by": str(r["reviewed_by"]) if r["reviewed_by"] else None,
            "reviewed_at": r["reviewed_at"].isoformat() if r["reviewed_at"] else None,
        }
        for r in rows
    ]


async def list_vocab_items(
    conn: asyncpg.Connection, language_id: str, support_locale: str | None = None
) -> list[dict]:
    """List a language's vocabulary for review: word, gloss, and how much
    supporting content each entry carries (definition + example count), so a
    reviewer can spot thin or missing entries at a glance. Mirrors
    list_grammar_points; the change-request board is where fixes are proposed
    and voted on (no direct vocab authoring surface yet).

    `flagged_count` / `suggestion_count` are the per-word locator for the two
    inbox tiles that were previously un-navigable: the counts were computed
    language-wide, but the only surface that ACTS on them is buried inside a
    single word's ExamplesEditor. Without a marker on the list, finding the
    four flagged sentences among two thousand words meant opening words at
    random. Both degrade to 0 when their column hasn't been migrated yet.
    """
    present = await _present(
        conn,
        columns=(
            "example_sentences.flagged",
            "example_sentences.suggested_translation",
        ),
    )
    flagged_sql = (
        """(SELECT count(*) FROM example_sentences es
             WHERE es.vocabulary_id = v.id AND es.flagged = true)"""
        if "example_sentences.flagged" in present
        else "0::bigint"
    )
    suggestion_sql = (
        """(SELECT count(*) FROM example_sentences es
             WHERE es.vocabulary_id = v.id
               AND es.suggested_translation IS NOT NULL)"""
        if "example_sentences.suggested_translation" in present
        else "0::bigint"
    )
    rows = await conn.fetch(
        f"""
        SELECT v.id, v.word, v.reading, v.part_of_speech, v.level,
               v.frequency_rank,
               v.ai_check_status, v.ai_check_notes,
               COALESCE(t.definition, t_en.definition) AS definition,
               (SELECT count(*) FROM example_sentences es
                 WHERE es.vocabulary_id = v.id) AS example_count,
               {flagged_sql} AS flagged_count,
               {suggestion_sql} AS suggestion_count
        FROM vocabulary v
        LEFT JOIN translations t
               ON v.id = t.vocabulary_id AND t.locale = $2
        LEFT JOIN translations t_en
               ON v.id = t_en.vocabulary_id AND t_en.locale = 'en'
        WHERE v.language_id = $1
        ORDER BY v.frequency_rank ASC NULLS LAST, v.word ASC
        """,
        language_id, support_locale or "en",
    )
    return [
        {
            "id": str(r["id"]),
            "word": r["word"],
            "reading": r["reading"],
            "part_of_speech": r["part_of_speech"],
            "level": r["level"],
            "frequency_rank": r["frequency_rank"],
            "definition": r["definition"],
            "example_count": r["example_count"],
            # Locators for the "Flagged examples" / "Translation fixes" tiles.
            "flagged_count": int(r["flagged_count"]),
            "suggestion_count": int(r["suggestion_count"]),
            "ai_check_status": r["ai_check_status"],
            "ai_check_notes": r["ai_check_notes"],
        }
        for r in rows
    ]


async def get_vocab_for_check(
    conn: asyncpg.Connection, vocabulary_id: str
) -> dict | None:
    """Load a vocab word + its definition and example sentences for the AI
    semantic review (privileged). Mirrors get_point_for_check."""
    v = await conn.fetchrow(
        """
        SELECT v.word, l.code AS language_code,
               COALESCE(t.definition, t_en.definition) AS definition
        FROM vocabulary v
        JOIN languages l ON v.language_id = l.id
        LEFT JOIN translations t ON v.id = t.vocabulary_id AND t.locale = l.code
        LEFT JOIN translations t_en ON v.id = t_en.vocabulary_id AND t_en.locale = 'en'
        WHERE v.id = $1
        """,
        vocabulary_id,
    )
    if v is None:
        return None
    examples = await conn.fetch(
        """
        SELECT sentence, translation
        FROM example_sentences WHERE vocabulary_id = $1
        ORDER BY difficulty_rank ASC NULLS LAST
        LIMIT 20
        """,
        vocabulary_id,
    )
    return {
        "word": v["word"],
        "definition": v["definition"],
        "language_code": v["language_code"],
        "examples": [dict(e) for e in examples],
    }


async def save_vocab_ai_check(
    conn: asyncpg.Connection, vocabulary_id: str, status: str, notes: str
) -> None:
    """Persist the AI semantic-check verdict on a vocab word (privileged)."""
    await conn.execute(
        """
        UPDATE vocabulary
        SET ai_check_status = $2, ai_check_notes = NULLIF($3, ''), ai_checked_at = now()
        WHERE id = $1
        """,
        vocabulary_id, status, notes,
    )


async def get_point_for_check(
    conn: asyncpg.Connection, point_id: str
) -> dict | None:
    """Load a grammar point + its drills for the AI semantic review."""
    gp = await conn.fetchrow(
        """
        SELECT gp.title, gp.explanation, l.code AS language_code
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        WHERE gp.id = $1
        """,
        point_id,
    )
    if gp is None:
        return None
    drills = await conn.fetch(
        """
        SELECT sentence, answer, translation
        FROM drill_sentences WHERE grammar_point_id = $1
        ORDER BY display_order ASC
        """,
        point_id,
    )
    return {
        "title": gp["title"],
        "explanation": gp["explanation"],
        "language_code": gp["language_code"],
        "drills": [dict(d) for d in drills],
    }


async def save_ai_check(
    conn: asyncpg.Connection, point_id: str, status: str, notes: str
) -> None:
    """Persist the AI semantic-check verdict (privileged)."""
    await conn.execute(
        """
        UPDATE grammar_points
        SET ai_check_status = $2, ai_check_notes = NULLIF($3, ''), ai_checked_at = now()
        WHERE id = $1
        """,
        point_id, status, notes,
    )


async def get_language_policy(conn: asyncpg.Connection, language_id: str) -> str:
    """Return a language's grammar_review_policy ('strict' | 'ai_ok')."""
    policy = await conn.fetchval(
        "SELECT grammar_review_policy FROM languages WHERE id = $1", language_id
    )
    return policy or "strict"


async def get_language_tutor_model(
    conn: asyncpg.Connection, language_id: str
) -> str | None:
    """The language's tutor model override (None = global default)."""
    return await conn.fetchval(
        "SELECT tutor_model FROM languages WHERE id = $1", language_id
    )


async def set_language_tutor_model(
    conn: asyncpg.Connection, language_id: str, model: str | None
) -> None:
    """Set (or clear) a language's tutor model (privileged, admin-only)."""
    await conn.execute(
        "UPDATE languages SET tutor_model = $2 WHERE id = $1",
        language_id, model,
    )


async def set_all_languages_tutor_model(
    conn: asyncpg.Connection, model: str | None
) -> int:
    """Set (or clear) the tutor model on EVERY language at once (admin).

    Owner pain point: the per-language picker meant re-doing the same choice
    for each language — and each newly added language arrived back at the
    default. One fleet-wide apply replaces that ritual. Returns the number
    of languages updated."""
    result = await conn.execute("UPDATE languages SET tutor_model = $1", model)
    return int(result.split()[-1])


async def set_language_policy(
    conn: asyncpg.Connection, language_id: str, policy: str
) -> bool:
    """Set a language's grammar review policy (privileged, admin-only)."""
    result = await conn.execute(
        "UPDATE languages SET grammar_review_policy = $2 WHERE id = $1",
        language_id, policy,
    )
    return result.endswith("1")


async def get_point_language(conn: asyncpg.Connection, point_id: str) -> str | None:
    """Return the language_id of a grammar point, or None if it doesn't exist."""
    lid = await conn.fetchval(
        "SELECT language_id FROM grammar_points WHERE id = $1", point_id
    )
    return str(lid) if lid else None


async def get_vocab_language(conn: asyncpg.Connection, vocabulary_id: str) -> str | None:
    """Return the language_id of a vocabulary word, or None if it doesn't exist."""
    lid = await conn.fetchval(
        "SELECT language_id FROM vocabulary WHERE id = $1", vocabulary_id
    )
    return str(lid) if lid else None


async def get_point_language_and_code(
    conn: asyncpg.Connection, point_id: str
) -> tuple[str, str] | None:
    """Return (language_id, language_code) for a grammar point, or None."""
    row = await conn.fetchrow(
        """
        SELECT gp.language_id, l.code
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        WHERE gp.id = $1
        """,
        point_id,
    )
    if row is None:
        return None
    return str(row["language_id"]), row["code"]


async def create_grammar_point(
    conn: asyncpg.Connection,
    language_id: str,
    title: str,
    level: str | None,
    explanation: str | None,
    culture_note: str | None,
    references: list | None,
    submitted_by: str,
) -> str | None:
    """Create a contributor grammar point (privileged). None if the title exists."""
    next_order = await conn.fetchval(
        "SELECT COALESCE(MAX(display_order), 0) + 1 FROM grammar_points WHERE language_id = $1",
        language_id,
    )
    pid = await conn.fetchval(
        """
        INSERT INTO grammar_points
            (language_id, title, explanation, culture_note, level,
             display_order, explanation_source, reviewed,
             reference_links, explanation_submitted_by)
        VALUES ($1, $2, $3, $4, $5, $6, 'contributor', false, $7::jsonb, $8)
        ON CONFLICT (language_id, title) DO NOTHING
        RETURNING id
        """,
        language_id, title, explanation, culture_note, level, next_order,
        json.dumps(clean_references(references), ensure_ascii=False), submitted_by,
    )
    return str(pid) if pid else None


async def list_drills(conn: asyncpg.Connection, point_id: str) -> list[dict]:
    """List a grammar point's drill sentences for editing, with provenance."""
    rows = await conn.fetch(
        """
        SELECT id, sentence, answer, translation, hint, display_order,
               source, is_modified, flagged, flag_reason
        FROM drill_sentences
        WHERE grammar_point_id = $1
        ORDER BY display_order ASC
        """,
        point_id,
    )
    return [
        {
            "id": str(r["id"]),
            "sentence": r["sentence"],
            "answer": r["answer"],
            "translation": r["translation"],
            "hint": r["hint"],
            "display_order": r["display_order"],
            "source": r["source"],
            "is_modified": r["is_modified"],
            "flagged": r["flagged"],
            "flag_reason": r["flag_reason"],
        }
        for r in rows
    ]


async def add_drill(
    conn: asyncpg.Connection,
    point_id: str,
    sentence: str,
    answer: str,
    translation: str | None,
    hint: str | None,
    source: str = "human",
    origin_detail: str | None = None,
    decertify: bool = True,
    cell: str | None = None,
    created_by: str | None = None,
    lemma: str | None = None,
) -> str:
    """Insert a drill sentence (privileged). *source* tags provenance (WP38):
    'human' for a drill added by hand (the default — never mistaken for
    seed/import), 'ai' for a generated one, with the model in *origin_detail*.
    *cell* is the paradigm cell the drill exercises (for balanced generation and
    the adaptive gym); None for non-paradigm drills. *lemma* is the dictionary
    form of the word the blank exercises — it anchors the Gym's chart lookup
    and standardized baseline; None for legacy/hand-added rows.

    A hand edit de-certifies the point (reviewed → false) so a second reviewer
    re-approves. Gym on-demand generation passes decertify=False: the generated
    drills are tagged 'ai' for later review, but the point stays visible so
    generating extra variations never hides the form the learner is drilling."""
    next_order = await conn.fetchval(
        "SELECT COALESCE(MAX(display_order), 0) + 1 FROM drill_sentences WHERE grammar_point_id = $1",
        point_id,
    )
    # Generated ('ai') drills wait for review before learners see them; seed/
    # human/imported drills are trusted and go in visible.
    reviewed = source != "ai"
    drill_id = await conn.fetchval(
        """
        INSERT INTO drill_sentences
            (grammar_point_id, sentence, answer, translation, hint, display_order,
             source, origin_detail, cell, reviewed, created_by, lemma)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING id
        """,
        point_id, sentence, answer, translation or None, hint or None, next_order,
        source, origin_detail, cell, reviewed, created_by, lemma or None,
    )
    if decertify:
        await conn.execute(
            "UPDATE grammar_points SET reviewed = false WHERE id = $1", point_id
        )
    if source == "human":
        # A hand-added drill makes this a human-owned point: a later doc
        # re-seed must route through the suggestion queue, not overwrite it.
        await conn.execute(
            "UPDATE grammar_points SET curated = true WHERE id = $1", point_id
        )
    return str(drill_id)


async def get_vocab_generation_context(
    conn: asyncpg.Connection, vocabulary_id: str
) -> dict | None:
    """A word's context for the example-sentence generator: its surface + lemma,
    part of speech, English definition, language, and a few existing example
    sentences as style. None if the word doesn't exist."""
    row = await conn.fetchrow(
        """
        SELECT v.word, v.part_of_speech, v.morphology, v.language_id,
               l.code AS language_code, l.name AS language_name,
               (SELECT t.definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                 AS definition
        FROM vocabulary v
        JOIN languages l ON v.language_id = l.id
        WHERE v.id = $1
        """,
        vocabulary_id,
    )
    if row is None:
        return None
    examples = await conn.fetch(
        "SELECT sentence FROM example_sentences WHERE vocabulary_id = $1 "
        "ORDER BY difficulty_rank NULLS LAST LIMIT 6",
        vocabulary_id,
    )
    morph = row["morphology"]
    if isinstance(morph, str):
        try:
            morph = json.loads(morph)
        except (json.JSONDecodeError, TypeError):
            morph = {}
    lemma = (morph or {}).get("lemma") or row["word"]
    return {
        "vocabulary_id": str(vocabulary_id),
        "word": row["word"],
        "lemma": lemma,
        "part_of_speech": row["part_of_speech"],
        "definition": row["definition"],
        "language_id": str(row["language_id"]),
        "language_code": row["language_code"],
        "language_name": row["language_name"],
        "examples": [e["sentence"] for e in examples],
    }


async def add_example_sentence(
    conn: asyncpg.Connection,
    vocabulary_id: str,
    language_id: str,
    sentence: str,
    translation: str | None,
    source: str = "human",
    origin_detail: str | None = None,
    translation_locale: str = "en",
    reviewed: bool | None = None,
) -> str | None:
    """Insert a vocabulary example sentence (privileged), tagged with provenance
    (WP38): 'ai' for a generated one with the model in *origin_detail*. Returns
    the new row id, or None if an identical sentence already exists for the word
    in the same locale (the UNIQUE(vocabulary_id, sentence, translation_locale)
    guard — generation never duplicates).

    *translation_locale* is the language the *translation* is written in ('en'
    by default). A support-locale translation of an English sentence reuses the
    same sentence text with a different locale — a distinct row.

    Generated ('ai') examples land reviewed=false — hidden from learners until a
    human approves them (the WP42 review gate); seed/imported/human examples are
    trusted content and go in reviewed=true.

    *reviewed* overrides that default, and exists for exactly one case: a
    locale rendering of an English sentence a human ALREADY approved. The
    sentence is unchanged and the meaning was signed off; only the wording of
    the meaning line is new, and it came through the same maker-checker that
    word glosses use — and those apply straight away. Left as None, the
    ordinary gate applies, so AI-INVENTED sentences still wait for a human."""
    # Generated content waits for human review; everything else is trusted.
    if reviewed is None:
        reviewed = source != "ai"
    row_id = await conn.fetchval(
        """
        INSERT INTO example_sentences
            (language_id, vocabulary_id, sentence, translation, translation_locale,
             source, origin_detail, reviewed)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (vocabulary_id, sentence, translation_locale) DO NOTHING
        RETURNING id
        """,
        language_id, vocabulary_id, sentence, translation or None,
        translation_locale, source, origin_detail, reviewed,
    )
    return str(row_id) if row_id is not None else None


# ---------------------------------------------------------------------------
# Content-generation coverage + gap lists (WP42, admin generation panel).
#
# "Coverage" is how much of a language's curriculum has example/drill
# sentences at all; the gap lists drive an IDEMPOTENT fill — only items still
# under target are ever handed to the (paid) generator, so a re-run after a
# completed pass finds nothing and spends nothing.
# ---------------------------------------------------------------------------


async def _present(
    conn: asyncpg.Connection,
    tables: tuple[str, ...] = (),
    columns: tuple[str, ...] = (),
) -> set[str]:
    """Which of *tables* / *columns* actually exist, in ONE query.

    Migrations are applied by the owner, so a deploy routinely runs ahead of
    the schema. Every review-inbox read is on a hot admin path, and a raised
    UndefinedTable/UndefinedColumnError aborts the whole pooled transaction
    (privileged_connection wraps one) — taking the page down rather than one
    tile. So we PROBE first and drop the missing pieces from the SQL, the
    same shape `list_accounts` uses for `custom_prices`.

    *columns* are given as "table.column". Returned names are the inputs that
    were found, so callers can test membership directly.
    """
    rows = await conn.fetch(
        """
        SELECT name FROM (
            SELECT t AS name FROM unnest($1::text[]) AS t
             WHERE to_regclass(t) IS NOT NULL
            UNION ALL
            SELECT c.table_name || '.' || c.column_name AS name
              FROM information_schema.columns c
             WHERE c.table_schema = 'public'
               AND (c.table_name || '.' || c.column_name) = ANY($2::text[])
        ) s
        """,
        list(tables), list(columns),
    )
    return {r["name"] for r in rows}


# Every queue the Review Inbox rolls up, as (key, SQL predicate over a
# language id placeholder `%(lang)s`), plus what schema each one needs. One
# definition, used for BOTH the current-language counts and the
# cross-language roll-up, so the two can never drift apart (a breakdown that
# counted different things than the tiles would be worse than none).
_INBOX_QUEUES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("grammar_pending", """
        SELECT count(*) FROM grammar_points gp
         WHERE gp.language_id = {lang} AND gp.reviewed = false
           AND COALESCE(gp.explanation, '') <> ''
     """, ()),
    ("pending_drills", """
        SELECT count(*) FROM drill_sentences ds
          JOIN grammar_points gp ON ds.grammar_point_id = gp.id
         WHERE gp.language_id = {lang} AND ds.source = 'ai'
           AND ds.reviewed = false
     """, ()),
    ("flagged_drills", """
        SELECT count(*) FROM drill_sentences ds
          JOIN grammar_points gp ON ds.grammar_point_id = gp.id
         WHERE gp.language_id = {lang} AND ds.flagged = true
     """, ("drill_sentences.flagged",)),
    ("pending_examples", """
        SELECT count(*) FROM example_sentences es
          JOIN vocabulary v ON es.vocabulary_id = v.id
         WHERE v.language_id = {lang} AND es.source = 'ai'
           AND es.reviewed = false
     """, ()),
    ("flagged_examples", """
        SELECT count(*) FROM example_sentences es
          JOIN vocabulary v ON es.vocabulary_id = v.id
         WHERE v.language_id = {lang} AND es.flagged = true
     """, ("example_sentences.flagged",)),
    ("translation_suggestions", """
        SELECT count(*) FROM example_sentences es
          JOIN vocabulary v ON es.vocabulary_id = v.id
         WHERE v.language_id = {lang}
           AND es.suggested_translation IS NOT NULL
     """, ("example_sentences.suggested_translation",)),
    ("ai_levels", """
        SELECT count(*) FROM vocabulary v
         WHERE v.language_id = {lang} AND v.level_source = 'ai'
     """, ("vocabulary.level_source",)),
    ("change_requests", """
        SELECT count(*) FROM card_change_requests ccr
         WHERE ccr.language_id = {lang} AND ccr.status = 'open'
     """, ("card_change_requests",)),
    ("suggestions", """
        SELECT count(*) FROM content_suggestions cs
         WHERE cs.language_id = {lang} AND cs.status = 'pending'
     """, ("content_suggestions",)),
    ("notes", """
        SELECT count(*) FROM point_review_notes n
          LEFT JOIN grammar_points gp ON n.grammar_point_id = gp.id
          LEFT JOIN vocabulary v ON n.vocabulary_id = v.id
         WHERE COALESCE(gp.language_id, v.language_id) = {lang}
           AND n.status = 'open'
     """, ("point_review_notes",)),
    ("feedback", """
        SELECT count(*) FROM card_feedback f
         WHERE f.language_id = {lang} AND f.status = 'open'
     """, ("card_feedback",)),
    ("overlaps", """
        SELECT count(*) FROM grammar_point_overlaps o
         WHERE o.language_id = {lang} AND o.status = 'open'
     """, ("grammar_point_overlaps",)),
    ("ai_translations", """
        SELECT count(*) FROM translation_reviews r
          JOIN vocabulary v ON r.vocabulary_id = v.id
         WHERE v.language_id = {lang} AND r.status = 'pending'
     """, ("translation_reviews",)),
    # A tester's advisory ✓/✗ counts as a queue in its own right: it is the
    # only output most trial reviewers produce, and until now it appeared
    # nowhere the admin looks. Scoped to targets that are STILL PENDING —
    # once a reviewer publishes or rejects the item the advice is spent.
    ("tester_recommendations", """
        SELECT count(*) FROM review_recommendations rr
         WHERE rr.language_id = {lang}
           AND ((rr.target_type = 'drill' AND EXISTS (
                   SELECT 1 FROM drill_sentences ds
                    WHERE ds.id = rr.target_id AND ds.reviewed = false))
             OR (rr.target_type = 'example' AND EXISTS (
                   SELECT 1 FROM example_sentences es
                    WHERE es.id = rr.target_id AND es.reviewed = false)))
     """, ("review_recommendations",)),
    # General app feedback — the home-page "tell us what you think" button.
    # It was the one stream with no place on the per-language map: reports
    # arrived, were counted nowhere a reviewer looks, and were triaged on a
    # page the workspace never links to. Rows that name no language belong
    # to no course and are deliberately NOT here — they surface in the
    # notifications endpoint's own bucket instead of being mis-filed.
    ("app_feedback", """
        SELECT count(*) FROM app_feedback af
         WHERE af.language_id = {lang} AND af.status = 'open'
     """, ("app_feedback",)),
)

# Queues only an admin can open a panel for. Their counts must be REMOVED
# from anything a non-admin is shown, not merely hidden client-side: a
# reviewer told "9 waiting" when 3 of those are admin-only is being handed
# a number they can never bring to zero, and the badge stops being
# trustworthy the first time they notice.
ADMIN_ONLY_QUEUES = ("ai_translations", "app_feedback")

# Everything the queue set can need, so one probe covers the whole roll-up.
_INBOX_TABLES = tuple(sorted({
    n for _, _, needs in _INBOX_QUEUES for n in needs if "." not in n
}))
_INBOX_COLUMNS = tuple(sorted({
    n for _, _, needs in _INBOX_QUEUES for n in needs if "." in n
}))

# Queues that add up to "this language needs attention" in the cross-language
# strip. Deliberately every queue: an admin whose selector sits on Arabic must
# see that Hebrew has traffic, whatever KIND of traffic it is.
INBOX_QUEUE_KEYS = tuple(k for k, _, _ in _INBOX_QUEUES)


def strip_admin_queues(languages: list[dict]) -> list[dict]:
    """The same per-language rows, minus the queues only an admin can open.

    For everything a non-admin is shown in aggregate — the inbox's
    other-languages strip, the bell's per-language rows. Counts are zeroed,
    totals recomputed, and a row whose total falls to zero drops out
    entirely: a language holding only admin-only work has nothing for this
    viewer, and listing it would send them somewhere with an empty page.
    """
    out = []
    for lang in languages:
        counts = {
            k: (0 if k in ADMIN_ONLY_QUEUES else v)
            for k, v in lang["counts"].items()
        }
        total = sum(counts.values())
        if total == 0:
            continue
        out.append({**lang, "counts": counts, "total": total})
    return out


def _inbox_selects(present: set[str], lang_sql: str) -> str:
    """The queue subqueries, with any whose table/column is missing replaced
    by a literal 0 (so a pre-migration deploy reads 'nothing here' instead of
    500ing the Review workspace)."""
    parts = []
    for key, sql, needs in _INBOX_QUEUES:
        if all(n in present for n in needs):
            parts.append(f"({sql.format(lang=lang_sql)}) AS {key}")
        else:
            parts.append(f"0::bigint AS {key}")
    return ",\n          ".join(parts)


async def review_inbox_counts(
    conn: asyncpg.Connection, language_id: str
) -> dict:
    """One roll-up of everything awaiting review action for a language — the
    unified Review Inbox. Each key is a queue the existing panels already act
    on; this just answers 'what needs attention, and how much' in one query."""
    present = await _present(conn, _INBOX_TABLES, _INBOX_COLUMNS)
    row = await conn.fetchrow(
        f"""
        SELECT
          {_inbox_selects(present, "$1")}
        """,
        language_id,
    )
    return {k: int(row[k]) for k in row.keys()}


async def review_inbox_by_language(
    conn: asyncpg.Connection, *, exclude: str | None = None,
    include_empty: bool = False,
) -> list[dict]:
    """Every queue, counted for every language, in ONE query.

    This is the shape the cross-language surfaces want: a reviewer picking
    which language to work on next needs the counts for ALL of them at once,
    not one endpoint call per language. Sorted noisiest first, so "where is
    the work" is answered by reading the top of the list.

    *include_empty* keeps the quiet languages in, which the language picker
    wants (it lists everything, badge or no badge) and the alert strip does
    not (it exists only to say "there is traffic over there").
    """
    present = await _present(conn, _INBOX_TABLES, _INBOX_COLUMNS)
    rows = await conn.fetch(
        f"""
        SELECT l.id, l.code, l.name, l.is_visible,
          {_inbox_selects(present, "l.id")}
        FROM languages l
        WHERE ($1::uuid IS NULL OR l.id <> $1::uuid)
        """,
        exclude,
    )
    out = []
    for r in rows:
        counts = {k: int(r[k]) for k in INBOX_QUEUE_KEYS}
        total = sum(counts.values())
        if total == 0 and not include_empty:
            continue
        out.append({
            "id": str(r["id"]),
            "code": r["code"],
            "name": r["name"],
            "is_visible": r["is_visible"],
            "total": total,
            "counts": counts,
        })
    out.sort(key=lambda d: (-d["total"], d["name"]))
    return out


async def review_inbox_other_languages(
    conn: asyncpg.Connection, language_id: str
) -> list[dict]:
    """The same queues, counted for every OTHER language.

    The bug this exists for: every review surface is scoped to the admin's
    working language, but a submission carries the language the TESTER was
    studying. Testers exercising Hebrew while the selector sits on Arabic
    made the inbox read "All clear" — the single biggest cause of "they say
    they're sending reviews and I'm not seeing them".

    Only languages with a non-zero total come back, noisiest first, so the
    strip is empty exactly when there is genuinely nothing elsewhere.
    """
    return await review_inbox_by_language(conn, exclude=language_id)


async def language_release_readiness(conn: asyncpg.Connection) -> list[dict]:
    """Per-language "is this safe to release?" roll-up for the visibility panel.

    Owner: "languages will need to be released after review." Visibility is
    the release switch, so the switch has to say what's still unreviewed —
    otherwise an admin flips a half-reviewed language live without knowing.
    One row per language, whether or not it's currently visible.

    `awaiting_review` is the number a reviewer would still have to act on:
    draft grammar points and un-reviewed AI drills/examples. `open_reports`
    is human-raised traffic (notes, change requests, learner feedback) —
    counted separately because it doesn't gate a first release the way
    unreviewed content does.
    """
    rows = await conn.fetch(
        """
        SELECT l.id, l.code, l.name, l.is_visible,
          l.grammar_review_policy, l.tutor_model,
          (SELECT count(*) FROM grammar_points gp
            WHERE gp.language_id = l.id AND gp.reviewed = false
              AND COALESCE(gp.explanation, '') <> '') AS draft_points,
          (SELECT count(*) FROM drill_sentences ds
             JOIN grammar_points gp ON ds.grammar_point_id = gp.id
            WHERE gp.language_id = l.id AND ds.source = 'ai'
              AND ds.reviewed = false) AS pending_drills,
          (SELECT count(*) FROM example_sentences es
             JOIN vocabulary v ON es.vocabulary_id = v.id
            WHERE v.language_id = l.id AND es.source = 'ai'
              AND es.reviewed = false) AS pending_examples,
          (SELECT count(*) FROM point_review_notes n
             LEFT JOIN grammar_points gp ON n.grammar_point_id = gp.id
             LEFT JOIN vocabulary v ON n.vocabulary_id = v.id
            WHERE COALESCE(gp.language_id, v.language_id) = l.id
              AND n.status = 'open') AS open_notes,
          (SELECT count(*) FROM card_change_requests cr
            WHERE cr.language_id = l.id AND cr.status = 'open')
            AS open_change_requests,
          (SELECT count(*) FROM card_feedback f
            WHERE f.language_id = l.id AND f.status = 'open') AS open_feedback
        FROM languages l
        ORDER BY l.name
        """
    )
    out = []
    for r in rows:
        awaiting = (
            int(r["draft_points"])
            + int(r["pending_drills"])
            + int(r["pending_examples"])
        )
        reports = (
            int(r["open_notes"])
            + int(r["open_change_requests"])
            + int(r["open_feedback"])
        )
        out.append({
            "id": str(r["id"]),
            "code": r["code"],
            "name": r["name"],
            "is_visible": r["is_visible"],
            # The other two per-language dials, so the admin can work every
            # language from the one panel instead of switching their own
            # active course fourteen times to reach each one's controls.
            "review_policy": r["grammar_review_policy"],
            "tutor_model": r["tutor_model"],
            "draft_points": int(r["draft_points"]),
            "pending_drills": int(r["pending_drills"]),
            "pending_examples": int(r["pending_examples"]),
            "awaiting_review": awaiting,
            "open_reports": reports,
        })
    return out


async def generation_coverage(conn: asyncpg.Connection) -> list[dict]:
    """Per-language content coverage for the admin generation panel: how many
    words/points exist, how many still have NO example/drill, and how much
    'ai'-sourced content is already in the pool. One row per language."""
    rows = await conn.fetch(
        """
        SELECT l.id, l.code, l.name,
          (SELECT count(*) FROM vocabulary v WHERE v.language_id = l.id)
            AS vocab_total,
          (SELECT count(*) FROM vocabulary v WHERE v.language_id = l.id
             AND NOT EXISTS (SELECT 1 FROM example_sentences es
                              WHERE es.vocabulary_id = v.id))
            AS vocab_no_examples,
          (SELECT count(*) FROM grammar_points gp WHERE gp.language_id = l.id)
            AS grammar_total,
          (SELECT count(*) FROM grammar_points gp WHERE gp.language_id = l.id
             AND NOT EXISTS (SELECT 1 FROM drill_sentences ds
                              WHERE ds.grammar_point_id = gp.id))
            AS grammar_no_drills,
          (SELECT count(*) FROM example_sentences es
             JOIN vocabulary v ON es.vocabulary_id = v.id
            WHERE v.language_id = l.id AND es.source = 'ai')
            AS ai_examples,
          (SELECT count(*) FROM example_sentences es
             JOIN vocabulary v ON es.vocabulary_id = v.id
            WHERE v.language_id = l.id AND es.source = 'ai'
              AND es.reviewed = false)
            AS pending_examples,
          (SELECT count(*) FROM drill_sentences ds
             JOIN grammar_points gp ON ds.grammar_point_id = gp.id
            WHERE gp.language_id = l.id AND ds.source = 'ai')
            AS ai_drills
        FROM languages l
        ORDER BY l.name
        """
    )
    return [
        {
            "language_id": str(r["id"]),
            "language_code": r["code"],
            "language_name": r["name"],
            "vocab_total": r["vocab_total"],
            "vocab_no_examples": r["vocab_no_examples"],
            "grammar_total": r["grammar_total"],
            "grammar_no_drills": r["grammar_no_drills"],
            "ai_examples": r["ai_examples"],
            "pending_examples": r["pending_examples"],
            "ai_drills": r["ai_drills"],
        }
        for r in rows
    ]


async def list_pending_examples(
    conn: asyncpg.Connection, language_id: str, limit: int = 50
) -> list[dict]:
    """Generated example sentences awaiting human review for a language (WP42
    gate): the sentence, its word, translation, and the model that made it."""
    rows = await conn.fetch(
        """
        SELECT es.id, es.sentence, es.translation, es.origin_detail,
               v.word, v.id AS vocabulary_id
        FROM example_sentences es
        JOIN vocabulary v ON es.vocabulary_id = v.id
        WHERE v.language_id = $1 AND es.source = 'ai' AND es.reviewed = false
        ORDER BY es.created_at ASC
        LIMIT $2
        """,
        language_id, limit,
    )
    return [
        {
            "id": str(r["id"]),
            "sentence": r["sentence"],
            "translation": r["translation"],
            "origin_detail": r["origin_detail"],
            "word": r["word"],
            "vocabulary_id": str(r["vocabulary_id"]),
        }
        for r in rows
    ]


async def review_example(
    conn: asyncpg.Connection, example_id: str, approve: bool,
    actor_id: str | None = None,
) -> bool:
    """Approve (reviewed → true, now served to learners) or reject (deleted) a
    pending generated example. Only ever touches an unreviewed 'ai' row, so it
    can't disturb seed/imported/human content. Returns True if a row changed."""
    row = await conn.fetchrow(
        "SELECT language_id, sentence, translation FROM example_sentences WHERE id = $1",
        example_id,
    )
    if approve:
        result = await conn.execute(
            "UPDATE example_sentences SET reviewed = true "
            "WHERE id = $1 AND source = 'ai' AND reviewed = false",
            example_id,
        )
    else:
        result = await conn.execute(
            "DELETE FROM example_sentences "
            "WHERE id = $1 AND source = 'ai' AND reviewed = false",
            example_id,
        )
    changed = result.rsplit(" ", 1)[-1] == "1"
    if changed and row:
        await log_change(
            conn, entity_type="example_sentence", entity_id=example_id,
            actor_id=actor_id, action="approved" if approve else "rejected",
            language_id=str(row["language_id"]),
            # A rejected example is deleted; keep its content so the log stays
            # meaningful (it is not restorable — no 'before' snapshot).
            note=None if approve else f"deleted: {row['sentence']}",
        )
    return changed


async def review_examples_bulk(
    conn: asyncpg.Connection,
    language_id: str,
    approve: bool,
    only_unflagged: bool = True,
) -> int:
    """Approve or reject EVERY pending ('ai', reviewed=false) example for a
    language in one shot — the queue-clearing action. Only ever touches
    unreviewed 'ai' rows, so seed/human content is untouched. When approving,
    *only_unflagged* skips any row a recheck has flagged (don't bulk-publish a
    known-bad one). Returns the number of rows changed."""
    flag_clause = " AND es.flagged = false" if (only_unflagged and approve) else ""
    if approve:
        result = await conn.execute(
            f"""
            UPDATE example_sentences es SET reviewed = true
            FROM vocabulary v
            WHERE es.vocabulary_id = v.id AND v.language_id = $1
              AND es.source = 'ai' AND es.reviewed = false{flag_clause}
            """,
            language_id,
        )
    else:
        result = await conn.execute(
            """
            DELETE FROM example_sentences es USING vocabulary v
            WHERE es.vocabulary_id = v.id AND v.language_id = $1
              AND es.source = 'ai' AND es.reviewed = false
            """,
            language_id,
        )
    return int(result.rsplit(" ", 1)[-1])


async def list_vocab_examples(
    conn: asyncpg.Connection, vocabulary_id: str
) -> list[dict]:
    """Every example sentence for a word — for the reviewer's inline editor.
    Pending ('ai', reviewed=false) rows come first so they're easy to act on."""
    rows = await conn.fetch(
        "SELECT id, sentence, translation, source, reviewed, is_modified, "
        "       flagged, flag_reason, suggested_translation, suggestion_reason "
        "FROM example_sentences WHERE vocabulary_id = $1 "
        "ORDER BY flagged DESC, (suggested_translation IS NOT NULL) DESC, "
        "         reviewed, id",
        vocabulary_id,
    )
    return [
        {
            "id": str(r["id"]),
            "sentence": r["sentence"],
            "translation": r["translation"],
            "source": r["source"],
            "reviewed": r["reviewed"],
            "is_modified": r["is_modified"],
            "flagged": r["flagged"],
            "flag_reason": r["flag_reason"],
            "suggested_translation": r["suggested_translation"],
            "suggestion_reason": r["suggestion_reason"],
        }
        for r in rows
    ]


async def edit_example_sentence(
    conn: asyncpg.Connection,
    example_id: str,
    sentence: str,
    translation: str | None,
    editor_id: str,
) -> bool:
    """Reviewer edit of an example sentence: update the text/translation and
    stamp the provenance (is_modified + who + when). Clears any quality flag and
    pending translation suggestion — an edited sentence has been addressed.
    Returns True if a row changed."""
    prev = await conn.fetchrow(
        "SELECT language_id, sentence, translation FROM example_sentences WHERE id = $1",
        example_id,
    )
    result = await conn.execute(
        "UPDATE example_sentences "
        "SET sentence = $2, translation = $3, "
        "    is_modified = true, modified_by = $4, modified_at = now(), "
        "    flagged = false, flag_reason = NULL, "
        "    suggested_translation = NULL, suggestion_reason = NULL "
        "WHERE id = $1",
        example_id, sentence, translation or None, editor_id,
    )
    changed = result.rsplit(" ", 1)[-1] == "1"
    if changed and prev:
        await log_change(
            conn, entity_type="example_sentence", entity_id=example_id,
            actor_id=editor_id, action="edited",
            language_id=str(prev["language_id"]),
            before={"sentence": prev["sentence"], "translation": prev["translation"]},
            after={"sentence": sentence, "translation": translation or None},
        )
    return changed


async def suggest_example_translation(
    conn: asyncpg.Connection, example_id: str, suggestion: str, reason: str
) -> bool:
    """Record the audit's PROPOSED better translation/description (--recheck),
    without touching the live translation. Idempotent — only writes when no
    suggestion is pending, so a re-run doesn't clobber one a human is weighing.
    Returns True if a row changed."""
    text = (suggestion or "").strip()
    if not text:
        return False
    result = await conn.execute(
        "UPDATE example_sentences "
        "SET suggested_translation = $2, suggestion_reason = $3 "
        "WHERE id = $1 AND suggested_translation IS NULL",
        example_id, text, (reason or "translation could be clearer")[:500],
    )
    return result.rsplit(" ", 1)[-1] == "1"


async def accept_example_translation(
    conn: asyncpg.Connection, example_id: str, editor_id: str
) -> bool:
    """Reviewer accepts a suggested translation: apply it to the live
    translation (stamped as a modification) and clear the suggestion. Returns
    True if a suggestion was applied."""
    result = await conn.execute(
        "UPDATE example_sentences "
        "SET translation = suggested_translation, "
        "    is_modified = true, modified_by = $2, modified_at = now(), "
        "    suggested_translation = NULL, suggestion_reason = NULL "
        "WHERE id = $1 AND suggested_translation IS NOT NULL",
        example_id, editor_id,
    )
    return result.rsplit(" ", 1)[-1] == "1"


async def dismiss_example_translation(
    conn: asyncpg.Connection, example_id: str
) -> bool:
    """Reviewer dismisses a suggested translation, keeping the current one.
    Returns True if a suggestion was cleared."""
    result = await conn.execute(
        "UPDATE example_sentences "
        "SET suggested_translation = NULL, suggestion_reason = NULL "
        "WHERE id = $1 AND suggested_translation IS NOT NULL",
        example_id,
    )
    return result.rsplit(" ", 1)[-1] == "1"


async def flag_example_sentence(
    conn: asyncpg.Connection, example_id: str, reason: str,
    actor_id: str | None = None,
) -> bool:
    """Mark an example sentence as failing the quality audit (--recheck), with a
    short reason for the reviewer. Idempotent — only flips an unflagged row so a
    re-run doesn't overwrite a reason a human is already acting on. Returns True
    if a row changed. *actor_id* is None for the automated CLI recheck."""
    clean = (reason or "flagged by quality audit")[:500]
    result = await conn.execute(
        "UPDATE example_sentences SET flagged = true, flag_reason = $2 "
        "WHERE id = $1 AND flagged = false",
        example_id, clean,
    )
    changed = result.rsplit(" ", 1)[-1] == "1"
    if changed:
        lang = await conn.fetchval(
            "SELECT language_id FROM example_sentences WHERE id = $1", example_id
        )
        await log_change(
            conn, entity_type="example_sentence", entity_id=example_id,
            actor_id=actor_id, action="flagged",
            language_id=str(lang) if lang else None, note=clean,
        )
    return changed


async def flag_drill(
    conn: asyncpg.Connection, drill_id: str, reason: str,
    actor_id: str | None = None,
) -> bool:
    """Mark a drill as failing the quality audit (--recheck), with a short reason
    for the reviewer — the drill twin of flag_example_sentence. Idempotent: only
    flips an unflagged row. Returns True if a row changed. *actor_id* is None for
    the automated CLI recheck."""
    clean = (reason or "flagged by quality audit")[:500]
    result = await conn.execute(
        "UPDATE drill_sentences SET flagged = true, flag_reason = $2 "
        "WHERE id = $1 AND flagged = false",
        drill_id, clean,
    )
    changed = result.rsplit(" ", 1)[-1] == "1"
    if changed:
        lang = await conn.fetchval(
            "SELECT gp.language_id FROM drill_sentences ds "
            "JOIN grammar_points gp ON ds.grammar_point_id = gp.id WHERE ds.id = $1",
            drill_id,
        )
        await log_change(
            conn, entity_type="drill", entity_id=drill_id,
            actor_id=actor_id, action="flagged",
            language_id=str(lang) if lang else None, note=clean,
        )
    return changed


# ---------------------------------------------------------------------------
# Grammar-point overlap flags (owner, 2026-07-26): pairs of points that teach
# substantially the same thing, detected by the audit judge, resolved by a
# human — merged, kept distinct, or dismissed.
# ---------------------------------------------------------------------------

OVERLAP_RESOLUTIONS = ("merged", "distinct", "dismissed")


async def points_for_overlap_audit(
    conn: asyncpg.Connection, language_id: str
) -> list[dict]:
    """A language's whole grammar syllabus, in path order, for the overlap
    judge: id + the identity fields the judge compares (title, function note,
    level). Explanations stay out — titles + can-do lines are what learners
    see side by side, and they keep the judge call bounded."""
    rows = await conn.fetch(
        """
        SELECT id, title, function_note, level
        FROM grammar_points
        WHERE language_id = $1
        ORDER BY level NULLS LAST, display_order, title
        """,
        language_id,
    )
    return [
        {
            "id": str(r["id"]),
            "title": r["title"],
            "function_note": r["function_note"],
            "level": r["level"],
        }
        for r in rows
    ]


async def record_overlap(
    conn: asyncpg.Connection,
    language_id: str,
    point_a_id: str,
    point_b_id: str,
    verdict: str,
    reason: str | None,
    detected_by: str | None = None,
) -> bool:
    """Record one overlap pair for review. The pair is canonicalized in SQL
    (LEAST/GREATEST on the uuids) and deduped against the open-pair unique
    index, so re-running the audit never stacks duplicate flags. Returns True
    when a new row was created; both points get a change-log entry."""
    clean = (reason or "")[:500] or None
    result = await conn.execute(
        """
        INSERT INTO grammar_point_overlaps
            (language_id, point_a_id, point_b_id, verdict, reason, detected_by)
        VALUES ($1, LEAST($2::uuid, $3::uuid), GREATEST($2::uuid, $3::uuid),
                $4, $5, $6)
        ON CONFLICT (point_a_id, point_b_id) WHERE status = 'open' DO NOTHING
        """,
        language_id, point_a_id, point_b_id, verdict, clean, detected_by,
    )
    created = result.endswith(" 1")
    if created:
        for pid in (point_a_id, point_b_id):
            await log_change(
                conn, entity_type="grammar_point", entity_id=pid,
                actor_id=None, action="overlap_flagged",
                language_id=language_id, note=f"{verdict}: {clean or ''}"[:500],
            )
    return created


async def list_overlaps(
    conn: asyncpg.Connection, language_id: str, status: str = "open"
) -> list[dict]:
    """Overlap pairs for the review panel, both titles resolved."""
    rows = await conn.fetch(
        """
        SELECT o.id, o.verdict, o.reason, o.status, o.created_at,
               o.point_a_id, ga.title AS point_a_title, ga.level AS point_a_level,
               o.point_b_id, gb.title AS point_b_title, gb.level AS point_b_level
        FROM grammar_point_overlaps o
        JOIN grammar_points ga ON o.point_a_id = ga.id
        JOIN grammar_points gb ON o.point_b_id = gb.id
        WHERE o.language_id = $1 AND o.status = $2
        ORDER BY o.created_at DESC, ga.title
        """,
        language_id, status,
    )
    return [
        {
            "id": str(r["id"]),
            "verdict": r["verdict"],
            "reason": r["reason"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat(),
            "point_a": {"id": str(r["point_a_id"]), "title": r["point_a_title"],
                        "level": r["point_a_level"]},
            "point_b": {"id": str(r["point_b_id"]), "title": r["point_b_title"],
                        "level": r["point_b_level"]},
        }
        for r in rows
    ]


async def resolve_overlap(
    conn: asyncpg.Connection,
    overlap_id: str,
    status: str,
    actor_id: str | None,
) -> bool:
    """Reviewer verdict on an overlap pair: merged (they fixed the content),
    distinct (real but fine as two points), or dismissed (judge was wrong).
    Only open pairs resolve; returns True if a row changed."""
    if status not in OVERLAP_RESOLUTIONS:
        raise ValueError(f"status must be one of {OVERLAP_RESOLUTIONS}")
    result = await conn.execute(
        """
        UPDATE grammar_point_overlaps
        SET status = $2, resolved_by = $3, resolved_at = now()
        WHERE id = $1 AND status = 'open'
        """,
        overlap_id, status, actor_id,
    )
    return result.endswith(" 1")


async def backfill_example_translation(
    conn: asyncpg.Connection, example_id: str, translation: str
) -> bool:
    """Fill in a MISSING translation the audit produced. Only ever writes when
    the row's translation is currently absent, so it never clobbers a human's.
    Returns True if a row changed."""
    text = (translation or "").strip()
    if not text:
        return False
    result = await conn.execute(
        "UPDATE example_sentences SET translation = $2 "
        "WHERE id = $1 AND (translation IS NULL OR btrim(translation) = '')",
        example_id, text,
    )
    return result.rsplit(" ", 1)[-1] == "1"


async def vocab_with_examples(
    conn: asyncpg.Connection, language_id: str, limit: int
) -> list[dict]:
    """Words that HAVE at least one example sentence, each with its current
    sentences — the work-list for a quality recheck. Commonest words first so a
    bounded run audits the highest-traffic content. Already-flagged sentences
    are excluded from the judged set (a human is handling them), but still count
    against coverage via list order."""
    rows = await conn.fetch(
        """
        SELECT v.id AS vocabulary_id, v.word, v.part_of_speech, v.level,
               (SELECT t.definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                 AS definition,
               (SELECT count(*) FROM example_sentences es
                 WHERE es.vocabulary_id = v.id AND es.flagged = false)
                 AS good_count
        FROM vocabulary v
        WHERE v.language_id = $1
          AND EXISTS (SELECT 1 FROM example_sentences es
                       WHERE es.vocabulary_id = v.id AND es.flagged = false)
        ORDER BY v.frequency_rank NULLS LAST, v.word
        LIMIT $2
        """,
        language_id, limit,
    )
    out = []
    for r in rows:
        sents = await conn.fetch(
            "SELECT id, sentence, translation FROM example_sentences "
            "WHERE vocabulary_id = $1 AND flagged = false ORDER BY id",
            r["vocabulary_id"],
        )
        out.append({
            "vocabulary_id": str(r["vocabulary_id"]),
            "word": r["word"],
            "part_of_speech": r["part_of_speech"],
            "level": r["level"],
            "definition": r["definition"],
            "examples": [
                {"id": str(s["id"]), "sentence": s["sentence"],
                 "translation": s["translation"]}
                for s in sents
            ],
        })
    return out


async def points_with_drills(
    conn: asyncpg.Connection, language_id: str, limit: int
) -> list[dict]:
    """Grammar points that HAVE at least one unflagged drill, each with its
    current drills — the work-list for a drill quality recheck. Mirrors
    vocab_with_examples. Already-flagged drills are excluded from the judged set
    (a human is handling them)."""
    rows = await conn.fetch(
        """
        SELECT gp.id AS point_id, gp.title, gp.explanation, gp.level
        FROM grammar_points gp
        WHERE gp.language_id = $1
          AND EXISTS (SELECT 1 FROM drill_sentences ds
                       WHERE ds.grammar_point_id = gp.id AND ds.flagged = false)
        ORDER BY gp.display_order, gp.title
        LIMIT $2
        """,
        language_id, limit,
    )
    out = []
    for r in rows:
        drills = await conn.fetch(
            "SELECT id, sentence, answer, translation, hint, cell "
            "FROM drill_sentences "
            "WHERE grammar_point_id = $1 AND flagged = false ORDER BY id",
            r["point_id"],
        )
        out.append({
            "point_id": str(r["point_id"]),
            "title": r["title"],
            "explanation": r["explanation"],
            "level": r["level"],
            "drills": [
                {"id": str(d["id"]), "sentence": d["sentence"],
                 "answer": d["answer"], "translation": d["translation"],
                 "hint": d["hint"], "cell": d["cell"]}
                for d in drills
            ],
        })
    return out


async def delete_example_sentence(
    conn: asyncpg.Connection, example_id: str
) -> bool:
    """Reviewer delete of an example sentence. Returns True if a row was removed."""
    result = await conn.execute(
        "DELETE FROM example_sentences WHERE id = $1", example_id
    )
    return result.rsplit(" ", 1)[-1] == "1"


async def add_recommendation(
    conn: asyncpg.Connection,
    recommender_id: str,
    language_id: str,
    target_type: str,
    target_id: str,
    recommendation: str,
    note: str = "",
) -> None:
    """Record (or update) a trial reviewer's advisory approve/reject on a
    pending item. Never publishes — a full reviewer still makes the call."""
    await conn.execute(
        """
        INSERT INTO review_recommendations
            (recommender_id, language_id, target_type, target_id, recommendation, note)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (recommender_id, target_type, target_id) DO UPDATE SET
            recommendation = EXCLUDED.recommendation,
            note = EXCLUDED.note,
            created_at = now()
        """,
        recommender_id, language_id, target_type, target_id, recommendation, note,
    )


async def recommendations_for_targets(
    conn: asyncpg.Connection, target_type: str, target_ids: list[str]
) -> dict[str, dict]:
    """Advisory-recommendation summary per target id: {approve, reject, notes}.
    Lets a full reviewer see what the trial reviewers think before acting."""
    if not target_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT rr.target_id,
               count(*) FILTER (WHERE rr.recommendation = 'approve') AS approve,
               count(*) FILTER (WHERE rr.recommendation = 'reject')  AS reject,
               array_remove(array_agg(NULLIF(rr.note, '')), NULL)    AS notes
        FROM review_recommendations rr
        WHERE rr.target_type = $1 AND rr.target_id = ANY($2::uuid[])
        GROUP BY rr.target_id
        """,
        target_type, target_ids,
    )
    return {
        str(r["target_id"]): {
            "approve": int(r["approve"]),
            "reject": int(r["reject"]),
            "notes": list(r["notes"] or []),
        }
        for r in rows
    }


async def list_tester_recommendations(
    conn: asyncpg.Connection, language_id: str, limit: int = 200
) -> list[dict]:
    """Advisory ✓/✗ + WRITTEN NOTE on items still awaiting a decision.

    The tally attached to a pending item only exists on the one panel that
    lists that item, and the tester's note was rendered as a hover tooltip —
    so the single thing a trial reviewer produces had no durable surface an
    admin could open. This is that surface, and the queue the inbox's
    `tester_recommendations` tile counts (same still-pending filter).

    Rejections first: a "needs work" on something about to be published is
    the one that has to be read before the bulk-approve button is pressed.
    """
    present = await _present(conn, ("review_recommendations",))
    if "review_recommendations" not in present:
        return []
    rows = await conn.fetch(
        """
        SELECT rr.id, rr.target_type, rr.target_id, rr.recommendation,
               rr.note, rr.created_at, u.email AS recommender_email,
               COALESCE(ds.sentence, es.sentence)       AS target_label,
               COALESCE(ds.translation, es.translation) AS target_translation,
               gp.title AS point_title, v.word AS word
        FROM review_recommendations rr
        LEFT JOIN auth.users u ON u.id = rr.recommender_id
        LEFT JOIN drill_sentences ds
               ON rr.target_type = 'drill' AND ds.id = rr.target_id
              AND ds.reviewed = false
        LEFT JOIN grammar_points gp ON ds.grammar_point_id = gp.id
        LEFT JOIN example_sentences es
               ON rr.target_type = 'example' AND es.id = rr.target_id
              AND es.reviewed = false
        LEFT JOIN vocabulary v ON es.vocabulary_id = v.id
        WHERE rr.language_id = $1
          AND (ds.id IS NOT NULL OR es.id IS NOT NULL)
        ORDER BY (rr.recommendation = 'reject') DESC, rr.created_at DESC
        LIMIT $2
        """,
        language_id, limit,
    )
    return [
        {
            "id": str(r["id"]),
            "target_type": r["target_type"],
            "target_id": str(r["target_id"]),
            "recommendation": r["recommendation"],
            # The note is the point of the whole channel — plain text, always
            # present as a key (empty string when they left none).
            "note": r["note"] or "",
            "recommender_email": r["recommender_email"],
            "target_label": r["target_label"],
            "target_translation": r["target_translation"],
            "context": r["point_title"] or r["word"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def trial_reviewer_activity(
    conn: asyncpg.Connection, language_id: str
) -> list[dict]:
    """Trial reviewers for a language and how much they've done — recommendations
    made and content edited — so an admin can decide who to promote."""
    rows = await conn.fetch(
        """
        SELECT cr.user_id,
               u.email,
               (SELECT count(*) FROM review_recommendations rr
                 WHERE rr.recommender_id = cr.user_id
                   AND rr.language_id = cr.language_id)          AS recommendations,
               (SELECT count(*) FROM example_sentences es
                 WHERE es.modified_by = cr.user_id
                   AND es.language_id = cr.language_id)          AS edits,
               (SELECT max(rr.created_at) FROM review_recommendations rr
                 WHERE rr.recommender_id = cr.user_id)           AS last_active
        FROM contributor_roles cr
        JOIN auth.users u ON u.id = cr.user_id
        WHERE cr.role = 'trial_reviewer'
          AND (cr.language_id = $1 OR cr.language_id IS NULL)
        ORDER BY recommendations DESC, u.email
        """,
        language_id,
    )
    return [
        {
            "user_id": str(r["user_id"]),
            "email": r["email"],
            "recommendations": int(r["recommendations"]),
            "edits": int(r["edits"]),
            "last_active": r["last_active"].isoformat() if r["last_active"] else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Trial-reviewer feedback prompt: occasionally nudge a trial reviewer to judge
# one real pending item before they use the dashboard. Their answer is recorded
# as an advisory recommendation (add_recommendation).
#
# The cadence is ADAPTIVE and self-explaining: each real answer schedules the
# next check-in further out (they "earn" quiet by contributing), a skip brings
# it back soon (so skipping can't buy the long gap), and a brand-new trial
# reviewer is nudged on their first dashboard visit.
# ---------------------------------------------------------------------------

# First real answer → 2 days; each further answer adds a day, capped at 2 weeks.
_PROMPT_BASE_HOURS = 48
_PROMPT_STEP_HOURS = 24
_PROMPT_MAX_HOURS = 24 * 14
# A skip comes back the same day-ish — it satisfies the nudge but earns no quiet.
_PROMPT_SKIP_HOURS = 8


def _next_prompt_hours(answered: int, gave_feedback: bool) -> int:
    """Hours until the next nudge. *answered* is the running count of real
    answers AFTER this one; skips don't grow the gap."""
    if not gave_feedback:
        return _PROMPT_SKIP_HOURS
    grown = _PROMPT_BASE_HOURS + _PROMPT_STEP_HOURS * max(0, answered - 1)
    return min(grown, _PROMPT_MAX_HOURS)


async def trial_prompt_due(conn: asyncpg.Connection, user_id: str) -> bool:
    """True if it's time to nudge this trial reviewer — no scheduled next
    check-in yet (never answered), or that time has passed."""
    scheduled = await conn.fetchval(
        """
        SELECT 1 FROM trial_review_prompt_state
        WHERE user_id = $1 AND next_prompt_at > now()
        """,
        user_id,
    )
    # A row means a future check-in is scheduled → NOT due yet.
    return scheduled is None


async def pick_review_prompt(
    conn: asyncpg.Connection,
    user_id: str,
    *,
    all_languages: bool,
    language_ids: list[str],
) -> dict | None:
    """Pick ONE pending item for this trial reviewer to judge — a generated
    drill first, else a generated example — in a language they can trial-review
    and haven't already recommended on. Returns a prompt payload, or None if
    there's nothing to ask about."""
    if not all_languages and not language_ids:
        return None
    lang_ids = None if all_languages else language_ids

    drill = await conn.fetchrow(
        """
        SELECT ds.id, ds.sentence, ds.answer, ds.translation,
               gp.language_id, gp.title AS context
        FROM drill_sentences ds
        JOIN grammar_points gp ON ds.grammar_point_id = gp.id
        WHERE ds.source = 'ai' AND ds.reviewed = false AND ds.flagged = false
          AND ($2::uuid[] IS NULL OR gp.language_id = ANY($2::uuid[]))
          AND NOT EXISTS (
            SELECT 1 FROM review_recommendations rr
             WHERE rr.recommender_id = $1
               AND rr.target_type = 'drill' AND rr.target_id = ds.id)
        ORDER BY ds.created_at
        LIMIT 1
        """,
        user_id, lang_ids,
    )
    if drill is not None:
        return {
            "target_type": "drill",
            "target_id": str(drill["id"]),
            "language_id": str(drill["language_id"]),
            "context": drill["context"],
            "sentence": drill["sentence"],
            "answer": drill["answer"],
            "translation": drill["translation"],
            "word": None,
            "question": "Is this a correct, natural drill you'd approve for learners?",
        }

    example = await conn.fetchrow(
        """
        SELECT es.id, es.sentence, es.translation, es.language_id,
               v.word AS context
        FROM example_sentences es
        JOIN vocabulary v ON es.vocabulary_id = v.id
        WHERE es.source = 'ai' AND es.reviewed = false AND es.flagged = false
          AND ($2::uuid[] IS NULL OR es.language_id = ANY($2::uuid[]))
          AND NOT EXISTS (
            SELECT 1 FROM review_recommendations rr
             WHERE rr.recommender_id = $1
               AND rr.target_type = 'example' AND rr.target_id = es.id)
        ORDER BY es.created_at
        LIMIT 1
        """,
        user_id, lang_ids,
    )
    if example is not None:
        return {
            "target_type": "example",
            "target_id": str(example["id"]),
            "language_id": str(example["language_id"]),
            "context": example["context"],
            "sentence": example["sentence"],
            "answer": None,
            "translation": example["translation"],
            "word": example["context"],
            "question": (
                f"Does this sentence use “{example['context']}” correctly "
                f"and read naturally?"
            ),
        }
    return None


async def record_trial_prompt_answer(
    conn: asyncpg.Connection, user_id: str, *, gave_feedback: bool
) -> str:
    """Stamp the answer and schedule the next check-in (privileged). Real
    feedback pushes it further out (they earn quiet); a skip brings it back
    soon. Returns the next_prompt_at ISO timestamp so the UI can tell them when
    they'll next be asked."""
    prior = await conn.fetchval(
        "SELECT prompts_answered FROM trial_review_prompt_state WHERE user_id = $1",
        user_id,
    ) or 0
    answered_after = prior + (1 if gave_feedback else 0)
    hours = _next_prompt_hours(answered_after, gave_feedback)
    ans_inc = 1 if gave_feedback else 0
    skip_inc = 0 if gave_feedback else 1
    row = await conn.fetchrow(
        """
        INSERT INTO trial_review_prompt_state
            (user_id, last_answered_at, prompts_answered, prompts_skipped, next_prompt_at)
        VALUES ($1, now(), $2, $3, now() + make_interval(hours => $4))
        ON CONFLICT (user_id) DO UPDATE SET
            last_answered_at = now(),
            prompts_answered = trial_review_prompt_state.prompts_answered + $2,
            prompts_skipped  = trial_review_prompt_state.prompts_skipped + $3,
            next_prompt_at   = now() + make_interval(hours => $4)
        RETURNING next_prompt_at
        """,
        user_id, ans_inc, skip_inc, hours,
    )
    return row["next_prompt_at"].isoformat()


async def list_pending_drills(
    conn: asyncpg.Connection, language_id: str, limit: int = 50
) -> list[dict]:
    """Generated grammar drills awaiting review for a language (WP gate): the
    cloze sentence, answer, its form (cell), the point it belongs to, and the
    model that made it — for the Contributor › Review 'Generated drills' panel."""
    rows = await conn.fetch(
        """
        SELECT ds.id, ds.sentence, ds.answer, ds.translation, ds.hint, ds.cell,
               ds.origin_detail, ds.flagged, ds.flag_reason,
               gp.title AS point_title, gp.id AS point_id
        FROM drill_sentences ds
        JOIN grammar_points gp ON ds.grammar_point_id = gp.id
        WHERE gp.language_id = $1 AND ds.source = 'ai' AND ds.reviewed = false
        ORDER BY gp.display_order, ds.created_at ASC
        LIMIT $2
        """,
        language_id, limit,
    )
    return [
        {
            "id": str(r["id"]),
            "sentence": r["sentence"],
            "answer": r["answer"],
            "translation": r["translation"],
            "hint": r["hint"],
            "cell": r["cell"],
            "origin_detail": r["origin_detail"],
            "flagged": r["flagged"],
            "flag_reason": r["flag_reason"],
            "point_title": r["point_title"],
            "point_id": str(r["point_id"]),
        }
        for r in rows
    ]


async def review_drill(
    conn: asyncpg.Connection, drill_id: str, approve: bool,
    actor_id: str | None = None,
) -> bool:
    """Approve (reviewed → true, now served to learners as permanent corpus) or
    reject (deleted) a pending generated drill. Only ever touches an unreviewed
    'ai' row. Returns True if a row changed."""
    ctx = await conn.fetchrow(
        "SELECT gp.language_id, gp.id AS point_id, ds.sentence "
        "FROM drill_sentences ds "
        "JOIN grammar_points gp ON ds.grammar_point_id = gp.id WHERE ds.id = $1",
        drill_id,
    )
    if approve:
        result = await conn.execute(
            "UPDATE drill_sentences SET reviewed = true "
            "WHERE id = $1 AND source = 'ai' AND reviewed = false",
            drill_id,
        )
    else:
        result = await conn.execute(
            "DELETE FROM drill_sentences "
            "WHERE id = $1 AND source = 'ai' AND reviewed = false",
            drill_id,
        )
    changed = result.rsplit(" ", 1)[-1] == "1"
    if changed and ctx:
        # A reviewer decision over this point's drills is human curation.
        await conn.execute(
            "UPDATE grammar_points SET curated = true WHERE id = $1",
            ctx["point_id"],
        )
    if changed and ctx:
        await log_change(
            conn, entity_type="drill", entity_id=drill_id, actor_id=actor_id,
            action="approved" if approve else "rejected",
            language_id=str(ctx["language_id"]),
            note=None if approve else f"deleted: {ctx['sentence']}",
        )
    return changed


async def vocab_needing_level(
    conn: asyncpg.Connection, language_id: str, limit: int = 500
) -> list[dict]:
    """Words with no CEFR level yet (no frequency rank to band from) — the gap an
    AI level estimate fills so they can enter a deck. Each row carries the word
    and its English gloss for the estimator's context."""
    rows = await conn.fetch(
        """
        SELECT v.id, v.word, v.part_of_speech,
               (SELECT t.definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                 AS definition
        FROM vocabulary v
        WHERE v.language_id = $1 AND v.level IS NULL
        ORDER BY v.frequency_rank NULLS LAST, v.word
        LIMIT $2
        """,
        language_id, limit,
    )
    return [
        {
            "vocabulary_id": str(r["id"]),
            "word": r["word"],
            "part_of_speech": r["part_of_speech"],
            "definition": r["definition"],
        }
        for r in rows
    ]


async def set_vocab_ai_level(
    conn: asyncpg.Connection, vocabulary_id: str, level: str
) -> bool:
    """Store an AI-estimated CEFR level (level_source='ai', provisional). Only
    touches rows that still have no level, so it never overwrites a real one."""
    result = await conn.execute(
        "UPDATE vocabulary SET level = $2, level_source = 'ai' "
        "WHERE id = $1 AND level IS NULL",
        vocabulary_id, level,
    )
    return result.rsplit(" ", 1)[-1] == "1"


async def list_ai_leveled_vocab(
    conn: asyncpg.Connection, language_id: str, limit: int = 200
) -> list[dict]:
    """Words carrying a provisional AI level, for a reviewer to confirm/adjust."""
    rows = await conn.fetch(
        """
        SELECT v.id, v.word, v.level, v.part_of_speech,
               (SELECT t.definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                 AS definition
        FROM vocabulary v
        WHERE v.language_id = $1 AND v.level_source = 'ai'
        ORDER BY v.level, v.word
        LIMIT $2
        """,
        language_id, limit,
    )
    return [
        {
            "id": str(r["id"]),
            "word": r["word"],
            "level": r["level"],
            "part_of_speech": r["part_of_speech"],
            "definition": r["definition"],
        }
        for r in rows
    ]


async def ensure_vocab_content_list(
    conn: asyncpg.Connection, language_id: str, level: str, language_code: str = ""
) -> None:
    """Make sure a subscribable vocab deck exists for this level — a newly
    leveled word at a level that had none otherwise wouldn't surface anywhere
    (decks resolve dynamically by level). Mirrors the seeder."""
    await conn.execute(
        """
        INSERT INTO content_lists (language_id, list_type, level, title, description)
        VALUES ($1, 'vocabulary', $2, $3, $4)
        ON CONFLICT (language_id, list_type, level) DO NOTHING
        """,
        language_id, level, f"{level} Vocabulary",
        f"Frequency-ranked {language_code} vocabulary ({level}).",
    )


async def confirm_vocab_level(
    conn: asyncpg.Connection, vocabulary_id: str, level: str,
    actor_id: str | None = None,
) -> bool:
    """A reviewer confirms (or adjusts) a provisional AI level — marks it curated
    so it's trusted and no longer flagged. Also its final deck placement."""
    prev = await conn.fetchrow(
        "SELECT language_id, level, level_source FROM vocabulary WHERE id = $1",
        vocabulary_id,
    )
    result = await conn.execute(
        "UPDATE vocabulary SET level = $2, level_source = 'curated' WHERE id = $1",
        vocabulary_id, level,
    )
    changed = result.rsplit(" ", 1)[-1] == "1"
    if changed and prev:
        await log_change(
            conn, entity_type="vocabulary", entity_id=vocabulary_id,
            actor_id=actor_id, action="level_confirmed", field="level",
            language_id=str(prev["language_id"]),
            before={"level": prev["level"], "level_source": prev["level_source"]},
            after={"level": level, "level_source": "curated"},
        )
    return changed


async def vocab_needing_examples(
    conn: asyncpg.Connection,
    language_id: str,
    min_examples: int,
    limit: int,
) -> list[dict]:
    """Words with FEWER than *min_examples* example sentences, commonest first
    (frequency_rank) so generation fills the highest-value gaps. Each row
    carries the context the generator needs."""
    rows = await conn.fetch(
        """
        SELECT v.id, v.word, v.part_of_speech, v.morphology,
               (SELECT t.definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                 AS definition,
               (SELECT count(*) FROM example_sentences es
                 WHERE es.vocabulary_id = v.id) AS example_count
        FROM vocabulary v
        WHERE v.language_id = $1
          AND (SELECT count(*) FROM example_sentences es
                WHERE es.vocabulary_id = v.id) < $2
        ORDER BY v.frequency_rank NULLS LAST, v.word
        LIMIT $3
        """,
        language_id, min_examples, limit,
    )
    out = []
    for r in rows:
        morph = r["morphology"]
        if isinstance(morph, str):
            try:
                morph = json.loads(morph)
            except (json.JSONDecodeError, TypeError):
                morph = {}
        out.append({
            "vocabulary_id": str(r["id"]),
            "word": r["word"],
            "lemma": (morph or {}).get("lemma") or r["word"],
            "part_of_speech": r["part_of_speech"],
            "definition": r["definition"],
            "example_count": r["example_count"],
        })
    return out


async def points_with_thin_cells(
    conn: asyncpg.Connection,
    language_id: str,
    target_per_cell: int,
    limit: int,
) -> list[dict]:
    """Paradigm points that have at least one cell BELOW *target_per_cell*, with
    their per-cell drill counts — the work-list for balanced thickening. Points
    with no cells (non-paradigm) are excluded; they thicken via
    points_needing_drills instead."""
    rows = await conn.fetch(
        """
        WITH cc AS (
            SELECT grammar_point_id AS pid, cell, count(*) AS n
            FROM drill_sentences
            WHERE cell IS NOT NULL
            GROUP BY grammar_point_id, cell
        )
        SELECT gp.id, gp.title, gp.explanation,
               jsonb_object_agg(cc.cell, cc.n) AS cell_counts
        FROM grammar_points gp
        JOIN cc ON cc.pid = gp.id
        WHERE gp.language_id = $1
        GROUP BY gp.id, gp.title, gp.explanation, gp.display_order
        HAVING min(cc.n) < $2
        ORDER BY gp.display_order, gp.title
        LIMIT $3
        """,
        language_id, target_per_cell, limit,
    )
    out = []
    for r in rows:
        cc = r["cell_counts"]
        if isinstance(cc, str):
            cc = json.loads(cc)
        out.append({
            "point_id": str(r["id"]),
            "title": r["title"],
            "explanation": r["explanation"],
            "cell_counts": cc or {},
        })
    return out


async def points_needing_drills(
    conn: asyncpg.Connection,
    language_id: str,
    min_drills: int,
    limit: int,
) -> list[dict]:
    """Grammar points with FEWER than *min_drills* drills, in curriculum order
    (display_order). Each row carries the context the drill generator needs."""
    rows = await conn.fetch(
        """
        SELECT gp.id, gp.title, gp.explanation,
               (SELECT count(*) FROM drill_sentences ds
                 WHERE ds.grammar_point_id = gp.id) AS drill_count
        FROM grammar_points gp
        WHERE gp.language_id = $1
          AND (SELECT count(*) FROM drill_sentences ds
                WHERE ds.grammar_point_id = gp.id) < $2
        ORDER BY gp.display_order, gp.title
        LIMIT $3
        """,
        language_id, min_drills, limit,
    )
    return [
        {
            "point_id": str(r["id"]),
            "title": r["title"],
            "explanation": r["explanation"],
            "drill_count": r["drill_count"],
        }
        for r in rows
    ]


async def update_drill(
    conn: asyncpg.Connection,
    drill_id: str,
    point_id: str,
    sentence: str,
    answer: str,
    translation: str | None,
    hint: str | None,
    modified_by: str | None = None,
) -> bool:
    """Edit a live drill (privileged). The edit de-certifies the point —
    reviewed flips false so a SECOND reviewer must re-approve before
    learners see the change (nobody self-certifies an edit) — and stamps
    provenance (is_modified / modified_by / modified_at) so an edited row is
    always distinguishable from its imported or seed original."""
    prev = await conn.fetchrow(
        "SELECT ds.sentence, ds.answer, ds.translation, ds.hint, gp.language_id "
        "FROM drill_sentences ds JOIN grammar_points gp "
        "ON ds.grammar_point_id = gp.id WHERE ds.id = $1",
        drill_id,
    )
    result = await conn.execute(
        """
        UPDATE drill_sentences
        SET sentence = $3, answer = $4, translation = $5, hint = $6,
            is_modified = true, modified_by = $7, modified_at = now()
        WHERE id = $1 AND grammar_point_id = $2
        """,
        drill_id, point_id, sentence, answer, translation or None, hint or None,
        modified_by,
    )
    if not result.endswith("1"):
        return False
    await conn.execute(
        "UPDATE grammar_points SET reviewed = false, curated = true WHERE id = $1",
        point_id,
    )
    if prev:
        await log_change(
            conn, entity_type="drill", entity_id=drill_id, actor_id=modified_by,
            action="edited", language_id=str(prev["language_id"]),
            before={"sentence": prev["sentence"], "answer": prev["answer"],
                    "translation": prev["translation"], "hint": prev["hint"]},
            after={"sentence": sentence, "answer": answer,
                   "translation": translation or None, "hint": hint or None},
        )
    return True


async def delete_drill(conn: asyncpg.Connection, drill_id: str) -> bool:
    """Delete a drill sentence (privileged). A human pruning drills is curation:
    the parent point is marked curated so a re-seed doesn't resurrect the drill
    by overwriting the set."""
    point_id = await conn.fetchval(
        "SELECT grammar_point_id FROM drill_sentences WHERE id = $1", drill_id
    )
    result = await conn.execute(
        "DELETE FROM drill_sentences WHERE id = $1", drill_id
    )
    ok = result.endswith("1")
    if ok and point_id:
        await conn.execute(
            "UPDATE grammar_points SET curated = true WHERE id = $1", point_id
        )
    return ok


async def save_explanation(
    conn: asyncpg.Connection,
    point_id: str,
    explanation: str,
    culture_note: str,
    submitted_by: str,
    references: list | None = None,
) -> bool:
    """Save a contributor explanation + references (privileged). Pending review."""
    refs = clean_references(references)
    prev = await conn.fetchrow(
        "SELECT language_id, explanation, culture_note, reference_links "
        "FROM grammar_points WHERE id = $1",
        point_id,
    )
    result = await conn.execute(
        """
        UPDATE grammar_points
        SET explanation = $2,
            culture_note = NULLIF($3, ''),
            reference_links = $5::jsonb,
            explanation_source = 'contributor',
            reviewed = false,
            curated = true,
            explanation_submitted_by = $4
        WHERE id = $1
        """,
        point_id, explanation, culture_note, submitted_by,
        json.dumps(refs, ensure_ascii=False),
    )
    if not result.endswith("1"):
        return False
    if prev:
        await log_change(
            conn, entity_type="grammar_point", entity_id=point_id,
            actor_id=submitted_by, action="edited", field="explanation",
            language_id=str(prev["language_id"]),
            before={"explanation": prev["explanation"],
                    "culture_note": prev["culture_note"],
                    "reference_links": _loads_json(prev["reference_links"])},
            after={"explanation": explanation,
                   "culture_note": culture_note or None,
                   "reference_links": refs},
        )
    return True


def _loads_json(v):
    """asyncpg returns jsonb as a str; a NULL comes back as None."""
    return json.loads(v) if isinstance(v, str) else v


async def approve_explanation(
    conn: asyncpg.Connection, point_id: str, reviewer_id: str
) -> bool:
    """Record the human linguist sign-off (privileged, admin-only).

    Marks the point reviewed and stamps who/when — this is the required
    semantic check that gates whether learners ever see the content.
    """
    lang = await conn.fetchval(
        "SELECT language_id FROM grammar_points WHERE id = $1", point_id
    )
    result = await conn.execute(
        """
        UPDATE grammar_points
        SET reviewed = true, curated = true, reviewed_by = $2, reviewed_at = now()
        WHERE id = $1
        """,
        point_id, reviewer_id,
    )
    if not result.endswith("1"):
        return False
    await log_change(
        conn, entity_type="grammar_point", entity_id=point_id,
        actor_id=reviewer_id, action="approved",
        language_id=str(lang) if lang else None,
        # A revert of an approval sends it back to pending review.
        before={"reviewed": False}, after={"reviewed": True},
    )
    return True


async def list_feedback(
    conn: asyncpg.Connection, language_id: str, status_filter: str = "open"
) -> list[dict]:
    """List learner feedback for a language (privileged read after role check)."""
    rows = await conn.fetch(
        """
        SELECT f.id, f.card_type, f.content_id, f.message, f.status, f.created_at,
               COALESCE(gp.title, v.word) AS card_title
        FROM card_feedback f
        LEFT JOIN grammar_points gp
               ON f.card_type = 'grammar' AND gp.id = f.content_id
        LEFT JOIN vocabulary v
               ON f.card_type = 'vocabulary' AND v.id = f.content_id
        WHERE f.language_id = $1 AND f.status = $2
        ORDER BY f.created_at DESC
        LIMIT 100
        """,
        language_id, status_filter,
    )
    return [
        {
            "id": str(r["id"]),
            "card_type": r["card_type"],
            "content_id": str(r["content_id"]),
            "card_title": r["card_title"],
            "message": r["message"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def get_feedback_language(
    conn: asyncpg.Connection, feedback_id: str
) -> str | None:
    """Return the language_id of a feedback row, or None."""
    lid = await conn.fetchval(
        "SELECT language_id FROM card_feedback WHERE id = $1", feedback_id
    )
    return str(lid) if lid else None


async def resolve_feedback(conn: asyncpg.Connection, feedback_id: str) -> bool:
    """Mark a feedback item resolved (privileged)."""
    result = await conn.execute(
        "UPDATE card_feedback SET status = 'resolved' WHERE id = $1", feedback_id
    )
    return result.endswith("1")


async def add_review_note(
    conn: asyncpg.Connection,
    grammar_point_id: str,
    author_id: str,
    note: str,
) -> str:
    """File a reviewer note against a grammar point (privileged, after role
    check)."""
    return str(await conn.fetchval(
        """
        INSERT INTO point_review_notes (grammar_point_id, author_id, note)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        grammar_point_id, author_id, note,
    ))


async def add_vocab_review_note(
    conn: asyncpg.Connection,
    vocabulary_id: str,
    author_id: str,
    note: str,
) -> str:
    """File a reviewer note against a vocabulary word (privileged, after role
    check). Same table as grammar notes — the entity is the vocab word."""
    return str(await conn.fetchval(
        """
        INSERT INTO point_review_notes (vocabulary_id, author_id, note)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        vocabulary_id, author_id, note,
    ))


async def list_review_notes(
    conn: asyncpg.Connection,
    language_id: str,
    *,
    include_resolved: bool = False,
) -> list[dict]:
    """Reviewer notes for a language — grammar-point AND vocabulary notes,
    newest first (privileged). Each row carries an entity_type and a human
    entity_label (the point title or the word)."""
    rows = await conn.fetch(
        """
        SELECT n.id, n.grammar_point_id, n.vocabulary_id,
               n.note, n.status, n.created_at, u.email AS author_email,
               CASE WHEN n.grammar_point_id IS NOT NULL
                    THEN 'grammar' ELSE 'vocab' END AS entity_type,
               COALESCE(gp.title, v.word) AS entity_label,
               gp.level AS level
        FROM point_review_notes n
        LEFT JOIN grammar_points gp ON gp.id = n.grammar_point_id
        LEFT JOIN vocabulary v ON v.id = n.vocabulary_id
        JOIN auth.users u ON u.id = n.author_id
        WHERE COALESCE(gp.language_id, v.language_id) = $1
          AND ($2 OR n.status = 'open')
        ORDER BY n.created_at DESC
        LIMIT 200
        """,
        language_id, include_resolved,
    )
    return [
        {
            "id": str(r["id"]),
            "grammar_point_id": (
                str(r["grammar_point_id"]) if r["grammar_point_id"] else None
            ),
            "vocabulary_id": (
                str(r["vocabulary_id"]) if r["vocabulary_id"] else None
            ),
            "entity_type": r["entity_type"],
            "entity_label": r["entity_label"],
            # Kept for backward compatibility with the existing grammar UI.
            "point_title": r["entity_label"],
            "level": r["level"],
            "note": r["note"],
            "status": r["status"],
            "author_email": r["author_email"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def get_note_language(
    conn: asyncpg.Connection, note_id: str
) -> str | None:
    """The language a note belongs to (for the resolve role check) — resolves
    through whichever entity (grammar point or vocab word) the note targets."""
    row = await conn.fetchval(
        """
        SELECT COALESCE(gp.language_id, v.language_id)
        FROM point_review_notes n
        LEFT JOIN grammar_points gp ON gp.id = n.grammar_point_id
        LEFT JOIN vocabulary v ON v.id = n.vocabulary_id
        WHERE n.id = $1
        """,
        note_id,
    )
    return str(row) if row else None


async def resolve_review_note(
    conn: asyncpg.Connection, note_id: str, resolver_id: str
) -> bool:
    """Mark a note resolved (privileged, after role check)."""
    result = await conn.execute(
        """
        UPDATE point_review_notes
        SET status = 'resolved', resolved_at = now(), resolved_by = $2
        WHERE id = $1 AND status = 'open'
        """,
        note_id, resolver_id,
    )
    return result.endswith("1")


async def grant_role(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str | None,
    role: str,
) -> None:
    """Grant a contributor/reviewer/admin role (privileged, admin-only)."""
    await conn.execute(
        """
        INSERT INTO contributor_roles (user_id, language_id, role)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, language_id, role) DO NOTHING
        """,
        user_id, language_id, role,
    )


async def revoke_role(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str | None,
    role: str,
) -> bool:
    """Remove one role row (privileged, admin-only). True if a row existed."""
    result = await conn.execute(
        """
        DELETE FROM contributor_roles
        WHERE user_id = $1 AND language_id IS NOT DISTINCT FROM $2 AND role = $3
        """,
        user_id, language_id, role,
    )
    return result.endswith("1")


async def list_all_roles(conn: asyncpg.Connection) -> list[dict]:
    """Every role grant with the holder's email (privileged, admin-only)."""
    rows = await conn.fetch(
        """
        SELECT cr.user_id, u.email, cr.language_id, l.code AS language_code,
               cr.role, cr.created_at
        FROM contributor_roles cr
        JOIN auth.users u ON u.id = cr.user_id
        LEFT JOIN languages l ON l.id = cr.language_id
        ORDER BY u.email, cr.role
        """
    )
    return [
        {
            "user_id": str(r["user_id"]),
            "email": r["email"],
            "language_id": str(r["language_id"]) if r["language_id"] else None,
            "language_code": r["language_code"],
            "role": r["role"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def find_user_by_email(
    conn: asyncpg.Connection, email: str
) -> str | None:
    """Resolve an account email to its user id (privileged, admin-only)."""
    row = await conn.fetchval(
        "SELECT id FROM auth.users WHERE lower(email) = lower($1)", email.strip()
    )
    return str(row) if row else None


async def list_accounts(conn: asyncpg.Connection) -> list[dict]:
    """Every account with what an admin needs at a glance (privileged;
    router verifies the admin role first): email, joined, plan, roles,
    how much they've studied, and their admin-set monthly charge."""
    # Probe rather than try/except: a raised UndefinedTableError aborts the
    # whole pooled transaction, and this listing must keep working before
    # migration 20260920 lands (the price column just reads as unset).
    has_prices = bool(
        await conn.fetchval("SELECT to_regclass('custom_prices') IS NOT NULL")
    )
    price_select = (
        "cp.monthly_cents, cp.currency AS price_currency,"
        if has_prices
        else "NULL::int AS monthly_cents, NULL::text AS price_currency,"
    )
    price_join = (
        "LEFT JOIN custom_prices cp ON cp.user_id = u.id" if has_prices else ""
    )
    rows = await conn.fetch(
        f"""
        SELECT u.id, u.email, u.created_at, u.last_sign_in_at,
               up.plan_scope, pl.code AS plan_language,
               up.tutor_access, up.tutor_daily_cap,
               {price_select}
               COALESCE(r.roles, '{{}}') AS roles,
               COALESCE(c.cards, 0) AS cards,
               COALESCE(c.langs, 0) AS languages_studied
        FROM auth.users u
        LEFT JOIN user_profiles up ON up.id = u.id
        LEFT JOIN languages pl ON pl.id = up.plan_language_id
        {price_join}
        LEFT JOIN LATERAL (
            SELECT array_agg(DISTINCT cr.role) AS roles
            FROM contributor_roles cr WHERE cr.user_id = u.id
        ) r ON true
        LEFT JOIN LATERAL (
            SELECT count(*) AS cards, count(DISTINCT uc.language_id) AS langs
            FROM user_cards uc WHERE uc.user_id = u.id
        ) c ON true
        ORDER BY u.created_at DESC
        """
    )
    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "last_sign_in_at": (
                r["last_sign_in_at"].isoformat() if r["last_sign_in_at"] else None
            ),
            "plan_scope": r["plan_scope"],
            "plan_language": r["plan_language"],
            "tutor_access": r["tutor_access"] or "default",
            "tutor_daily_cap": r["tutor_daily_cap"],
            "monthly_cents": r["monthly_cents"],
            "price_currency": r["price_currency"],
            "roles": list(r["roles"] or []),
            "cards": r["cards"],
            "languages_studied": r["languages_studied"],
        }
        for r in rows
    ]


async def delete_account(conn: asyncpg.Connection, user_id: str) -> bool:
    """Permanently delete an account (privileged; router verifies admin +
    not-self). Deleting the auth.users row cascades through the auth
    schema AND every app table (all carry ON DELETE CASCADE on user_id):
    profile, cards, review history, notes, subscriptions, roles."""
    result = await conn.execute("DELETE FROM auth.users WHERE id = $1", user_id)
    return result.endswith("1")


async def set_account_plan(
    conn: asyncpg.Connection,
    user_id: str,
    plan_scope: str,
    plan_language_id: str | None,
) -> bool:
    """Admin plan override: switch an account between Single and All."""
    result = await conn.execute(
        """
        UPDATE user_profiles
        SET plan_scope = $2,
            plan_language_id = CASE WHEN $2 = 'single'
                                    THEN $3::uuid ELSE NULL END
        WHERE id = $1
        """,
        user_id, plan_scope, plan_language_id,
    )
    return result.endswith("1")


async def create_auth_user(
    conn: asyncpg.Connection, email: str, password: str,
    user_meta: dict | None = None,
) -> str:
    """Create a confirmed email+password auth account via SQL (privileged).

    user_meta lands in raw_user_meta_data, which GoTrue serves as the JWT's
    user_metadata — the seam the trial flow uses for its
    must_change_password flag (rides in every session, cleared client-side
    via auth.updateUser, no profile column or migration involved).

    Fallback for when the GoTrue admin HTTP API is unreachable from the
    server (the deploy's egress to *.supabase.co hangs while the database
    pooler works fine). Writes exactly what /auth/v1/admin/users with
    email_confirm=true writes: a confirmed auth.users row hashed with
    pgcrypto's bf crypt — the same check GoTrue runs at sign-in — plus its
    email identity. Token columns are '' not NULL (GoTrue scans them).
    Raises ValueError on a duplicate email.
    """
    try:
        async with conn.transaction():
            # pgcrypto lives in `extensions` on Supabase and `public` on a
            # plain Postgres. Naming both here means the crypt() call below
            # resolves on either, instead of the query being the one thing
            # that pins this app to Supabase. LOCAL: reverts at commit.
            await conn.execute(
                "SET LOCAL search_path = public, extensions"
            )
            row = await conn.fetchrow(
                """
                INSERT INTO auth.users
                    (instance_id, id, aud, role, email, encrypted_password,
                     email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
                     created_at, updated_at,
                     confirmation_token, recovery_token,
                     email_change, email_change_token_new)
                VALUES
                    ('00000000-0000-0000-0000-000000000000', gen_random_uuid(),
                     'authenticated', 'authenticated', lower($1),
                     -- Unqualified: the SET LOCAL search_path above puts
                     -- both candidate schemas in scope.
                     crypt($2, gen_salt('bf')),
                     now(), '{"provider": "email", "providers": ["email"]}',
                     $3::jsonb, now(), now(), '', '', '', '')
                RETURNING id
                """,
                email, password, json.dumps(user_meta or {}),
            )
            uid = str(row["id"])
            await conn.execute(
                """
                INSERT INTO auth.identities
                    (id, user_id, provider_id, identity_data, provider,
                     last_sign_in_at, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), $1::uuid, $1,
                     jsonb_build_object('sub', $1, 'email', lower($2),
                                        'email_verified', true),
                     'email', now(), now(), now())
                """,
                uid, email,
            )
    except asyncpg.UniqueViolationError as exc:
        raise ValueError("email already registered") from exc
    return uid


# ── Content suggestions (contributor-proposed card edits) ─────────────────
# The editable text fields a contributor may propose changing on a card.
SUGGESTION_FIELDS = {
    "vocabulary": ("definition", "part_of_speech", "usage_note"),
    "grammar": ("function_note", "explanation", "culture_note"),
}

# content_suggestions uses entity_type 'vocabulary'/'grammar'; the audit log's
# CHECK constraint names the grammar entity 'grammar_point'. Map when logging.
_AUDIT_ENTITY = {"vocabulary": "vocabulary", "grammar": "grammar_point"}


def reseed_grammar_proposal(point: dict, current: dict) -> dict:
    """The part of a re-seed grammar point that DIFFERS from a live *curated*
    card, shaped as a content_suggestions proposal ({function_note?,
    explanation?, culture_note?}). Returns {} when the reseed proposes nothing
    new. *point* is a seed-file point dict (its one-liner is under "function");
    *current* is the live row's values. Blank incoming values never propose
    blanking a field a human wrote."""
    proposed: dict = {}
    pairs = (
        ("function_note", (point.get("function") or "").strip()),
        ("explanation", (point.get("explanation") or "").strip()),
        ("culture_note", (point.get("culture_note") or "").strip()),
    )
    for field, new in pairs:
        cur = (current.get(field) or "").strip()
        if new and new != cur:
            proposed[field] = new
    return proposed


def reseed_vocab_proposal(record: dict, current: dict) -> dict:
    """The part of a re-seed record that DIFFERS from a live *curated* vocab
    card, shaped as a content_suggestions proposal ({part_of_speech?,
    definition?}). Returns {} when the reseed proposes nothing new, so a reseed
    that merely re-confirms the card makes no noise suggestion.

    Only the fields a CSV seed can carry and a reviewer may suggest are
    compared: part_of_speech and the English definition. (usage_note is a
    contributor-only field; the seed never sets it.)"""
    proposed: dict = {}
    new_pos = (record.get("pos") or "").strip()
    cur_pos = (current.get("part_of_speech") or "").strip()
    if new_pos and new_pos != cur_pos:
        proposed["part_of_speech"] = new_pos
    new_def = ((record.get("translations") or {}).get("en") or "").strip()
    cur_def = (current.get("definition") or "").strip()
    if new_def and new_def != cur_def:
        proposed["definition"] = new_def
    return proposed


async def entity_language(
    conn: asyncpg.Connection, entity_type: str, entity_id: str
) -> str | None:
    """The language_id owning a vocabulary row or grammar point, or None."""
    table = "vocabulary" if entity_type == "vocabulary" else "grammar_points"
    lid = await conn.fetchval(
        f"SELECT language_id FROM {table} WHERE id = $1", entity_id
    )
    return str(lid) if lid else None


async def submit_suggestion(
    conn: asyncpg.Connection,
    language_id: str,
    entity_type: str,
    entity_id: str,
    author_id: str,
    proposed: dict,
    note: str | None,
) -> str:
    """Store a proposed edit (pending). Only known fields are kept."""
    allowed = SUGGESTION_FIELDS[entity_type]
    clean = {
        k: (v.strip() if isinstance(v, str) else v)
        for k, v in proposed.items()
        if k in allowed and v is not None and str(v).strip() != ""
    }
    if not clean:
        raise ValueError("no editable fields in proposal")
    row = await conn.fetchrow(
        """
        INSERT INTO content_suggestions
            (language_id, entity_type, entity_id, author_id, proposed, note)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        language_id, entity_type, entity_id, author_id,
        json.dumps(clean, ensure_ascii=False), (note or "").strip() or None,
    )
    return str(row["id"])


async def _current_fields(
    conn: asyncpg.Connection, entity_type: str, entity_id: str
) -> dict:
    """The card's current values for the suggestable fields (for the diff)."""
    if entity_type == "vocabulary":
        r = await conn.fetchrow(
            """
            SELECT v.word, v.part_of_speech, v.usage_note,
                   (SELECT definition FROM translations
                     WHERE vocabulary_id = v.id AND locale = 'en' LIMIT 1) AS definition
            FROM vocabulary v WHERE v.id = $1
            """,
            entity_id,
        )
        if not r:
            return {}
        return {"title": r["word"], "definition": r["definition"],
                "part_of_speech": r["part_of_speech"], "usage_note": r["usage_note"]}
    r = await conn.fetchrow(
        "SELECT title, function_note, explanation, culture_note "
        "FROM grammar_points WHERE id = $1", entity_id,
    )
    if not r:
        return {}
    return {"title": r["title"], "function_note": r["function_note"],
            "explanation": r["explanation"], "culture_note": r["culture_note"]}


async def create_extraction_suggestion(
    conn: asyncpg.Connection,
    language_id: str,
    entity_id: str,
    proposed: dict,
    *,
    entity_type: str = "vocabulary",
    origin: str = "document re-seed",
    current: dict | None = None,
) -> str | None:
    """Stash a doc re-seed's proposed values for a CURATED card (vocabulary or
    grammar) as a pending suggestion instead of overwriting the reviewer's work.
    System authored (no auth user), marked source='extraction' so admin metrics
    can track how often these are accepted.

    Idempotent per card: a repeated reseed refreshes the single pending
    extraction row (partial unique index) rather than piling up duplicates. The
    prior values are recorded to the audit log so a reviewer can always see what
    the reseed would have changed. Returns the suggestion id, or None when
    there is nothing new to propose."""
    allowed = SUGGESTION_FIELDS[entity_type]
    clean = {
        k: v.strip()
        for k, v in proposed.items()
        if k in allowed and isinstance(v, str) and v.strip()
    }
    if not clean:
        return None
    row = await conn.fetchrow(
        """
        INSERT INTO content_suggestions
            (language_id, entity_type, entity_id, author_id, proposed,
             source, origin)
        VALUES ($1, $2, $3, NULL, $4, 'extraction', $5)
        ON CONFLICT (entity_type, entity_id)
            WHERE source = 'extraction' AND status = 'pending'
            DO UPDATE SET proposed = EXCLUDED.proposed,
                          origin = EXCLUDED.origin,
                          created_at = now()
        RETURNING id
        """,
        language_id, entity_type, entity_id,
        json.dumps(clean, ensure_ascii=False), origin,
    )
    sid = str(row["id"])
    before = {k: (current or {}).get(k) for k in clean} if current else None
    await log_change(
        conn, entity_type=_AUDIT_ENTITY.get(entity_type, entity_type),
        entity_id=str(entity_id),
        action="suggested", language_id=str(language_id),
        before=before, after=clean, note=origin,
    )
    return sid


async def list_suggestions(
    conn: asyncpg.Connection,
    language_id: str,
    status_filter: str = "pending",
    source: str | None = None,
) -> list[dict]:
    """Pending suggestions for a language, each with current vs proposed.

    *source* optionally narrows to one origin ('contributor' | 'extraction') so
    the reviewer can page just the doc-sourced AI recommendations."""
    rows = await conn.fetch(
        """
        SELECT s.id, s.entity_type, s.entity_id, s.proposed, s.note,
               s.status, s.source, s.origin, s.created_at
        FROM content_suggestions s
        WHERE s.language_id = $1 AND s.status = $2
          AND ($3::text IS NULL OR s.source = $3)
        ORDER BY s.created_at ASC
        LIMIT 100
        """,
        language_id, status_filter, source,
    )
    out = []
    for r in rows:
        current = await _current_fields(conn, r["entity_type"], str(r["entity_id"]))
        proposed = r["proposed"]
        if isinstance(proposed, str):
            proposed = json.loads(proposed)
        out.append({
            "id": str(r["id"]),
            "entity_type": r["entity_type"],
            "entity_id": str(r["entity_id"]),
            "card_title": current.get("title"),
            "current": {k: v for k, v in current.items() if k != "title"},
            "proposed": proposed,
            "note": r["note"],
            "status": r["status"],
            "source": r["source"],
            "origin": r["origin"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return out


async def get_suggestion(conn: asyncpg.Connection, suggestion_id: str) -> dict | None:
    """Raw suggestion row (for the router's language + status checks)."""
    r = await conn.fetchrow(
        "SELECT id, language_id, entity_type, entity_id, proposed, status, "
        "source, origin FROM content_suggestions WHERE id = $1", suggestion_id,
    )
    if not r:
        return None
    proposed = r["proposed"]
    if isinstance(proposed, str):
        proposed = json.loads(proposed)
    return {"id": str(r["id"]), "language_id": str(r["language_id"]),
            "entity_type": r["entity_type"], "entity_id": str(r["entity_id"]),
            "proposed": proposed, "status": r["status"],
            "source": r["source"], "origin": r["origin"]}


async def _apply_to_entity(
    conn: asyncpg.Connection, entity_type: str, entity_id: str, proposed: dict
) -> None:
    """Write an approved proposal onto the live card."""
    allowed = SUGGESTION_FIELDS[entity_type]
    fields = {k: v for k, v in proposed.items() if k in allowed}
    if entity_type == "vocabulary":
        if "part_of_speech" in fields:
            await conn.execute(
                "UPDATE vocabulary SET part_of_speech = $1 WHERE id = $2",
                fields["part_of_speech"], entity_id,
            )
            # a POS change can retire wrong-sense gender/number chips
            m = await conn.fetchval(
                "SELECT morphology FROM vocabulary WHERE id = $1", entity_id)
            if isinstance(m, str):
                m = json.loads(m) if m else {}
            new = strip_nominal_chips(m, fields["part_of_speech"])
            if new != m:
                await conn.execute(
                    "UPDATE vocabulary SET morphology = $1 WHERE id = $2",
                    json.dumps(new, ensure_ascii=False), entity_id)
        if "usage_note" in fields:
            await conn.execute(
                "UPDATE vocabulary SET usage_note = $1 WHERE id = $2",
                fields["usage_note"], entity_id,
            )
        if "definition" in fields:
            await conn.execute(
                """
                INSERT INTO translations (vocabulary_id, locale, definition)
                VALUES ($1, 'en', $2)
                ON CONFLICT (vocabulary_id, locale)
                    DO UPDATE SET definition = EXCLUDED.definition
                """,
                entity_id, fields["definition"],
            )
        # An approved human edit makes this a human-owned card: mark it curated
        # so a later doc re-seed routes to the suggestion queue instead of
        # overwriting the reviewer's work.
        await conn.execute(
            "UPDATE vocabulary SET curated = true WHERE id = $1", entity_id)
    else:  # grammar
        cols = [k for k in ("function_note", "explanation", "culture_note")
                if k in fields]
        if cols:
            sets = ", ".join(f"{c} = ${i + 2}" for i, c in enumerate(cols))
            await conn.execute(
                f"UPDATE grammar_points SET {sets} WHERE id = $1",
                entity_id, *[fields[c] for c in cols],
            )
        # An approved human edit makes this a human-owned point — later doc
        # re-seeds route to the suggestion queue instead of overwriting.
        await conn.execute(
            "UPDATE grammar_points SET curated = true WHERE id = $1", entity_id)


async def approve_suggestion(
    conn: asyncpg.Connection, suggestion_id: str, reviewer_id: str
) -> bool:
    """Apply a pending suggestion to the card and mark it approved. Records the
    prior values to the audit log (before/after) so the change is reviewable
    and revertible."""
    s = await get_suggestion(conn, suggestion_id)
    if not s or s["status"] != "pending":
        return False
    before = await _current_fields(conn, s["entity_type"], s["entity_id"])
    async with conn.transaction():
        await _apply_to_entity(conn, s["entity_type"], s["entity_id"], s["proposed"])
        await conn.execute(
            """
            UPDATE content_suggestions
            SET status = 'approved', reviewer_id = $2, resolved_at = now()
            WHERE id = $1
            """,
            suggestion_id, reviewer_id,
        )
        await log_change(
            conn,
            entity_type=_AUDIT_ENTITY.get(s["entity_type"], s["entity_type"]),
            entity_id=str(s["entity_id"]), actor_id=reviewer_id,
            action="approved", language_id=str(s["language_id"]),
            before={k: before.get(k) for k in s["proposed"]},
            after=dict(s["proposed"]),
            note=f"{s.get('source') or 'contributor'} suggestion",
        )
    return True


async def reject_suggestion(
    conn: asyncpg.Connection, suggestion_id: str, reviewer_id: str,
    review_note: str | None,
) -> bool:
    """Mark a pending suggestion rejected (nothing is applied). Logs the
    rejected proposal so a dismissed AI recommendation stays reviewable."""
    s = await get_suggestion(conn, suggestion_id)
    if not s or s["status"] != "pending":
        return False
    result = await conn.execute(
        """
        UPDATE content_suggestions
        SET status = 'rejected', reviewer_id = $2, review_note = $3,
            resolved_at = now()
        WHERE id = $1 AND status = 'pending'
        """,
        suggestion_id, reviewer_id, (review_note or "").strip() or None,
    )
    ok = result.endswith("1")
    if ok:
        await log_change(
            conn,
            entity_type=_AUDIT_ENTITY.get(s["entity_type"], s["entity_type"]),
            entity_id=str(s["entity_id"]), actor_id=reviewer_id,
            action="rejected", language_id=str(s["language_id"]),
            after=dict(s["proposed"]),
            note=(review_note or "").strip()
            or f"{s.get('source') or 'contributor'} suggestion",
        )
    return ok


async def extraction_suggestion_metrics(
    conn: asyncpg.Connection, language_id: str | None = None
) -> dict:
    """Acceptance stats for doc-sourced (extraction) vocab suggestions — how
    often these comparatively expensive AI recommendations get accepted. Admin
    metric; filter to one language or across all."""
    row = await conn.fetchrow(
        """
        SELECT
          count(*)                                     AS total,
          count(*) FILTER (WHERE status = 'pending')   AS pending,
          count(*) FILTER (WHERE status = 'approved')  AS approved,
          count(*) FILTER (WHERE status = 'rejected')  AS rejected
        FROM content_suggestions
        WHERE source = 'extraction'
          AND ($1::uuid IS NULL OR language_id = $1)
        """,
        language_id,
    )
    approved = row["approved"] or 0
    rejected = row["rejected"] or 0
    resolved = approved + rejected
    return {
        "total": row["total"] or 0,
        "pending": row["pending"] or 0,
        "approved": approved,
        "rejected": rejected,
        "resolved": resolved,
        "acceptance_rate": (approved / resolved) if resolved else None,
    }


async def admin_engagement_users(
    conn: asyncpg.Connection, days: int = 30
) -> list[dict]:
    """Per-user engagement drill-down for the admin panel (privileged conn).

    One row per account: identity, when they joined, when they were last
    active anywhere, and their activity counts inside the window — the
    detail behind the aggregate tiles. Same activity tables, no new
    tracking.
    """
    rows = await conn.fetch(
        """
        SELECT u.id, u.email, p.created_at AS joined,
          (SELECT count(*) FROM review_log rl
            WHERE rl.user_id = u.id
              AND rl.created_at > now() - make_interval(days => $1)) AS reviews,
          (SELECT COALESCE(sum(rl.time_taken_ms), 0) FROM review_log rl
            WHERE rl.user_id = u.id
              AND rl.created_at > now() - make_interval(days => $1)) AS review_ms,
          (SELECT count(*) FROM tutor_usage tu
            WHERE tu.user_id = u.id
              AND tu.created_at > now() - make_interval(days => $1)) AS tutor_messages,
          (SELECT count(*) FROM readings r
            WHERE r.user_id = u.id
              AND r.created_at > now() - make_interval(days => $1)) AS readings,
          (SELECT count(*) FROM user_cards uc
            WHERE uc.user_id = u.id
              AND uc.created_at > now() - make_interval(days => $1)) AS cards_started,
          (SELECT count(*) FROM user_cards uc
            WHERE uc.user_id = u.id) AS cards_total,
          (SELECT max(t) FROM (
              SELECT max(created_at) AS t FROM review_log WHERE user_id = u.id
              UNION ALL SELECT max(created_at) FROM tutor_usage WHERE user_id = u.id
              UNION ALL SELECT max(created_at) FROM readings WHERE user_id = u.id
              UNION ALL SELECT max(created_at) FROM user_cards WHERE user_id = u.id
          ) acts) AS last_active,
          (SELECT COALESCE(array_agg(DISTINCT l.code), '{}') FROM user_cards uc
            JOIN languages l ON uc.language_id = l.id
            WHERE uc.user_id = u.id) AS languages
        FROM auth.users u
        LEFT JOIN user_profiles p ON p.id = u.id
        ORDER BY last_active DESC NULLS LAST
        LIMIT 200
        """,
        days,
    )
    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "joined": r["joined"].isoformat() if r["joined"] else None,
            "last_active": r["last_active"].isoformat() if r["last_active"] else None,
            "reviews": r["reviews"],
            "review_minutes": round((r["review_ms"] or 0) / 60_000),
            "tutor_messages": r["tutor_messages"],
            "readings": r["readings"],
            "cards_started": r["cards_started"],
            "cards_total": r["cards_total"],
            "languages": list(r["languages"] or []),
        }
        for r in rows
    ]


async def admin_timeseries(conn: asyncpg.Connection, days: int = 30) -> list[dict]:
    """Daily activity series for the admin analytics charts (WP26a).

    One row per calendar day (UTC): distinct active users across every
    activity table, review count, study minutes, and new signups. All
    from tables normal use writes — no extra tracking.
    """
    rows = await conn.fetch(
        """
        SELECT day::date AS day,
          (SELECT count(DISTINCT u) FROM (
              SELECT user_id AS u FROM review_log
               WHERE (created_at AT TIME ZONE 'UTC')::date = day
              UNION SELECT user_id FROM tutor_usage
               WHERE (created_at AT TIME ZONE 'UTC')::date = day
              UNION SELECT user_id FROM readings
               WHERE (created_at AT TIME ZONE 'UTC')::date = day
              UNION SELECT user_id FROM user_cards
               WHERE (created_at AT TIME ZONE 'UTC')::date = day
          ) acts) AS active_users,
          (SELECT count(*) FROM review_log
            WHERE (created_at AT TIME ZONE 'UTC')::date = day) AS reviews,
          (SELECT COALESCE(sum(time_taken_ms), 0) / 60000 FROM review_log
            WHERE (created_at AT TIME ZONE 'UTC')::date = day) AS minutes,
          (SELECT count(*) FROM user_profiles
            WHERE (created_at AT TIME ZONE 'UTC')::date = day) AS new_users
        FROM generate_series(
            (now() AT TIME ZONE 'UTC')::date - ($1 - 1),
            (now() AT TIME ZONE 'UTC')::date,
            interval '1 day'
        ) AS day
        ORDER BY day
        """,
        days,
    )
    return [
        {
            "date": r["day"].isoformat(),
            "active_users": int(r["active_users"]),
            "reviews": int(r["reviews"]),
            "minutes": int(r["minutes"]),
            "new_users": int(r["new_users"]),
        }
        for r in rows
    ]


def compute_cohort_grid(
    signups: list[tuple[str, str]],
    activity: set[tuple[str, str]],
) -> list[dict]:
    """Weekly retention grid (WP26b), pure so it's unit-testable.

    *signups*: (user_id, iso signup-week-start); *activity*: distinct
    (user_id, iso activity-week-start). Week 0 is the signup week itself.
    """
    from datetime import date, timedelta

    cohorts: dict[str, list[str]] = {}
    for uid, wk in signups:
        cohorts.setdefault(wk, []).append(uid)

    grid = []
    for wk in sorted(cohorts):
        members = cohorts[wk]
        start = date.fromisoformat(wk)
        weeks = []
        for offset in range(8):
            target = (start + timedelta(weeks=offset)).isoformat()
            returned = sum(1 for uid in members if (uid, target) in activity)
            weeks.append(returned)
        grid.append({"cohort_week": wk, "size": len(members), "returned": weeks})
    return grid


async def admin_cohorts(conn: asyncpg.Connection, weeks: int = 8) -> list[dict]:
    """Signup-cohort retention (WP26b): of each week's signups, how many
    were active in week 0, 1, 2…  Small data — aggregate in Python."""
    signup_rows = await conn.fetch(
        """
        SELECT id, date_trunc('week', created_at AT TIME ZONE 'UTC')::date AS wk
        FROM user_profiles
        WHERE created_at > now() - make_interval(weeks => $1)
        """,
        weeks,
    )
    activity_rows = await conn.fetch(
        """
        SELECT DISTINCT user_id,
               date_trunc('week', created_at AT TIME ZONE 'UTC')::date AS wk
        FROM (
            SELECT user_id, created_at FROM review_log
            UNION ALL SELECT user_id, created_at FROM tutor_usage
            UNION ALL SELECT user_id, created_at FROM readings
            UNION ALL SELECT user_id, created_at FROM user_cards
        ) acts
        WHERE created_at > now() - make_interval(weeks => $1)
        """,
        weeks,
    )
    signups = [(str(r["id"]), r["wk"].isoformat()) for r in signup_rows]
    activity = {(str(r["user_id"]), r["wk"].isoformat()) for r in activity_rows}
    return compute_cohort_grid(signups, activity)


async def admin_engagement_user_detail(
    conn: asyncpg.Connection, user_id: str, days: int = 30
) -> list[dict]:
    """Per-language activity for ONE account (privileged conn) — what an
    admin sees when they expand a row in the engagement users table.
    review_log carries no language_id, so reviews route through the card.
    """
    rows = await conn.fetch(
        """
        SELECT l.code, l.name,
          (SELECT count(*) FROM user_cards uc
            WHERE uc.user_id = $1 AND uc.language_id = l.id) AS cards_total,
          (SELECT count(*) FROM review_log rl
            JOIN user_cards uc2 ON uc2.id = rl.card_id
            WHERE rl.user_id = $1 AND uc2.language_id = l.id
              AND rl.created_at > now() - make_interval(days => $2)) AS reviews,
          (SELECT COALESCE(sum(rl.time_taken_ms), 0) FROM review_log rl
            JOIN user_cards uc2 ON uc2.id = rl.card_id
            WHERE rl.user_id = $1 AND uc2.language_id = l.id
              AND rl.created_at > now() - make_interval(days => $2)) AS review_ms,
          (SELECT count(*) FROM tutor_usage tu
            WHERE tu.user_id = $1 AND tu.language_id = l.id
              AND tu.created_at > now() - make_interval(days => $2)) AS tutor_messages,
          (SELECT count(*) FROM readings r
            WHERE r.user_id = $1 AND r.language_id = l.id
              AND r.created_at > now() - make_interval(days => $2)) AS readings,
          (SELECT max(uc3.last_review) FROM user_cards uc3
            WHERE uc3.user_id = $1 AND uc3.language_id = l.id) AS last_review
        FROM languages l
        WHERE EXISTS (SELECT 1 FROM user_cards uc0
                       WHERE uc0.user_id = $1 AND uc0.language_id = l.id)
           OR EXISTS (SELECT 1 FROM tutor_usage tu0
                       WHERE tu0.user_id = $1 AND tu0.language_id = l.id)
           OR EXISTS (SELECT 1 FROM readings r0
                       WHERE r0.user_id = $1 AND r0.language_id = l.id)
        ORDER BY cards_total DESC
        """,
        user_id, days,
    )
    return [
        {
            "code": r["code"],
            "name": r["name"],
            "cards_total": r["cards_total"],
            "reviews": r["reviews"],
            "review_minutes": round((r["review_ms"] or 0) / 60_000),
            "tutor_messages": r["tutor_messages"],
            "readings": r["readings"],
            "last_review": r["last_review"].isoformat() if r["last_review"] else None,
        }
        for r in rows
    ]


# ── Translation review queue (what the AI maker-checker wouldn't apply) ───
async def sentences_needing_locale(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int
) -> list[dict]:
    """Reviewed example sentences with NO translation yet in *locale* — the
    idempotent gap-list for generating support-locale sentence translations (a
    non-English speaker learning English). English-course sentences are stored
    per support locale (one row each), so the English text is taken from ANY
    existing reviewed row for the sentence, not a specific locale. Returns each
    distinct sentence with its word's id so a new locale row can be inserted."""
    rows = await conn.fetch(
        """
        SELECT DISTINCT es.vocabulary_id, es.sentence
        FROM example_sentences es
        JOIN vocabulary v ON es.vocabulary_id = v.id
        WHERE v.language_id = $1
          AND es.reviewed
          AND es.translation_locale <> $2
          AND NOT EXISTS (
              SELECT 1 FROM example_sentences e2
              WHERE e2.vocabulary_id = es.vocabulary_id
                AND e2.sentence = es.sentence
                AND e2.translation_locale = $2)
        ORDER BY es.vocabulary_id
        LIMIT $3
        """,
        language_id, locale, limit,
    )
    return [
        {"vocabulary_id": str(r["vocabulary_id"]), "sentence": r["sentence"]}
        for r in rows
    ]


async def vocab_needing_definition(
    conn: asyncpg.Connection, language_id: str, locale: str, limit: int
) -> list[dict]:
    """Words in a language with NO definition in *locale* and no pending review
    for it — the idempotent gap-list for the definitions generator. Commonest
    words first; each carries an example sentence for sense disambiguation."""
    rows = await conn.fetch(
        """
        SELECT v.id, v.word, v.part_of_speech,
               (SELECT es.sentence FROM example_sentences es
                 WHERE es.vocabulary_id = v.id
                 ORDER BY es.difficulty_rank NULLS LAST LIMIT 1) AS example
        FROM vocabulary v
        WHERE v.language_id = $1
          AND NOT EXISTS (SELECT 1 FROM translations t
                           WHERE t.vocabulary_id = v.id AND t.locale = $2)
          AND NOT EXISTS (SELECT 1 FROM translation_reviews r
                           WHERE r.vocabulary_id = v.id AND r.locale = $2
                             AND r.status = 'pending')
        ORDER BY v.frequency_rank NULLS LAST, v.word
        LIMIT $3
        """,
        language_id, locale, limit,
    )
    return [
        {
            "vocabulary_id": str(r["id"]), "word": r["word"],
            "part_of_speech": r["part_of_speech"], "example": r["example"],
        }
        for r in rows
    ]


async def apply_definition(
    conn: asyncpg.Connection, vocabulary_id: str, locale: str, definition: str
) -> bool:
    """Write a definition straight to the served `translations` table (the
    ai_ok path, or a reviewer's approval). Upserts on (vocabulary_id, locale).
    Returns True when a definition was written."""
    text = (definition or "").strip()
    if not text:
        return False
    await conn.execute(
        """
        INSERT INTO translations (vocabulary_id, locale, definition)
        VALUES ($1, $2, $3)
        ON CONFLICT (vocabulary_id, locale)
            DO UPDATE SET definition = EXCLUDED.definition
        """,
        vocabulary_id, locale, text,
    )
    return True


async def queue_definition_review(
    conn: asyncpg.Connection, vocabulary_id: str, locale: str,
    proposed: str, reason: str,
) -> bool:
    """Queue an AI definition for a human (the gated path): reviewers approve it
    into `translations` via resolve_translation_review. Upserts the pending row
    on (vocabulary_id, locale). Returns True."""
    await conn.execute(
        """
        INSERT INTO translation_reviews (vocabulary_id, locale, proposed, reason, status)
        VALUES ($1, $2, $3, $4, 'pending')
        ON CONFLICT (vocabulary_id, locale) DO UPDATE SET
            proposed = EXCLUDED.proposed, reason = EXCLUDED.reason,
            status = 'pending', created_at = now()
        """,
        vocabulary_id, locale, (proposed or "").strip() or None, (reason or "")[:2000],
    )
    return True


async def list_translation_reviews(
    conn: asyncpg.Connection, status_filter: str = "pending",
    language_id: str | None = None,
) -> list[dict]:
    """Pending AI-translation rejects, with the card's word + current gloss.
    language_id scopes the queue to one course — the Review workspace shows
    the working language's pile, not every language's at once."""
    rows = await conn.fetch(
        """
        SELECT r.id, r.locale, r.proposed, r.reason, r.status, r.created_at,
               v.word,
               (SELECT definition FROM translations t
                 WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                   AS current_definition
        FROM translation_reviews r
        JOIN vocabulary v ON r.vocabulary_id = v.id
        WHERE r.status = $1
          AND ($2::uuid IS NULL OR v.language_id = $2)
        ORDER BY r.locale, r.created_at
        LIMIT 200
        """,
        status_filter, language_id,
    )
    return [
        {
            "id": str(r["id"]), "locale": r["locale"], "word": r["word"],
            "proposed": r["proposed"], "reason": r["reason"],
            "current_definition": r["current_definition"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def resolve_translation_review(
    conn: asyncpg.Connection, review_id: str, approve: bool
) -> str:
    """Approve (apply the proposed gloss to its real locale) or reject.

    'en-hint' rows are flagged ENGLISH definitions, so they apply to 'en';
    every other row applies to its own support locale. Returns
    'ok' | 'not_found' | 'not_pending' | 'empty'.
    """
    r = await conn.fetchrow(
        "SELECT id, vocabulary_id, locale, proposed, status "
        "FROM translation_reviews WHERE id = $1",
        review_id,
    )
    if not r:
        return "not_found"
    if r["status"] != "pending":
        return "not_pending"
    if approve:
        proposed = (r["proposed"] or "").strip()
        if not proposed:
            return "empty"
        target = "en" if r["locale"] == "en-hint" else r["locale"]
        await conn.execute(
            """
            INSERT INTO translations (vocabulary_id, locale, definition)
            VALUES ($1, $2, $3)
            ON CONFLICT (vocabulary_id, locale)
                DO UPDATE SET definition = EXCLUDED.definition
            """,
            r["vocabulary_id"], target, proposed,
        )
    await conn.execute(
        "UPDATE translation_reviews SET status = $2 WHERE id = $1",
        review_id, "approved" if approve else "rejected",
    )
    return "ok"


async def admin_engagement(conn: asyncpg.Connection, days: int = 30) -> dict:
    """App-wide engagement snapshot for the admin panel (privileged conn).

    Answers "who is using the app, doing what, for how long" from the
    activity tables already written by normal use — review_log (reviews +
    per-answer time), tutor_usage (tutor messages), readings (Reader
    sessions), user_cards (cards started). No new tracking: this is a read
    over existing data. All users, all languages.
    """
    since_expr = f"now() - interval '{int(days)} days'"

    totals = await conn.fetchrow(
        f"""
        SELECT
          (SELECT count(*) FROM user_profiles) AS total_users,
          (SELECT count(*) FROM user_profiles
             WHERE created_at > {since_expr}) AS new_users,
          (SELECT count(*) FROM review_log
             WHERE created_at > {since_expr}) AS reviews,
          (SELECT COALESCE(sum(time_taken_ms), 0) FROM review_log
             WHERE created_at > {since_expr}) AS review_ms,
          (SELECT count(*) FROM tutor_usage
             WHERE created_at > {since_expr}) AS tutor_messages,
          (SELECT count(*) FROM readings
             WHERE created_at > {since_expr}) AS readings,
          (SELECT count(*) FROM user_cards
             WHERE created_at > {since_expr}) AS cards_started
        """
    )

    # Active users per window: anyone with ANY activity (review / tutor /
    # reading / new card) in the window.
    active = await conn.fetchrow(
        """
        SELECT
          count(DISTINCT u) FILTER (WHERE t > now() - interval '1 day')  AS d1,
          count(DISTINCT u) FILTER (WHERE t > now() - interval '7 days')  AS d7,
          count(DISTINCT u) FILTER (WHERE t > now() - interval '30 days') AS d30
        FROM (
          SELECT user_id AS u, created_at AS t FROM review_log
          UNION ALL SELECT user_id, created_at FROM tutor_usage
          UNION ALL SELECT user_id, created_at FROM readings
          UNION ALL SELECT user_id, created_at FROM user_cards
        ) acts
        """
    )

    # Distinct users who touched each feature in the window — which features
    # are actually pulling their weight.
    feature_users = await conn.fetchrow(
        f"""
        SELECT
          (SELECT count(DISTINCT user_id) FROM review_log
             WHERE created_at > {since_expr}) AS review_users,
          (SELECT count(DISTINCT user_id) FROM tutor_usage
             WHERE created_at > {since_expr}) AS tutor_users,
          (SELECT count(DISTINCT user_id) FROM readings
             WHERE created_at > {since_expr}) AS reader_users
        """
    )

    # Which languages people are actually studying (by active cards).
    top_langs = await conn.fetch(
        """
        SELECT l.code, l.name, count(DISTINCT uc.user_id) AS learners,
               count(*) AS cards
        FROM user_cards uc JOIN languages l ON uc.language_id = l.id
        GROUP BY l.code, l.name
        ORDER BY learners DESC, cards DESC
        LIMIT 8
        """
    )

    review_ms = int(totals["review_ms"] or 0)
    return {
        "days": days,
        "total_users": totals["total_users"],
        "new_users": totals["new_users"],
        "active_users": {
            "d1": active["d1"], "d7": active["d7"], "d30": active["d30"],
        },
        "reviews": totals["reviews"],
        "review_hours": round(review_ms / 3_600_000, 1),
        "tutor_messages": totals["tutor_messages"],
        "readings": totals["readings"],
        "cards_started": totals["cards_started"],
        "feature_users": {
            "review": feature_users["review_users"],
            "tutor": feature_users["tutor_users"],
            "reader": feature_users["reader_users"],
        },
        "top_languages": [
            {"code": r["code"], "name": r["name"],
             "learners": r["learners"], "cards": r["cards"]}
            for r in top_langs
        ],
    }


# ---------------------------------------------------------------------------
# Morphology chart backfill (-k forms, WP45 track 3): the work-list of drill
# answers and the vocabulary upsert the generated charts land in.
# ---------------------------------------------------------------------------


async def drill_answers_for_charts(
    conn: asyncpg.Connection, language_id: str
) -> list[dict]:
    """Every distinct drill answer in a language, with the context the chart
    maker needs (stored lemma, hint, sentence, point title). Filtering down to
    the answers that resolve to NO chart happens in the service — it needs the
    reverse form index the Gym's lookup uses."""
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (lower(ds.answer))
               ds.answer, ds.lemma, ds.hint, ds.sentence,
               gp.title AS point_title
        FROM drill_sentences ds
        JOIN grammar_points gp ON ds.grammar_point_id = gp.id
        WHERE gp.language_id = $1
          AND ds.answer IS NOT NULL AND btrim(ds.answer) <> ''
          AND ds.flagged = false
        ORDER BY lower(ds.answer), ds.created_at
        """,
        language_id,
    )
    return [dict(r) for r in rows]


async def upsert_vocabulary_charts(
    conn: asyncpg.Connection,
    language_id: str,
    word: str,
    part_of_speech: str | None,
    charts: list[dict],
    usage_note: str | None,
    origin_detail: str | None = None,
) -> tuple[str | None, str]:
    """Attach generated charts to *word*'s vocabulary row, creating the row if
    the word isn't in vocabulary at all (the dominant chart-coverage gap).

    NEVER overwrites existing charts — a row that already carries chart tables
    (the offline kaikki build) stays authoritative, and re-running the
    generator is a no-op for it. Returns (vocabulary_id, status) with status
    'created' | 'updated' | 'skipped'.
    """
    row = await conn.fetchrow(
        """
        SELECT id, morphology, usage_note FROM vocabulary
        WHERE language_id = $1 AND lower(word) = lower($2)
        LIMIT 1
        """,
        language_id, word,
    )
    titles = [c.get("title") for c in charts]
    if row is None:
        vid = await conn.fetchval(
            """
            INSERT INTO vocabulary
                (language_id, word, part_of_speech, morphology, usage_note)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            ON CONFLICT (language_id, word) DO NOTHING
            RETURNING id
            """,
            language_id, word, part_of_speech,
            json.dumps({"charts": charts}), usage_note,
        )
        if vid is None:  # raced an identical insert — treat as already done
            return None, "skipped"
        await log_change(
            conn, entity_type="vocabulary", entity_id=str(vid),
            action="charts_generated", language_id=language_id,
            after={"word": word, "charts": titles},
            note=origin_detail,
        )
        return str(vid), "created"

    morph = row["morphology"]
    if isinstance(morph, str):
        try:
            morph = json.loads(morph)
        except (json.JSONDecodeError, TypeError):
            morph = {}
    if not isinstance(morph, dict):
        morph = {}
    if morph.get("charts"):
        return str(row["id"]), "skipped"
    merged = {**morph, "charts": charts}
    await conn.execute(
        """
        UPDATE vocabulary
        SET morphology = $2::jsonb,
            usage_note = COALESCE(usage_note, $3)
        WHERE id = $1
        """,
        row["id"], json.dumps(merged), usage_note,
    )
    await log_change(
        conn, entity_type="vocabulary", entity_id=str(row["id"]),
        action="charts_generated", language_id=language_id,
        after={"word": word, "charts": titles},
        note=origin_detail,
    )
    return str(row["id"]), "updated"


async def count_unchecked_points(
    conn: asyncpg.Connection, language_id: str
) -> int:
    """Points invisible under 'ai_ok' policy: unreviewed AND never AI-checked.

    This is the number the admin panel must show — the owner flipped the
    policy to Open, saw nothing appear, and had no way to learn that the
    other half of the visibility gate (a stored check verdict) was empty.
    """
    return await conn.fetchval(
        """
        SELECT count(*) FROM grammar_points
        WHERE language_id = $1
          AND reviewed = false
          AND ai_check_status IS NULL
        """,
        language_id,
    ) or 0


async def list_unchecked_point_ids(
    conn: asyncpg.Connection, language_id: str, limit: int
) -> list[str]:
    """The next batch for the bulk AI check, in curriculum order so the
    early levels light up first while the tail is still being checked."""
    rows = await conn.fetch(
        """
        SELECT id FROM grammar_points
        WHERE language_id = $1
          AND reviewed = false
          AND ai_check_status IS NULL
        ORDER BY level ASC NULLS LAST, display_order ASC
        LIMIT $2
        """,
        language_id, limit,
    )
    return [str(r["id"]) for r in rows]


async def count_unchecked_vocab(
    conn: asyncpg.Connection, language_id: str
) -> int:
    """Vocabulary carrying no quality verdict yet: unreviewed AND unchecked.

    NOT a visibility count, unlike its grammar twin. The publish gate
    (`reviewed OR ai_check_status = 'pass'`) applies to grammar points only —
    every such clause in repositories/cards.py is `gp.`, never `v.`. What
    gates a word is `level_source <> 'ai' OR policy IN ('ai_ok','all')`.

    This is the size of the un-audited backlog: how many words no one and
    nothing has judged, which is what the bulk checker works through.
    """
    return await conn.fetchval(
        """
        SELECT count(*) FROM vocabulary
        WHERE language_id = $1
          AND reviewed = false
          AND ai_check_status IS NULL
        """,
        language_id,
    ) or 0


async def list_unchecked_vocab_ids(
    conn: asyncpg.Connection, language_id: str, limit: int, level: str | None = None
) -> list[str]:
    """The next batch for the bulk vocabulary AI check.

    Frequency order within level, and levels in order, so the words a
    beginner meets first become visible first while the C1/C2 tail is still
    being checked — a run over ten thousand words is long enough that the
    ordering is the difference between "usable after a minute" and "usable
    when it finishes". *level* narrows to one CEFR band.
    """
    rows = await conn.fetch(
        """
        SELECT id FROM vocabulary
        WHERE language_id = $1
          AND reviewed = false
          AND ai_check_status IS NULL
          AND ($3::text IS NULL OR level = $3)
        ORDER BY level ASC NULLS LAST, frequency_rank ASC NULLS LAST
        LIMIT $2
        """,
        language_id, limit, level,
    )
    return [str(r["id"]) for r in rows]
