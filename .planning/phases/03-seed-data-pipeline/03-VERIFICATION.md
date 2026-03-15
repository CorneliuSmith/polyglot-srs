---
phase: 03-seed-data-pipeline
verified: 2026-03-14T16:00:00Z
status: gaps_found
score: 2/4 success criteria verified
gaps:
  - truth: "Arabic vocabulary is loaded from Arabic Wordnet + OpenSubtitles frequency list with root extraction and morphology JSONB populated"
    status: failed
    reason: "Implementation uses a curated 225-word JSON file instead of the specified Arabic Wordnet + OpenSubtitles sources. REQUIREMENTS.md marks SEED-02 as Pending. ROADMAP success criterion SC-2 specifies a different data source than what was delivered. The data quality is good and morphology is correctly populated, but the stated source contract is unmet."
    artifacts:
      - path: "data/ar_seed.json"
        issue: "225-word curated file, not Arabic Wordnet + OpenSubtitles. Source change is undocumented in REQUIREMENTS.md."
      - path: "backend/services/seeder/seed_arabic.py"
        issue: "Reads bundled ar_seed.json rather than downloading from Wordnet/OpenSubtitles. Functional, but wrong source per spec."
    missing:
      - "Either: update REQUIREMENTS.md SEED-02 to reflect the curated-file approach and mark it complete, OR implement the originally specified Arabic Wordnet + OpenSubtitles sources"
      - "REQUIREMENTS.md checkbox for SEED-02 must be checked off"
  - truth: "English vocabulary is loaded from COCA frequency list + WordNet definitions with lemma and morphology data"
    status: partial
    reason: "Implementation correctly uses WordNet definitions but uses a public-domain subtitle frequency list instead of the specified COCA frequency list. REQUIREMENTS.md marks SEED-03 as Pending. The delivered frequency list (3000 words) and WordNet integration are fully functional, but the source contract differs from the spec."
    artifacts:
      - path: "data/en_frequency.tsv"
        issue: "3000-word subtitle-derived frequency list, not COCA. Source is not documented as a deliberate deviation."
      - path: "backend/services/seeder/seed_english.py"
        issue: "Functional implementation with WordNet (correct) but references subtitle-based frequency list (not COCA)."
    missing:
      - "Either: update REQUIREMENTS.md SEED-03 to reflect the alternative frequency source and mark it complete, OR replace en_frequency.tsv with COCA-derived data"
      - "REQUIREMENTS.md checkbox for SEED-03 must be checked off"
  - truth: "Russian vocabulary includes aspect partner data in morphology JSONB"
    status: failed
    reason: "ROADMAP SC-1 specifies 'morphology JSONB (including aspect partner data)'. The implementation explicitly excludes aspect_partner from pymorphy3 morphology output. The 03-01-PLAN.md acknowledges this as a known limitation deferred to Phase 6. However, the ROADMAP success criterion is not met."
    artifacts:
      - path: "backend/services/seeder/seed_russian.py"
        issue: "morphology only includes gender, aspect, animacy — no aspect_partner key. pymorphy3 limitation acknowledged."
    missing:
      - "ROADMAP SC-1 should be updated to remove 'including aspect partner data' from Phase 3 scope, OR aspect_partner enrichment must be implemented"
      - "Alternatively: document in ROADMAP that aspect partner is deferred to Phase 6 (as noted in 03-01-PLAN.md)"
human_verification: []
---

# Phase 3: Seed Data Pipeline Verification Report

