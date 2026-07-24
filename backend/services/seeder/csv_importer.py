"""Generic CSV/TSV vocabulary importer with row-level validation."""
import csv
import json
from pathlib import Path

from .base import BaseSeeder
from .validators import (
    VALID_LEVEL_SOURCES,
    VALID_LEVELS,
    VALID_POS,
    ValidationError,
    validate_script,
)


class CSVImporter(BaseSeeder):
    """Generic CSV/TSV vocabulary importer with validation.

    Validates every row before any DB write (fail-fast).  Passes cleaned
    records to the inherited BaseSeeder.load() UPSERT path.
    """

    def __init__(self, db_url: str, language_code: str, file_path: str):
        super().__init__(db_url)
        self._language_code = language_code
        self.file_path = Path(file_path)
        self.errors: list[ValidationError] = []

    @property
    def language_code(self) -> str:
        return self._language_code

    # ------------------------------------------------------------------
    # BaseSeeder abstract methods
    # ------------------------------------------------------------------

    async def download(self) -> None:
        """No download step — file is provided by the user."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Import file not found: {self.file_path}")

    def validate(self, rows: list[dict]) -> tuple[list[dict], list[ValidationError]]:
        """Validate all rows.

        Returns:
            (valid_rows, errors) — if *errors* is non-empty no data should
            be loaded (the caller is responsible for enforcing that).
        """
        errors: list[ValidationError] = []
        valid: list[dict] = []
        seen_words: set[str] = set()

        for i, row in enumerate(rows, start=2):  # row 1 is the header
            row_errors: list[ValidationError] = []

            # --- required fields ---
            word = row.get("word", "").strip()
            definition = row.get("definition", "").strip()

            if not word:
                row_errors.append(ValidationError(i, "word", "", "required field is empty"))
            if not definition:
                row_errors.append(ValidationError(i, "definition", "", "required field is empty"))

            # --- duplicate check within the file ---
            if word and word in seen_words:
                row_errors.append(ValidationError(i, "word", word, "duplicate word in file"))
            if word:
                seen_words.add(word)

            # --- script validation ---
            if word:
                script_err = validate_script(word, self.language_code)
                if script_err:
                    row_errors.append(ValidationError(i, "word", word, script_err))

            # --- POS validation ---
            pos = row.get("pos", "").strip().lower()
            if pos and pos not in VALID_POS:
                row_errors.append(
                    ValidationError(
                        i, "pos", pos,
                        f"invalid POS. Must be one of: {', '.join(sorted(VALID_POS))}",
                    )
                )

            # --- CEFR level validation ---
            level = row.get("level", "").strip().upper()
            if level and level not in VALID_LEVELS:
                row_errors.append(
                    ValidationError(
                        i, "level", level,
                        f"invalid CEFR level. Must be one of: {', '.join(sorted(VALID_LEVELS))}",
                    )
                )

            # --- level_source validation (optional) ---
            level_source = row.get("level_source", "").strip().lower()
            if level_source and level_source not in VALID_LEVEL_SOURCES:
                row_errors.append(
                    ValidationError(
                        i, "level_source", level_source,
                        f"invalid level_source. Must be one of: "
                        f"{', '.join(sorted(VALID_LEVEL_SOURCES))}",
                    )
                )

            # --- frequency_rank validation ---
            freq = row.get("frequency_rank", "").strip()
            if freq:
                if not freq.isdigit() or int(freq) <= 0:
                    row_errors.append(
                        ValidationError(i, "frequency_rank", freq, "must be a positive integer")
                    )

            if row_errors:
                errors.extend(row_errors)
            else:
                valid.append(row)

        return valid, errors

    async def transform(self) -> list[dict]:
        """Parse file, validate rows, and return cleaned vocabulary records.

        Raises:
            ValueError: if any validation errors are found (no partial load).
        """
        delimiter = "\t" if self.file_path.suffix == ".tsv" else ","

        with open(self.file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            raw_rows = list(reader)

        valid_rows, self.errors = self.validate(raw_rows)

        if self.errors:
            self.logger.error(f"Validation failed with {len(self.errors)} error(s):")
            for err in self.errors:
                self.logger.error(f"  {err}")
            raise ValueError(
                f"CSV validation failed: {len(self.errors)} error(s) in {len(raw_rows)} rows. "
                "Fix errors and retry. No data was loaded."
            )

        records = []
        for row in valid_rows:
            # Morphology JSONB from optional columns. The case columns
            # (acc/gen/prep/dat/inst) carry the mini declension sample that
            # case-language noun cards show on the item page — the learner
            # meets the forms where the word lives ("Language-shaped cards",
            # docs/curriculum-design.md).
            morphology: dict[str, str] = {}
            for key in ("root", "form", "gender", "aspect", "aspect_partner",
                        "acc", "gen", "prep", "dat", "inst"):
                val = (row.get(key) or "").strip()
                if val:
                    morphology[key] = val

            # Translations: always include English definition, add locale columns
            translations: dict[str, str] = {"en": row["definition"].strip()}
            for locale in ("ru", "ar", "es", "pt"):
                col = f"definition_{locale}"
                val = (row.get(col) or "").strip()
                if val:
                    translations[locale] = val

            # Pipe-separated alternatives
            alt_str = (row.get("alternatives") or "").strip()
            alternatives = (
                [a.strip() for a in alt_str.split("|") if a.strip()] if alt_str else []
            )

            freq = (row.get("frequency_rank") or "").strip()
            freq_rank = int(freq) if freq and freq.isdigit() else None
            level_raw = (row.get("level") or "").strip().upper()
            level = level_raw or self.rank_to_level(freq_rank)

            # Optional level provenance. Absent → None, so the loader falls back
            # to the objective 'frequency' default (unchanged from before this
            # column existed). 'ai' marks a provisional, model-estimated level.
            level_source = (row.get("level_source") or "").strip().lower() or None

            records.append({
                "word": row["word"].strip(),
                "reading": (row.get("reading") or "").strip() or None,
                "pos": (row.get("pos") or "").strip().lower() or None,
                "level": level or None,
                "level_source": level_source,
                "frequency_rank": freq_rank,
                "morphology": json.dumps(morphology, ensure_ascii=False) if morphology else "{}",
                "translations": translations,
                "alternatives": alternatives,
            })

        self.logger.info(
            f"Validated and transformed {len(records)} records from {self.file_path.name}"
        )
        return records
