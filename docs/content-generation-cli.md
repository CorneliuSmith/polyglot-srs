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
  -l <lang-code> -k <vocab|grammar|levels|definitions|translations|overlap|forms> \
  [--recheck] [--target N] [--max N] [--locale <code>] [--dry-run]
```

| Flag | Meaning | Default |
|---|---|---|
| `-l, --language` | language code, e.g. `en`, `sw` | required |
| `-k, --kind` | `vocab` · `grammar` · `levels` · `definitions` · `translations` · `overlap` · `forms` | required |
| `--recheck` | audit **existing** content (see below): `-k vocab` audits example sentences, `-k grammar` audits drills | off |
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

### 5. Translate sentences into a support locale — `-k translations`

For a **non-English speaker learning English**, translate existing English
example sentences into their language (`--locale`). New locale rows land
`source='ai'`, `reviewed=false` (gated) — and until each is approved, the
learner keeps seeing the **English fallback** (no blank sentences). English
course only (`-l en`, non-English `--locale`).

```bash
python -m backend.services.seeder.generate_content -l en -k translations --locale ru --max 200
```

> Serving already prefers the learner's `support_locale` per sentence and falls
> back to English when a locale translation is missing — so this pipeline just
> raises coverage over time.

### 6. Quality-recheck existing content — `--recheck`

Audits content that **already exists** with an LLM judge, rather than only
filling gaps. `-k vocab` audits a word's example sentences; `-k grammar` audits
a point's drills.

For **`-k vocab --recheck`**, each word:

- **Flags** sentences that are wrong, unnatural, don't use the word, **or are
  too simple / low-value** for a learner (judged relative to the word's CEFR
  level) — marked for a reviewer, **not deleted**.
- **Backfills** a missing translation (for English, a plain-English
  *description* rather than a redundant echo).
- **Suggests** a better translation when the current one is present but weak —
  a proposed edit a reviewer accepts or dismisses (never an in-place overwrite).
- **Tops the word back up** to `--target` good sentences with fresh, verified
  alternatives.

For **`-k grammar --recheck`**, each point:

- **Flags** drills that are ungrammatical, mis-keyed (the answer isn't the
  right form for the blank), **or too trivial** to teach the form — marked for
  a reviewer, **not deleted**.
- **Tops the point back up** to `--target` good drills with fresh, verified
  alternatives.

```bash
# Dry run first — items to audit + cost estimate (vocab shown; swap -k grammar for drills)
python -m backend.services.seeder.generate_content -l en -k vocab --recheck --dry-run

# Audit existing English example sentences, heal each word back to 3 good ones (≤100 words)
python -m backend.services.seeder.generate_content -l en -k vocab --recheck --target 3 --max 100

# Audit existing English drills, heal each point back to 3 good ones (≤100 points)
python -m backend.services.seeder.generate_content -l en -k grammar --recheck --target 3 --max 100
```

Admins can also run either recheck from the UI — **Contribute → Admin →
Content generation → Recheck now** (with a dry-run **Preview recheck**); the
`vocab`/`grammar` toggle picks the corpus.

### 7. Flag overlapping grammar points — `-k overlap`

Runs happily **alongside a recheck** (it reads the syllabus, not the
sentences): an LLM judge scans a language's grammar points per level band
(each level together with the next one up, so boundary drift is caught) and
reports **pairs that teach substantially the same thing** — duplicate,
subsumes, or partial. Every reported pair becomes an **open review row**;
nothing is ever merged or deleted automatically. Related-but-distinct points
(contrasts like ser/estar, sequels like present→past) are explicitly not
overlap.

```bash
# Dry run — points to judge, judge calls, cost estimate
python -m backend.services.seeder.generate_content -l es -k overlap --dry-run

# Scan for real; pairs land in Contributor → Review → Overlapping grammar points
python -m backend.services.seeder.generate_content -l es -k overlap
```

Idempotent: a pair that's already open is never re-flagged, so re-running
(or running for every language after a recheck) only adds what's new. A
reviewer resolves each pair as **merged** (they folded the content
together by editing the points), **keep both**, or **not an overlap**;
resolved pairs can be re-flagged by a later scan if the content drifts back
together. Admin UI: **Content generation → Scan now** under the recheck
controls.

Requires the flagging/suggestion columns: `example_sentences` (migrations
`20260821…`, `20260822…`) for vocab, and `drill_sentences` (migration
`20260826…`) for drills.

### 8. Backfill Gym morphology charts — `-k forms` (WP45)

The Gym shows a word's conjugation/declension **chart** when the drill's
answer resolves to a chartable vocabulary row. Eleven languages have no chart
data at all, and even charted languages miss the words the offline
morphology build never covered. This mode closes those holes from the drills
themselves:

1. **Work-list** — every distinct drill answer the Gym's chart lookup cannot
   resolve (word missing from vocabulary, or its row has no chart tables).
2. **Maker** — the LLM produces the word's paradigm chart(s): lemma, part of
   speech, `[cell label, form]` rows, exactly what the Gym renders.
3. **Checker** — containment: the drill's answer **is a known-true form** of
   the word, so a generated chart that doesn't contain it (stress-mark
   folding applied) is provably wrong and dropped. Charts are data, not
   prose, so this proof is the gate — no separate human review queue.
4. **Persist** — the chart lands on the word's vocabulary row, **creating the
   row if the word was missing** (the dominant gap). Existing chart tables
   (the offline kaikki build) are **never overwritten**.

```bash
# Dry run — unresolved answers, charts to attempt, cost estimate
python -m backend.services.seeder.generate_content -l ko -k forms --dry-run

# Generate for real (capped per run; re-run until charts_to_attempt is 0)
python -m backend.services.seeder.generate_content -l ko -k forms --max 100
```

Idempotent: the work-list only ever contains answers still without a chart,
and a word whose stored `lemma` already resolves to a charted row is excluded
up front — repeated runs converge to zero. Charts show in the Gym
immediately. Admin API: `POST /api/contribute/admin/generation/forms`.
Provenance: each write is a `charts_generated` entry in the content change
log with the model in the note.

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
  **recheck judge** is one call per item — all of a word's sentences, or all of
  a point's drills, at once — and is priced in the `--dry-run` estimate.

---

## Rolling back an AI batch

Every generated row is tagged `source='ai'` with the model in `origin_detail`,
so a batch is easy to find and remove — see the SQL in
[`admin-generation-first-run.md`](./admin-generation-first-run.md#rolling-back-a-batch-if-you-dont-like-the-output).
