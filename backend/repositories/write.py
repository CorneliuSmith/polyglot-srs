"""Write — prompts to write, and the attempt log.

Prompts come from content the app already holds, so the feature needs
nothing authored: a sentence is an example or drill line with its meaning
in the learner's support locale (the COALESCE overlay the cards use), a
word is one of the learner's own cards. The attempt log is best-effort and
probed (migration 20261018, owner-applied): a database without the table
records nothing and the assessment still comes back.
"""
from __future__ import annotations

import json
import logging

import asyncpg

from backend.services.auto_translate import table_present

logger = logging.getLogger("write")

MAX_PROMPTS = 20


async def sentence_prompts(
    conn: asyncpg.Connection, user_id: str, language_id: str,
    locale: str | None, limit: int = 10,
) -> list[dict]:
    """Sentences to translate and write: the learner's own cards first
    (their example sentences with a meaning in *locale*, falling back to
    the English line), then reviewed A1/A2 examples of the course. Each
    row: {prompt, answer, source}. The PROMPT is the meaning line in the
    learner's language; the ANSWER is the course-language sentence."""
    loc = locale or "en"
    lim = max(1, min(limit, MAX_PROMPTS))
    rows = await conn.fetch(
        """
        WITH mine AS (
            SELECT uc.card_id, min(uc.next_review) AS due
              FROM user_cards uc
             WHERE uc.user_id = $1 AND uc.language_id = $2
               AND uc.card_type = 'vocabulary' AND uc.is_suspended = false
             GROUP BY uc.card_id
        )
        SELECT DISTINCT ON (es.sentence)
               es.sentence AS answer,
               es.translation AS prompt,
               (m.card_id IS NOT NULL) AS own,
               m.due
          FROM example_sentences es
          JOIN vocabulary v ON v.id = es.vocabulary_id
          LEFT JOIN mine m ON m.card_id = es.vocabulary_id
         WHERE es.language_id = $2
           AND es.translation_locale IN ($3, 'en')
           AND es.translation IS NOT NULL AND es.translation <> ''
           AND (es.reviewed OR v.language_id IN (
                 SELECT id FROM languages
                  WHERE grammar_review_policy IN ('ai_ok', 'all')))
           AND (m.card_id IS NOT NULL OR v.level IN ('A1', 'A2'))
         ORDER BY es.sentence, (es.translation_locale = $3) DESC, es.id
        """,
        user_id, language_id, loc,
    )
    # Own cards first, soonest due first, then the course's beginner lines;
    # a stable shuffle within each group would be nicer but random() inside
    # DISTINCT ON is not — the client shuffles.
    ordered = sorted(rows, key=lambda r: (not r["own"], r["due"] or 0))
    return [
        {"prompt": r["prompt"], "answer": r["answer"],
         "source": "own" if r["own"] else "course"}
        for r in ordered[:lim]
    ]


async def word_prompts(
    conn: asyncpg.Connection, user_id: str, language_id: str,
    locale: str | None, limit: int = 10,
) -> list[dict]:
    """Words to write: the learner's own cards, soonest due first, with the
    gloss in *locale* (falling back to English) as the prompt."""
    loc = locale or "en"
    lim = max(1, min(limit, MAX_PROMPTS))
    rows = await conn.fetch(
        """
        SELECT v.word AS answer,
               COALESCE(t.definition, t_en.definition) AS prompt
          FROM user_cards uc
          JOIN vocabulary v ON v.id = uc.card_id
          LEFT JOIN translations t
                 ON t.vocabulary_id = v.id AND t.locale = $3
          LEFT JOIN translations t_en
                 ON t_en.vocabulary_id = v.id AND t_en.locale = 'en'
         WHERE uc.user_id = $1 AND uc.language_id = $2
           AND uc.card_type = 'vocabulary' AND uc.is_suspended = false
         ORDER BY uc.next_review
         LIMIT $4
        """,
        user_id, language_id, loc, lim,
    )
    return [
        {"prompt": r["prompt"] or "", "answer": r["answer"], "source": "own"}
        for r in rows if r["answer"]
    ]


async def record_attempt(
    conn: asyncpg.Connection, user_id: str, language_id: str,
    kind: str, target: str | None, result: dict,
) -> None:
    """Log one assessed attempt — never the ink. Skipped without the table."""
    try:
        if not await table_present(conn, "writing_attempts"):
            return
        await conn.execute(
            """INSERT INTO writing_attempts
                   (user_id, language_id, kind, target, read_as, matches,
                    legibility, confidence, feedback)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)""",
            user_id, language_id, kind, target, result["transcription"],
            result["matches_target"], result["legibility"],
            result["confidence"],
            json.dumps({"word_diffs": result["word_diffs"],
                        "letterform_notes": result["letterform_notes"]}),
        )
    except Exception as exc:  # noqa: BLE001 — a log line, never the verdict
        logger.debug("writing attempt not recorded: %s", exc)
