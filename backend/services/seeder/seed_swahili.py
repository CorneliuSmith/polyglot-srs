"""Swahili vocabulary seeder from a bundled frequency + translation TSV.

Expected file format (tab-separated, header row):
    rank	word	pos	en
    1	na	conj	and, with, by
    2	kwa	prep	for, to, by

Data source suggestion: the Helsinki Corpus of Swahili frequency list merged
with CLDR/SAWA translations — drop the merged TSV at data/sw_frequency.tsv.
"""
import csv
import json

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — DATA_DIR re-exported so tests can patch it

FREQ_FILENAME = "sw_frequency.tsv"


class SwahiliSeeder(BaseSeeder):
    language_code = "sw"

    async def download(self) -> None:
        """No automatic download — the merged TSV is bundled manually."""
        import backend.services.seeder.seed_swahili as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Swahili frequency file not found at %s — place the TSV there", path
            )

    async def transform(self) -> list[dict]:
        """Parse the frequency TSV into vocabulary records."""
        import backend.services.seeder.seed_swahili as _mod

        freq_path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not freq_path.exists():
            raise FileNotFoundError(f"Swahili frequency file not found at {freq_path}")

        records = []
        seen: set[str] = set()
        with open(freq_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                word = row["word"].strip().lower()
                translation = (row.get("en") or "").strip()
                if not word or not translation or word in seen:
                    continue
                seen.add(word)
                rank = int(row["rank"])
                records.append({
                    "word": word,
                    "reading": None,
                    "pos": (row.get("pos") or "").strip() or None,
                    "level": self.rank_to_level(rank),
                    "frequency_rank": rank,
                    "morphology": json.dumps({"lemma": word}, ensure_ascii=False),
                    "translations": {"en": translation},
                })

        self.logger.info(f"Transformed {len(records)} Swahili words")
        return records
