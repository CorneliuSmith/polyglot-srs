"""Hausa vocabulary seeder from a merged frequency + translation TSV.

Expected file format (tab-separated, header row):
    rank	word	pos	en	plural
    1	da	conj	and
    2	mutum	noun	person	mutane

The optional `plural` column (Hausa plurals are irregular and unpredictable)
is stored in morphology and as an answer alternative so the validation layer
accepts it. Build with the sourcing pipeline (a commercially-usable Hausa
corpus + kaikki/Wiktionary):
    python -m backend.services.seeder.source_data --language ha --source kaikki
"""
import csv
import json

from backend.services.nlp.hausa import normalize_hausa

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — DATA_DIR re-exported so tests can patch it

FREQ_FILENAME = "ha_frequency.tsv"


class HausaSeeder(BaseSeeder):
    language_code = "ha"

    async def download(self) -> None:
        """No automatic download — build the TSV with source_data.py."""
        import backend.services.seeder.seed_hausa as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Hausa frequency file not found at %s — run "
                "source_data --language ha --source kaikki", path
            )

    async def transform(self) -> list[dict]:
        """Parse the frequency TSV into vocabulary records."""
        import backend.services.seeder.seed_hausa as _mod

        freq_path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not freq_path.exists():
            raise FileNotFoundError(f"Hausa frequency file not found at {freq_path}")

        records = []
        seen: set[str] = set()
        with open(freq_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                word = normalize_hausa(row["word"])
                translation = (row.get("en") or "").strip()
                if not word or not translation or word in seen:
                    continue
                seen.add(word)
                rank = int(row["rank"])
                plural = (row.get("plural") or "").strip()
                morphology = {"lemma": word}
                record = {
                    "word": word,
                    "reading": None,
                    "pos": (row.get("pos") or "").strip() or None,
                    "level": self.rank_to_level(rank),
                    "frequency_rank": rank,
                    "translations": {"en": translation},
                }
                if plural:
                    # Irregular plural: keep it as an accepted alternative answer.
                    morphology["plural"] = plural
                    record["answer_alternatives"] = [normalize_hausa(plural)]
                record["morphology"] = json.dumps(morphology, ensure_ascii=False)
                records.append(record)

        self.logger.info(f"Transformed {len(records)} Hausa words")
        return records
