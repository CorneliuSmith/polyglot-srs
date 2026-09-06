# Refeed runbook — pushing committed content to production

**Who runs it: the owner.** This agent prepares the commands and never runs
a production write (CLAUDE.md). Every command below reads `DATABASE_URL`
from `.env`; none of them takes the DSN on the command line, and none of
them should ever be pasted with it.

Code deploys itself from `main`. Only DATA needs this sequence — and only
the courses whose files changed since the last run. `git log --stat
-- data/<code>_*.tsv data/grammar/<code>_grammar.json` tells you which.

## The sequence, per course

Run from the repository root with the project venv active
(`.venv/bin/python`). `<code>` is a course code; `-l all` is accepted by
`run` and `reconcile` but prefer one course at a time — the 30 Aug `all`
reconcile ran long enough that the owner asked whether it was still going.

```bash
./scripts/backup_db.sh
```
0. **Snapshot first.** A timestamped `pg_dump` of live data (accounts,
   cards, progress) — the thing source cannot reproduce. Complements
   Supabase PITR, does not replace it. Picks the lowest local `pg_dump` at
   least as new as the server and tells you which `postgresql@<ver>` to
   install if none fits.

```bash
supabase db push
```
1. **Migrations**, only when `supabase/migrations/` gained a file. Code that
   reads a new column degrades until this lands, by rule.

```bash
.venv/bin/python -m backend.services.seeder.run -l <code>
```
2. **Vocabulary and alphabet decks.** Upserts on `(language_id, word)` from
   `data/<code>_frequency.tsv` + `gloss_overrides.tsv`; the eight alphabet
   decks (ar el fa he hi ko ru th) seed here too. **Never deletes** — a word
   removed from the file (or listed in `vocab_exclusions.tsv`) stays in
   production; see "What this cannot do".

```bash
.venv/bin/python -m backend.services.seeder.reconcile -l <code>
.venv/bin/python -m backend.services.seeder.reconcile -l <code> --apply
```
3. **Corrections.** Dry run prints what would change (glosses, parts of
   speech, sentence layers — the `s-layer` column); `--apply` writes
   `out/reconcile-<stamp>.sql` FIRST, then applies in one transaction.
   `--detail` lists every gloss change. Never deletes a vocabulary row.

```bash
.venv/bin/python -m backend.services.seeder.seed_grammar -l <code>
```
4. **Grammar points and drills** from `data/grammar/<code>_grammar.json`.
   UPDATEs hint, translation and gloss in place (this is how the drill
   glosses reached production); attaches `en_drill_hints.<locale>.json`
   for the English course. No rollback file — re-run with the previous
   commit's JSON to revert.

```bash
.venv/bin/python -m backend.services.seeder.seed_sentences -l <code>
```
5. **Example sentences**, add-only (`ON CONFLICT DO NOTHING`). New rows
   land with the `difficulty_rank` in the file — the word's frequency rank
   (CHECKS §24). `--repair-locales` relabels rows filed under the wrong
   locale; not part of the routine run.

```bash
.venv/bin/python -m backend.services.seeder.prune_sentences -l <code>
.venv/bin/python -m backend.services.seeder.prune_sentences -l <code> --apply
```
6. **Prune.** Removes every sentence production holds that the committed
   bank does not endorse (CHECKS §18). Dry run first — read the count and
   the "stranded" line (must be 0); `--apply` writes `out/prune-<stamp>.sql`
   first. Refuses to run against an empty committed bank. This is the step
   that changes what a card shows; without it, step 5 only ever adds.

```bash
.venv/bin/python -m backend.services.seeder.morphology_charts -l <code>
```
7. **Gym charts**, only when `data/gym/<code>.json` or the morphology
   changed. Fourteen courses have charts (`ru es pt it fr ca ro de ar el tr
   sw xh yo`); the command lists them.

A loop for several courses, as the owner ran it on 31 Aug:

```bash
for c in ru ar; do .venv/bin/python -m backend.services.seeder.prune_sentences -l $c --apply; done
```

## Rolling back

| step | how |
| --- | --- |
| 3 reconcile | `reconcile --rollback out/reconcile-<stamp>.sql` |
| 6 prune | `prune_sentences --rollback out/prune-<stamp>.sql` |
| 2, 4, 5 | add-only or in-place update: re-run with the previous commit's files, or restore the step-0 snapshot |
| 1 migration | the migration's own down path, or the snapshot |

`out/` is gitignored; move a rollback file somewhere durable before you
delete it. The path is printed at the end of every `--apply`.

## After the run — what to look at

* `reconcile -l <code>` again: the dry run should now report nothing.
* One card you know: the word from the last screenshot, in Review. A
  sentence that changed in the file should be the one on the card once
  step 6 has run — and note CHECKS §26: the card draws by rank then id, so
  a NEW sentence does not win over an old short one until that fix lands.
* `SELECT count(*) FROM user_cards uc LEFT JOIN vocabulary v ON v.id =
  uc.card_id WHERE uc.card_type = 'vocabulary' AND v.id IS NULL` — must be
  0 (it was, on 30 Aug). `card_type` matters: grammar cards point at
  `grammar_points`, and without the filter every one of them counts as an
  orphan.

## What this cannot do

* **Delete a vocabulary row.** `user_cards` references it and the card
  draw INNER JOINs, so a delete orphans a learner's progress. Rows retired
  in files (`vocab_exclusions.tsv`, 727 today, 764 after `fix/en-symbol-glosses`) are still served in
  production until a retire step exists (DEBT.md, "Exclusions have no
  production write path").
* **Reorder a word's sentences.** Ids are assigned at insert; CHECKS §26.
* **Spend the API key.** Nothing here calls a model. The DB-side AI passes
  (`review_translations`, `review_hints`, gym top-up, example diversity) are
  owner decisions, listed in `docs/plans/quality-parity.md` Phase 6, and
  not part of this sequence.

## History

30 Aug 2026 — full sequence, all courses: ~17,800 definitions, ~5,200
parts of speech, ~15,350 vocabulary rows, 5,541 sentence glosses, 272
alphabet letters; five 90-word courses to full size; 0 orphaned cards.
31 Aug – 1 Sep — `prune_sentences --apply` for en (127,363 rows), ru, ar.
Details: `docs/decisions/2026-08-30-content-push-and-gloss-pass.md`.
