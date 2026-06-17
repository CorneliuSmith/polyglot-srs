"""Xhosa vocabulary seeder from a merged frequency + translation TSV.

Expected file format (tab-separated, header row):
    rank	word	pos	en
    1	ukuba	conj	that, if
    2	umntu	noun	person

Build with the sourcing pipeline (frequency from the public-domain Xhosa
bible corpus, translations from kaikki/Wiktionary):
    python -m backend.services.seeder.source_data --language xh --source kaikki
"""
import csv
import json

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — DATA_DIR re-exported so tests can patch it

FREQ_FILENAME = "xh_frequency.tsv"


class XhosaSeeder(BaseSeeder):
    language_code = "xh"

    async def download(self) -> None:
        """No automatic download — build the TSV with source_data.py."""
        import backend.services.seeder.seed_xhosa as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Xhosa frequency file not found at %s — run "
                "source_data --language xh --source kaikki", path
            )

    async def transform(self) -> list[dict]:
        """Parse the frequency TSV into vocabulary records."""
        import backend.services.seeder.seed_xhosa as _mod

        freq_path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not freq_path.exists():
            raise FileNotFoundError(f"Xhosa frequency file not found at {freq_path}")

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

        self.logger.info(f"Transformed {len(records)} Xhosa words")
        return records
