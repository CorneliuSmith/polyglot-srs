---
phase: 03-seed-data-pipeline
plan: "01"
subsystem: database
tags: [asyncpg, pymorphy3, httpx, openrussian, tsv, seed, upsert, cefr]

requires:
  - phase: 01-schema-auth-and-srs-engine
    provides: vocabulary and translations tables with JSONB morphology field
  - phase: 02-nlp-backends-and-answer-validation
    provides: pymorphy3 morphological analysis used in RussianSeeder.transform()

provides:
  - BaseSeeder ABC with download/transform/load/run template pattern
  - RussianSeeder that downloads OpenRussian TSV and enriches with pymorphy3
  - CLI runner: python -m backend.services.seeder.run --language ru
  - UPSERT idempotency via vocabulary_language_word_unique constraint
  - CEFR level mapping from frequency rank (rank_to_level static method)
  - data/ directory with gitignore rules for large downloaded files

affects:
  - 03-02 (ArabicSeeder — inherits BaseSeeder)
  - 03-03 (EnglishSeeder — inherits BaseSeeder)
  - 04-api-and-review-loop (vocabulary data drives card generation)

tech-stack:
  added: [httpx (async HTTP downloads), asyncpg (UPSERT queries)]
  patterns:
    - Template method pattern — BaseSeeder.run() orchestrates download/transform/load
    - Module-level filename constants (WORDS_FILENAME, TRANSLATIONS_FILENAME) enable test patching without file system mocking
    - morphology as JSON string passed with ::jsonb cast to asyncpg

key-files:
  created:
    - backend/services/seeder/__init__.py
    - backend/services/seeder/base.py
    - backend/services/seeder/seed_russian.py
    - backend/services/seeder/run.py
    - backend/tests/test_seeder_base.py
    - backend/tests/test_seeder_russian.py
    - backend/tests/fixtures/ru_words_sample.tsv
    - backend/tests/fixtures/ru_translations_sample.tsv
    - supabase/migrations/20260314000000_vocabulary_unique_word.sql
    - data/.gitkeep
  modified:
    - .gitignore

key-decisions:
  - "WORDS_FILENAME and TRANSLATIONS_FILENAME as module-level constants so tests can patch DATA_DIR + filenames without filesystem mocking"
  - "morphology passed as JSON string to asyncpg with ::jsonb cast — asyncpg does not auto-serialize dicts for jsonb columns"
  - "reading=None when accented == bare — avoids redundant data in DB for words with no accent markers"
  - "CLI runner gracefully skips ar/en seeders with ImportError — supports incremental rollout as plans 03-02 and 03-03 land"
  - "rank_to_level boundaries: A1<=500, A2<=1500, B1<=3000, B2<=5000, C1>5000"

patterns-established:
  - "Seeder pattern: subclass BaseSeeder, implement language_code/download/transform, run() is inherited"
  - "Test patching pattern: patch DATA_DIR + WORDS_FILENAME + TRANSLATIONS_FILENAME via fixture_patch() ExitStack"

requirements-completed: [SEED-01, SEED-04]

duration: 9min
completed: 2026-03-14
---

# Phase 3 Plan 01: Seed Infrastructure + Russian Seeder Summary

**BaseSeeder ABC with template method pattern + RussianSeeder downloading OpenRussian TSV, enriching with pymorphy3 morphology (gender/aspect/animacy), and UPSERTing via asyncpg into vocabulary/translations tables**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-14T15:15:39Z
- **Completed:** 2026-03-14T15:25:08Z
- **Tasks:** 5 (+ Task 4 tests written inline via TDD)
- **Files modified:** 11

## Accomplishments

- BaseSeeder ABC with `download()`, `transform()`, `load()`, `run()` template pattern and `rank_to_level()` CEFR mapper
- RussianSeeder parsing OpenRussian TSV with disabled-word filtering, accent/reading handling, pymorphy3 POS/gender/aspect/animacy enrichment, and multi-locale translation mapping
- UPSERT idempotency: new migration adds `UNIQUE (language_id, word)` constraint; `load()` uses `ON CONFLICT ... DO UPDATE`
- CLI runner supporting `--language ru|ar|en|all` with graceful skip for not-yet-implemented seeders
- 30 tests passing: 16 for BaseSeeder (rank_to_level boundaries, abstract enforcement) + 14 for RussianSeeder (transform, morphology, translations)

## Task Commits

Each task was committed atomically:

1. **Task 0: UNIQUE constraint migration** - `cde6863` (chore)
2. **Task 1: BaseSeeder infrastructure + tests** - `73622e1` (feat, TDD)
3. **Task 2: RussianSeeder + tests + fixtures** - `0b3f423` (feat, TDD)
4. **Task 3: CLI runner** - `accd058` (feat)
5. **Task 5: Data directory + .gitignore** - `957bcdf` (chore)

