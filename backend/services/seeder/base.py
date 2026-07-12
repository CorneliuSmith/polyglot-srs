"""Base seeder infrastructure for language vocabulary seed scripts."""
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import asyncpg

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


class BaseSeeder(ABC):
    """Base class for language seed scripts.

    Subclasses must implement:
      - language_code (property)
      - download()
      - transform()

    The load() and run() methods are provided by this base class.
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.logger = logging.getLogger(self.__class__.__name__)
        self.language_id: str | None = None  # set during load

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
            rec["morphology"] = {**base, **extra}
            merged += 1
        if merged:
            self.logger.info(
                f"Merged morphology charts for {merged} of {len(records)} words"
            )

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
                words, readings, poses, levels_col, ranks, morphs = (
                    [], [], [], [], [], []
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

                id_rows = await conn.fetch("""
                    INSERT INTO vocabulary (language_id, word, reading, part_of_speech, level, frequency_rank, morphology)
                    SELECT $1, u.word, u.reading, u.pos, u.level, u.rank, u.morphology::jsonb
                    FROM UNNEST($2::text[], $3::text[], $4::text[], $5::text[],
                                $6::int[], $7::text[])
                         AS u(word, reading, pos, level, rank, morphology)
                    ON CONFLICT (language_id, word) DO UPDATE SET
                        reading = EXCLUDED.reading,
                        part_of_speech = EXCLUDED.part_of_speech,
                        level = EXCLUDED.level,
                        frequency_rank = EXCLUDED.frequency_rank,
                        morphology = EXCLUDED.morphology
                    RETURNING id, word
                """, self.language_id, words, readings, poses, levels_col,
                    ranks, morphs)
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
    def rank_to_level(rank: int | None) -> str | None:
        """Map frequency rank to CEFR level."""
        if rank is None:
            return None
        if rank <= 500:
            return "A1"
        if rank <= 1500:
            return "A2"
        if rank <= 3000:
            return "B1"
        if rank <= 5000:
            return "B2"
        return "C1"
