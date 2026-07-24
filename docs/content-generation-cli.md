# Content generation from the CLI (`generate_content.py`)

The same maker–checker engine as the admin **Content generation** panel, run
from a terminal. Use it to fill example-sentence / drill gaps, estimate CEFR
levels for un-ranked vocab, and **quality-recheck existing sentences** in bulk.

For the point-and-click equivalent (and the cost/idempotency background), see
[`admin-generation-first-run.md`](./admin-generation-first-run.md). This doc is
the command-line reference.

---

## Prerequisites

| What | Why |
|---|---|
| Python env with the backend deps (`.venv`) | runs `backend.services.…` |
| `DATABASE_URL` | the database the run reads/writes |
| `SUPABASE_URL`, `SUPABASE_JWT_SECRET` | required to construct app settings |
| `ANTHROPIC_API_KEY` | **real** generation. Omit it and set `TUTOR_DEV_MOCK=1` for a deterministic **mock** run (no spend, for testing the pipeline) |

Everything generated lands **`source='ai'`, `reviewed=false`** — hidden from
learners until a human approves it in **Contributor → Review**. The CLI fills
the pool; approval stays a separate, human step.

```bash
# One-time per shell — point at the target DB and provide the settings inputs.
export DATABASE_URL="postgresql://…"          # your target database
export SUPABASE_URL="https://<project>.supabase.co"
export SUPABASE_JWT_SECRET="…"
export ANTHROPIC_API_KEY="sk-ant-…"           # real runs only
# (or, to test with no key/spend:)  export TUTOR_DEV_MOCK=1
```

> Tip: every command supports **`--dry-run`**, which resolves the exact
> work-list and a cost **estimate** *without calling the model*. Always dry-run
> first.

---

## Usage

```
python -m backend.services.seeder.generate_content \
  -l <lang-code> -k <vocab|grammar|levels|definitions> [--recheck] \
  [--target N] [--max N] [--locale <code>] [--dry-run]
```

| Flag | Meaning | Default |
|---|---|---|
| `-l, --language` | language code, e.g. `en`, `sw` | required |
| `-k, --kind` | `vocab` · `grammar` · `levels` · `definitions` | required |
| `--recheck` | vocab only — audit **existing** sentences (see below) | off |
| `--target` | example sentences per word / drills per grammar cell / good sentences per word (recheck) | 3 |
| `--max` | max gap items (or words) touched in one run | 200 |
| `--locale` | definitions only — locale the definition is written IN | `en` |
| `--dry-run` | work-list + cost estimate only; no model call | off |

---

## The four modes

### 1. Fill example-sentence gaps — `-k vocab`

Drafts + verifies new example sentences for words under `--target`.

```bash
# Dry run: show the work-list and cost, no model call
python -m backend.services.seeder.generate_content -l en -k vocab --dry-run

# Generate 3 examples per under-covered English word, up to 200 words
python -m backend.services.seeder.generate_content -l en -k vocab --target 3 --max 200
```

### 2. Fill grammar-drill gaps — `-k grammar`

Fills each thin paradigm cell of a grammar point up to `--target` drills.

```bash
python -m backend.services.seeder.generate_content -l en -k grammar --target 2 --max 100
```

### 3. Estimate CEFR levels — `-k levels`

AI-estimates a level for vocab that has none, so it can enter a deck
(`level_source='ai'`, provisional). Confirm the levels in **Contributor →
Review**; under a Strict language policy they stay out of learners' decks until
confirmed.

```bash
python -m backend.services.seeder.generate_content -l sw -k levels --max 200
```

### 4. Fill missing word definitions — `-k definitions`

Maker-checks a **definition** for words that have none (low-density languages
especially). Writes the definition in `--locale` (English by default). Owner's
rule for a concept the locale lacks a word for: **explain it in that locale; if
even that isn't possible, give the English explanation.**

**Gated:** definitions land in the **translation-review queue** for a human
(approve them in Contributor → Review), *unless* the language's policy is
`ai_ok`, in which case checker-passed ones apply directly and only rejects
queue. Idempotent — words already defined or already queued are skipped.

```bash
# Preview the gap
python -m backend.services.seeder.generate_content -l sw -k definitions --dry-run

# Fill missing English definitions for Swahili words (up to 200)
python -m backend.services.seeder.generate_content -l sw -k definitions --max 200
```

### 5. Quality-recheck existing sentences — `-k vocab --recheck`

Audits the sentences a word **already has** with an LLM judge, rather than only
filling gaps. For each word it:

- **Flags** sentences that are wrong, unnatural, don't use the word, **or are
  too simple / low-value** for a learner (judged relative to the word's CEFR
  level) — marked for a reviewer, **not deleted**.
- **Backfills** a missing translation (for English, a plain-English
  *description* rather than a redundant echo).
- **Suggests** a better translation when the current one is present but weak —
  a proposed edit a reviewer accepts or dismisses (never an in-place overwrite).
- **Tops the word back up** to `--target` good sentences with fresh, verified
  alternatives.

```bash
# Dry run first — words to audit + cost estimate
python -m backend.services.seeder.generate_content -l en -k vocab --recheck --dry-run

# Audit existing English sentences, heal each word back to 3 good ones (≤100 words)
python -m backend.services.seeder.generate_content -l en -k vocab --recheck --target 3 --max 100
```

Requires the `example_sentences` flagging + suggestion columns (migrations
`20260821…` and `20260822…`).

---

## Reviewing what a run produced

Open the word in **Contributor → Review** (the inline **ExamplesEditor**):

- **`pending review`** (amber) — a generated/alternative sentence. Approve or
  reject it.
- **`flagged`** (red) — a rechecked sentence the judge rejected, with the
  reason. Edit it to fix (clears the flag) or delete it.
- **Suggested translation** (indigo box) — a proposed replacement. **Accept**
  applies it; **Dismiss** keeps the current one. Trial reviewers see it
  read-only and can leave an advisory recommendation.

---

## Idempotency & cost

- **Gap runs** only touch items still under `--target`, and inserts dedupe on
  the sentence text — re-running continues rather than duplicating.
- **Recheck** excludes already-flagged rows and won't overwrite a pending
  suggestion, so a re-run converges.
- Only the **maker** is billed; the mechanical checker is offline. The LLM
  **recheck judge** is one call per word (all its sentences at once) and is
  priced in the `--dry-run` estimate.

---

## Rolling back an AI batch

Every generated row is tagged `source='ai'` with the model in `origin_detail`,
so a batch is easy to find and remove — see the SQL in
[`admin-generation-first-run.md`](./admin-generation-first-run.md#rolling-back-a-batch-if-you-dont-like-the-output).
