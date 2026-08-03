"""Grammar curriculum seeder — loads grammar points + drill sentences.

Reads a per-language curriculum file (data/grammar/{code}_grammar.json) and
populates grammar_points (with explanation, culture note, provenance), their
fill-in-the-blank drill_sentences (sentence + answer + translation + hint),
and a grammar content_list per level so the points are subscribable and
learnable. Re-running updates in place (UPSERT by language + title; drills are
diff-synced by (sentence, answer) — matched rows keep their ids so learners'
gym_progress survives, and human-touched drills are never deleted). A point a
human has curated (approved/edited in the app) is never overwritten: its text
diffs go to the content_suggestions review queue and its new drills land
reviewed=false in the pending-drills queue.

Curriculum file shape:
    {
      "lists":  [{"level": "A1", "title": "...", "description": "..."}],
      "points": [{
        "title": "...", "level": "A1", "display_order": 1,
        "explanation": "...", "culture_note": "",
        "source": "contributor", "reviewed": true,
        "drills": [{"sentence": "... {{answer}} ...", "answer": "...",
                    "translation": "...", "hint": "...", "display_order": 1}]
      }]
    }

Companion hint-translation files (WP17), one per locale
(data/grammar/{code}_drill_hints.{locale}.json), carry the drill
hint/translation in a learner's support language:
    {
      "locale": "es", "reviewed": false,
      "points": {"<point title>": {"<drill sentence>": {
          "hint": "...", "translation": "..."}}}
    }
Entries are keyed by the drill's exact sentence — the stable natural key
(drill ids now survive a reseed, but the sentence key stays the contract). A
key that no longer matches a drill fails the seed loudly: it means the
drill was reworded and the translation needs re-drafting, not silent loss.

CLI:
    python -m backend.services.seeder.seed_grammar --language ru
    python -m backend.services.seeder.seed_grammar --language all
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re

import asyncpg

from backend.services.references import clean_references, clean_related

from .base import DATA_DIR

GRAMMAR_DIR = DATA_DIR / "grammar"

logger = logging.getLogger("seed_grammar")

VALID_SOURCES = {"contributor", "ai", "wiktionary", "pending"}


def plan_drill_sync(
    existing: list[dict], incoming: list[dict], *, protect: bool = False
) -> dict:
    """Decide how a point's live drills change on re-seed. Pure, so the policy
    is testable without a DB.

    *existing*: live rows (dicts with id, sentence, answer, source, is_modified,
    flagged). *incoming*: the seed file's drill dicts. Matching is by the
    natural key (sentence, answer) — the same key the hint-translation files
    rely on.

    Returns {"update": [(row, drill)], "insert": [drill], "delete": [row]}.

    Normal mode: matches update IN PLACE (the row id — and with it each
    learner's gym_progress — survives), new drills insert, and only stale rows
    that are pure untouched seed content (source='seed', not human-modified,
    not flagged) are deleted. A human-added, human-edited, flagged, or
    pending-'ai' drill is never deleted by a re-seed.

    Protect mode (curated point): additive only — genuinely new drills are
    returned to insert (the caller lands them reviewed=false for the pending
    queue); nothing is updated or deleted.
    """
    # Dedupe incoming by key (a merged multi-chunk extraction can repeat one).
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for d in incoming:
        key = (d["sentence"], d["answer"])
        if key not in seen:
            seen.add(key)
            deduped.append(d)

    by_key = {(r["sentence"], r["answer"]): r for r in existing}
    plan: dict = {"update": [], "insert": [], "delete": []}
    for d in deduped:
        row = by_key.get((d["sentence"], d["answer"]))
        if row is None:
            plan["insert"].append(d)
        elif not protect:
            plan["update"].append((row, d))
    if not protect:
        incoming_keys = {(d["sentence"], d["answer"]) for d in deduped}
        plan["delete"] = [
            r for (k, r) in by_key.items()
            if k not in incoming_keys
            and r.get("source") == "seed"
            and not r.get("is_modified")
            and not r.get("flagged")
        ]
    return plan


def _clean_prerequisites(raw) -> list[str]:
    """Sanitize the authored `prerequisites` list — titles of points that must
    be learned first. Resolved to grammar_point ids at load time; a title that
    doesn't resolve is simply dropped (same tolerance as `related`)."""
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        title = str(t or "").strip()
        if title and title not in seen:
            seen.add(title)
            out.append(title)
    return out


class GrammarSeeder:
    """Loads a grammar curriculum JSON for one language into the DB."""

    def __init__(self, db_url: str, language_code: str):
        self.db_url = db_url
        self.language_code = language_code

    def transform(self) -> dict:
        """Parse and validate the curriculum file. No DB access (testable)."""
        path = GRAMMAR_DIR / f"{self.language_code}_grammar.json"
        if not path.exists():
            raise FileNotFoundError(f"No grammar curriculum at {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        points = []
        for p in data.get("points", []):
            title = (p.get("title") or "").strip()
            if not title:
                continue
            source = p.get("source") or "pending"
            if source not in VALID_SOURCES:
                source = "pending"
            drills = []
            for d in p.get("drills", []):
                sentence = (d.get("sentence") or "").strip()
                answer = (d.get("answer") or "").strip()
                if not sentence or not answer or "{{answer}}" not in sentence:
                    continue
                drills.append({
                    "sentence": sentence,
                    "answer": answer,
                    "translation": (d.get("translation") or "").strip() or None,
                    "hint": (d.get("hint") or "").strip() or None,
                    "gloss": (d.get("gloss") or "").strip() or None,
                    "transliteration": (d.get("transliteration") or "").strip() or None,
                    "cell": (d.get("cell") or "").strip() or None,
                    "display_order": int(d.get("display_order") or 0),
                })
            # Paradigm coverage: a point tagged with paradigm cells (subject
            # pronouns, a conjugation table…) is really N questions in one
            # card, so EVERY cell must have a drill — a member the drills
            # never test is a member the learner never learns. Fails the
            # seed loudly rather than shipping silent gaps.
            paradigm = [
                str(c).strip() for c in (p.get("paradigm") or []) if str(c).strip()
            ]
            if paradigm:
                covered = {d["cell"] for d in drills if d["cell"]}
                unknown = covered - set(paradigm)
                missing = set(paradigm) - covered
                if unknown:
                    raise ValueError(
                        f"{title}: drill cells not in the paradigm: {sorted(unknown)}"
                    )
                if missing:
                    raise ValueError(
                        f"{title}: paradigm cells with no drill: {sorted(missing)}"
                    )
                # Density gate: 2 drills per cell, so the rotation can vary
                # the frame within a cell (one frame per form invites
                # memorizing the sentence instead of the form). Hard error —
                # every shipped path meets it as of 2026-07.
                thin = sorted(
                    c for c in paradigm
                    if sum(1 for d in drills if d["cell"] == c) < 2
                )
                if thin:
                    raise ValueError(
                        f"{title}: paradigm cells below 2 drills: {thin}"
                    )
            points.append({
                "title": title,
                "level": p.get("level"),
                "function": (p.get("function") or "").strip() or None,
                "explanation": (p.get("explanation") or "").strip() or None,
                "culture_note": (p.get("culture_note") or "").strip() or None,
                "source": source,
                "reviewed": bool(p.get("reviewed", False)),
                "display_order": int(p.get("display_order") or 0),
                "references": clean_references(p.get("references")),
                "related": clean_related(p.get("related")),
                "prerequisites": _clean_prerequisites(p.get("prerequisites")),
                "drills": drills,
            })
        self._attach_hint_translations(points)
        self._attach_explanation_translations(points)
        # Every level that has points must have a deck (content_list) —
        # otherwise the level is invisible in Learn and the deck browser.
        # The A2–C2 deepening waves appended points without lists, which
        # left eight languages showing only their A1 deck.
        lists = list(data.get("lists", []))
        covered = {lst.get("level") for lst in lists}
        for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
            if level in covered:
                continue
            if any(p.get("level") == level for p in points):
                lists.append({
                    "level": level,
                    "title": f"{level} Grammar Path",
                    "description": f"Grammar points at {level}, in path order.",
                })
        return {"lists": lists, "points": points}

    def _attach_hint_translations(self, points: list[dict]) -> None:
        """Merge {code}_drill_hints.{locale}.json files onto their drills.

        Every entry must land on a real drill: an unknown point title or a
        sentence that no longer matches means the drill was reworded after
        the translation was drafted — fail the seed so the locale file gets
        re-drafted instead of silently dropping the learner's scaffolding.
        Partial coverage is fine (locales roll out tier by tier).
        """
        by_title = {p["title"]: p for p in points}
        for path in sorted(
            GRAMMAR_DIR.glob(f"{self.language_code}_drill_hints.*.json")
        ):
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
            locale = (payload.get("locale") or "").strip()
            if not locale or locale == "en":
                raise ValueError(f"{path.name}: missing or invalid locale")
            reviewed = bool(payload.get("reviewed", False))
            for title, sentences in (payload.get("points") or {}).items():
                point = by_title.get(title)
                if point is None:
                    raise ValueError(f"{path.name}: unknown point: {title}")
                by_sentence = {d["sentence"]: d for d in point["drills"]}
                for sentence, entry in sentences.items():
                    drill = by_sentence.get(sentence)
                    if drill is None:
                        raise ValueError(
                            f"{path.name}: {title}: no drill matches "
                            f"{sentence[:50]!r} (reworded since drafting?)"
                        )
                    hint = (entry.get("hint") or "").strip()
                    translation = (entry.get("translation") or "").strip()
                    if not hint or not translation:
                        raise ValueError(
                            f"{path.name}: {title}: empty hint/translation "
                            f"for {sentence[:50]!r}"
                        )
                    # Same answer-leak gate as authored hints: a translated
                    # hint that spells out the answer defeats the drill.
                    ans = drill["answer"].lower()
                    if len(ans) > 3 and re.search(
                        rf"(?<![^\W\d_]){re.escape(ans)}(?![^\W\d_])",
                        hint.lower(),
                    ):
                        raise ValueError(
                            f"{path.name}: {title}: hint reveals answer "
                            f"{drill['answer']!r}: {hint!r}"
                        )
                    drill.setdefault("hint_translations", {})[locale] = {
                        "hint": hint,
                        "translation": translation,
                        "reviewed": reviewed,
                    }

    def _attach_explanation_translations(self, points: list[dict]) -> None:
        """Merge {code}_explanations.{locale}.json onto their points (WP22).

        L1-aware explanations for English-from-X learners: the whole
        explanation, written IN the support locale FOR speakers of it.
        Unknown titles fail the seed (the point was renamed after the
        translation was drafted); partial coverage is fine.
        """
        by_title = {p["title"]: p for p in points}
        for path in sorted(
            GRAMMAR_DIR.glob(f"{self.language_code}_explanations.*.json")
        ):
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
            locale = (payload.get("locale") or "").strip()
            if not locale or locale == "en":
                raise ValueError(f"{path.name}: missing or invalid locale")
            reviewed = bool(payload.get("reviewed", False))
            for title, text in (payload.get("points") or {}).items():
                point = by_title.get(title)
                if point is None:
                    raise ValueError(f"{path.name}: unknown point: {title}")
                if not (text or "").strip():
                    raise ValueError(f"{path.name}: empty explanation: {title}")
                point.setdefault("explanation_translations", {})[locale] = {
                    "explanation": text.strip(),
                    "reviewed": reviewed,
                }

    async def load(self, data: dict) -> int:
        """Write lists, points, and drills. Returns the number of points loaded."""
        conn = await asyncpg.connect(self.db_url)
        try:
            language_id = await conn.fetchval(
                "SELECT id FROM languages WHERE code = $1", self.language_code
            )
            if not language_id:
                raise ValueError(f"Language '{self.language_code}' not found in DB")

            for lst in data.get("lists", []):
                await conn.execute(
                    """
                    INSERT INTO content_lists (language_id, list_type, level, title, description)
                    VALUES ($1, 'grammar', $2, $3, $4)
                    ON CONFLICT (language_id, list_type, level) DO UPDATE SET
                        title = EXCLUDED.title, description = EXCLUDED.description
                    """,
                    language_id, lst.get("level"), lst.get("title", "Grammar"),
                    lst.get("description"),
                )

            # Curated points are human-owned: the re-seed never overwrites them
            # (text diffs go to the suggestion queue) and never deletes their
            # drills. Same protection vocabulary already has (Option B).
            from backend.repositories.audit import log_change  # noqa: PLC0415
            from backend.repositories.contributor import (  # noqa: PLC0415
                create_extraction_suggestion,
                reseed_grammar_proposal,
            )

            curated_rows = await conn.fetch(
                "SELECT id, title, function_note, explanation, culture_note "
                "FROM grammar_points WHERE language_id = $1 AND curated = true",
                language_id,
            )
            curated_by_title = {r["title"]: r for r in curated_rows}

            count = 0
            hint_rows = 0
            expl_rows = 0
            new_points = 0
            suggested = 0
            drills_updated = drills_inserted = drills_deleted = 0
            drills_pending = 0
            origin = f"document re-seed ({self.language_code})"
            # Prerequisites reference other points by title; resolve to ids only
            # after every point in this file has an id (a point may depend on a
            # later one). Collected here, applied in one pass below.
            pending_prereqs: list[tuple] = []
            for point in data["points"]:
                cur = curated_by_title.get(point["title"])
                protect = cur is not None
                if protect:
                    gp_id = cur["id"]
                    proposal = reseed_grammar_proposal(point, dict(cur))
                    if proposal:
                        await create_extraction_suggestion(
                            conn, language_id, str(gp_id), proposal,
                            entity_type="grammar", origin=origin,
                            current={k: cur[k] for k in proposal},
                        )
                        suggested += 1
                else:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO grammar_points
                            (language_id, title, function_note, explanation, culture_note,
                             level, display_order, explanation_source, reviewed, reference_links,
                             related)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb)
                        ON CONFLICT (language_id, title) DO UPDATE SET
                            function_note = EXCLUDED.function_note,
                            explanation = EXCLUDED.explanation,
                            culture_note = EXCLUDED.culture_note,
                            level = EXCLUDED.level,
                            display_order = EXCLUDED.display_order,
                            explanation_source = EXCLUDED.explanation_source,
                            reviewed = EXCLUDED.reviewed,
                            reference_links = EXCLUDED.reference_links,
                            related = EXCLUDED.related
                        RETURNING id, (xmax = 0) AS inserted
                        """,
                        language_id, point["title"], point.get("function"),
                        point["explanation"], point["culture_note"], point["level"],
                        point["display_order"], point["source"], point["reviewed"],
                        json.dumps(point.get("references") or [], ensure_ascii=False),
                        json.dumps(point.get("related") or [], ensure_ascii=False),
                    )
                    gp_id = row["id"]
                    if row["inserted"]:
                        new_points += 1
                        # Actor NULL = system: the admin audit feed doubles as
                        # an import digest of what each seed run added.
                        await log_change(
                            conn, entity_type="grammar_point",
                            entity_id=str(gp_id), action="seeded",
                            language_id=str(language_id), note=origin,
                        )

                # Diff-sync drills in place of the old delete-and-rebuild:
                # matched rows update IN PLACE, so drill ids — and each
                # learner's gym_progress (ON DELETE CASCADE) — survive a
                # re-seed. Human-touched drills are never deleted; on a curated
                # point nothing is deleted or updated, and new drills land
                # source='ai'/reviewed=false in the pending-drills queue.
                existing = [
                    dict(r) for r in await conn.fetch(
                        "SELECT id, sentence, answer, source, is_modified, "
                        "flagged, translation, hint "
                        "FROM drill_sentences WHERE grammar_point_id = $1", gp_id,
                    )
                ]
                sync = plan_drill_sync(existing, point["drills"], protect=protect)

                async def _write_hints(drill_id, d):
                    # Seed-authored rows are authoritative for their locale
                    # (upsert over a machine-filled draft); locales the seed
                    # doesn't carry are left to the auto-translate loop.
                    n = 0
                    for locale, ht in (d.get("hint_translations") or {}).items():
                        await conn.execute(
                            """
                            INSERT INTO drill_hint_translations
                                (drill_id, locale, hint, translation, reviewed)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (drill_id, locale) DO UPDATE
                              SET hint = EXCLUDED.hint,
                                  translation = EXCLUDED.translation,
                                  reviewed = EXCLUDED.reviewed
                            """,
                            drill_id, locale, ht["hint"], ht["translation"],
                            ht["reviewed"],
                        )
                        n += 1
                    return n

                for row, d in sync["update"]:
                    await conn.execute(
                        """
                        UPDATE drill_sentences
                        SET translation = $2, hint = $3, gloss = $4,
                            transliteration = $5, display_order = $6, cell = $7
                        WHERE id = $1
                        """,
                        row["id"], d["translation"], d["hint"], d.get("gloss"),
                        d.get("transliteration"), d["display_order"], d.get("cell"),
                    )
                    # Locale rows are renderings of the English translation
                    # and hint — they go stale only when THOSE changed. A
                    # re-seed that merely reorders or re-cells a drill must
                    # not wipe machine-filled overlays (the loop would just
                    # re-spend to restore them). Seed-authored locales upsert
                    # either way.
                    if (row.get("translation"), row.get("hint")) != (
                        d["translation"], d["hint"]
                    ):
                        await conn.execute(
                            "DELETE FROM drill_hint_translations WHERE drill_id = $1",
                            row["id"],
                        )
                    hint_rows += await _write_hints(row["id"], d)
                    drills_updated += 1
                for d in sync["insert"]:
                    drill_id = await conn.fetchval(
                        """
                        INSERT INTO drill_sentences
                            (grammar_point_id, sentence, answer, translation, hint,
                             gloss, transliteration, display_order, cell,
                             source, reviewed, origin_detail)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        RETURNING id
                        """,
                        gp_id, d["sentence"], d["answer"], d["translation"],
                        d["hint"], d.get("gloss"), d.get("transliteration"),
                        d["display_order"], d.get("cell"),
                        "ai" if protect else "seed",
                        not protect,  # curated additions wait for review
                        origin if protect else None,
                    )
                    hint_rows += await _write_hints(drill_id, d)
                    drills_inserted += 1
                    if protect:
                        drills_pending += 1
                if sync["delete"]:
                    await conn.execute(
                        "DELETE FROM drill_sentences WHERE id = ANY($1::uuid[])",
                        [r["id"] for r in sync["delete"]],
                    )
                    drills_deleted += len(sync["delete"])

                if not protect:
                    # WP22: localized explanations upsert by (point, locale).
                    # Skipped for curated points — they mirror the main text,
                    # which the human owns.
                    for locale, et in (
                        point.get("explanation_translations") or {}
                    ).items():
                        await conn.execute(
                            """
                            INSERT INTO explanation_translations
                                (grammar_point_id, locale, explanation, reviewed)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (grammar_point_id, locale) DO UPDATE SET
                                explanation = EXCLUDED.explanation,
                                reviewed = EXCLUDED.reviewed
                            """,
                            gp_id, locale, et["explanation"], et["reviewed"],
                        )
                        expl_rows += 1
                    if point.get("prerequisites"):
                        pending_prereqs.append((gp_id, point["prerequisites"]))
                count += 1

            # Resolve prerequisite titles → ids now that every point (this
            # file's plus any already in the DB) has one. Re-seeding replaces
            # the array, so it stays idempotent; unresolved titles are dropped.
            prereq_rows = 0
            if pending_prereqs:
                rows = await conn.fetch(
                    "SELECT id, title FROM grammar_points WHERE language_id = $1",
                    language_id,
                )
                id_by_title = {r["title"]: r["id"] for r in rows}
                for gp_id, titles in pending_prereqs:
                    ids = [id_by_title[t] for t in titles if t in id_by_title]
                    await conn.execute(
                        "UPDATE grammar_points SET prerequisites = $2 WHERE id = $1",
                        gp_id, ids,
                    )
                    prereq_rows += len(ids)

            logger.info(
                "Loaded %d grammar points for %s (%d new, %d hint rows, %d "
                "explanation rows, %d prerequisite links); drills: %d updated "
                "in place, %d inserted, %d deleted",
                count, self.language_code, new_points, hint_rows, expl_rows,
                prereq_rows, drills_updated, drills_inserted, drills_deleted,
            )
            if suggested or drills_pending:
                logger.info(
                    "Protected %d curated point(s): %d text change(s) routed to "
                    "the review suggestion queue, %d new drill(s) pending review "
                    "(not overwritten)",
                    len(curated_by_title), suggested, drills_pending,
                )
            return count
        finally:
            await conn.close()

    async def run(self) -> int:
        return await self.load(self.transform())


def _available_languages() -> list[str]:
    if not GRAMMAR_DIR.exists():
        return []
    return sorted(
        p.name.removesuffix("_grammar.json")
        for p in GRAMMAR_DIR.glob("*_grammar.json")
    )


async def _main() -> None:
    import os

    parser = argparse.ArgumentParser(description="Seed grammar curricula")
    parser.add_argument("--language", "-l", default="all")
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        return

    languages = _available_languages() if args.language == "all" else [args.language]
    for lang in languages:
        try:
            n = await GrammarSeeder(args.db_url, lang).run()
            print(f"OK {lang}: {n} grammar points loaded")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {lang}: {e}")


if __name__ == "__main__":
    asyncio.run(_main())
