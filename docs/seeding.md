# Seeding a language

What has to run, in what order, for a language to be usable — and what each
step actually puts in the database.

If a language shows an empty grammar path, or every word in it is A1, or the
placement test cannot find enough items, the cause is almost always on this
page: the migration ran but the seeders did not.

---

## The order

```
1. supabase db push                      creates the LANGUAGE ROW itself
2. seeder.run          --language <code> vocabulary        (frequency list)
3. seeder.seed_grammar --language <code> grammar_points + drill_sentences
                                          + one content_list per CEFR level
4. generate_grammar    --language <code> --ai-check  (ai_ok languages ONLY —
                                          see below; this is the step people miss)
```

Steps 2–4 are idempotent — re-run them freely. They UPSERT, ids stay stable so
learners' `gym_progress` survives, and anything a human has curated in the app
is never overwritten: text diffs on a curated point go to the review queue
instead.

Step 1 first, always. The languages are rows created by migration
(`20260901000000_seed_he_la_fa_id_tl.sql` for the five newest), and seeding a
language whose row does not exist fails with "language not found".

## The commands

```bash
export DATABASE_URL=postgresql://...
export ANTHROPIC_API_KEY=...   # needed for step 4 only

# steps 1-3 accept --language all; step 4 (generate_grammar) does not — loop it
supabase db push
python -m backend.services.seeder.run          --language all
python -m backend.services.seeder.seed_grammar --language all
for l in he la fa id tl sw mi ha xh yo hi th ko; do
    python -m backend.services.seeder.generate_grammar --language "$l" --ai-check
done

# or one language at a time
python -m backend.services.seeder.run             --language he
python -m backend.services.seeder.seed_grammar     --language he
python -m backend.services.seeder.generate_grammar --language he --ai-check
```

Or use the wrapper, which runs all three steps in order for each code:

```bash
./scripts/seed_language.sh he la fa id tl
```

## Why C2 (and all grammar) can be missing

**`seed_grammar` is a separate command from `run`.** Running only
`seeder.run` loads vocabulary and nothing else — the grammar path renders
empty at every level, C2 included, because no `grammar_points` rows exist.
The curriculum files are in the repository (`data/grammar/{code}_grammar.json`,
40+ points each, A1 through C2 for every language) but a file in the repo is
not a row in the database.

Check before assuming:

```sql
SELECT l.code, gp.level, count(*)
FROM grammar_points gp JOIN languages l ON l.id = gp.language_id
GROUP BY 1, 2 ORDER BY 1, 2;
```

No rows for a level means `seed_grammar` has not been run for it.

## Why grammar STILL doesn't show, even after `seed_grammar` ran

This is the trap: the query above can report `points = 41, levels = 6` and
the grammar path can still render empty for learners. Two different gates
sit between "the row exists" and "a learner can see it".

`backend/repositories/curriculum.py` only returns a point when:

```sql
gp.reviewed = true
OR (l.grammar_review_policy = 'ai_ok' AND gp.ai_check_status = 'pass')
```

`seed_grammar` writes every AI-authored point with `reviewed = false` (a
human hasn't signed off on it) — that's true for every "draft tier"
language: sw, mi, ha, xh, yo, hi, th, ko, and the five newest. Those
languages are given `grammar_review_policy = 'ai_ok'` specifically so they
can be visible WITHOUT a human reviewing all 40 points by hand — but that
only works once `ai_check_status` is set to `'pass'`, and **nothing in the
seed pipeline sets it.** The only thing that ever did was the "Run AI check"
button in the Contribute editor — one point at a time, so a fresh 40-point
language needed 40 clicks before anyone could study it. That's the gap: the
tooling to do it in bulk didn't exist.

It now does — `generate_grammar --ai-check` (step 4 above) runs the same
semantic check the button does, looped over every point in the language, and
stores the verdict. Needs `ANTHROPIC_API_KEY` (or `TUTOR_DEV_MOCK=1` for a
canned pass, useful for testing the pipeline without spending anything). Safe
to re-run — by default it only checks points with no verdict yet, so an
interrupted run resumes instead of re-billing everything; pass
`--recheck-all` to force a redo.

```bash
python -m backend.services.seeder.generate_grammar --language he --ai-check
```

Check whether this is actually the blocker:

```sql
SELECT l.code,
       count(*) FILTER (WHERE gp.reviewed) AS reviewed,
       count(*) FILTER (WHERE gp.ai_check_status = 'pass') AS ai_passed,
       count(*) FILTER (WHERE NOT gp.reviewed AND gp.ai_check_status IS DISTINCT FROM 'pass') AS still_hidden
FROM grammar_points gp JOIN languages l ON l.id = gp.language_id
WHERE l.grammar_review_policy = 'ai_ok'
GROUP BY 1 ORDER BY 1;
```

`still_hidden > 0` means those points exist in the database and are
genuinely invisible to every learner until `--ai-check` runs.

## Why every word is A1 in the newest languages

`rank_to_level` bands a word by its frequency rank, and for the five newest
languages the frequency list in `data/` is a **90-word placeholder**, not a
corpus:

| language | `data/<code>_frequency.tsv` |
|---|---|
| Spanish (reference) | 10,000 words |
| he, la, fa, id, tl | 90 words |

With 90 words the whole list is inside the A1 band by design (corpora under
500 words keep the absolute thresholds — rank ≤ 500 is A1), so no amount of
re-seeding produces B1+ vocabulary. That needs a real list:

```bash
python -m backend.services.seeder.source_data --language he --source kaikki
python -m backend.services.seeder.run --language he
```

`source_data` needs open internet access to kaikki.org — see
`scripts/refresh_seed_data.sh`. A CSV/TSV you already have can be loaded
directly instead:

```bash
python -m backend.services.seeder.run --language he --file my_he_list.tsv
```

Grammar is unaffected by this — the curricula are hand-authored and complete
to C2 regardless of corpus size.

## Optional steps

None of these are needed for a language to work; each fills in depth.

| What | Command | Needs |
|---|---|---|
| Example sentences | `seeder.seed_sentences --language <code>` | `data/sentences/<code>_sentences.tsv` |
| Morphology charts | `seeder.morphology_charts --language <code>` | a chart builder for that language |
| Alphabet cards | `seeder.seed_alphabet --language <code>` | `data/alphabet/<code>.json` or a built-in table (ru, ko) |
| AI gap-fill | `seeder.generate_content -l <code> -k definitions --max 200` | an API key; costs money |
| AI curriculum | `seeder.generate_curriculum --language <code> --generate` | an API key; only for languages with no hand-authored file |

The Gym needs no seeding at all — its manifests are read from
`data/gym/<code>.json` at request time.

## Verifying

```sql
-- one row per language, with what it actually has
SELECT l.code,
       (SELECT count(*) FROM vocabulary       v WHERE v.language_id = l.id) AS words,
       (SELECT count(*) FROM grammar_points  g WHERE g.language_id = l.id) AS points,
       (SELECT count(DISTINCT g.level) FROM grammar_points g WHERE g.language_id = l.id) AS levels
FROM languages l ORDER BY l.code;
```

`levels` below 6 means that language's grammar path stops short of C2.
