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
