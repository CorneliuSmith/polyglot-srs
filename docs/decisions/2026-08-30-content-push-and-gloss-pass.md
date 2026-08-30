# 30 August 2026 — the production push, and the gloss pass

Written as a handover. Numbers here were measured on the day; re-measure
before relying on them (`audit_content`, and the counters below).

## 1. The production sequence ran

The owner ran migrations, `seeder.run` and `reconcile --apply` against
production. What landed: ~17,800 corrected definitions, ~5,200 parts of
speech, ~15,350 new vocabulary rows, **5,541 interlinear glosses and
transliterations**, and 272 alphabet letters across 8 scripts. Five courses
went from 90 words to full size (`id` 3,000, `he` 3,022, `fa` 3,028,
`tl` 2,999, `la` 598). **Zero learner cards were orphaned** — verified by
query, not assumed.

Three defects were found by running it, each fixed and merged:

* `backup_db.sh` **could never have worked on macOS**. bash 3.2 treats
  `"${arr[@]}"` on an empty array as unbound under `set -u`, and
  `SCOPE_FLAGS` is empty on the default path. CI runs bash 5, so it was
  green throughout. Then the same script picked pg_dump 16 for a 17.6
  server; the fix is the LOWEST client at least as new as the server, not
  the newest — a 17 client dumping a 16 server writes
  `SET transaction_timeout`, which 16 cannot restore.
* **All eight alphabet decks had never seeded.** `vocabulary.alternatives`
  is `NOT NULL DEFAULT '{}'` and an explicit NULL does not fall back to a
  default; `_letter_alternatives` returns None for any letter without a
  special case, which is the FIRST letter of every one of those alphabets.
  Each seeder died on its opening row, under 27 `OK` lines.
* **CI had been red for four days** on a shared-state test bug (the
  auto-translate baseline lane sees courses the toggle no longer covers).

## 2. What production still needs — the one a learner sees

`seed_sentences` inserts `ON CONFLICT DO NOTHING`, so it can only ADD. The
English thinning was applied to the FILE and never reached the database:
production carried 196,004 English sentences against a curated 70,975, and
the card for `I` served "I am you." while the bank held "I think he did it."

**`prune_sentences -l en --apply` is built, tested and merged, and has not
been run.** 127,363 rows go, 68,641 stay, zero words stranded, rollback file
written first. It is a bulk production DELETE, so it is the owner's to run —
an agent attempt was blocked by the auto-mode classifier, correctly.

Across all 27, 147,246 rows are unendorsed by any committed bank. See
CHECKS.md §18.

Also unexplained: **`EnglishSeeder` transforms 8,600 words** while
`en_frequency.tsv` holds 10,000, so `en` sits at 8,996 rows in production and
1,400 new words never inserted. Not a blocker at 99% top-1000 coverage.

## 3. The gloss pass: 16% → 73%

6,437 of 8,874 drills now carry a structural Leipzig gloss.

**100%:** en es ru hi it ca de el tr sw ha mi yo · **99%:** ko fr ·
**93%:** ro · **78%:** he · **zero:** ar fa id jam la nl pt th tl.

Two things make this repeatable rather than a one-off:

* `scripts/apply_drill_glosses.py` — the gate every proposal passes before
  it reaches a learner: cells == tokens, exactly one `___` on the
  `{{answer}}` token, the answer absent from every cell under a folded
  comparison at both granularities, at least one cell decomposing, and the
  gloss is not merely the blank. Ten tests.
* It reads a run's `journal.jsonl` as well as the task output, because the
  journal has held the full result **every time** the task file came back
  empty — which happened twice, and salvaged 2,541 glosses plus 1,570
  sentences from runs the usage limit killed.

**Verification is not uniform, and the difference matters.** es ru hi it ca
fr tr en were checker-verified. ko de el ro he are **maker-only** — the
session limit killed the check stage — and warrant a re-check.

## 4. Three measurements that were wrong before they were right

Recorded because each cost real time and each would recur.

* **"121 unanswerable drills" was 45.** The other 76 were the same answer
  capitalised because the blank opens its sentence (`Hi`/`hi`, `la`/`La`).
  Fold before comparing answers. (CHECKS.md §20)
* **"Arabic romanisation covers 7%" was 41%**, twice, in the same direction:
  `isascii()` rejects the `ā` of DIN 31635, and
  `name().startswith("LATIN")` rejects `ʼ` and `ʻ`, which is how that
  standard writes hamza and ayn. Name the Unicode blocks explicitly.
* **`test_portability` was "environmental"** — it was reporting a real bug
  in `backup_db.sh`, twice, while I called it a container-layout quirk.
  CI being green is not evidence a script works when CI runs a different
  bash.

## 5. Conventions clarified

* **A conjugation cue is not an answer leak** (CHECKS.md §19). `haben, wir`
  is the exercise's premise. And where the mark IS the answer — Romanian
  `a cânta` → `cântă` — the fold must not run at all.
* **Glosses are structural on all 27 courses, English included.** An earlier
  tripwire blocking `en` as "circular" treated the layer as a translation.
  The value is the decomposition (`have.NEG`, `bark.3SG`), the metalanguage
  is English everywhere, and no gloss field needs a locale.
* **The translation pipeline re-runs the guards on its own output**
  (CHECKS.md §16), because the label charter's correct instruction to copy
  quoted course-language material faithfully carries a hint's answer-leak
  into every locale.
