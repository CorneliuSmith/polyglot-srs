---
phase: "03"
plan: "02"
subsystem: seed-data-pipeline
completed: "2026-03-14T15:33:05Z"
duration_min: 8
tasks_completed: 4
files_created: 4
files_modified: 0
tags: [arabic, seeder, vocabulary, morphology, seed-data]
requirements: [SEED-02]

dependency_graph:
  requires: [03-01]
  provides: [arabic-seed-data, arabic-seeder]
  affects: []

tech_stack:
  added: []
  patterns:
    - curated-bundled-seed-file
    - optional-camel-tools-enrichment
    - ExitStack-patch-helper

key_files:
  created:
    - data/ar_seed.json
    - backend/services/seeder/seed_arabic.py
    - backend/tests/test_seeder_arabic.py
    - backend/tests/fixtures/ar_seed_sample.json
  modified: []

key_decisions:
  - "Curated 225-word seed instead of Arabic Wordnet — better quality, stable, under 100 KB"
  - "transform() self-references module-level DATA_DIR (same pattern as RussianSeeder) so tests can patch path"
  - "None values stripped from morphology with 'if v is not None' (not 'if v') to preserve falsy strings"
  - "camel-tools enrichment uses setdefault — seed file morphology takes priority over analyzer output"
  - "_SampleDir helper class used in tests to redirect ar_seed.json reads to ar_seed_sample.json fixture"
---

# Phase 3 Plan 02: Arabic Seeder Summary

**One-liner:** ArabicSeeder with 225-word curated seed file covering Forms I-X, noun gender, CEFR ranking, and graceful camel-tools fallback.

## What Was Built

### data/ar_seed.json (225 entries, 31.7 KB)

Curated high-frequency Arabic vocabulary covering A1-B1 range:
- 49 verbs across Forms I, II, III, IV, V, VIII, X
- 97 nouns with gender (m/f) marked
- 25 adjectives with root
- 43 particles and adverbs
- 11 common phrases and greetings
- All 225 entries have English translations and tashkeel readings

### backend/services/seeder/seed_arabic.py

`ArabicSeeder(BaseSeeder)` with:
- `language_code = "ar"`
- `download()` — validates bundled seed file exists; raises `FileNotFoundError` with clear message if absent
- `transform()` — parses JSON, builds morphology JSONB from seed fields (root, form, gender, pattern), optionally enriches via camel-tools Analyzer; strips None values cleanly

### backend/tests/test_seeder_arabic.py (20 tests)

Full coverage:
- Language code, download success/failure
- Transform output: word, reading, POS, frequency_rank, level mapping
- Morphology JSONB: root present for verbs, form I and X, gender m/f for nouns, no None values
- All records have English translation
- Graceful degradation: two tests mock ImportError for camel_tools and verify seed-file morphology still populated

### backend/tests/fixtures/ar_seed_sample.json (10 words)

Fixture covering: verb (Form I, V, X), noun (m, f, no root), adjective, particle, phrase — all edge cases exercised.

## Decisions Made

| Decision | Rationale |
|---|---|
| Curated seed over Arabic Wordnet | Wordnet XML is complex, URLs unstable, frequency ranking poor |
| 225 words over 500 | Quality + size trade-off; covers A1-B1 fully at 31.7 KB |
| `setdefault` for camel-tools enrichment | Seed file morphology (human-verified) takes priority over analyzer |
| `if v is not None` (not `if v`) | Preserves legitimate falsy strings while stripping None |
| `_SampleDir` helper in tests | Clean redirection of `ar_seed.json` to sample fixture without temp files |

## Verification Results

- [x] `pytest backend/tests/test_seeder_arabic.py` — 20/20 passed
- [x] `ArabicSeeder.transform()` produces records with root in morphology JSONB
- [x] Seed file exists and is valid JSON (225 entries, 31.7 KB)
- [x] Works without camel-tools installed (graceful degradation tested)
- [x] All 225 records have at least one English translation

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist:
- data/ar_seed.json: FOUND
- backend/services/seeder/seed_arabic.py: FOUND
- backend/tests/test_seeder_arabic.py: FOUND
- backend/tests/fixtures/ar_seed_sample.json: FOUND

Commits:
- bc3d069: feat(03-02): add curated Arabic seed data with 225 high-frequency words
- 3273b1c: feat(03-02): implement ArabicSeeder with camel-tools enrichment fallback
- 991c487: test(03-02): add 20 tests for ArabicSeeder
