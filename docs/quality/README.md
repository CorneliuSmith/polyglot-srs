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

### Where languages may differ

The universal hint rules are restated in every `docs/quality/<code>.md`, and a
language file may **tighten or relax one — but only with the reason written
down**. Silent divergence is how "the same standard everywhere" quietly stops
being true, and it makes two languages' debt counts incomparable.

Two live examples, both legitimate:

- **Gender marking** is absolute in the Romance files (gender is arbitrary, so
  the learner cannot recover it) and conditional in Russian (gender is
  usually readable off the nominative ending, so marking it everywhere is
  noise). Russian says so in its own rule.
- **Quoting a base form in the hint** is capped at one form in the
  Arabic-script languages, where the quoted form is often the answer's own
  stem and a second quote starts giving the pattern away.

If you find a divergence with no stated reason, that is a bug in the docs —
either bring the file back to the shared rule or write the justification.

## Layer 1 — Mechanical checks (fast, every commit)

`backend/services/quality/audit_content.py` scans all in-repo learning content
and reports per language. Rules, and why each exists:

**Fail-level** (blocks CI when it exceeds baseline):

| Rule | What it catches | Guard against false positives |
| --- | --- | --- |
| `leak_hard` | The answer appears in its own hint as a whole word | Substring matches inside a longer word are legitimate — `trabajar, él/ella` for answer `trabaja` is the standard "infinitive, person" convention |
| `self_answering` | Hints shaped `answer — explanation` | The single worst pattern found; it simply prints the answer |
| `giveaway_by_gloss` | A ≤3-word hint that already appears verbatim in the drill's own translation | For closed-class answers the hint then uniquely determines the answer |
| `agreement_feature` | A hint that is *nothing but* the agreement features the drill exists to make the learner derive (`masculine plural`) | Only fires when the hint is EXCLUSIVELY features and the point offers a choice — `the definite article — check the noun's gender` says to do the work rather than doing it |
| `duplicate_hint` | One hint mapped to several answers inside a point | Allomorph sets are exempt (Turkish `mı/mi/mu/mü` — the sentence disambiguates) |
| `empty` | Empty hint, translation or explanation | — |
| `ar_register` | Dialect markers in a course that teaches MSA | Whole-word matching only |
| `wrong_sense_gloss` | A top-1000 vocabulary word whose gloss describes a letter of the alphabet or an ISO region code instead of the word — French rank 15 `ne` (the negator) glossed as a Swiss canton, Yoruba's five commonest grammar words glossed as letters | Only the FIRST sense counts (`fedha` = "silver…; money" leads with what the learner wants), and only inside the top 1000. Words that genuinely name a letter — `herufi`, `χι`, `fi`, `알파` — all sit at rank 2417+, so the band separates the two populations with nothing on the wrong side |

**Warn-level** (reported, never blocks):

`construction_quote` (hint quotes a multiword construction containing the
answer), `vague_translation` (translation far shorter than its sentence —
exempt for `en`, whose translation field is a usage note by design),
`hint_language` (target-script prose left in an English hint),
`structural` (missing grammar file, thin sentence bank, empty morphology).

**Report-level** (measured and printed, never scored):
`gender_marking` — "how often do noun hints mark gender" is a number to drive
editorial work, not a threshold anyone can set honestly.

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

Integration tests skip silently without a database — a green run with no
services proves nothing. Point the two env vars at ANY Postgres and Redis you
have; only the URLs matter, not how they were started:

```bash
INTEGRATION_DATABASE_URL="postgresql://<user>@<host>:<port>/<db>" \
REDIS_URL="redis://<host>:<port>/0" \
.venv/bin/pytest backend/tests -q -p no:randomly
```

`docker run -p 5432:5432 -e POSTGRES_PASSWORD=x postgres:16` and
`docker run -p 6379:6379 redis:7` are enough locally; CI wires its own
services (see `.github/workflows/ci.yml`). Inside the dev container the exact
`pg_ctl` invocation is in `CLAUDE.md`.

---

## Layer 3 — AI review passes (costs allowance; run deliberately)

> Running these yourself, from your own machine, against the live database?
> **`docs/quality/running-locally.md`** is the runbook: safe order, exactly
> what each pass writes, how to undo a run, and the two ways a correct fix
> can quietly un-do itself.

Mechanical rules cannot judge *meaning*. Three maker–checker passes do.

### English is the pivot — fix it first

Every locale is generated **from the English**, and the checker then grades
that locale **against that same English**. So the English is ground truth in
both directions and was never itself examined: a loose English silently caps
every language derived from it, while each downstream locale still looks
correct *relative to its source*. A Spanish rendering can be excellent and
still be wrong, because it faithfully translated a poor English.

**The English sits in two tables, and both are pivots.** Checking one and
not the other leaves half the cards in the product unexamined:

| Where | Feeds | Seen by the learner as |
| --- | --- | --- |
| `example_sentences.translation` (locale `en`) | every other locale's row for that sentence | the "in context" line under a vocabulary card |
| `drill_sentences.translation` | every `drill_hint_translations` row | the English under a grammar drill |

`review_translations` covers both by default (`--source example` / `--source
drill` narrows it). Drill hints are deliberately out of its scope — a hint is
judged on whether it narrows without leaking, which is Layer 1's job.

