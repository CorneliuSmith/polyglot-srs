# Decision log

Short records of choices that constrain future work — why something is the
way it is, what else was considered, and what it cost. The convention is
called an **ADR** (Architecture Decision Record).

Numbered in the order they were written. A decision that gets reversed later
is not deleted; it is marked superseded and the new one links back, because
the reasoning that turned out to be wrong is usually more instructive than
the reasoning that held.

Written via the `explain-decisions` skill (`.claude/skills/explain-decisions/`),
which also carries the template.

| # | Decision |
|---|----------|
| [0001](0001-probe-tables-instead-of-catching-errors.md) | Ask whether a table exists; don't find out by failing |
| [0002](0002-a-failed-translation-is-not-a-finished-one.md) | A failed translation is not a finished one |
| [0003](0003-offline-belongs-in-the-web-layer.md) | Offline belongs in the web layer, not in a new native app |
| [0004](0004-the-toggle-governs-the-backlog-not-the-learner.md) | The auto-translate toggle governs the backlog, not the learner |

## Dated records — owner decisions and handovers

Not ADRs: standing instructions from the owner, and end-of-pass handovers
written for the next session. Read the newest first.

- [2026-09-08](2026-09-08-markdown-batch-5.md) — the last nine courses; 26 of 27 done, 1,623 content corrections in all; the restraint guard rebuilt on whether a bold names the taught form
- [2026-09-07](2026-09-07-markdown-batch-4.md) — ar, he, fa, hi, th, tr, sw: 207 of 310 formatted, 539 content corrections, 20 refusals mostly invented rules
- [2026-09-07](2026-09-07-markdown-batch-3.md) — nl, ca, ro, el, ru: 148 of 222 formatted, 412 content corrections, and the restraint guard rebuilt on the right signal
- [2026-09-07](2026-09-07-markdown-batch-2.md) — es, it, pt, de through the markdown pass: 104 of 174 explanations formatted, 151 content corrections
- [2026-09-07](2026-09-07-fr-markdown-pass.md) — French explanations formatted and corrected: 20 of 42 render as markdown, 13 content fixes, four paradigms had no vous form
- [2026-09-07](2026-09-07-file-headword-repairs.md) — 56 of 65 committed-file headwords repaired; the Romanian noun/verb fold the course can only card once
- [2026-09-07](2026-09-07-unmarked-twins.md) — the 678 unmarked twins judged: 386 retired, 65 file defects found, 223 real words left alone (decision D option 3)
- [2026-09-07](2026-09-07-turkish-harmony-one-card.md) — Turkish harmony spellings are one card; the sentence fixes the shape (CHECKS §30)
- [2026-09-06](2026-09-06-review-pass.md) — old versus modern: the card draws the old sentence first (CHECKS §26); the ordered queue for implementation
- [2026-09-04](2026-09-04-one-staff-console.md) — one staff console
- [2026-08-30](2026-08-30-content-push-and-gloss-pass.md) — the production push ran; the gloss pass 16% → 73%
- [2026-08-26](2026-08-26-owner-decisions.md) — four owner decisions (push gate — superseded in practice 30 Aug — English thinning, Semitic romanisation, Thai phonetics)
