# Running the AI content passes locally

For running the allowance-spending passes from your own machine against the
live database, instead of paying for a hosted agent to do it.

The whole document assumes the thing that makes this safe: **every applied
change is journaled to disk before it lands, and a whole run can be undone
exactly.** Nothing here is a one-way door except the parts called out under
"Where the sharp edges actually are".

---

## 1. What you are running

| Pass | Judges | Writes | Undo |
| --- | --- | --- | --- |
| `review_translations` | the **English**, against the sentence it claims to translate | `example_sentences.translation` (locale `en`), `drill_sentences.translation` | `--restore` |
| `review_hints` | clarity of card **definitions** | `translations.definition` | `--restore` |
| `generate_content --recheck` | accuracy/level of generated sentences and drills | sets `flagged` on rejects and parks `suggested_translation` for a human; it does not replace text a human approved | no journal — undo through the Review workspace |

This document is mostly about the first, which is the one that rewrites
content in place across every course.

**Why the English and not the locales.** Every other locale is generated
*from* the English, and the checker then grades that locale *against* that
same English. So the English is ground truth in both directions and was
never itself examined. A Spanish rendering can be excellent and still be
wrong, because it faithfully translated a poor English. Fixing a locale
without fixing its English fixes one card; fixing the English fixes every
language derived from it.

---

## 1a. Two ways to run it, and which one you want

`review_translations` can get its verdicts from either place:

| | Judge | Costs | Use when |
| --- | --- | --- | --- |
| **API mode** | the Anthropic API, called by the script | **billed per row** | unattended sweeps, cron |
| **Offline mode** | **the Claude Code session you are already in** | nothing extra | you are sitting here anyway |

**Offline mode is the default choice when a session is running the job.** The
model is already in the room; paying the API to do the same reading is
buying it twice. It needs no `ANTHROPIC_API_KEY` at all.

```bash
# 1. Pull the rows out. Calls no model, spends nothing.
python -m backend.services.seeder.review_translations \
  --language hi --limit 50 --export hi.jsonl

# 2. The session reads hi.jsonl, judges each line, and fills in
#    verdict / fixed / note ON THE SAME LINES, saving in place.

# 3. Write the verdicts back — same journal, same deletes, same mirrors.
python -m backend.services.seeder.review_translations --apply hi.jsonl --dry-run
python -m backend.services.seeder.review_translations --apply hi.jsonl
```

Each exported line looks like this — `sentence` is what the English is
judged *against* (a drill's blank is already filled in), and the last three
fields are blank for the judge:

```json
{"id": "652797d4-…", "source": "drill", "language": "hi",
 "sentence": "मैं चाय पीता हूँ।", "english": "I drink tea.",
 "verdict": "", "fixed": "", "note": ""}
```

`verdict` is one of:

- **`ok`** — the English is accurate and natural. Nothing is written.
- **`fixed`** — put the better English in `fixed`. Correct meaning errors,
  wrong register, and renderings that are defensible but misleading out of
  context. Do not drift further from the source than the original did, and
  keep the same kind of utterance: a question stays a question.
- **`reject`** — too broken or ambiguous to fix confidently (e.g. the
  English translates a different sentence). The row is flagged for a human;
  its text is never guessed at.

**One file round-trips on purpose.** A separate verdicts file would lose the
original `english`, and without it there is no way to notice a row changed
between export and apply — a stale export would silently overwrite whoever
edited it. Rows that changed are skipped and counted as `stale`.

The apply summary distinguishes `unchanged` (judged, left alone) from
`unjudged` (nobody filled a verdict in), so a careful pass that concludes
"this English is fine" does not read like a file that never got opened.

Everything from section 4 onward applies to both modes — they share the
write path exactly.

---

## 2. Before you start

```bash
git pull                       # you want #261 or later for offline mode
export DATABASE_URL=...        # the live database
export ANTHROPIC_API_KEY=...   # API mode ONLY; offline mode needs no key
```

Confirm you are pointed where you think you are — this is the single
highest-consequence line in the whole process:

```bash
psql "$DATABASE_URL" -c "select current_database(), count(*) from languages;"
```

**Take a snapshot first anyway.** The journal undoes what this tool did; it
does not undo a typo in `DATABASE_URL`.

---

## 3. The safe order

Never start with `--all`. Work outward:

```bash
# 1. Look, change nothing. --dry-run writes NOTHING — not even a review flag.
python -m backend.services.seeder.review_translations \
  --language hi --limit 20 --dry-run

# 2. Read the FIX lines it printed. Are the corrections actually better?
#    If the model is rewriting good English into different good English,
#    stop and say so rather than spending on 6672 drills.

# 3. Same language, for real. Note the journal path it prints.
python -m backend.services.seeder.review_translations --language hi --limit 20

# 4. Spot-check in the app, then widen one language at a time,
#    or sweep once you trust it:
python -m backend.services.seeder.review_translations --all --limit 50 --dry-run
python -m backend.services.seeder.review_translations --all --limit 50
```

`--limit` is **per language per source**. `--all --limit 50` is
26 × 2 × 50 = 2,600 rows of judging, not 50.

Useful narrowing while you build trust:

```bash
--source drill      # grammar drills only
--source example    # vocabulary example sentences only
--language ar       # one course
```

---

## 4. Exactly what it writes

| Write | When |
| --- | --- |
| `UPDATE … SET translation` | verdict `fixed`, and the new text differs from the old |
| `DELETE` of derived locale rows | alongside each fix — see below |
| `flagged = true, flag_reason` | verdict `reject`; the pass refuses to guess |
| `data/grammar/<code>_grammar.json` | **always**, when a drill is fixed |
| `data/<code>_sentences.tsv` | only with `--write-tsv` |
| `data/backups/translations_<code>_<source>_<stamp>.jsonl` | before any database write |

**The deletes are intentional, not damage.** When the English changes, every
locale rendering built from it was faithful to the *old* text and is now
quietly wrong. Those rows are dropped so the demand-driven loop refills them
from the corrected English the next time a learner sees the card. For a
drill the whole `drill_hint_translations` row goes, hint included — that
table holds hint and translation together and the loop refills only rows
that are *absent*, so blanking one column would strand it forever.

The consequence is a **cost you pay later**: `stale locale rows dropped` in
the summary is roughly how many re-translations the loop will do on demand.
A large sweep is two bills, not one.

## 5. What it will not touch

- Any row already `flagged` — a human is handling it.
- Example rows with a `suggested_translation` pending.
- The `sentence`, the `answer`, and the drill `hint`. It only ever rewrites
  a `translation` field. Hints are Layer 1's job (`audit_content`), because
  a hint is judged on whether it narrows without leaking, not on fidelity.
- Any locale row directly — it reads `translation_locale = 'en'` only.
- The English course (`--all` excludes `en`, whose translation field is a
  usage note by design).

---

## 6. Undo

Each run prints its journal path. To reverse one completely:

```bash
python -m backend.services.seeder.review_translations \
  --restore translations_hi_drill_20260814-001500.jsonl
```

This restores the database **and** re-mirrors the grammar JSON. It is
idempotent — running it twice, or after a run you interrupted halfway, is
safe, because it sets each row back to a known previous value rather than
stepping backwards.

To throw away the file mirrors instead, they are ordinary tracked files:

```bash
git checkout -- data/grammar data/            # revert mirrors
git diff --stat                               # see what a run touched
```

**One honest gap: `--restore` does not clear review flags.** Flags are
written during the judging loop, before the journal exists, so a restore
leaves the `reject` rows flagged. They are harmless — a flag only parks a
row in the Review workspace — but if you want them gone:

```sql
UPDATE drill_sentences    SET flagged = false, flag_reason = NULL
  WHERE flag_reason LIKE 'English translation needs review:%';
UPDATE example_sentences  SET flagged = false, flag_reason = NULL
  WHERE flag_reason LIKE 'English translation needs review:%';
```

---

## 7. Where the sharp edges actually are

**a) Commit the grammar JSON, or the fix un-does itself.**
`seed_grammar` matches a drill on `(sentence, answer)` and **UPDATEs its
translation in place**, so the next re-seed overwrites a database-only fix
with the file's stale English. That is why drill fixes always write the file
rather than hiding behind a flag. After a run:

