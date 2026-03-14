---
phase: 02-nlp-backends-and-answer-validation
plan: "04"
subsystem: nlp
tags: [nlp, english, spacy, lemminflect, morphology, articles]

requires:
  - phase: 02-nlp-backends-and-answer-validation
    provides: BaseNLP ABC, AnswerResult enum, NLP registry (02-01)
  - phase: 02-nlp-backends-and-answer-validation
    provides: Failing English test contracts (02-00 RED phase)

provides:
  - EnglishNLP backend with spaCy lemmatization and lemminflect inflection in backend/services/nlp/english.py
  - Leading article stripping (the/a/an) in normalization
  - Irregular verb/noun handling via spaCy en_core_web_sm model

affects:
  - None (final backend in Phase 2)

tech-stack:
  added:
    - spacy>=3.7 (English NLP pipeline)
    - lemminflect>=0.2.3 (English inflection generation)
    - en_core_web_sm (spaCy model)
  patterns:
    - "Leading article stripping in normalize() — case-insensitive, only first occurrence"
    - "lemminflect side-effect import registers spaCy token extensions"
    - "getAllInflections for morphological family — covers irregulars (went, gone, mice)"

key-files:
  created:
    - backend/services/nlp/english.py

key-decisions:
  - "normalize() strips leading articles (the/a/an) case-insensitively but only when followed by content"
  - "get_aspect_partner() always returns None — English has no aspect partner system"
  - "Graceful degradation: if spaCy unavailable, lemmatize falls back to word.lower()"
  - "Module-level spaCy load with separate ImportError/OSError handling for missing lib vs missing model"

requirements-completed: [NLP-09]

duration: 2min
completed: 2026-03-14
---

# Phase 2 Plan 04: English NLP Backend Summary

**EnglishNLP backend with spaCy lemmatization, lemminflect morphological family, and article-stripping normalization**

## Performance

- **Duration:** ~2 min
- **Completed:** 2026-03-14
- **Tasks:** 1 (single-file implementation)
- **Files created:** 1

## Accomplishments

- Created `backend/services/nlp/english.py` with `EnglishNLP(BaseNLP)` implementing all 4 abstract methods
- normalize(): lowercase, strip whitespace, strip leading articles (the/a/an) case-insensitively
- lemmatize(): spaCy en_core_web_sm for irregular verbs (went→go) and plurals (mice→mouse)
- get_morphological_family(): lemminflect getAllInflections for complete inflection enumeration
- get_aspect_partner(): always returns None (English has no aspect system)
- All 28 English NLP tests pass (RED → GREEN)

## Task Commits

1. **EnglishNLP backend implementation** — `bb7a7f3` (feat)

## Deviations from Plan

None.

## Issues Encountered

None.

---
*Phase: 02-nlp-backends-and-answer-validation*
*Completed: 2026-03-14*
