# First run: admin content generation (WP42)

A runbook for the first time you use **Content generation** to fill a
language's example sentences and grammar drills with the Anthropic key.

Read the two ⚠️ callouts before your first real run — they're the ones that
cost money or surprise learners.

---

## TL;DR (the 60-second version)

1. Log in as an **admin** on the deployed app (the deployed server is the only
   place with the key).
2. **Contributor → Admin tab → "Content generation"**.
3. Pick a language (start with a **low-resource** one — the "Suggested next"
   chips rank them for you).
4. Choose **vocab** or **grammar**, set **max items = 5** for your very first
   run, leave target/each at 3.
5. Click **Preview cost** (free — no model call). Sanity-check the number.
6. Click **Generate now**, confirm the dialog.
7. In the **"awaiting review"** list that appears, **Approve** the good
   sentences (they go live to learners) and **Reject** the rest. Nothing
   reaches learners until you approve it.

---

## Before you start

| Requirement | How to check |
|---|---|
| `ANTHROPIC_API_KEY` set on the **deployed** server | The panel header shows **"Key ready"** (green). If it says "No server key", the *Generate now* button is disabled and you're on an environment without the key (e.g. local). |
| You have the **admin** role | The **Admin** tab only appears for admins. |
| You have credit on the Anthropic account | This spends real money — see [Cost](#what-it-costs). |

> The maker (drafting sentences) is the only paid step. The checker runs
> **offline** on the server (no model call), so it never adds to the bill.

---

## Where it is

**Contributor page → `Admin` tab → the "Content generation" card.**

It has three parts:

- **Suggested next** — languages ranked by how much is unfilled, low-resource
  first (they're the reason this pipeline exists). Click a chip to select it.
- **Coverage table** — every language: *vocab without examples*, *grammar
  without drills*, and *AI so far*. Click a row to select it.
- **Run controls** (appear once a language is selected) — kind, target/each,
  max items, **Preview cost**, and **Generate now**.

---

## Step by step

### 1. Pick a language

Click a **Suggested next** chip or a **coverage** row. The gap counts tell you
where the work is:

- `80/100` under *vocab without examples* → 80 of 100 words have zero example
  sentences.
- `5/20` under *grammar without drills* → 5 of 20 points have no drills.

### 2. Choose what to generate

Toggle **vocab** (example sentences for words) or **grammar** (fill-in-the-blank
drills for points). The card then shows:

- the **gap** for that kind, and
- the **model** it will use (from the task→model registry — low-resource
  languages are pinned to a stronger model automatically).

### 3. Set the size

- **target/each** — how many sentences each word/point should end up with
  (default 3, max 10). The run only tops up items *below* this.
- **max items** — how many words/points this one run will touch (default 25,
  max 100).

> **For your first run, set `max items = 5`.** You want a handful of real
> sentences to inspect before committing budget.

### 4. Preview the cost (free)

Click **Preview cost**. This is a **dry run**: it resolves the exact work-list
and an estimated bill **without calling the model**. You'll see:

> Would process **N** words, attempt **M** sentences — est. **~$X.XX**.

The estimate is deliberately **generous** (it over-states), so the real charge
is normally lower.

### 5. Generate

Click **Generate now** and confirm the dialog (it repeats the estimate). The run
does *maker → checker → save* for each gap item, then refreshes the coverage
numbers.

### 6. Read the result

> Done: processed 5, saved **12** new examples (1 duplicate skipped) —
> est. ~$0.04. They're tagged "ai" and await review.

- **saved** = sentences that passed the checker and were written **as pending**.
- **duplicates skipped** = the checker produced a sentence already in the pool;
  the idempotency guard dropped it (no harm, no extra learner content).
- If **saved is 0**, see [Troubleshooting](#troubleshooting).

Those saved examples now appear in the **"awaiting review"** list just below the
run controls. **Nothing reaches learners until you approve it there.**

---

## Generated vocab examples wait for your review

Generated **example sentences** do **not** reach learners automatically. Each
one lands **`reviewed = false`** — hidden from the reader, word examples, and
first-check quiz — and shows up in the panel's **"awaiting review"** list under
the language. There you:

- **Approve** → the sentence flips to reviewed and is served to learners.
- **Reject** → the sentence is deleted.

So the flow is: **generate → read the pending list → approve the good ones,
reject the rest.** The automated maker-checker is the first filter; your review
is the publish gate. The **"Pending"** column in the coverage table shows how
many are waiting per language.

> **Grammar drills are different.** A generated drill on an *already-published*
> grammar point is live immediately (drills don't have a per-row review flag
> yet). If you want the same wait-for-review gate on drills, say so and I'll add
> it. For now, treat a grammar run as publishing directly.

Everything generated also carries **`source = 'ai'`** with the model in
`origin_detail`, so it's always distinguishable and easy to
[roll back](#rolling-back-a-batch-if-you-dont-like-the-output).

---

## ⚠️ Low-resource languages have a stricter bar

The checker's core rule is: **the sentence must actually use the target word.**

- For a language **with an NLP backend** (e.g. Russian), an *inflected* form
  counts — `кошки` is accepted for the word `кошка`.
- For a language with **no backend** (many low-resource ones — exactly the ones
  you most want to fill), the check falls back to a **whole-word surface match**.
  A sentence that only uses an inflected form gets **rejected**.

Net effect: **accept-rates on backend-less languages will be lower**, and you
may need a couple of runs (idempotent, so that's fine) to reach target. This is
intentional — better to drop a sentence than serve one that doesn't teach the
word.

**To raise accept-rates on those languages**, point `APERTIUM_API_URL` at an
[Apertium-APy](https://apertium.org/apy) server (public or self-hosted). The
checker then asks Apertium whether a token is an inflected form of the target
word, so inflected forms count instead of being rejected. It's opt-in and
fail-safe (unset or unreachable = today's surface-match behavior), and currently
mapped for the languages Apertium ships analyzers for (e.g. `sw`, `ar`; see
`backend/services/apertium.py` to add more). For a language with neither a local
NLP backend nor an Apertium mode, adding a local backend is still the strongest
fix.

---

## What it costs

Only the maker is billed; the checker is free. A run of **25 words at target 3**
(~75 sentences attempted) estimates around:

| Model (task) | ~Cost for that run |
|---|---|
| `claude-sonnet-5` (high-resource default) | ~$0.10 |
| `claude-opus-4-8` (low-resource pin) | ~$0.20 |

Real charges usually come in **under** the estimate. A **$100** budget therefore
covers **thousands** of words across several languages — you are very unlikely
to run out on a first pass. The dry-run preview always shows the number before
you commit.

---

## Idempotency: why re-running is safe

Two guarantees make it safe to hand a button the key:

1. **Only gaps are touched.** A run reads the *current* count for each word/point
   and skips anything already at target. A word with enough examples is never
   sent to the model.
2. **Inserts dedupe.** Every generated sentence is unique-checked against what's
   already stored; a repeat is skipped, not duplicated.

So if a run is interrupted, or you run the same language twice, it **continues**
rather than re-spending. Bump `target/each` later and a re-run only fills the
*new* gap.

---

## After a run: auditing what was made

- The **coverage table** updates immediately — watch the "vocab without
  examples" / "grammar without drills" counts drop and "AI so far" rise.
- Generated content is browsable in the normal review surfaces (the **Vocab**
  review panel shows each word's example count; drills list under their point).
- Everything carries **`source = 'ai'`** with the **model id** in
  `origin_detail`, so it's always distinguishable from seed/imported/human
  content.

### Rolling back a batch (if you don't like the output)

Generated rows are tagged, so a bad batch is easy to find and remove. Against
the database:

```sql
-- Preview what a language's AI examples look like before deleting
SELECT es.sentence, es.translation, es.origin_detail
FROM example_sentences es
JOIN vocabulary v ON es.vocabulary_id = v.id
JOIN languages l ON v.language_id = l.id
WHERE l.code = 'sw' AND es.source = 'ai'
ORDER BY es.created_at DESC;

-- Remove them if needed
DELETE FROM example_sentences
WHERE source = 'ai' AND vocabulary_id IN (
  SELECT v.id FROM vocabulary v JOIN languages l ON v.language_id = l.id
  WHERE l.code = 'sw'
);
-- (Grammar equivalent: drill_sentences WHERE source = 'ai'.)
```

---

## Recommended first-run recipe

1. Pick **one** low-resource language from "Suggested next".
2. **vocab**, target/each **3**, **max items 5**.
3. **Preview cost** → **Generate now**.
4. In the **"awaiting review"** list that appears, **read each sentence** —
   check it's natural and actually uses the word. **Approve** the good ones
   (they go live), **Reject** the rest (deleted).
5. Happy with the quality? Re-run with **max items 25–50**, then move to the
   next language. Consistently bad? Tell me what was wrong so I can tune the
   maker prompt.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| **"No server key"**, Generate disabled | You're on an environment without `ANTHROPIC_API_KEY` (e.g. local). Use the deployed app. |
| **503** on generate | Same — the server has no key. Dry-run/preview still works everywhere. |
| **saved: 0** on a real run | Most likely the checker rejected everything — common on a backend-less language where the model used inflected forms. Try again (idempotent), or pick a language with an NLP backend to compare. |
| **Estimate looks high** | It's intentionally generous; the real charge is lower. Lower `max items` to cap any single run. |
| **Numbers didn't drop after a run** | If everything was a duplicate or rejected, nothing was saved. Check the result line's "saved" count. |

---

## What's under the hood (for reference)

- **Endpoints:** `GET /api/contribute/admin/generation/coverage`,
  `POST /api/contribute/admin/generation/run` (both admin-only).
- **Generator:** `services/generate.py` (`generate_examples` / `generate_drills`)
  → maker (model) + checker (offline).
- **Orchestration:** `services/generation_admin.py` (`plan_run`, `run_generation`).
- **Model choice:** `services/models.py` registry (`sentence_maker`,
  `grammar_maker`; low-resource pin).
- **Provenance:** every row tagged `source='ai'`, model in `origin_detail`
  (WP38).