```bash
git diff --stat data/grammar/     # expect one line per fixed drill
git add data/grammar && git commit -m "Drill English corrections from review_translations"
```

Example sentences are the opposite — `ON CONFLICT DO NOTHING` means the TSV
cannot affect a running deployment at all, so `--write-tsv` matters only for
seeding a *fresh* environment. Two stores, opposite behaviour, and only one
of them forgives you.

**b) Re-seeding overwrites reviewer hint edits.** Independent of this pass:
the grammar update path protects human-edited rows from *deletion* but not
from *update*. If a reviewer edited a hint in the app and the sentence and
answer still match, a re-seed replaces it. Check the change log for a
language before any bulk re-seed.

**c) Never change `sentence` or `answer` by hand in the JSON.** They are the
match key. Changing either orphans the existing row along with every
learner's SRS history on that card.

**d) Don't run two passes at once** against the same database. They journal
independently and a mixed interleaving is painful to unwind.

---

## 8. When it's done

```bash
python -m backend.services.quality.audit_content --language hi
.venv/bin/pytest backend/tests -q -p no:randomly
.venv/bin/ruff check backend/
cd frontend && npm run build && npx vitest run
```

Deploy is only needed if code changed; correcting content does not require
one. Committing the grammar JSON does mean the next deploy carries it.

---

## 9. Paste this into the local session

> Read `docs/quality/running-locally.md` and `docs/quality/README.md`.
> I want to run `review_translations` against the live database in
> **offline mode** — you do the judging, not the API. `DATABASE_URL` is
> set; there is deliberately no `ANTHROPIC_API_KEY`.
>
> Work one language at a time, starting with `<code>`:
>
> 1. `--language <code> --limit 50 --export <code>.jsonl`
> 2. Read every line. For each, judge the `english` against the
>    `sentence`, and fill in `verdict` (`ok` / `fixed` / `reject`),
>    `fixed`, and `note` on that same line. Save in place. Do not
>    invent, reorder or drop lines, and do not touch `id`, `source`,
>    `sentence` or `english`.
> 3. `--apply <code>.jsonl --dry-run`, show me the summary and a sample
>    of the corrections, and wait for me before applying for real.
> 4. After applying, tell me the journal path and commit the
>    `data/grammar/*.json` diff — a re-seed reverts a database-only
>    drill fix.
>
> Judging standard: `ok` unless you can genuinely do better. Correct
> meaning errors, wrong register, and renderings that mislead out of
> context. Do not drift further from the source than the original did;
> keep a question a question. Use `reject` — never a guess — when the
> pair is too broken or ambiguous to fix confidently.
>
> Rules: never run `--all` without a dry run I have seen; never edit a
> drill's `sentence` or `answer`; if anything looks wrong, stop and use
> `--restore` rather than repairing by hand.
