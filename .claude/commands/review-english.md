---
description: Judge the English on one language's cards and apply the corrections, using this session as the judge instead of the paid API
argument-hint: <language-code> [limit]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

Run the English-on-trial pass for language `$1` with **you** as the judge. Do
not use the Anthropic API for this; `--export`/`--apply` deliberately need no
`ANTHROPIC_API_KEY`.

Row budget: `$2` rows per source. If that came through empty — no second
argument was given — use **50**. Substitute the number into the commands
below yourself; do not leave a shell placeholder in the command line.

Read `docs/quality/running-locally.md` and `docs/quality/$1.md` before you
start. The second file is that language's own standards and it overrides
anything general below.

## Why this exists

Every other locale is generated **from** the English, and the checker then
grades that locale **against** that same English. So the English is ground
truth in both directions and was never itself examined. A Spanish card can be
excellent and still wrong, because it faithfully translated a poor English.
You are reading in the opposite direction: the target-language sentence is the
source of truth, the English is the thing on trial.

## Steps

**1. Preflight.** Confirm you are pointed at the intended database and that the
working tree is clean, and say what you found:

```bash
psql "$DATABASE_URL" -c "select current_database();"
git status --short
```

Stop and ask if `DATABASE_URL` is unset, or if the tree has uncommitted changes
under `data/` (a later step commits that directory, and it must not sweep up
someone else's work).

**2. Export.** Nothing is written and nothing is spent:

```bash
python -m backend.services.seeder.review_translations \
  --language $1 --limit <the row budget> --export /tmp/review-$1.jsonl
```

**3. Judge every line.** Each line is JSON with `sentence` (the language being
taught — a drill's blank is already filled) and `english` (what you are
judging). Fill in three fields **on that same line** and save in place:

- `verdict`: `ok` | `fixed` | `reject`
- `fixed`: the better English, when and only when `verdict` is `fixed`
- `note`: a few words on what was wrong

The standard:

- **`ok`** unless you can genuinely do better. Rewriting good English into
  different good English burns the run and churns every derived locale for
  nothing.
- **`fixed`** for meaning errors, wrong register, and renderings that are
  defensible in isolation but misleading on a card. Prefer the natural English
  a speaker would actually say over a word-by-word gloss — but do not drift
  further from the source than the original did, and keep the same kind of
  utterance: a question stays a question, a fragment stays a fragment.
- **`reject`** when the pair is too broken or ambiguous to fix confidently —
  e.g. the English translates a different sentence. This flags the row for a
  human. Never guess in place of a reject.

Do not add, drop or reorder lines, and never edit `id`, `source`, `sentence`
or `english` — those are how the apply step finds the row and proves it has
not changed underneath you.

**4. Dry run, then stop.** Show me the summary and a representative sample of
the corrections — including at least one you left `ok` and one you rejected,
so I can see your bar and not just your hits:

```bash
python -m backend.services.seeder.review_translations \
  --apply /tmp/review-$1.jsonl --dry-run
```

**Wait for my go-ahead before applying.** This is the approval gate; do not
skip it because the diff looks small.

**5. Apply,** then tell me the journal path it printed:

```bash
python -m backend.services.seeder.review_translations --apply /tmp/review-$1.jsonl
```

**6. Commit the mirror.** A drill fix that only lives in the database is
reverted by the next `seed_grammar` run, which matches on `(sentence, answer)`
and updates in place. The file is not bookkeeping, it is the fix:

```bash
git diff --stat data/grammar/
git add data/grammar && git commit -m "English corrections for $1 from review_translations"
```

If `git diff` shows nothing there, say so — for a language whose fixes were all
example sentences that is correct and expected, not a failure.

**7. Report:** how many fixed, queued for a human, left as-is; the journal
path; the number of stale locale rows dropped (that is roughly how many
re-translations the demand loop will do later, so it is a cost, not just a
statistic); and anything you were unsure about.

## Rules

- Read the counters, don't just run the command. `unchanged` means judged and
  left alone; `unjudged` means no verdict was filled in. A non-zero `stale`
  means somebody edited those rows while you were judging — report it and
  re-export them rather than forcing anything.
- Never edit a drill's `sentence` or `answer` anywhere. They are the seeder's
  match key; changing either orphans the row and every learner's SRS history
  on that card.
- If anything looks wrong after applying, stop and use
  `--restore <journal-file>`. Do not repair by hand. Note that `--restore`
  does not clear review flags — that is expected, and the SQL to clear them is
  in `docs/quality/running-locally.md`.
- Do not run `--all`. This command is one language at a time on purpose, so
  the diffs stay reviewable and a bad judging pass is cheap to undo.
