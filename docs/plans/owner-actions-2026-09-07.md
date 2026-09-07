# What you still need to do — 7 September 2026

Everything below is either a command only you can run (production writes)
or a decision only you can make. Nothing here is code work; that continues
without you. Read top to bottom: the order matters.

## STOP — read this first (7 Sep, late evening)

Your dry run of `reconcile -l all` at 11:39 showed `gloss 0` for every course
but English. That was not because the definitions were already right: **the
1,611 definitions authored this week reached neither the frequency files nor
production**, because the override file (`gloss_overrides.tsv`) only ever got
into a course through a rebuild of its frequency file, and the reconcile
compared against the file's column alone. Production still teaches Turkish
`mi` as "Used to form interrogatives." — after your `seeder.run -l tr`, which
wrote the linked spellings correctly but, like every non-English seeder, read
the stale column. Measured read-only, per course, before the fix:

| in the override file | already in the file | already in production | in neither |
|---:|---:|---:|---:|
| 4,297 | 2,537 | 2,686 | **1,611** |

Fixed in the PR after #430: the reconcile now compares against the file
**with the overrides laid over it**, every seeder lays the same overlay over
its records before writing (so a re-seed can no longer put a stale column
back), the dry run prints the **retire** column it had been computing and
not showing, and `new` counts only rows a seeder would actually create.

The retire step exists and the migration has landed (checked read-only at
the same time: `retired_at` present, 0 rows retired). Everything you have run
so far — backup, `supabase db push`, `seeder.run -l tr` — stands. What is
left, from here, once that PR is merged and pulled:

```bash
git pull origin main
```

```bash
.venv/bin/python -m backend.services.seeder.reconcile -l all
```

The fixed tool's own dry run against production, 7 Sep late evening, read
`gloss 1,594 · pos 3,370 · gone 40,861 · new 0 · s-layer 191 · retire 848 ·
unret 0`. Yours should match; if a number is far off, stop and paste it.
`new 0` means the English seeder step (old step 2) has nothing to add —
the reconcile now carries English's part-of-speech corrections too — so
skip it. Then:

```bash
.venv/bin/python -m backend.services.seeder.reconcile -l all --apply
```

Grammar, one course at a time — `-l all` hung after its fifth course on
7 Sep when the pooler dropped the session (DEBT); ar ca de el en are done,
so the loop below starts at es. Rerunning a finished course is harmless.

```bash
for c in es fa fr ha he hi id it jam ko la mi nl pt ro ru sw th tl tr xh yo; do .venv/bin/python -m backend.services.seeder.seed_grammar -l $c; done
```

```bash
for c in ar ca de el en es fa fr ha he hi id it jam ko la mi nl pt ro ru sw th tl tr xh yo; do .venv/bin/python -m backend.services.seeder.prune_sentences -l $c --apply; done
```

The original step list below is kept for the record; steps 0, 1 and 2b are
done.

**A fourth decision, D, surfaced by the same dry run** — see Part 2.

## Part 1 — Commands, in this order

Every command reads `DATABASE_URL` from `.env`. None takes the DSN on the
command line. Run from the repository root.

### 0. Snapshot

```bash
./scripts/backup_db.sh
```

### 1. The migration that makes the retire step work

Migration `20261016_vocabulary_retired` adds `vocabulary.retired_at`. Until
it lands, every exclusion this week made — 868 words — is still served, and
step 3 below reports "skipped".

```bash
supabase db push
```

### 2. English vocabulary: the words WordNet never had

66 glosses for words like `what`, `how`, `because` that the course did not
teach at all. Add-only; nothing is touched that exists.

```bash
.venv/bin/python -m backend.services.seeder.run -l en
```

### 2b. Turkish: the linked harmony spellings (added 7 Sep, evening)

`mi/mı/mu/mü`, `de/da` and `ta/te` are one card each now (your decision;
CHECKS §30). The seeder is what writes the linked spellings to
`vocabulary.alternatives` and loads the 13 re-tagged sentences under the head
spelling — `reconcile` does not carry either — so this runs BEFORE step 3,
which then retires the five variant rows and `ii`. Add-only for everything
else; the Turkish file also renames `irak` → `ırak` (the old row is left in
place and can be retired later — it is a proper noun at rank 3,117).

```bash
.venv/bin/python -m backend.services.seeder.run -l tr
```

### 3. Corrections and retirements — the big one

This applies the Phase 2d definitions (1,602 rows across all 27 courses; the
three Turkish particles now state the harmony rule instead of the outcome)
AND retires the 868 excluded words. Dry run first, read the `retire` count,
then apply. The rollback file is written before anything changes.

```bash
.venv/bin/python -m backend.services.seeder.reconcile -l all
```

```bash
.venv/bin/python -m backend.services.seeder.reconcile -l all --apply
```

### 4. Grammar: the rewritten hints and the Thai glosses

508 hints rewritten across 22 courses, 151 Thai glosses, 11 English notes.
All 27 grammar files changed, so run it for all.

```bash
.venv/bin/python -m backend.services.seeder.seed_grammar -l all
```

### 5. Prune — still outstanding from last week