So the order matters. Fix the English, then let the locales re-derive:

```bash
# 1. Judge the ENGLISH against the sentence it claims to translate.
#    Reads the target-language sentence; the English is what's on trial.
#    Both content types, one language, nothing written:
python -m backend.services.seeder.review_translations --language hi --limit 20 --dry-run
python -m backend.services.seeder.review_translations --language hi --limit 20

#    Every language, both content types. --limit is per language PER SOURCE,
#    so this is 27 × 2 × 50 rows of judging — size it against the allowance
#    and start with --dry-run.
python -m backend.services.seeder.review_translations --all --limit 50 --dry-run
python -m backend.services.seeder.review_translations --all --limit 50

#    One run, undone exactly — file mirrors included.
python -m backend.services.seeder.review_translations --restore <journal-file>

# 2. Rewrite confusing/dictionary-jargon definitions.
python -m backend.services.seeder.review_hints --language ru --limit 30 --dry-run

# 3. Audit generated sentences/drills for accuracy, level and usefulness.
python -m backend.services.seeder.generate_content --language ca --recheck
```

Correcting an English **deletes the locale renderings built from it** — they
were faithful to the old text and are now quietly wrong. The demand-driven
loop refills them from the corrected English on next use. For a drill the
whole `drill_hint_translations` row goes, hint included: that table holds both
in one row and the loop refills only rows that are *absent*, so blanking a
column would strand it forever. Anything the checker is unsure about is
flagged for a human rather than guessed at, and surfaces in the **Review
inbox**.

### Where a content fix actually has to land

The two content stores do not behave the same on re-seed, and getting this
wrong means editing a file and seeing nothing change:

| Content | Re-seed behaviour | So a fix must… |
| --- | --- | --- |
| Grammar drills (`data/grammar/<code>_grammar.json`) | Matched on `(sentence, answer)` and **updated in place** — the row id survives, so learner progress does too | Edit the JSON, then `python -m backend.services.seeder.seed_grammar --language <code>`. Never change `sentence` or `answer`: they are the match key, and changing either orphans the old row and its history. The reverse also bites — a database-only fix is **reverted by the next seed**, which is why `review_translations` writes the JSON for drills automatically rather than behind `--write-tsv`. Commit that diff. |
| Example sentences (`data/<code>_sentences.tsv`) | `ON CONFLICT … DO NOTHING` — an existing row **never** changes | Go through the database (`review_translations` does). `--write-tsv` mirrors the change into the repo so a FRESH environment seeds the corrected text, but it will not touch a running deployment. |
| AI-generated cards | Not in the repo at all | `generate_content --recheck`, or human review through the Review workspace. |

One more caveat before any bulk re-seed: the grammar update path does **not**
exempt human-edited rows. Deletion protects them — a drill a reviewer touched
is never deleted — but an update will overwrite a reviewer's in-app hint edit
if the sentence and answer still match. Check the change log for a language
before re-seeding it.

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

## Numbers in these docs go stale, and stale numbers get acted on

A claim audit on 18 Aug 2026 checked every falsifiable statement in all 27
language files against the data it describes. **118 defects: 45 outright
false, 52 stale, 18 true-but-misleading.** Two failure modes, and both cost
real work:

- **Undercounting live debt.** `sw.md` says "50 grammar points, 308 drills";
  the file holds **64 points and 442 drills**. `ko.md` says "verified on disk:
  40 points, 240 drills, six each" — it is **156 points and 1,217 drills**,
  and "six each" stopped being true long ago. Anyone scoping a burn-down from
  those pages plans a job a third the real size.
- **Describing defects that are already fixed.** `el.md`, `hi.md`, `th.md`,
  `es.md` and `ca.md` each still name specific rows or grading bugs that have
  since been repaired. A reader who checks the cited example finds it clean,
  concludes the page is wrong, and stops trusting the rest of it.

`la.md` was the worst case and the reason this audit ran: it reported the
macron policy "verified" against the grammar file while the vocabulary file
sat at 48% non-compliant, seeding 40 duplicate cards.

**So, three rules for writing these pages:**

1. **Never freeze a count the audit already computes.** `leak_hard`,
   `giveaway_by_gloss`, `agreement_feature`, `duplicate_hint`,
   `wrong_sense_gloss`, `circular_gloss` — cite the RULE NAME and let
   `python -m backend.services.quality.audit_content --language <code>` say
   the number. Four language files currently assert `leak_hard: 0` or `2`
   where the audit prints 10, 11, 7 and 3; the docs and the tool disagree
   because a human typed one of them once.
2. **A number the audit does NOT compute must carry its date and how it was
   measured** — the command or query, not just the figure. "18 hint leaks"
   is unfalsifiable a month later; "18 by whole-word match on 12 Aug, audit
   says 17" can be re-run and corrected.
3. **"Verified" must name every file the claim covers.** A policy that spans
   the grammar file, the frequency file and the gym is not verified until all
   three are checked, and saying so is what stops the next `la.md`.

Prefer a pointer to a count. "The `agreement_feature` rule is the largest
class here" ages well; "18 agreement-feature hints" does not.

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
