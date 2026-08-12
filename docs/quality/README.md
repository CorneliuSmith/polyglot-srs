# Content Quality Program

How we keep hints, questions, translations and reviews at one standard across
every language — and how to prove it, on demand, from a clean checkout.

Three things live here:

1. **Per-language standards** — `docs/quality/<code>.md`, one per course. What
   "good" means for that language, with its current debt written down honestly.
2. **An automated checker** — `backend/services/quality/audit_content.py`.
   Mechanical rules with a baseline ratchet, wired into CI.
3. **This plan** — the human + machine testing protocol, runnable end to end.

---

## Quick start

```bash
# 0. Fresh checkout
git pull

# 1. Mechanical content audit — all languages, human-readable
python -m backend.services.quality.audit_content

# 2. One language, in detail
python -m backend.services.quality.audit_content --language ca

# 3. The full gate (what CI runs)
.venv/bin/pytest backend/tests -q -p no:randomly
.venv/bin/ruff check backend/
cd frontend && npm run build && npx vitest run
```

The audit exits non-zero **only when a language regresses past its recorded
baseline**. Existing debt does not block you; adding new debt does.

---

## Why this exists

Three complaints, all the same shape — "the content or the process is
inconsistent and I cannot see it from here":

| Complaint | What it actually was |
| --- | --- |
| "Testers say they're submitting reviews; I don't see them" | Reviews arrive, then get filtered out of the admin's view (see below) |
| "Spanish hints give the answer away" | A real leak class, plus a legitimate convention that looks like one |
| "Catalan has gender problems" | Gender is carried in the morphology data but almost never surfaced in hints |
| "The Arabic may not be MSA" | Register was never written down, so nothing could enforce it |

None of these were visible to a test suite, because none of them were ever
*stated as a rule*. That is what this program fixes: every standard is written
per language, and every mechanically-checkable part of it is enforced.

---

## Layer 1 — Mechanical checks (fast, every commit)

`backend/services/quality/audit_content.py` scans all in-repo learning content
and reports per language. Rules, and why each exists:

**Fail-level** (blocks CI when it exceeds baseline):

| Rule | What it catches | Guard against false positives |
| --- | --- | --- |
| `leak_hard` | The answer appears in its own hint as a whole word | Substring matches inside a longer word are legitimate — `trabajar, él/ella` for answer `trabaja` is the standard "infinitive, person" convention |
| `self_answering` | Hints shaped `answer — explanation` | The single worst pattern found; it simply prints the answer |
| `giveaway_by_gloss` | A ≤3-word hint that already appears verbatim in the drill's own translation | For closed-class answers the hint then uniquely determines the answer |
| `duplicate_hint` | One hint mapped to several answers inside a point | Allomorph sets are exempt (Turkish `mı/mi/mu/mü` — the sentence disambiguates) |
| `empty` | Empty hint, translation or explanation | — |
| `ar_register` | Dialect markers in a course that teaches MSA | Whole-word matching only |

**Warn-level** (reported, never blocks):

`construction_quote` (hint quotes a multiword construction containing the
answer), `vague_translation` (translation far shorter than its sentence —
exempt for `en`, whose translation field is a usage note by design),
`hint_language` (target-script prose left in an English hint),
`structural` (missing grammar file, thin sentence bank, empty morphology),
`gender_marking` (percentage of noun hints that mark gender).

### The baseline ratchet

`data/quality/baseline.json` records today's fail-level counts per
`language.rule`. CI fails only on an **increase**. To burn debt down:

```bash
python -m backend.services.quality.audit_content --language es   # see the list
# ... fix drills in data/grammar/es_grammar.json ...
python -m backend.services.quality.audit_content --update-baseline
```

Never run `--update-baseline` to silence a regression you just introduced — the
diff is reviewed in the PR, and a baseline that goes *up* needs a reason in the
commit message.

---

## Layer 2 — Test suites

| Suite | Command | Covers |
| --- | --- | --- |
| Content audit | `.venv/bin/pytest backend/tests/test_content_quality.py -q` | The rules above, in-process, against the baseline |
| Answer grading | `.venv/bin/pytest backend/tests/test_nlp_*.py backend/tests/test_typed_input.py -q` | Per-language acceptance: accents, scripts, look-alikes, morphology |
| Review pipeline | `.venv/bin/pytest backend/tests -k "contribut or review or inbox" -q` | Every submission channel reaching the admin |
| Full backend | `.venv/bin/pytest backend/tests -q -p no:randomly` | Everything, vs the documented baseline in `CLAUDE.md` |
| Frontend | `cd frontend && npm run build && npx vitest run` | Type-check + component behaviour |

