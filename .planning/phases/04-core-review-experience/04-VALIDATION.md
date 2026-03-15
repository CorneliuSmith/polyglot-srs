---
phase: 04
slug: core-review-experience
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 04 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend), vitest (frontend) |
| **Config file** | pyproject.toml (backend), vitest.config.ts (frontend -- Wave 0 installs) |
| **Quick run command** | `python -m pytest backend/tests/ -x -q` and `npx vitest run --reporter=verbose` |
| **Full suite command** | `python -m pytest backend/tests/ -v && npx vitest run` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command for relevant layer (backend or frontend)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | REV-01, REV-07 | integration | `pytest backend/tests/test_review_endpoints.py` | No (W0) | pending |
| 04-01-02 | 01 | 1 | REV-04, REV-05, UX-01 | integration | `pytest backend/tests/test_review_endpoints.py backend/tests/test_dashboard_endpoint.py` | No (W0) | pending |
| 04-02-01 | 02 | 1 | PROF-02 | build | `cd frontend && npx vite build` | No (W0) | pending |
| 04-02-02 | 02 | 1 | PROF-02 | build | `cd frontend && npx vite build` | No (W0) | pending |
| 04-03-01 | 03 | 2 | UX-01 | build | `cd frontend && npx vite build` | No (W0) | pending |
| 04-03-02 | 03 | 2 | REV-07, REV-08 | component | `cd frontend && npx vitest run --reporter=verbose` | No (W0) | pending |
| 04-04-01 | 04 | 3 | REV-02, REV-03, REV-04, REV-05, REV-06 | component | `cd frontend && npx vitest run --reporter=verbose` | No (W0) | pending |
| 04-04-02 | 04 | 3 | REV-03, REV-06 | component | `cd frontend && npx vitest run --reporter=verbose` | No (W0) | pending |
| 04-05-01 | 05 | 4 | UX-02, UX-03 | component | `cd frontend && npx vitest run --reporter=verbose` | No (W0) | pending |
| 04-05-02 | 05 | 4 | UX-08 | build + visual | `cd frontend && npx vite build` + manual | N/A | pending |
| 04-05-03 | 05 | 4 | UX-02, UX-03, UX-08 | visual | Manual -- responsive breakpoints, RTL, keyboards | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `frontend/` -- Vite + React + Tailwind v4 project scaffold
- [ ] `frontend/vitest.config.ts` -- vitest configuration
- [ ] `frontend/src/test/setup.ts` -- test setup with jsdom
- [ ] `package.json` -- vitest, @testing-library/react, jsdom dependencies

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RTL layout renders correctly | UX-02 | Visual verification needed | Open Arabic language, verify text direction, mirrored layout |
| Mobile responsiveness | UX-08 | Visual at breakpoints | Test at 320px, 375px, 768px widths -- all touch targets 44px+ |
| On-screen keyboard usability | UX-03 | Input interaction | Type Arabic/Russian via on-screen keyboard, verify characters appear correctly |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
