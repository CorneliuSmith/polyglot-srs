"""Base seeder infrastructure for language vocabulary seed scripts."""
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import asyncpg

from backend.services.content_filter import is_explicit

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


class BaseSeeder(ABC):
    """Base class for language seed scripts.

    Subclasses must implement:
      - language_code (property)
      - download()
      - transform()

    The load() and run() methods are provided by this base class.
    """

    # When True, a re-seed does NOT overwrite a vocabulary card a human has
    # curated; the model's proposed values are stashed as a pending
    # content_suggestion the reviewer can accept or dismiss (Option B). Only the
    # doc-import path (CSVImporter, fed by the extractor) opts in — the objective
    # frequency-corpus seeders keep overwriting as before.
    protect_curated: bool = False

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.logger = logging.getLogger(self.__class__.__name__)
        self.language_id: str | None = None  # set during load
        self.suggested_curated = 0  # curated words routed to the suggestion queue

    @property
    @abstractmethod
    def language_code(self) -> str:
        """ISO 639-1 code: 'ru', 'ar', 'en'"""

    @abstractmethod
    async def download(self) -> None:
        """Download raw data files to DATA_DIR."""

    @abstractmethod
    async def transform(self) -> list[dict]:
        """Parse raw files into list of vocabulary dicts."""

    def _merge_morphology_charts(self, records: list[dict]) -> None:
        """Fold data/{code}_morphology.json (chips + charts built by
        morphology_charts.py from the language's Wiktionary extract) into
        each record's morphology dict. The card page renders these as the
        language-shaped Forms panel (§3b): conjugations, declensions,
        aspect pairs, gender/plural, noun classes — per language, per POS.
        """
        path = DATA_DIR / f"{self.language_code}_morphology.json"
        if not path.exists():
            return
        from .morphology_charts import strip_nominal_chips
        with open(path, encoding="utf-8") as f:
            by_word = json.load(f)
        merged = 0
        for rec in records:
            extra = by_word.get(rec["word"])
            if not extra:
                continue
            base = rec.get("morphology") or {}
            if isinstance(base, str):
                base = json.loads(base) if base.strip() else {}
            # A word's chosen POS vetoes gender/number chips inherited from a
            # homographic noun sense (de/para/no showing "Plural des").
            rec["morphology"] = strip_nominal_chips(
                {**base, **extra}, rec.get("pos")
            )
            merged += 1
        if merged:
            self.logger.info(
                f"Merged morphology charts for {merged} of {len(records)} words"
            )

    async def _route_curated(
        self, conn: "asyncpg.Connection", records: list[dict]
    ) -> list[dict]:
        """Split re-seed records: a word a human has curated is never
        overwritten — its differing values become a pending suggestion — so the
        returned list is only the words safe to UPSERT. Requires
        ``self.language_id`` to be set."""
        from backend.repositories.contributor import (
            create_extraction_suggestion,
            reseed_vocab_proposal,
        )

        words = [rec["word"] for rec in records]
        curated_rows = await conn.fetch(
            """
            SELECT v.id, v.word, v.part_of_speech,
                   (SELECT t.definition FROM translations t
                     WHERE t.vocabulary_id = v.id AND t.locale = 'en' LIMIT 1)
                     AS definition
            FROM vocabulary v
            WHERE v.language_id = $1 AND v.curated = true
              AND v.word = ANY($2::text[])
            """,
            self.language_id, words,
        )
        curated = {
            r["word"]: {"id": r["id"], "part_of_speech": r["part_of_speech"],
                        "definition": r["definition"]}
            for r in curated_rows
        }
        if not curated:
            return records

        safe: list[dict] = []
        for rec in records:
            cur = curated.get(rec["word"])
            if cur is None:
                safe.append(rec)  # new or non-curated word → normal upsert
                continue
            proposal = reseed_vocab_proposal(rec, cur)
            if proposal:
                await create_extraction_suggestion(
                    conn, self.language_id, str(cur["id"]), proposal,
                    origin=f"document re-seed ({self.language_code})",
                    current=cur,
                )
                self.suggested_curated += 1
            # Either way the curated card is left untouched (not upserted).
        if self.suggested_curated:
            self.logger.info(
                f"Routed {self.suggested_curated} curated word(s) to the "
                f"suggestion queue instead of overwriting"
            )
        return safe

    async def load(self, records: list[dict]) -> int:
        """UPSERT records into vocabulary + translations tables. Returns count."""
        self._merge_morphology_charts(records)
        # Sources can repeat a word (case variants, merged sense rows); a
        # duplicate inside one UNNEST statement makes ON CONFLICT DO UPDATE
        # fail with "cannot affect row a second time". Merge duplicates
        # first: later fields win, translation dicts accumulate.
        merged: dict[str, dict] = {}
        for rec in records:
            prev = merged.get(rec["word"])
            if prev is None:
                merged[rec["word"]] = rec
            else:
                translations = {**prev.get("translations", {}),
                                **rec.get("translations", {})}
                prev.update({k: v for k, v in rec.items() if v is not None})
                prev["translations"] = translations
        records = list(merged.values())

        conn = await asyncpg.connect(self.db_url)
        try:
            # Look up language_id
            self.language_id = await conn.fetchval(
                "SELECT id FROM languages WHERE code = $1", self.language_code
            )
            if not self.language_id:
                raise ValueError(f"Language '{self.language_code}' not found in DB")

            # Option B: on the doc-import path, don't overwrite human-curated
            # cards. Route their re-seed diffs to the suggestion queue and drop
            # them from the upsert set (the reviewer decides what goes live).
            if self.protect_curated:
                records = await self._route_curated(conn, records)

            # Batched UNNEST upserts: corpus-scale seeds are 10k words plus
            # tens of thousands of translations, and one round trip per row
            # over a pooled (high-latency) connection turns a seed into
            # hours. One statement per chunk keeps it to seconds. The
            # vocabulary upsert never touches `alternatives` (regional
            # spellings, aspect/motion partners survive reseeds); the few
            # records that DO carry alternatives get a per-row update below.
            chunk_size = 2000
            count = 0
            for start in range(0, len(records), chunk_size):
                chunk = records[start:start + chunk_size]
                words, readings, poses, levels_col, ranks, morphs, sources = (
                    [], [], [], [], [], [], []
                )
                for rec in chunk:
                    morphology = rec.get("morphology", "{}")
                    if isinstance(morphology, dict):
                        morphology = json.dumps(morphology, ensure_ascii=False)
                    words.append(rec["word"])
                    readings.append(rec.get("reading"))
                    poses.append(rec.get("pos"))
                    levels_col.append(rec.get("level"))
                    ranks.append(rec.get("frequency_rank"))
                    morphs.append(morphology)
                    sources.append(rec.get("level_source"))

                # level_source: a record without one lowers to the objective
                # 'frequency' default (COALESCE). On reseed we never downgrade a
                # 'curated' level (a reviewer confirmed it) back to 'frequency'
                # or 'ai' — that confirmation must survive re-seeding, exactly
                # like `alternatives` above.
                id_rows = await conn.fetch("""
                    INSERT INTO vocabulary (language_id, word, reading, part_of_speech, level, frequency_rank, morphology, level_source)
                    SELECT $1, u.word, u.reading, u.pos, u.level, u.rank, u.morphology::jsonb,
                           COALESCE(u.level_source, 'frequency')
                    FROM UNNEST($2::text[], $3::text[], $4::text[], $5::text[],
                                $6::int[], $7::text[], $8::text[])
                         AS u(word, reading, pos, level, rank, morphology, level_source)
                    ON CONFLICT (language_id, word) DO UPDATE SET
                        reading = EXCLUDED.reading,
                        part_of_speech = EXCLUDED.part_of_speech,
                        level = EXCLUDED.level,
                        frequency_rank = EXCLUDED.frequency_rank,
                        morphology = EXCLUDED.morphology,
                        level_source = CASE
                            WHEN vocabulary.level_source = 'curated' THEN 'curated'
                            ELSE EXCLUDED.level_source
                        END
                    RETURNING id, word
                """, self.language_id, words, readings, poses, levels_col,
                    ranks, morphs, sources)
                id_by_word = {r["word"]: r["id"] for r in id_rows}

                t_ids, t_locales, t_defs = [], [], []
                seen_pairs: set[tuple] = set()
                for rec in chunk:
                    vocab_id = id_by_word.get(rec["word"])
                    if vocab_id is None:
                        continue
                    # Alternatives only overwrite when the record carries
                    # them (same semantics as the old per-row COALESCE).
                    if rec.get("alternatives") is not None:
                        await conn.execute(
                            "UPDATE vocabulary SET alternatives = $2 WHERE id = $1",
                            vocab_id, rec["alternatives"],
                        )
                    for locale, definition in rec.get("translations", {}).items():
                        # ON CONFLICT DO UPDATE can't touch the same row twice
                        # in one statement — last write wins here instead.
                        if (vocab_id, locale) in seen_pairs:
                            continue
                        seen_pairs.add((vocab_id, locale))
                        t_ids.append(vocab_id)
                        t_locales.append(locale)
                        t_defs.append(definition)
                if t_ids:
                    await conn.execute("""
                        INSERT INTO translations (vocabulary_id, locale, definition)
                        SELECT * FROM UNNEST($1::uuid[], $2::text[], $3::text[])
                        ON CONFLICT (vocabulary_id, locale) DO UPDATE SET
                            definition = EXCLUDED.definition
                    """, t_ids, t_locales, t_defs)
                    # Mark explicit words as they load. The migration's
                    # backfill only covers what was already in the database,
                    # so without this the NEXT language seeded would ship its
                    # slurs unflagged and visible — the exact bug, reopened by
                    # the next `seed_vocabulary` run.
                    explicit_ids = [
                        vid for vid, definition in zip(t_ids, t_defs)
                        if is_explicit(definition)
                    ]
                    if explicit_ids:
                        try:
                            await conn.execute(
                                "UPDATE vocabulary SET is_explicit = true "
                                "WHERE id = ANY($1::uuid[])",
                                list(set(explicit_ids)),
                            )
                        except asyncpg.exceptions.UndefinedColumnError:
                            # Migration 20260910 not applied yet — seeding
                            # still succeeds; the backfill will catch these.
                            self.logger.warning(
                                "vocabulary.is_explicit missing; %d explicit "
                                "words left unflagged until the migration runs",
                                len(set(explicit_ids)),
                            )

                count += len(chunk)
                self.logger.info(f"Loaded {count} records...")

            # Create a vocabulary content_list per CEFR level present, so the
            # loaded words are subscribable (onboarding) and learnable. Without
            # this, "Learn Vocabulary" has nothing to draw from after seeding.
            levels = sorted({rec.get("level") for rec in records if rec.get("level")})
            for level in levels:
                await conn.execute("""
                    INSERT INTO content_lists (language_id, list_type, level, title, description)
                    VALUES ($1, 'vocabulary', $2, $3, $4)
                    ON CONFLICT (language_id, list_type, level) DO UPDATE SET
                        title = EXCLUDED.title
                """, self.language_id, level, f"{level} Vocabulary",
                    f"Frequency-ranked {self.language_code} vocabulary ({level}).")
            if levels:
                self.logger.info(
                    f"Ensured {len(levels)} vocabulary content list(s): {', '.join(levels)}"
                )

            self.logger.info(f"Finished loading {count} records for {self.language_code}")
            return count
        finally:
            await conn.close()

    async def run(self) -> int:
        """Full pipeline: download → transform → load."""
        self.logger.info(f"Starting seed for {self.language_code}")
        await self.download()
        records = await self.transform()
        return await self.load(records)

    @staticmethod
    def rank_to_level(rank: int | None, total_words: int | None = None) -> str | None:
        """Map frequency rank to CEFR level.

        The absolute thresholds (500/1500/3000/5000/8000) are the 10k-corpus
        proportions 5/15/30/50/80%. Low-resource corpora (Māori ~800 words,
        Hausa ~1.1k) pass *total_words* so the SAME proportions band their
        list — otherwise everything lands in A1/A2 and the ladder never
        reaches C1/C2.
        """
        if rank is None:
            return None
        # Proportional banding only for REAL corpora: a 30-word curated
        # starter (or a tiny test fixture) is all beginner vocabulary, not
        # a ladder — those keep the absolute thresholds.
        base = (min(total_words, 10000)
                if total_words and total_words >= 500 else 10000)
        if rank <= 0.05 * base:
            return "A1"
        if rank <= 0.15 * base:
            return "A2"
        if rank <= 0.30 * base:
            return "B1"
        if rank <= 0.50 * base:
            return "B2"
        if rank <= 0.80 * base:
            return "C1"
        return "C2"
