"""Yoruba vocabulary seeder from a merged frequency + translation TSV.

Expected file format (tab-separated, header row):
    rank	word	pos	en
    1	àti	conj	and
    2	ọmọ	noun	child

Build the file with the sourcing pipeline (frequency from the
Niger-Volta-LTI diacritized corpora, translations from kaikki/Wiktionary):
    python -m backend.services.seeder.source_data --language yo --source kaikki
"""
import csv
import json
import unicodedata

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — DATA_DIR re-exported so tests can patch it

FREQ_FILENAME = "yo_frequency.tsv"


class YorubaSeeder(BaseSeeder):
    language_code = "yo"

    async def download(self) -> None:
        """No automatic download — build the TSV with source_data.py."""
        import backend.services.seeder.seed_yoruba as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Yoruba frequency file not found at %s — run "
                "source_data --language yo --source kaikki", path
            )

    async def transform(self) -> list[dict]:
        """Parse the frequency TSV into vocabulary records."""
        import backend.services.seeder.seed_yoruba as _mod

        freq_path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not freq_path.exists():
            raise FileNotFoundError(f"Yoruba frequency file not found at {freq_path}")

        records = []
        seen: set[str] = set()
        with open(freq_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # NFC so composed/decomposed diacritics can't create duplicates
                word = unicodedata.normalize("NFC", row["word"].strip().lower())
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

        # Re-band with the corpus size known: small corpora (mi ~800,
        # ha ~1.1k) use the same PROPORTIONS as a 10k corpus, so every
        # language's ladder reaches C1/C2.
        total = len(records)
        for rec in records:
            if rec.get("frequency_rank") is not None:
                rec["level"] = self.rank_to_level(rec["frequency_rank"], total)

        self.logger.info(f"Transformed {len(records)} Yoruba words")
        return records
