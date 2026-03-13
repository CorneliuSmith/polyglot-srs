---
phase: 2
slug: nlp-backends-and-answer-validation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-13
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x with pytest-asyncio |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest backend/tests/test_nlp*.py -v --tb=short -x` |
| **Full suite command** | `python -m pytest backend/tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/test_nlp*.py -v --tb=short -x`
- **After every plan wave:** Run `python -m pytest backend/tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-00-01 | 00 | 0 | NLP-01..NLP-10 | scaffold | `python -m pytest backend/tests/test_nlp_base.py -x -q 2>&1 \| grep ERROR` | W0 creates | ⬜ pending |
| 02-00-02 | 00 | 0 | NLP-03..NLP-09 | scaffold | `python -m pytest backend/tests/test_nlp_russian.py backend/tests/test_nlp_arabic.py backend/tests/test_nlp_english.py -x -q 2>&1 \| grep ERROR` | W0 creates | ⬜ pending |
| 02-01-01 | 01 | 1 | NLP-01 | unit | `python -m pytest backend/tests/test_nlp_base.py -v` | ✅ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | NLP-02 | unit | `python -m pytest backend/tests/test_nlp_base.py -v` | ✅ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | NLP-03, NLP-04, NLP-05 | unit | `python -m pytest backend/tests/test_nlp_russian.py -v` | ✅ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | NLP-06, NLP-07, NLP-08 | unit | `python -m pytest backend/tests/test_nlp_arabic.py -v` | ✅ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | NLP-09 | unit | `python -m pytest backend/tests/test_nlp_english.py -v` | ✅ W0 | ⬜ pending |
| 02-04-02 | 04 | 2 | NLP-10 | integration | `python -m pytest backend/tests/test_nlp_base.py backend/tests/test_nlp_russian.py backend/tests/test_nlp_arabic.py backend/tests/test_nlp_english.py -x -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Plan

Plan 02-00 creates all four test files with failing tests (RED phase):
- [x] `backend/tests/test_nlp_base.py` — failing tests for NLP-01, NLP-02
- [x] `backend/tests/test_nlp_russian.py` — failing tests for NLP-03, NLP-04, NLP-05
- [x] `backend/tests/test_nlp_arabic.py` — failing tests for NLP-06, NLP-07, NLP-08
- [x] `backend/tests/test_nlp_english.py` — failing tests for NLP-09, NLP-10

Plans 02-01 through 02-04 depend on 02-00 and turn tests GREEN.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Arabic RTL rendering | NLP-06 | Visual inspection | Verify Arabic text displays correctly in terminal output |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (02-00-PLAN.md creates all test files)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
