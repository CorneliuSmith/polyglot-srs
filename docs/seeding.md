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
2. seeder.run          --language <code> vocabulary_items  (frequency list)
3. seeder.seed_grammar --language <code> grammar_points + drill_sentences
                                          + one content_list per CEFR level
```

Steps 2 and 3 are idempotent — re-run them freely. They UPSERT, drill ids stay
stable so learners' `gym_progress` survives, and anything a human has curated
in the app is never overwritten: text diffs on a curated point go to the
review queue instead.

Step 1 first, always. The languages are rows created by migration
(`20260901000000_seed_he_la_fa_id_tl.sql` for the five newest), and seeding a
language whose row does not exist fails with "language not found".

## The commands

```bash
export DATABASE_URL=postgresql://...

# everything, every language
supabase db push
python -m backend.services.seeder.run          --language all
python -m backend.services.seeder.seed_grammar --language all

# or one language at a time
python -m backend.services.seeder.run          --language he
python -m backend.services.seeder.seed_grammar --language he
```

Or use the wrapper, which runs both steps in order for each code:

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
       (SELECT count(*) FROM vocabulary_items v WHERE v.language_id = l.id) AS words,
       (SELECT count(*) FROM grammar_points  g WHERE g.language_id = l.id) AS points,
       (SELECT count(DISTINCT g.level) FROM grammar_points g WHERE g.language_id = l.id) AS levels
FROM languages l ORDER BY l.code;
```

`levels` below 6 means that language's grammar path stops short of C2.