_Task 4 (tests) was implemented inline via TDD in Tasks 1 and 2._

## Files Created/Modified

- `supabase/migrations/20260314000000_vocabulary_unique_word.sql` — UNIQUE constraint on vocabulary(language_id, word)
- `backend/services/seeder/__init__.py` — Package init
- `backend/services/seeder/base.py` — BaseSeeder ABC with UPSERT load() and rank_to_level()
- `backend/services/seeder/seed_russian.py` — RussianSeeder: downloads OpenRussian TSV, transforms with pymorphy3
- `backend/services/seeder/run.py` — CLI runner: `python -m backend.services.seeder.run --language ru`
- `backend/tests/test_seeder_base.py` — 16 tests for BaseSeeder (rank_to_level, abstract enforcement)
- `backend/tests/test_seeder_russian.py` — 14 tests for RussianSeeder (fixture-based, no network)
- `backend/tests/fixtures/ru_words_sample.tsv` — 10-row fixture (1 disabled)
- `backend/tests/fixtures/ru_translations_sample.tsv` — Corresponding multi-locale translations
- `data/.gitkeep` — Tracks data/ directory in git
- `.gitignore` — Adds rules to ignore large downloaded TSV files, allow curated data files

## Decisions Made

- **WORDS_FILENAME/TRANSLATIONS_FILENAME as module-level constants:** Enables `patch()` in tests to redirect seeder to fixture files without touching the filesystem or mocking `open()`.
- **morphology as JSON string + ::jsonb cast:** asyncpg doesn't auto-serialize Python dicts to JSONB; passing `json.dumps()` output with explicit `::jsonb` cast is required.
- **reading=None when accented == bare:** Words where OpenRussian provides the same accented form as the base form carry no accent information — storing None is cleaner than redundant data.
- **CLI gracefully skips missing seeders:** `ImportError` on `seed_arabic`/`seed_english` prints SKIP instead of crashing, supporting incremental delivery across plans 03-02 and 03-03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] morphology JSONB requires explicit ::jsonb cast in asyncpg**
- **Found during:** Task 1 (BaseSeeder load() implementation)
- **Issue:** Plan showed `$7` for the morphology parameter but asyncpg does not auto-cast Python strings/dicts to PostgreSQL JSONB. Without `::jsonb` the INSERT would fail at runtime.
- **Fix:** Changed the INSERT to use `$7::jsonb` in the SQL and ensured morphology is always passed as a `json.dumps()` string.
- **Files modified:** `backend/services/seeder/base.py`
- **Verification:** 30 tests pass including morphology JSON string validation test.
- **Committed in:** `73622e1`

**2. [Rule 1 - Bug] Test fixture had incorrect level expectation for rank 1600**
- **Found during:** Task 2 (test_level_derived_from_rank)
- **Issue:** Test asserted `книга` (rank 1600) maps to A2 but `rank_to_level(1600)` correctly returns B1 (boundary is `rank <= 1500` for A2).
- **Fix:** Updated test assertion to `"B1"` with a clarifying comment.
- **Files modified:** `backend/tests/test_seeder_russian.py`
- **Verification:** Test passes with corrected assertion.
- **Committed in:** `0b3f423`

**3. [Rule 1 - Bug] Test fixture translation data contradicted test assertion**
- **Found during:** Task 2 (test_word_with_no_translations_has_empty_dict)
- **Issue:** Test asserted `работать` has no translations, but the fixture had a translation row for word_id=8 (работать).
- **Fix:** Removed word_id=8 from `ru_translations_sample.tsv` so работать has no translations in the fixture.
- **Files modified:** `backend/tests/fixtures/ru_translations_sample.tsv`
- **Verification:** Test passes — `работать["translations"] == {}`.
- **Committed in:** `0b3f423`

---

**Total deviations:** 3 auto-fixed (1 missing critical, 2 bugs)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None — no external service configuration required for this plan. The seed script requires `DATABASE_URL` at runtime (documented in CLI help), but no credentials need to be configured for tests.

## Next Phase Readiness

- BaseSeeder is fully operational. Plans 03-02 (ArabicSeeder) and 03-03 (EnglishSeeder) can subclass it immediately.
- CLI runner already handles `--language ar` and `--language en` with graceful ImportError skip.
- Fixture pattern established (fixture_patch() ExitStack) — reuse in 03-02 and 03-03 tests.
- Migration is applied and UPSERT constraint is in place.

## Self-Check: PASSED

All created files verified present on disk. All 5 task commits verified in git log.

---
*Phase: 03-seed-data-pipeline*
*Completed: 2026-03-14*
