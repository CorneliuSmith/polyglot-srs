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

    async def load(self, records: list[dict]) -> int:
        """UPSERT records into vocabulary + translations tables. Returns count."""
        conn = await asyncpg.connect(self.db_url)
        try:
            # Look up language_id
            self.language_id = await conn.fetchval(
                "SELECT id FROM languages WHERE code = $1", self.language_code
            )
            if not self.language_id:
                raise ValueError(f"Language '{self.language_code}' not found in DB")

            count = 0
            for rec in records:
                # Ensure morphology is a JSON string for the ::jsonb cast
                morphology = rec.get("morphology", "{}")
                if isinstance(morphology, dict):
                    morphology = json.dumps(morphology, ensure_ascii=False)

                # UPSERT vocabulary
                vocab_id = await conn.fetchval("""
                    INSERT INTO vocabulary (language_id, word, reading, part_of_speech, level, frequency_rank, morphology)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                    ON CONFLICT (language_id, word) DO UPDATE SET
                        reading = EXCLUDED.reading,
                        part_of_speech = EXCLUDED.part_of_speech,
                        level = EXCLUDED.level,
                        frequency_rank = EXCLUDED.frequency_rank,
                        morphology = EXCLUDED.morphology
                    RETURNING id
                """, self.language_id, rec["word"], rec.get("reading"),
                    rec.get("pos"), rec.get("level"), rec.get("frequency_rank"),
                    morphology)

                # UPSERT translations
                for locale, definition in rec.get("translations", {}).items():
                    await conn.execute("""
                        INSERT INTO translations (vocabulary_id, locale, definition)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (vocabulary_id, locale) DO UPDATE SET
                            definition = EXCLUDED.definition
                    """, vocab_id, locale, definition)

                count += 1
                if count % 1000 == 0:
                    self.logger.info(f"Loaded {count} records...")

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
