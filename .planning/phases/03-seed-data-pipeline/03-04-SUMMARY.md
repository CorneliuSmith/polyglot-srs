---
phase: 03-seed-data-pipeline
plan: "04"
subsystem: database
tags: [csv, tsv, seeder, validation, unicode, script-validation]

requires:
  - phase: 03-01
    provides: BaseSeeder infrastructure with UPSERT load path

provides:
  - Generic CSV/TSV vocabulary importer with per-row fail-fast validation
  - validators.py with Arabic/Cyrillic/Latin script regex and VALID_POS/VALID_LEVELS sets
  - CSVImporter class wired into BaseSeeder.load() UPSERT path
  - CLI --file/-f flag on seeder runner
  - 53-test suite covering all validation rules and transform paths

affects:
  - Phase 4 (any user-facing import workflow)
  - Future Arabic/English seeders that may adopt the validators module

tech-stack:
  added: []
  patterns:
    - "Fail-fast validation: collect ALL row errors before any DB write, raise ValueError with full report"
    - "csv.DictReader None-safety: use (row.get(key) or '') pattern — empty cells yield None not empty string"
    - "Delimiter auto-detection: .tsv extension → tab, everything else → comma"
    - "Morphology JSONB: optional columns (root, form, gender, aspect, aspect_partner) merged into JSON string"
    - "Translations dict: always includes 'en' key, locale columns (definition_ru/ar/es/pt) added when non-empty"

key-files:
  created:
    - backend/services/seeder/validators.py
    - backend/services/seeder/csv_importer.py
    - backend/tests/test_csv_importer.py
    - backend/tests/fixtures/valid_vocab.csv
    - backend/tests/fixtures/invalid_vocab.csv
    - backend/tests/fixtures/arabic_vocab_sample.csv
  modified:
    - backend/services/seeder/run.py

key-decisions:
  - "Fail-fast validation: all errors are collected before any DB write; ValueError lists every failure so user fixes CSV in one round-trip"
  - "Script validation uses Unicode block ranges not library detection — lightweight, no extra deps"
  - "DictReader None-safety: (row.get(col) or '') pattern used everywhere in transform — DictReader yields None for empty cells when column exists in header"
  - "Unknown language codes skip script validation rather than failing — forward-compatible for new languages"

patterns-established:
  - "csv.DictReader None coercion: always use (row.get(key) or '') not row.get(key, '') for nullable cell values"
  - "Row numbers in errors start at 2 (header occupies row 1) — matches what a spreadsheet user sees"

requirements-completed: [SEED-04]

duration: 4min
completed: 2026-03-14
---

# Phase 3 Plan 04: Generic CSV/TSV Importer with Validation Summary

**Fail-fast CSV/TSV vocabulary importer with Unicode script validation (Arabic/Cyrillic/Latin), full schema enforcement, and 53 tests covering all validation and transform paths**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-14T15:28:17Z
- **Completed:** 2026-03-14T15:32:06Z
- **Tasks:** 4
- **Files modified:** 7

## Accomplishments

- `validators.py` provides regex-based script validation for Arabic, Cyrillic, and Latin characters plus `VALID_POS` / `VALID_LEVELS` sets used by the importer
- `CSVImporter` collects all row-level errors before any DB write; raises `ValueError` with a full, line-numbered report so the user fixes CSV in one round-trip
- CLI `--file/-f` flag added to `run.py` — `python -m backend.services.seeder.run --file vocab.csv --language ar` is now the fast path for adding Arabic vocabulary
- 53 tests pass covering script validation, required-field checks, duplicates, POS/CEFR/frequency validation, morphology JSONB mapping, locale translation columns, pipe-split alternatives, TSV vs CSV delimiter detection, and rank-to-level fallback

## Task Commits

1. **Task 1: Script validation utilities** - `b06777c` (feat)
2. **Task 2: CSV importer implementation** - `1548e0a` (feat)
3. **Task 3: Wire into CLI runner** - `7fab040` (feat)
4. **Task 4: Tests and fixtures** - `74f6e7c` (feat)

## Files Created/Modified

- `backend/services/seeder/validators.py` — ARABIC/CYRILLIC/LATIN regexes, VALID_POS, VALID_LEVELS, ValidationError, validate_script()
- `backend/services/seeder/csv_importer.py` — CSVImporter(BaseSeeder): download/validate/transform pipeline
- `backend/services/seeder/run.py` — added `--file`/`-f` argument, CSVImporter routing
- `backend/tests/test_csv_importer.py` — 53 tests across TestValidateScript, TestValidationError, TestCSVImporterValidate, TestCSVImporterTransform
- `backend/tests/fixtures/valid_vocab.csv` — 10 valid English rows with alternatives and locale translations
- `backend/tests/fixtures/invalid_vocab.csv` — 8 rows with missing fields, bad POS/level, negative frequency, duplicates
- `backend/tests/fixtures/arabic_vocab_sample.csv` — 5 Arabic rows with morphology and Russian translations

## Decisions Made

- **Fail-fast over partial load:** All rows are validated before any DB write. A file with even one error produces no inserts. This avoids partial-state problems and forces the user to have a clean file.
- **Unknown language codes skip script validation:** `validate_script()` returns `None` for language codes not in `SCRIPT_VALIDATORS`. This makes the importer forward-compatible with new languages without code changes.
- **DictReader None-safety via `(row.get(col) or '')`:** Python's `csv.DictReader` yields `None` (not `""`) for empty cells when the column header exists. The `dict.get(key, default)` form does not help because the key is present. All optional cell reads use the `or ''` coercion pattern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DictReader None-safety for empty optional cells**
- **Found during:** Task 4 (running tests against valid_vocab.csv fixture)
- **Issue:** `row.get(col, "").strip()` raises `AttributeError: 'NoneType' object has no attribute 'strip'` when a column header exists but the cell is empty — DictReader sets the value to `None`, not `""`. `dict.get(key, default)` only uses the default when the key is absent, not when its value is `None`.
- **Fix:** Changed all optional cell reads in `transform()` to `(row.get(col) or "").strip()` pattern
- **Files modified:** `backend/services/seeder/csv_importer.py`
- **Verification:** All 53 tests pass
- **Committed in:** `74f6e7c` (Task 4 commit)

**2. [Rule 1 - Bug] CSV fixture column alignment error**
- **Found during:** Task 4 (first test run)
- **Issue:** `valid_vocab.csv` had `walk|jog` in the `aspect_partner` column and `walk` in `alternatives` for the `run` row — columns were off by one during fixture authoring
- **Fix:** Rewrote fixture row to align `walk|jog` under `alternatives` column
- **Files modified:** `backend/tests/fixtures/valid_vocab.csv`
- **Verification:** `test_pipe_separated_alternatives_parsed` and `test_empty_morphology_columns_not_stored` pass
- **Committed in:** `74f6e7c` (Task 4 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs found during test execution)
**Impact on plan:** Both fixes are correctness requirements. No scope creep.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Generic CSV import path is now fully operational for any language
- Arabic vocabulary seeding can proceed immediately with the `arabic_vocab_sample.csv` fixture pattern
- `validators.py` constants (`VALID_POS`, `VALID_LEVELS`) available for reuse in any future form validation

---
*Phase: 03-seed-data-pipeline*
*Completed: 2026-03-14*