Integration tests skip silently without a database. Start both services first,
or you will report a pass that tested nothing:

```bash
su postgres -c '/usr/lib/postgresql/16/bin/pg_ctl -D /var/tmp/pgtest -o "-p 5433" -l /var/tmp/pgtest.log start'
redis-server --port 6380 --daemonize yes
INTEGRATION_DATABASE_URL="postgresql://postgres@127.0.0.1:5433/postgres" \
REDIS_URL="redis://127.0.0.1:6380/0" .venv/bin/pytest backend/tests -q
```

---

## Layer 3 — AI review passes (costs allowance; run deliberately)

Mechanical rules cannot judge *meaning*. Two maker–checker passes do:

```bash
# Rewrite confusing/dictionary-jargon definitions. Journals every change; revertible.
python -m backend.services.seeder.review_hints --language ru --limit 30 --dry-run
python -m backend.services.seeder.review_hints --language ru --limit 30

# Audit generated sentences/drills for accuracy, level and usefulness.
python -m backend.services.seeder.generate_content --language ca --recheck
```

Anything the checker is unsure about lands in the **Review inbox** for a human,
rather than being silently applied.

---

## Layer 4 — Human spot-check protocol

Per language, per release. Budget ~20 minutes.

1. Open `docs/quality/<code>.md` and read the Hint standards section.
2. Pull 10 random drills:
   ```bash
   python -m backend.services.quality.audit_content --language <code> --sample 10
   ```
3. For each, answer: could I get this right *without knowing the language*?
   If yes, the hint leaks. Could a competent speaker produce a **different**
   correct answer? If yes, the hint is underdetermined.
4. Check 5 noun definitions carry gender/class if the language needs it.
5. Check the register matches the profile (MSA for Arabic, and so on).
6. File what you find through the **Review workspace** — it now reaches the
   admin regardless of which language they are working in.

---

## The review pipeline (why submissions went missing)

Traced end to end. Submissions were never lost — they were filtered out before
the admin's eyes:

1. **Cross-language blindness (primary cause).** Every admin review surface —
   inbox, feedback, issues, change requests, suggestions — filters by the
   *admin's* working language, while a submission carries the language the
   *tester* was studying. Testers on Spanish + admin's selector on Arabic =
   "All clear". The inbox now carries a cross-language roll-up.
2. **Trial reviewers could not raise change requests.** Both the UI affordance
   and the endpoint excluded the role, so their reviews silently degraded to
   plain card feedback while the admin watched the change-request board.
3. **Trial reviewers were locked out of the vocab surface** by a role gate the
   per-item endpoints did not share.
4. **Advisory recommendations had no durable surface** — not counted, shown
   only as a tooltip, orphaned by bulk approve.
5. **Panels rendered nothing on fetch failure**, indistinguishable from a quiet
   day.

Roles, and what each may do, live in `docs/review-workflow.md`. When briefing a
tester, confirm their role there first — most "I submitted and nothing
happened" reports are a role that lacks the affordance being described.

---

## Cadence

| When | What |
| --- | --- |
| Every commit | CI: content audit vs baseline + full suites |
| Every content change | `--language <code>` audit before pushing |
| Weekly | Review inbox to zero, all languages (use the roll-up) |
| Per release, per language | Layer 4 human spot-check |
| When adding a language | Write `docs/quality/<code>.md` **first**, then seed |

---

## Adding a language

1. Write `docs/quality/<code>.md` from the shared skeleton (copy the closest
   relative — Romance, Semitic, agglutinative…).
2. Add the code to the audit's language list and any script/gender sets.
3. Seed content, then run the audit and record the initial baseline.
4. Add NLP grading tests if the language has script or morphology specifics.
5. Confirm the Letters & Sounds guide and keyboard exist for non-Latin scripts.

---

## Running this with Claude

Everything here is repo-relative and committed, so a fresh session can pick it
up with no context:

```
Read docs/quality/README.md and docs/quality/es.md, then run the audit for
Spanish and fix the top leak class. Verify with the audit and the full gates.
```

For a whole-repo sweep, ask for the burn-down explicitly — it is long-running
work and best done one language per change so the diffs stay reviewable:

```
Burn down the fail-level debt in docs/quality/id.md (the self-answering hint
template). Rewrite the hints in data/grammar/id_grammar.json, keep every answer
unchanged, then update the baseline and show me the before/after counts.
```
