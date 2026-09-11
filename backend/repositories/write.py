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
from backend.services.ink_method import compact, summarize_method
from backend.services.write_coverage import pick_coverage
from backend.services.write_diff import misread_letters, same_text

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


# ---------------------------------------------------------------------------
# The hand profile (docs/plans/handwriting.md, §11): what the reader is
# told about THIS writer, and the samples it is shown. Everything here is
# probed — migration 20261019 is owner-applied — and everything degrades
# to "no references, nothing kept", which is exactly Phase 1.
# ---------------------------------------------------------------------------

SAMPLE_CAP = 12
REFERENCE_LIMIT = 3
HABIT_CAP = 20


async def _hand_tables(conn: asyncpg.Connection) -> bool:
    return (await table_present(conn, "writing_settings")
            and await table_present(conn, "writing_profiles")
            and await table_present(conn, "writing_samples"))


async def adapt_enabled(conn: asyncpg.Connection, user_id: str) -> bool:
    """The account toggle. On by default; off without the tables, since
    there is nowhere to keep anything."""
    if not await _hand_tables(conn):
        return False
    row = await conn.fetchval(
        "SELECT adapt FROM writing_settings WHERE user_id = $1", user_id)
    return True if row is None else bool(row)


async def set_adapt(conn: asyncpg.Connection, user_id: str, adapt: bool) -> None:
    """Flip the toggle. OFF deletes every sample and every habit the
    reader had — the promise under the switch is 'turn it off and they
    are deleted', not 'paused'."""
    if not await _hand_tables(conn):
        return
    await conn.execute(
        """INSERT INTO writing_settings (user_id, adapt, updated_at)
           VALUES ($1, $2, now())
           ON CONFLICT (user_id) DO UPDATE
             SET adapt = EXCLUDED.adapt, updated_at = now()""",
        user_id, adapt)
    if not adapt:
        await reset_hand(conn, user_id, None)


async def reset_hand(conn: asyncpg.Connection, user_id: str,
                     language_id: str | None) -> None:
    """Forget what the reader learned — for one language, or all."""
    if not await _hand_tables(conn):
        return
    if language_id:
        await conn.execute(
            "DELETE FROM writing_samples WHERE user_id = $1 AND language_id = $2",
            user_id, language_id)
        await conn.execute(
            "DELETE FROM writing_profiles WHERE user_id = $1 AND language_id = $2",
            user_id, language_id)
    else:
        await conn.execute("DELETE FROM writing_samples WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM writing_profiles WHERE user_id = $1", user_id)


async def hand_profile(conn: asyncpg.Connection, user_id: str,
                       language_id: str) -> dict:
    """What the Account page and the Write page show: the toggle, the
    habits, the counts. `available` is false without the migration."""
    if not await _hand_tables(conn):
        return {"available": False, "adapt": False, "habits": [],
                "stats": {}, "samples": 0, "confirmed": 0}
    adapt = await adapt_enabled(conn, user_id)
    prof = await conn.fetchrow(
        "SELECT habits, stats FROM writing_profiles "
        "WHERE user_id = $1 AND language_id = $2", user_id, language_id)
    counts = await conn.fetchrow(
        """SELECT count(*) AS n, count(*) FILTER (WHERE confirmed) AS c
             FROM writing_samples WHERE user_id = $1 AND language_id = $2""",
        user_id, language_id)
    habits = _loads(prof["habits"], []) if prof else []
    stats = _loads(prof["stats"], {}) if prof else {}
    return {"available": True, "adapt": adapt, "habits": habits,
            "stats": stats, "samples": int(counts["n"] if counts else 0),
            "confirmed": int(counts["c"] if counts else 0),
            "readout": readout(stats)}


def readout(stats: dict) -> dict:
    """The accuracy line and the letters to watch, from the stats: how
    often the reader got this hand right by the writer's own verdict, and
    which letters it trips on most. Right = the writer said yes, or the
    read matched the expected text with high confidence; wrong = the
    writer corrected it. A profile with no verdicts reads 0 of 0."""
    right = int(stats.get("right", 0))
    wrong = int(stats.get("wrong", 0))
    misread = stats.get("misread_letters") or {}
    watch = sorted(misread.items(), key=lambda kv: (-int(kv[1]), kv[0]))[:5]
    return {"right": right, "wrong": wrong, "total": right + wrong,
            "letters_to_watch": [{"letter": k, "count": int(v)} for k, v in watch],
            "legibility_mean": stats.get("legibility_mean"),
            "history": stats.get("history") or []}