**Phase Goal:** The database contains usable vocabulary and grammar data for all three languages, ready for review sessions
**Verified:** 2026-03-14T16:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Russian vocabulary loaded from OpenRussian TSV with translations, morphology JSONB **including aspect partner data**, and frequency ranking | PARTIAL | Russian seeder exists, is substantive, and downloads OpenRussian TSV correctly. However, aspect_partner is explicitly absent from morphology — pymorphy3 does not provide it. 03-01-PLAN.md acknowledges this as a known limitation deferred to Phase 6, but ROADMAP SC-1 still requires it. |
| 2 | Arabic vocabulary loaded from **Arabic Wordnet + OpenSubtitles frequency list** with root extraction and morphology JSONB | FAILED | ArabicSeeder is fully implemented and morphology JSONB is correctly populated with root/form/gender. But source is a curated 225-word JSON file, not the specified Arabic Wordnet + OpenSubtitles. REQUIREMENTS.md SEED-02 is marked Pending (unchecked). |
| 3 | English vocabulary loaded from **COCA frequency list** + WordNet definitions with lemma and morphology data | PARTIAL | EnglishSeeder uses WordNet correctly and morphology includes lemma. But frequency source is a subtitle-derived list, not COCA. REQUIREMENTS.md SEED-03 is marked Pending (unchecked). |
| 4 | Seed scripts are repeatable (download, transform, load) and produce data shaped for the application schema | VERIFIED | BaseSeeder UPSERT pattern with `ON CONFLICT (language_id, word) DO UPDATE` is implemented and tested. All four seeders (ru, ar, en, csv) follow the template method pattern. Integration tests validate record shape matches vocabulary schema. 132 total tests across all plans. |

