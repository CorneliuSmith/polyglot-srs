---
phase: 02-nlp-backends-and-answer-validation
plan: "02"
subsystem: nlp
tags: [nlp, russian, pymorphy3, cyrtranslit, morphology, transliteration, aspect]

requires:
  - phase: 02-nlp-backends-and-answer-validation
    provides: BaseNLP ABC, AnswerResult enum, NLP registry (02-01)
  - phase: 02-nlp-backends-and-answer-validation
    provides: Failing Russian test contracts (02-00 RED phase)

provides:
  - RussianNLP backend with pymorphy3 morphological analysis in backend/services/nlp/russian.py
  - Latin-to-Cyrillic transliteration pre-check returning CORRECT_SLOPPY
  - Aspect partner detection from card_context morphology JSONB

affects:
  - 02-04-english-nlp (reference pattern for language backend implementation)

tech-stack:
  added:
    - pymorphy3>=2.0 (Russian morphological analyzer)
    - cyrtranslit>=1.1 (Latin to Cyrillic transliteration)
  patterns:
    - "Transliteration pre-check in overridden check_answer before super() call"
    - "Aspect partner from card_context only — pymorphy3 doesn't provide aspect data"
    - "Module-level MorphAnalyzer singleton (loaded once)"

key-files:
  created:
    - backend/services/nlp/russian.py

key-decisions:
  - "normalize() is lowercase + strip only — standard Cyrillic has no diacritics to strip"
  - "get_aspect_partner reads from card_context['morphology']['aspect_partner'] only — does NOT compute from pymorphy3 (research pitfall #2)"
  - "Transliteration pre-check only fires when input is ASCII — avoids false positives on Cyrillic input"
  - "Module-level _morph and cyrtranslit wrapped in try/except for graceful fallback"

requirements-completed: [NLP-03, NLP-04, NLP-05]

duration: 2min
completed: 2026-03-14
---

# Phase 2 Plan 02: Russian NLP Backend Summary

**RussianNLP backend with pymorphy3 lemmatization, morphological family, Latin-to-Cyrillic transliteration, and aspect partner detection**

## Performance

- **Duration:** ~2 min
- **Completed:** 2026-03-14
- **Tasks:** 1 (single-file implementation)
- **Files created:** 1

## Accomplishments

- Created `backend/services/nlp/russian.py` with `RussianNLP(BaseNLP)` implementing all 4 abstract methods
- normalize(): lowercase + strip (no diacritics in standard Cyrillic)
- lemmatize(): pymorphy3 `morph.parse(word)[0].normal_form` — handles nouns, verbs, adjectives
- get_morphological_family(): pymorphy3 lexeme enumeration — returns all inflected forms as a set
- get_aspect_partner(): reads `card_context["morphology"]["aspect_partner"]` — no computation from pymorphy3
- Overridden check_answer() with transliteration pre-check: ASCII input → cyrtranslit → compare → CORRECT_SLOPPY with "Use Cyrillic next time" nudge
- All 24 Russian NLP tests pass (RED → GREEN)

## Task Commits

1. **RussianNLP backend implementation** — `8e35939` (feat)

## Deviations from Plan

None.

## Issues Encountered

None.

---
*Phase: 02-nlp-backends-and-answer-validation*
*Completed: 2026-03-14*
