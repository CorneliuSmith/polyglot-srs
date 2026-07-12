"""Vocabulary seeders for the Latin-script languages (es/it/fr/de/ca/mi).

All consume the same merged frequency + translation TSV
(data/{code}_frequency.tsv, columns rank/word/pos/en), built by the sourcing
pipeline. One base class, one subclass per language with its filename.
"""
import csv
import json

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — DATA_DIR re-exported so tests can patch it


class _FrequencyTsvSeeder(BaseSeeder):
    """Loads a rank/word/pos/en TSV into vocabulary + translations."""

    freq_filename: str = ""

    async def download(self) -> None:
        import backend.services.seeder.seed_latin as _mod

        path = _mod.DATA_DIR / self.freq_filename
        if not path.exists():
            self.logger.warning(
                "Frequency file not found at %s — run "
                "source_data --language %s --source kaikki",
                path, self.language_code,
            )

    async def transform(self) -> list[dict]:
        import backend.services.seeder.seed_latin as _mod

        freq_path = _mod.DATA_DIR / self.freq_filename
        if not freq_path.exists():
            raise FileNotFoundError(f"Frequency file not found at {freq_path}")

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

        self.logger.info(f"Transformed {len(records)} {self.language_code} words")
        return records


class SpanishSeeder(_FrequencyTsvSeeder):
    language_code = "es"
    freq_filename = "es_frequency.tsv"


class ItalianSeeder(_FrequencyTsvSeeder):
    language_code = "it"
    freq_filename = "it_frequency.tsv"


class FrenchSeeder(_FrequencyTsvSeeder):
    language_code = "fr"
    freq_filename = "fr_frequency.tsv"


class GermanSeeder(_FrequencyTsvSeeder):
    language_code = "de"
    freq_filename = "de_frequency.tsv"


class CatalanSeeder(_FrequencyTsvSeeder):
    language_code = "ca"
    freq_filename = "ca_frequency.tsv"


class MaoriSeeder(_FrequencyTsvSeeder):
    language_code = "mi"
    freq_filename = "mi_frequency.tsv"


class PortugueseSeeder(_FrequencyTsvSeeder):
    language_code = "pt"
    freq_filename = "pt_frequency.tsv"


class RomanianSeeder(_FrequencyTsvSeeder):
    language_code = "ro"
    freq_filename = "ro_frequency.tsv"


class GreekSeeder(_FrequencyTsvSeeder):
    language_code = "el"
    freq_filename = "el_frequency.tsv"


SEEDERS = {
    "es": SpanishSeeder, "it": ItalianSeeder, "fr": FrenchSeeder,
    "de": GermanSeeder, "ca": CatalanSeeder, "mi": MaoriSeeder,
    "ro": RomanianSeeder, "el": GreekSeeder, "pt": PortugueseSeeder,
}
