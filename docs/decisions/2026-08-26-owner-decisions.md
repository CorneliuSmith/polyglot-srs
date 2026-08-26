# Owner decisions, 26 Aug 2026

Four calls made on the status write-up. These are standing instructions, not
suggestions — check this file before planning work in any of these areas.

## 1. The production push is GATED. Do not run it, do not ask to run it yet.

**The owner runs the production sequence when two things are complete:**

1. **The Gym level is finished.**
2. **The grammar concepts have been reviewed — and the grammar must be
   comprehensive**, not merely free of defects.

Until both hold, everything stays in files and git. This supersedes any
earlier reading of "ship what exists first": the owner has weighed the
argument that the deployed app is worse than the repository and decided the
release waits. Do not re-litigate it each session.

The sequence itself, for when the gate opens:

```
python -m backend.services.seeder.reconcile              # report only
python -m backend.services.seeder.run                    # new rows
python -m backend.services.seeder.reconcile --apply      # corrections + backfill
```

## 2. Thin the English sentence bank. Approved.

English carries 202,772 example sentences — 20 per word, against 2–3 in every
other course. Reduce to the best few per word, **selected for variety**, not
just the first N by rank. Glossing the unthinned set would cost more than the
other 26 courses combined.

## 3. Hebrew, Persian and Arabic get a real romanisation. Approved.

No romanizer can be computed for these — the scripts drop the vowels a reading
needs. So:

- **Follow a published standard and NAME it** in the module and the docs, the
  way `el` names ELOT 743 and `ko` names Revised Romanization.
- **Look words up** where the script is ambiguous. This is the method that
  rescued Thai: the reading is a LOOKUP from a dictionary, not a computation.
  `data/raw/{ar,he,fa}_kaikki.jsonl` are already on disk.
- Arabic was previously excluded "by design". That exclusion is overruled:
  excluded because it cannot be COMPUTED is not the same as excluded because
  it cannot be DONE.

## 4. Thai gets a phonetics hint under the romanisation. New layer.

RTGS carries no tone, and Thai is tonal, so the reading tells a learner how to
approximate a word rather than how to say it. Add a **phonetics** line beneath
the romanisation carrying the tone.

The data already exists: `data/th_readings.tsv` column 3 holds the Paiboon
tone-marked form for every row. The open problem is that 34% of Paiboon
entries use IPA letters (`gɔɔ-rá-nii`) a learner cannot read — so the work is
choosing a learner-readable notation, not finding the data.

**The owner intends to roll this layer out to other languages later**, so
build it as a general card layer, not a Thai special case.