def _loads(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


async def reference_samples(conn: asyncpg.Connection, user_id: str,
                            language_id: str,
                            limit: int = REFERENCE_LIMIT) -> list[dict]:
    """The samples shown to the reader: confirmed first, newest first."""
    if not await _hand_tables(conn):
        return []
    # Confirmed first, the baseline's among those first: eight sentences
    # chosen to show every letter beat a lucky match on one word.
    rows = await conn.fetch(
        """SELECT text, image, method FROM writing_samples
            WHERE user_id = $1 AND language_id = $2
            ORDER BY confirmed DESC, (source = 'baseline') DESC, created_at DESC
            LIMIT $3""",
        user_id, language_id, limit)
    return [{"text": r["text"], "image": bytes(r["image"]),
             "method": _loads(r["method"], {})} for r in rows]


async def keep_sample(conn: asyncpg.Connection, user_id: str, language_id: str,
                      text: str, image: bytes, confirmed: bool,
                      strokes=None, source: str = "check") -> int:
    """Keep one sample — the picture, the text, and HOW it was made (the
    compacted strokes and their method summary) — then trim to the cap,
    unconfirmed oldest first, so a writer's own confirmations are the last
    thing to go. Returns the number kept for the language."""
    if not await _hand_tables(conn):
        return 0
    st = compact(strokes) if strokes else []
    await conn.execute(
        """INSERT INTO writing_samples
               (user_id, language_id, text, image, strokes, method, confirmed, source)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8)""",
        user_id, language_id, text, image,
        json.dumps(st) if st else None, json.dumps(summarize_method(st)),
        confirmed, source if source in ("check", "confirm", "baseline") else "check")
    await conn.execute(
        """DELETE FROM writing_samples WHERE id IN (
             SELECT id FROM writing_samples
              WHERE user_id = $1 AND language_id = $2
              ORDER BY confirmed DESC, (source = 'baseline') DESC, created_at DESC
             OFFSET $3)""",
        user_id, language_id, SAMPLE_CAP)
    return int(await conn.fetchval(
        "SELECT count(*) FROM writing_samples WHERE user_id = $1 AND language_id = $2",
        user_id, language_id) or 0)


async def note_habits(conn: asyncpg.Connection, user_id: str, language_id: str,
                      notes: list[dict], *, confirmed_ok: bool,
                      legibility: int | None = None) -> list[dict]:
    """Merge letterform notes into the hand's habits. A note the reader
    made counts once more against its letter; a form the writer confirmed
    is marked known-fine and is never flagged again. Capped by count so
    the profile stays a list of habits, not a log."""
    if not await _hand_tables(conn):
        return []
    row = await conn.fetchrow(
        "SELECT habits, stats FROM writing_profiles "
        "WHERE user_id = $1 AND language_id = $2", user_id, language_id)
    habits: list[dict] = _loads(row["habits"], []) if row else []
    stats: dict = _loads(row["stats"], {}) if row else {}
    by_letter = {h.get("letter"): h for h in habits if isinstance(h, dict)}
    for n in notes:
        letter = str(n.get("letter") or "").strip()
        if not letter:
            continue
        h = by_letter.get(letter)
        if h is None:
            h = {"letter": letter, "note": "", "count": 0, "confirmed_ok": False}
            by_letter[letter] = h
        h["count"] = int(h.get("count", 0)) + 1
        note = str(n.get("note") or "").strip()
        if note:
            h["note"] = note
        if confirmed_ok:
            h["confirmed_ok"] = True
    merged = sorted(by_letter.values(),
                    key=lambda h: (-int(h.get("confirmed_ok", False)),
                                   -int(h.get("count", 0))))[:HABIT_CAP]
    if legibility is not None:
        n = int(stats.get("n", 0))
        mean = float(stats.get("legibility_mean", 0.0))
        stats["n"] = n + 1
        stats["legibility_mean"] = round((mean * n + legibility) / (n + 1), 2)
        # A short trend for the Progress page: the last thirty checks'
        # legibility, oldest first.
        stats["history"] = (list(stats.get("history") or []) + [legibility])[-30:]
    await _save_profile(conn, user_id, language_id, merged, stats)
    return merged


async def _save_profile(conn, user_id, language_id, habits, stats) -> None:
    await conn.execute(
        """INSERT INTO writing_profiles (user_id, language_id, habits, stats, updated_at)
           VALUES ($1, $2, $3::jsonb, $4::jsonb, now())
           ON CONFLICT (user_id, language_id) DO UPDATE
             SET habits = EXCLUDED.habits, stats = EXCLUDED.stats,
                 updated_at = now()""",
        user_id, language_id, json.dumps(habits), json.dumps(stats))


def habit_counts(habits: list[dict], letters: list[str]) -> dict[str, int]:
    """How many times each of *letters* has been noted before — what lets
    the Write page say "your д again — third time" instead of discovering
    it afresh (§11, mechanism 3)."""
    by = {h.get("letter"): int(h.get("count", 0)) for h in habits if isinstance(h, dict)}
    return {x: by[x] for x in letters if x in by and by[x] > 1}


async def record_verdict(conn: asyncpg.Connection, user_id: str, language_id: str,
                         *, read: str, wrote: str) -> dict:
    """The writer's verdict on a reading — the ground truth (§12.1).
    Same text → the reader was right; different → wrong, and every
    misread unit counts against the letter the writer actually wrote.
    Returns {right: bool, misread: [{wrote, read}], readout}."""
    if not await _hand_tables(conn):
        return {"right": same_text(read, wrote), "misread": [], "readout": readout({})}
    row = await conn.fetchrow(
        "SELECT habits, stats FROM writing_profiles "
        "WHERE user_id = $1 AND language_id = $2", user_id, language_id)
    habits = _loads(row["habits"], []) if row else []
    stats = _loads(row["stats"], {}) if row else {}
    right = same_text(read, wrote)
    misread = [] if right else misread_letters(read, wrote)
    if right:
        stats["right"] = int(stats.get("right", 0)) + 1
    else:
        stats["wrong"] = int(stats.get("wrong", 0)) + 1
        counts = dict(stats.get("misread_letters") or {})
        for m in misread:
            letter = m["wrote"] or m["read"]
            if letter:
                counts[letter] = int(counts.get(letter, 0)) + 1
        # Bounded: the twenty letters it trips on most.
        stats["misread_letters"] = dict(
            sorted(counts.items(), key=lambda kv: -kv[1])[:20])
    await _save_profile(conn, user_id, language_id, habits, stats)
    return {"right": right, "misread": misread, "readout": readout(stats)}


async def admin_hand_accuracy(conn: asyncpg.Connection) -> list[dict]:
    """Per course: how many writers the reader has a profile for, and how
    often it gets their hands right by their own verdicts — the staff
    signal for which scripts the reader is weak on (§12.1). Privileged
    connection: profiles are own-only under RLS."""
    if not await table_present(conn, "writing_profiles"):
        return []
    rows = await conn.fetch(
        """SELECT l.code, l.name, count(*) AS writers,
                  coalesce(sum((p.stats->>'right')::int), 0) AS right,
                  coalesce(sum((p.stats->>'wrong')::int), 0) AS wrong,
                  coalesce(avg((p.stats->>'legibility_mean')::float), 0) AS legibility,
                  json_agg(p.stats->'misread_letters') AS misread
             FROM writing_profiles p JOIN languages l ON l.id = p.language_id
            GROUP BY l.code, l.name ORDER BY count(*) DESC, l.name""")
    out = []
    for r in rows:
        totals: dict[str, int] = {}
        for m in _loads(r["misread"], []) or []:
            for k, v in (m or {}).items():
                totals[k] = totals.get(k, 0) + int(v)
        watch = sorted(totals.items(), key=lambda kv: -kv[1])[:5]
        right, wrong = int(r["right"]), int(r["wrong"])
        out.append({
            "code": r["code"], "language": r["name"], "writers": int(r["writers"]),
            "right": right, "wrong": wrong,
            "accuracy": round(right / (right + wrong), 2) if right + wrong else None,
            "legibility_mean": round(float(r["legibility"]), 2) if r["legibility"] else None,
            "letters_to_watch": [{"letter": k, "count": v} for k, v in watch],
        })
    return out


def known_forms(habits: list[dict]) -> list[str]:
    """The habits the reader is told not to flag: the ones the writer has
    confirmed legible, as 'letter — note' lines."""
    out = []
    for h in habits:
        if isinstance(h, dict) and h.get("confirmed_ok") and h.get("letter"):
            note = str(h.get("note") or "").strip()
            out.append(f"{h['letter']}" + (f" — {note}" if note else ""))
    return out


# ---------------------------------------------------------------------------
# The baseline session (§12.2): eight sentences that show every letter in
# every form, each confirmed by the writer.
# ---------------------------------------------------------------------------

BASELINE_POOL = 400


async def baseline_prompts(
    conn: asyncpg.Connection, user_id: str, language_id: str,
    code: str, locale: str | None,
) -> dict:
    """The eight prompts for a baseline in this course: a greedy coverage
    pick over the course's served beginner sentences (own cards or not —
    a baseline is about the hand, not the syllabus), with the meaning line
    in the learner's language as the prompt. {items, covered, total}."""
    loc = locale or "en"
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (es.sentence)
               es.sentence AS answer, es.translation AS prompt
          FROM example_sentences es
          JOIN vocabulary v ON v.id = es.vocabulary_id
         WHERE es.language_id = $1
           AND es.translation_locale IN ($2, 'en')
           AND es.translation IS NOT NULL AND es.translation <> ''
           AND (es.reviewed OR v.language_id IN (
                 SELECT id FROM languages
                  WHERE grammar_review_policy IN ('ai_ok', 'all')))
           AND v.level IN ('A1', 'A2')
           AND length(es.sentence) BETWEEN 6 AND 60
         ORDER BY es.sentence, (es.translation_locale = $2) DESC, es.id
         LIMIT $3
        """,
        language_id, loc, BASELINE_POOL,
    )
    pool = [{"answer": r["answer"], "prompt": r["prompt"]} for r in rows]
    return pick_coverage(code, pool)


async def baseline_state(conn: asyncpg.Connection, user_id: str,
                         language_id: str) -> dict:
    """When this hand's baseline was last set, and whether one may run
    today (one per language per day, so it cannot become unlimited
    spend)."""
    if not await _hand_tables(conn):
        return {"available": False, "allowed": False, "last": None}
    row = await conn.fetchrow(
        "SELECT stats FROM writing_profiles WHERE user_id = $1 AND language_id = $2",
        user_id, language_id)
    stats = _loads(row["stats"], {}) if row else {}
    last = stats.get("baseline_at")
    today = await conn.fetchval("SELECT to_char(now(), 'YYYY-MM-DD')")
    return {"available": True, "allowed": not last or str(last)[:10] != today,
            "last": last}


async def record_baseline(conn: asyncpg.Connection, user_id: str,
                          language_id: str, coverage: dict | None = None) -> dict:
    """The session is done: stamp the profile. The zero point for the
    Progress trend and the personal neatness of Phase D."""
    if not await _hand_tables(conn):
        return {}
    row = await conn.fetchrow(
        "SELECT habits, stats FROM writing_profiles WHERE user_id = $1 AND language_id = $2",
        user_id, language_id)
    habits = _loads(row["habits"], []) if row else []
    stats = _loads(row["stats"], {}) if row else {}
    stats["baseline_at"] = await conn.fetchval("SELECT to_char(now(), 'YYYY-MM-DD\"T\"HH24:MI:SSZ')")
    stats["baselines"] = int(stats.get("baselines", 0)) + 1
    if coverage:
        stats["baseline_coverage"] = {"covered": int(coverage.get("covered", 0)),
                                      "total": int(coverage.get("total", 0))}
    await _save_profile(conn, user_id, language_id, habits, stats)
    return stats