The dry runs you did on 6 Sep are still valid (91,774 rows). Apply per
course; each writes its own rollback under `out/`.

```bash
for c in ar ca de el en es fa fr ha he hi id it jam ko la mi nl pt ro ru sw th tl tr xh yo; do .venv/bin/python -m backend.services.seeder.prune_sentences -l $c --apply; done
```

### After the run

Open the English course in Review and check one card each for `what`,
`em` (should be gone), and any Turkish yes/no question — those three
exercise steps 2, 3 and 4. Full detail: `docs/quality/refeed.md`.

## Part 2 — Decisions only you can make

### A. Turkish `mi / mı / mu / mü` — four cards or one?

**Decided, 7 Sep evening: one card, linked, showing the parity the sentence
takes — shipped (CHECKS §30, `tr.md`). Nothing left to decide here; the only
action is step 2b above.**

They are one morpheme, the yes/no question particle, in four spellings
that vowel harmony chooses. The vocabulary file has always carried them as
four rows (ranks 6, 16, 48, 163), and until this week all four showed the
identical definition "Used to form interrogatives" — so a learner facing
any of the four cards could not know which spelling to type.

**What was changed:** only the definition text, via `gloss_overrides.tsv`.
Each now says it is the yes/no question particle and names the vowels it
follows. The rows, ranks and parts of speech are untouched (one row's POS
was `prep`, a pre-existing error; the override says `particle`).

**What was NOT changed, and is your call:** whether four cards should exist
at all. The Gym already drills the harmony choice. If you would rather one
vocabulary card — "the yes/no particle" — with harmony left to the Gym, that
means retiring three rows, which the retire step can now do. Say which and
it is a one-line change to the exclusions file. Until then, the four cards
are at least answerable.

### B. Twelve written abbreviations, held

Portuguese `s` (segundo), `h` (hora), `d` (Dom) were judged not-words;
Spanish `s` (sur), `x` (por), `m` (metro) were defended as things Spanish
writers really write. Both readings are reasonable and they cannot both be
the rule. Is a written abbreviation a vocabulary card? Whichever way, it
applies to every course at once. Details in DEBT.md.

### D. 40,861 production rows the files no longer govern (new, 7 Sep)

The `gone` column: rows in the database that are not in any committed
frequency file — reported, never deleted, and not retired because they are
not in `vocab_exclusions.tsv`. Classified read-only on 7 Sep:

| class | rows | what it is |
|---|---:|---|
| tail | 39,004 | words an older generation of the list had (ru 5,913, es 4,871, ca 4,941, pt 4,578, fr 3,988, it 3,936, de 3,687, el 3,486, ro 2,871). Almost all sit INSIDE the file's rank range, not beyond it: a regenerated list ranked different words there. Live cards, glosses from before the quality program. |
| unmarked twin | 678 | a spelling that differs from a file word only by a mark: la `amo`/`amō` (39, the whole Latin departed set, with 2 learner cards), yo 122, ro 101, fr 90, pt 74, es 71 … Some are the WORSE form (es `salio`), some the BETTER one (ru `актёр` — the file has `актер`). |
| letter / mark / digit | 331 | ko jamo ㄱ ㄴ ㄷ … (40, 12 with learner cards), th consonants (36, 4 with cards), fa 32, he 22, tr 27, hi 17 … deleted from the files directly instead of through the exclusions file, so the retire step cannot see them. |

Options, cheapest first: (1) leave all live and record it (today's state);
(2) add the 331 glyphs to `vocab_exclusions.tsv` mechanically and retire
them on the next reconcile — low risk, one PR; (3) a judged pass over the
678 twins deciding per pair which spelling the course keeps — Phase 2e
work, a workflow, not mechanical; (4) retire every ungoverned row — 40,861
cards gone from the decks, ~37% of Russian's. Recommendation: 2 now, 3 as
the next Phase 2e item, 4 only after 3 has said which twins are the better
form. Full list: session scratchpad `departed.json` (regenerate with the
read-only query in CHECKS §31 if that is gone).

### C. Korean teaches four topics twice

"Topic particle 은/는" appears as two grammar points, so does "에 vs 에서".
Merging them needs a retire path for grammar points that does not exist
yet — the same gap vocabulary had until this week. Say whether you want
that built (a migration + reconcile step, mirroring #417) and the four
pairs merged.

## Part 3 — What was verified about the vocabulary this week

Because you asked: every change to the vocabulary layer since 6 Sep,
measured against git.

- **194 words removed** from frequency files — every one has a row in
  `vocab_exclusions.tsv` with a reason: 94 letters, punctuation and
  extraction debris across 24 courses; 37 English words WordNet glossed as
  chemical symbols or clitics; 59 English given names and contraction
  fragments; 4 rare twins breaking the grading of common words.
- **0 words added.** **0 ranks changed.** **0 glosses edited inside a
  frequency file** — every definition change is an override row, and the
  applier refuses a definition for a word the course does not have.
- A second reader defended every exclusion candidate before it was
  removed, and saved 135 of 241: Russian `я`, French `à`, Korean `그` were
  all candidates and all stayed.

None of it reaches production until steps 1 and 3 above.