**Score:** 1/4 truths fully verified (SC-4). SC-1 is partial (aspect partner missing). SC-2 and SC-3 fail source contract — data exists but from different sources than specified.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/seeder/__init__.py` | Package init | VERIFIED | Exists |
| `backend/services/seeder/base.py` | BaseSeeder ABC with template methods | VERIFIED | 112 lines, full implementation: abstract download/transform, concrete load() with UPSERT, run() orchestrator, rank_to_level() |
| `backend/services/seeder/seed_russian.py` | RussianSeeder — OpenRussian TSV + pymorphy3 | VERIFIED | 119 lines, downloads from openrussian.org, transforms with pymorphy3 POS/gender/aspect/animacy, uses WORDS_FILENAME/TRANSLATIONS_FILENAME module constants for testability |
| `backend/services/seeder/seed_arabic.py` | ArabicSeeder — Arabic vocabulary with morphology | VERIFIED (source gap) | 74 lines, reads curated ar_seed.json, builds morphology JSONB with root/form/gender, camel-tools optional enrichment. Functional but source differs from SEED-02 spec |
| `backend/services/seeder/seed_english.py` | EnglishSeeder — WordNet + frequency list | VERIFIED (source gap) | 95 lines, WordNet synsets for definitions, FREQ_FILENAME constant, spaCy POS optional. Functional but frequency source differs from SEED-03 spec |
| `backend/services/seeder/validators.py` | Script validation for Arabic/Cyrillic/Latin | VERIFIED | 55 lines, ARABIC/CYRILLIC/LATIN regex patterns, VALID_POS, VALID_LEVELS, ValidationError class, validate_script() |
| `backend/services/seeder/csv_importer.py` | Generic CSV/TSV importer with fail-fast validation | VERIFIED | 177 lines, DictReader None-safety via `(row.get(key) or '')`, fail-fast validation, script checking, morphology JSONB mapping, multi-locale translations |
| `backend/services/seeder/run.py` | CLI runner with --language and --file flags | VERIFIED | 81 lines, argparse with --language (ru/ar/en/all) and --file/-f, routes to CSVImporter or language seeders, graceful ImportError skip |
| `supabase/migrations/20260314000000_vocabulary_unique_word.sql` | UNIQUE constraint for UPSERT idempotency | VERIFIED | `ALTER TABLE vocabulary ADD CONSTRAINT vocabulary_language_word_unique UNIQUE (language_id, word)` |
| `data/ar_seed.json` | Arabic vocabulary data | VERIFIED (source gap) | 225 entries, 227 lines, all entries have English translations and tashkeel readings, root/form/gender present |
| `data/en_frequency.tsv` | English frequency word list | VERIFIED (source gap) | 3001 lines (header + 3000 words), rank+word columns, starts with content words (time, person, year) |
| `data/.gitkeep` | Data directory tracking | VERIFIED | Exists |
| `backend/tests/test_seeder_base.py` | BaseSeeder tests | VERIFIED | 16 tests: rank_to_level boundary tests (all CEFR levels), abstract enforcement, stub instantiation |
| `backend/tests/test_seeder_russian.py` | RussianSeeder tests with fixtures | VERIFIED | 14 tests: transform, disabled word skip, accented reading, locale translations, pymorphy3 morphology enrichment |
| `backend/tests/test_seeder_arabic.py` | ArabicSeeder tests | VERIFIED | 20 tests: transform output, morphology JSONB, camel-tools graceful fallback |
| `backend/tests/test_seeder_english.py` | EnglishSeeder tests | VERIFIED | 14 tests: WordNet integration, POS mapping, morphology lemma |
| `backend/tests/test_seeder_integration.py` | Integration tests for all seeders | VERIFIED | 15 tests: all four seeder classes importable, CLI runner importable, record schema validation for ru/ar/en |
| `backend/tests/test_csv_importer.py` | CSV importer tests | VERIFIED | 53 tests: script validation, required fields, duplicates, POS/CEFR/frequency validation, morphology JSONB, locale translations, TSV vs CSV |
| `backend/tests/fixtures/ru_words_sample.tsv` | Russian word fixture | VERIFIED | 10 rows (1 disabled) |
| `backend/tests/fixtures/ru_translations_sample.tsv` | Russian translation fixture | VERIFIED | Exists |
| `backend/tests/fixtures/ar_seed_sample.json` | Arabic seed fixture | VERIFIED | 10 words covering verb/noun/adj/particle edge cases |
| `backend/tests/fixtures/en_frequency_sample.tsv` | English frequency fixture | VERIFIED | Listed in test directory |
| `backend/tests/fixtures/valid_vocab.csv` | Valid CSV fixture | VERIFIED | Exists |
| `backend/tests/fixtures/invalid_vocab.csv` | Invalid CSV fixture | VERIFIED | Exists |
| `backend/tests/fixtures/arabic_vocab_sample.csv` | Arabic CSV fixture | VERIFIED | Exists |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `RussianSeeder.transform()` | `seed_russian.WORDS_FILENAME` / `TRANSLATIONS_FILENAME` | module-level constants patched in tests | WIRED | Tests use `patch("backend.services.seeder.seed_russian.WORDS_FILENAME", ...)` pattern correctly |
| `ArabicSeeder.transform()` | `data/ar_seed.json` | `DATA_DIR / "ar_seed.json"` | WIRED | File exists at expected path, seeder references `_mod.DATA_DIR` for test patching |
| `EnglishSeeder.transform()` | `data/en_frequency.tsv` | `DATA_DIR / FREQ_FILENAME` | WIRED | File exists, FREQ_FILENAME constant enables test patching |
| `CSVImporter` | `BaseSeeder.load()` | inherits via `run()` | WIRED | CSVImporter extends BaseSeeder, transform() returns cleaned records, run() calls load() |
| `run.py --file` | `CSVImporter` | `from .csv_importer import CSVImporter` | WIRED | `if args.file:` branch imports and routes to CSVImporter correctly |
| `base.py load()` | vocabulary + translations tables | `ON CONFLICT (language_id, word) DO UPDATE` with `$7::jsonb` | WIRED | UPSERT query correct, `::jsonb` cast present, translations UPSERT on `(vocabulary_id, locale)` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|----------|
| SEED-01 | 03-01 | Russian seed data from OpenRussian TSV | SATISFIED | RussianSeeder downloads from openrussian.org, transforms with pymorphy3, loads via UPSERT. 14 tests passing. REQUIREMENTS.md checkbox is checked. |
| SEED-02 | 03-02 | Arabic seed data from Arabic Wordnet + OpenSubtitles | BLOCKED | ArabicSeeder is functional and morphology is correctly populated, but source is a curated 225-word JSON file — not Arabic Wordnet or OpenSubtitles. REQUIREMENTS.md checkbox is unchecked (Pending). The 03-02-PLAN.md documents the source substitution rationale but REQUIREMENTS.md was never updated. |
| SEED-03 | 03-03 | English seed data from COCA frequency list + WordNet | BLOCKED | EnglishSeeder uses WordNet (correct) but frequency source is subtitle-derived, not COCA. REQUIREMENTS.md checkbox is unchecked (Pending). No documented deviation in REQUIREMENTS.md. |
| SEED-04 | 03-01, 03-03, 03-04 | Seed scripts download, transform, load — data shaped for schema | SATISFIED | BaseSeeder template pattern with UPSERT, CLI runner, integration tests validating all seeders produce schema-conformant records. REQUIREMENTS.md checkbox is checked. |

**Orphaned requirements check:** REQUIREMENTS.md maps SEED-01 through SEED-04 to Phase 3. All four appear in plan frontmatter. No orphaned requirements.

**REQUIREMENTS.md staleness:** SEED-02 and SEED-03 remain marked Pending in REQUIREMENTS.md despite implementations existing. This is a documentation gap — either the requirements need updating to reflect the source substitutions (with the checkboxes checked), or the implementations need to be replaced with the originally specified sources.

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | — |

No TODO/FIXME/placeholder/stub anti-patterns found in any seeder implementation file. All methods contain substantive implementations. The `download()` no-op in `ArabicSeeder` and `CSVImporter` is intentional design (bundled file / user-provided file), not a stub.

---

## Human Verification Required

None — all automated checks are sufficient for this phase. The seed scripts require a live DATABASE_URL to run end-to-end, but the unit and integration tests fully validate the transform pipeline without a live database. The data files are committed and verified by file inspection.

---

## Gaps Summary

Three gaps block the phase goal as specified by ROADMAP success criteria and REQUIREMENTS.md:

**Gap 1 — SEED-02 source contract mismatch (FAILED):** The ROADMAP specifies "Arabic vocabulary loaded from Arabic Wordnet + OpenSubtitles frequency list." The delivered implementation uses a curated 225-word JSON file. The 03-02-PLAN.md explicitly justified this substitution ("Arabic Wordnet XML is complex, URLs are unstable, frequency ranking poor"), but this rationale was never reflected back into REQUIREMENTS.md. The checkbox for SEED-02 remains unchecked. The implementation is high-quality — the gap is a requirements documentation problem, not a functionality problem. Resolution: update REQUIREMENTS.md to reflect the deliberate source substitution and mark SEED-02 complete.

**Gap 2 — SEED-03 source contract mismatch (PARTIAL):** The ROADMAP specifies "COCA frequency list." The delivered en_frequency.tsv is a subtitle-derived public domain list. WordNet integration is correct. Same documentation gap as SEED-02. Resolution: update REQUIREMENTS.md to reflect the frequency source used and mark SEED-03 complete.

**Gap 3 — Russian morphology aspect partner missing (PARTIAL):** ROADMAP SC-1 specifies "morphology JSONB (including aspect partner data)." The 03-01-PLAN.md explicitly states: "pymorphy3 does not provide aspect partner data... aspect partner enrichment is deferred to Phase 6." The ROADMAP success criterion was not updated to remove this requirement from Phase 3 scope. Resolution: remove "including aspect partner data" from ROADMAP SC-1 for Phase 3 (it belongs in Phase 6), or add aspect_partner enrichment now.

**Root cause:** All three gaps share the same root cause — implementation decisions (justified source substitutions, known library limitations) were documented in PLAN files but not reflected back into REQUIREMENTS.md or ROADMAP success criteria. The code and tests are complete and high-quality; the documentation contract was not kept in sync.

**Recommended resolution path:** Update REQUIREMENTS.md to mark SEED-02 and SEED-03 as complete (with notes on source substitutions), and update ROADMAP Phase 3 SC-1 to remove the aspect_partner clause. This is a documentation fix, not a code fix, unless the original sources are strictly required.

---

*Verified: 2026-03-14T16:00:00Z*
*Verifier: Claude (gsd-verifier)*
