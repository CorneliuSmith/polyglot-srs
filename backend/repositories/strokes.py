"""The stroke library: glyph forms and exemplar sentences (migration
20261020, owner-applied, probed everywhere). Writes run on a privileged
connection — the tables have read policies only — behind the language
roles the contributor router checks."""
from __future__ import annotations

import json

import asyncpg

from backend.services.auto_translate import table_present
from backend.services.scripts import alphabet_for, expected_forms, styles_of

MAX_STROKES = 60
MAX_POINTS = 200
BOX = 1000


def _loads(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def clean_strokes(strokes) -> list[list[list[int]]]:
    """Strokes as the library stores them: integer [x, y] pairs inside the
    1000×1000 box, at most MAX_STROKES strokes of MAX_POINTS points. Raises
    ValueError on anything that is not strokes — an author's save should
    fail loudly, unlike a learner's Check."""
    if not isinstance(strokes, list) or not strokes:
        raise ValueError("strokes must be a non-empty list")
    out = []
    for stroke in strokes[:MAX_STROKES]:
        pts = []
        for p in (stroke or [])[:MAX_POINTS]:
            try:
                x, y = (p["x"], p["y"]) if isinstance(p, dict) else (p[0], p[1])
                x, y = int(round(float(x))), int(round(float(y)))
            except (TypeError, ValueError, IndexError, KeyError) as exc:
                raise ValueError("a point must be [x, y]") from exc
            pts.append([max(0, min(BOX, x)), max(0, min(BOX, y))])
        if len(pts) >= 2:
            out.append(pts)
    if not out:
        raise ValueError("no stroke has two points")
    return out


async def _present(conn) -> bool:
    return await table_present(conn, "script_glyphs")


def _row(r) -> dict:
    return {
        "id": str(r["id"]), "script": r["script"], "glyph": r["glyph"],
        "form": r["form"], "style": r["style"],
        "strokes": _loads(r["strokes"], []), "joins": _loads(r["joins"], {}),
        "hints": _loads(r["hints"], []), "source": r["source"],
        "reviewed": bool(r["reviewed"]),
    }


async def list_glyphs(conn: asyncpg.Connection, script: str, style: str | None,
                      *, reviewed_only: bool) -> list[dict]:
    if not await _present(conn):
        return []
    rows = await conn.fetch(
        """SELECT id, script, glyph, form, style, strokes, joins, hints, source, reviewed
             FROM script_glyphs
            WHERE script = $1 AND ($2::text IS NULL OR style = $2)
              AND (NOT $3::boolean OR reviewed)
            ORDER BY style, glyph, form""",
        script, style, reviewed_only)
    return [_row(r) for r in rows]


async def upsert_glyph(conn: asyncpg.Connection, *, script: str, glyph: str,
                       form: str, style: str, strokes, joins: dict | None,
                       hints: list | None, user_id: str | None,
                       source: str = "workshop", reviewed: bool | None = None) -> dict | None:
    """Save one form. A re-save of a reviewed form drops it back to draft
    unless the caller says otherwise: content is never self-certified."""
    if not await _present(conn):
        return None
    st = clean_strokes(strokes)
    hints = [str(h or "")[:120] for h in (hints or [])][:MAX_STROKES]
    joins = joins if isinstance(joins, dict) else {}
    row = await conn.fetchrow(
        """INSERT INTO script_glyphs
               (script, glyph, form, style, strokes, joins, hints, source, reviewed,
                created_by, updated_at)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8,
                   COALESCE($9::boolean, false), $10, now())
           ON CONFLICT (script, glyph, form, style) DO UPDATE SET
               strokes = EXCLUDED.strokes, joins = EXCLUDED.joins,
               hints = EXCLUDED.hints, source = EXCLUDED.source,
               reviewed = COALESCE($9::boolean, false),
               created_by = COALESCE(EXCLUDED.created_by, script_glyphs.created_by),
               updated_at = now()
           RETURNING id, script, glyph, form, style, strokes, joins, hints, source, reviewed""",
        script, glyph, form, style, json.dumps(st), json.dumps(joins),
        json.dumps(hints), source, reviewed, user_id)
    return _row(row)


async def set_glyph_reviewed(conn: asyncpg.Connection, glyph_id: str, reviewed: bool) -> bool:
    if not await _present(conn):
        return False
    status = await conn.execute(
        "UPDATE script_glyphs SET reviewed = $2, updated_at = now() WHERE id = $1",
        glyph_id, reviewed)
    return status.endswith("1")


async def delete_glyph(conn: asyncpg.Connection, glyph_id: str) -> bool:
    if not await _present(conn):
        return False
    status = await conn.execute("DELETE FROM script_glyphs WHERE id = $1", glyph_id)
    return status.endswith("1")


async def list_exemplars(conn: asyncpg.Connection, script: str, style: str | None,
                         *, reviewed_only: bool) -> list[dict]:
    if not await table_present(conn, "script_exemplars"):
        return []
    rows = await conn.fetch(
        """SELECT id, script, language_code, style, text, strokes, source, reviewed
             FROM script_exemplars
            WHERE script = $1 AND ($2::text IS NULL OR style = $2)
              AND (NOT $3::boolean OR reviewed)
            ORDER BY created_at""",
        script, style, reviewed_only)
    return [{"id": str(r["id"]), "script": r["script"],
             "language_code": r["language_code"], "style": r["style"],
             "text": r["text"], "strokes": _loads(r["strokes"], []),
             "source": r["source"], "reviewed": bool(r["reviewed"])} for r in rows]


async def add_exemplar(conn: asyncpg.Connection, *, script: str, language_code: str,
                       style: str, text: str, strokes, user_id: str | None,
                       source: str = "workshop", reviewed: bool = False) -> dict | None:
    if not await table_present(conn, "script_exemplars"):
        return None
    st = clean_strokes(strokes)
    row = await conn.fetchrow(
        """INSERT INTO script_exemplars
               (script, language_code, style, text, strokes, source, reviewed, created_by)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8)
           RETURNING id, script, language_code, style, text, strokes, source, reviewed""",
        script, language_code, style, text.strip(), json.dumps(st), source, reviewed, user_id)
    return {"id": str(row["id"]), "script": row["script"],
            "language_code": row["language_code"], "style": row["style"],
            "text": row["text"], "strokes": st, "source": row["source"],
            "reviewed": bool(row["reviewed"])}


async def set_exemplar_reviewed(conn: asyncpg.Connection, exemplar_id: str, reviewed: bool) -> bool:
    if not await table_present(conn, "script_exemplars"):
        return False
    status = await conn.execute(
        "UPDATE script_exemplars SET reviewed = $2 WHERE id = $1", exemplar_id, reviewed)
    return status.endswith("1")


async def delete_exemplar(conn: asyncpg.Connection, exemplar_id: str) -> bool:
    if not await table_present(conn, "script_exemplars"):
        return False
    status = await conn.execute("DELETE FROM script_exemplars WHERE id = $1", exemplar_id)
    return status.endswith("1")


async def manifest(conn: asyncpg.Connection, code: str, script: str) -> dict:
    """Per style: how many of the course's (glyph, form) pairs are authored
    and reviewed, plus exemplar counts. What the Write page keys the guided
    Letters mode on: a style is live when every form is reviewed... or,
    more usefully, when ANY is — the Letters strip simply skips the rest."""
    expected = expected_forms(code)
    out = {"script": script, "styles": {}, "expected_forms": expected,
           "available": await _present(conn)}
    for style in styles_of(script):
        entry = {"authored": 0, "reviewed": 0, "exemplars": 0, "exemplars_reviewed": 0}
        if out["available"]:
            row = await conn.fetchrow(
                """SELECT count(*) AS a, count(*) FILTER (WHERE reviewed) AS r
                     FROM script_glyphs WHERE script = $1 AND style = $2""",
                script, style)
            entry["authored"], entry["reviewed"] = int(row["a"]), int(row["r"])
            if await table_present(conn, "script_exemplars"):
                row = await conn.fetchrow(
                    """SELECT count(*) AS a, count(*) FILTER (WHERE reviewed) AS r
                         FROM script_exemplars WHERE script = $1 AND style = $2""",
                    script, style)
                entry["exemplars"], entry["exemplars_reviewed"] = int(row["a"]), int(row["r"])
        out["styles"][style] = entry
    out["alphabet_size"] = len(alphabet_for(code))
    return out
