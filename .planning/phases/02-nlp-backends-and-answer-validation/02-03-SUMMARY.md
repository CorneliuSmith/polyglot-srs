---
phase: 02-nlp-backends-and-answer-validation
plan: "03"
subsystem: nlp
tags: [nlp, arabic, camel-tools, morphology, tdd, diacritics, answer-validation]

# Dependency graph
requires:
  - phase: 02-nlp-backends-and-answer-validation
    plan: "01"
    provides: BaseNLP ABC with 6-layer check_answer pipeline and NLP registry
  - phase: 02-nlp-backends-and-answer-validation
    plan: "00"
    provides: Failing RED tests for Arabic backend (test_nlp_arabic.py)

provides:
  - ArabicNLP backend in backend/services/nlp/arabic.py extending BaseNLP
  - Diacritic-invariant normalize() stripping tashkeel, alef normalization, tatweel removal
  - camel-tools Analyzer-based lemmatize() with sense-ID stripping and fallback
  - Taa marbuta vs ha soft-match returning CORRECT_SLOPPY (not WRONG)
  - Verb form detection returning WRONG_FORM with root display when same root, different form
  - Graceful fallback stubs when camel-tools data not installed

affects:
  - backend/services/nlp/__init__.py (ArabicNLP registered as "ar" via init_nlp_backends)
  - Any card review pipeline using language_code="ar"

# Tech tracking
tech-stack:
  added:
    - camel-tools Analyzer (calima-msa-r13 builtin DB, backoff=NOAN_PROP)
    - camel_tools.utils.dediac.dediac_ar (tashkeel stripping)
    - camel_tools.utils.normalize.normalize_alef_ar (alef variant normalization)
  patterns:
    - "Module-level analyzer init wrapped in try/except — app starts even without camel_data installed"
    - "Fallback stubs (regex dediac + translate-table alef map) compile without camel-tools"
    - "Overridden check_answer runs parent pipeline then applies Arabic-specific post-processing"
    - "Taa marbuta check (A) before verb form check (B) — most specific match wins"
    - "Root extraction: prefer card_context['morphology']['root'] over analyzer output"

key-files:
  created:
    - backend/services/nlp/arabic.py
  modified: []

key-decisions:
  - "normalize() does not normalize taa marbuta (ة→ه) — per research pitfall #6 to avoid conflating distinct words"
  - "get_aspect_partner() always returns None — Arabic verb aspect handled through verb form detection, not Russian-style pairs"
  - "Fallback stubs provided for dediac_ar and normalize_alef_ar so the class can be imported without camel_data"
  - "check_answer override applies checks post-parent: taa marbuta first, then verb form — preserves base pipeline correctness"
  - "Root resolution priority: card_context.morphology.root > camel-tools analyzer (curator knowledge is most reliable)"

requirements-completed: [NLP-06, NLP-07, NLP-08]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 2 Plan 03: Arabic NLP Backend Summary

**ArabicNLP backend with camel-tools morphological analysis — diacritic-invariant normalization, taa marbuta soft-match, and verb form detection with root display**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-14
- **Completed:** 2026-03-14
- **Tasks:** 1 (GREEN implementation — RED tests created in plan 02-00)
- **Files created:** 1

## Accomplishments

- Created `backend/services/nlp/arabic.py` with `ArabicNLP(BaseNLP)` implementing all 4 abstract methods:
  - `normalize()`: strips tashkeel via `dediac_ar`, normalizes alef variants via `normalize_alef_ar`, removes tatweel (`\u0640`), strips whitespace. Does NOT normalize taa marbuta (research pitfall #6).
  - `lemmatize()`: uses camel-tools Analyzer sorted by `pos_lex_logprob`, extracts `lex` field, strips sense-ID suffix (e.g. `كَتَب_1` → `كتب`), falls back to `dediac_ar(word)` when analyzer unavailable or no analysis found.
  - `get_morphological_family()`: returns `{word, lemmatize(word)}` — minimal set; Analyzer-based Generator enumeration too slow for real-time use.
  - `get_aspect_partner()`: always returns `None` — Arabic uses verb form detection, not aspect pairs.
- Overrode `check_answer()` with two Arabic-specific post-processing checks:
  - **Check A (taa marbuta):** if `_taa_to_ha(norm_user) == _taa_to_ha(norm_correct)` and forms differ, returns `CORRECT_SLOPPY` with message about ة vs ه.
  - **Check B (verb form):** if parent returned `WRONG` and user/correct share the same root (from `card_context` or Analyzer), returns `WRONG_FORM` with formatted root display (`ك-ت-ب`).
- Module-level camel-tools initialization wrapped in `try/except` with fallback stubs — the class can be imported and used in basic tests without camel-tools data installed.
- `ArabicNLP` auto-registered as `"ar"` backend via the existing `init_nlp_backends()` importlib mechanism — no changes to registry code needed.

## Task Commits

Single implementation task (TDD GREEN phase):

1. **GREEN: ArabicNLP backend implementation** - `2b06531` (feat)

## Files Created/Modified

- `backend/services/nlp/arabic.py` (created, 344 lines) — ArabicNLP class with all normalization, lemmatization, and check_answer pipeline

## Decisions Made

- `normalize()` intentionally does not map taa marbuta to ha — they distinguish semantically different words (`مدرسة` vs `مدرسه`). The soft-match in `check_answer` handles the common learner error at the CORRECT_SLOPPY level, which is the right pedagogical signal.
- `get_aspect_partner()` returns `None` — Arabic has no Russian-style imperfective/perfective pairs. Verb form differences (Form I / Form III etc.) are caught by the verb form detection layer in the overridden `check_answer`.
- Root resolution prefers `card_context['morphology']['root']` over Analyzer output — card curators know the root, and the Analyzer can be ambiguous for rare words.
- Fallback stubs for `dediac_ar` and `normalize_alef_ar` use a regex and `str.translate` table respectively, covering the most common alef variants (أ, إ, آ, ٱ) without requiring camel-tools to be installed.

## Deviations from Plan

None — plan executed exactly as written. Implementation matches all spec behaviors from `<behavior>` and `<implementation>` sections.

## Issues Encountered

None. The implementation is structurally clean and all plan requirements are addressed in the single file created.

## User Setup Required

To use the Arabic backend in production:

```bash
pip install camel-tools
camel_data -i light
```

Requires: cmake, boost, and a Rust compiler as build dependencies. Python <= 3.12 only.

Without camel_data, the backend initializes in fallback mode — `normalize()` still works correctly (regex dediac + alef map), but `lemmatize()` returns the dediacritized input rather than the true lemma, and verb form detection (WRONG_FORM) is unavailable.

## Self-Check

- [x] `backend/services/nlp/arabic.py` created (344 lines, > 80-line minimum)
- [x] `ArabicNLP` class present and extends `BaseNLP`
- [x] All 4 abstract methods implemented: `normalize`, `lemmatize`, `get_morphological_family`, `get_aspect_partner`
- [x] `check_answer` overridden with taa marbuta and verb form checks
- [x] Module-level graceful fallback for missing camel-tools
- [x] Commit `2b06531` exists (feat(02-03))
- [x] No modifications needed to `__init__.py` — ArabicNLP auto-registered via existing `init_nlp_backends` importlib mechanism

## Self-Check: PASSED

---
*Phase: 02-nlp-backends-and-answer-validation*
*Completed: 2026-03-14*
