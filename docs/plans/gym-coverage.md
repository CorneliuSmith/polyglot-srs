# Gym coverage: expose what exists, then deepen what's thin

The owner's report, from two screenshots side by side: the English Gym is
poor "by name and by fullness" next to Portuguese. Measured across all
twenty languages before planning, the diagnosis inverts the obvious fix:
**the biggest gap is not missing content — it is existing content the Gym
never shows.**

Measured 17 Aug 2026 from `data/gym/*.json` (the manifests: which grammar
points appear as pickable forms) joined to `data/grammar/*_grammar.json`
(the points and their seeded drills).

## The two axes, measured

### Breadth — what the picker offers

| lang | forms shown | drilled points HIDDEN (≥6 drills, not in manifest) |
| --- | --- | --- |
| en | **12** | **31** |
| es | 15 | 32 |
| ca | 12 | 30 |
| ru | 25 | 30 |
| hi | 13 | 29 |
| ro | 13 | 29 |
| de / el | 15 / 13 | 28 each |
| it / fr | 15 | 27 each |
| nl | 16 | 26 |
| ar / tr | 15 / 17 | 25 each |
| pt | 19 | 23 |
| ko | 80 | 21 |
| he / fa / la / id / tl | 41 / 34 / 36 / 14 / 15 | **0 drilled** (their unexposed points have no drills) |
| **total** | 435 | **411 hidden, fully drilled** |

English is the worst case of a general pattern: its grammar path holds 43
drilled points and the manifest shows 12. The 31 hidden ones are not
scraps — they are *Do-support*, *the passive*, *relative clauses*,
*reported speech*, *gerund vs infinitive*, *third/mixed conditionals*,
*modals of deduction*, *inversion*, *cleft sentences*, the *mandative
subjunctive* — precisely the forms whose absence makes the picker read
as shallow next to Portuguese's future subjunctive and personal
infinitive. **The content exists. The menu doesn't mention it.**

Why: the manifests were authored at different moments with different
ambition — en/ca/es in the original WP25a pass, ko/he/fa/la in later,
more thorough passes — and nothing ever measured the drift.

### Depth — drills per exposed form

| band | languages | avg drills/form | forms under 6 | deficit to floor-10 |
| --- | --- | --- | --- | --- |
| deep | ko | 11.6 | 1 | 124* |
| adequate | it, ca, de, fr, el, ro, tr, es, ar, ru, hi, nl, pt, en | 6.0–8.5 | 0 | 28–86 each |
| **thin** | **he, fa, la, id, tl** | **3.9–4.7** | **138 of 138** | **84–219 each** |
| total | | | 139 | **1,578 drills** |

\* Korean's deficit is spread across its 80 forms; nothing there is under 6
except one.

The thin five are the newer languages whose baseline pass (task #80)
seeded 3–5 drills per form — enough to prove the Gym worked, never topped
up. A learner who picks one form and asks for 10 questions exhausts the
pool and sees repeats; that is the fullness the owner can feel.

## Targets (the definition of "full")

1. **Every drilled grammar point is exposed in the manifest**, grouped and
   labeled — unless deliberately excluded, in which case the manifest
   carries an explicit `"excluded": "reason"` entry so absence is a
   decision, not drift.
2. **Every exposed form has ≥ 10 unique seeded drills** (12 for A1 forms —
   they get the most traffic). 10 = one full default session on a single
   form with zero repeats, before generated drills add variety on top.
3. **Every entry has `label`, `usage`, `example`** — the "by name" half:
   a picker row must say what the form is and show it in action, in the
   house style Portuguese already has.
4. **A standing fullness report** so this cannot silently regress again.

## The plan

### Stage A — the exposure pass (breadth, near-free, biggest win)

No generation, no new content. For each of the 15 languages with hidden
drilled points: extend `data/gym/<code>.json` with entries for them —
title match to the grammar point, a short `label`, one-line `usage`, one
`example`. A script emits the candidate list per language (the audit
above is 80% of it); a human pass writes the labels and grouping, adding
picker columns where a category is missing (English needs at least
*Questions & negation* and *Clauses & style* beside its current two).
~411 entries × one line of copy each. English, as the named complaint,
goes first and becomes the reference manifest.

Effort: authoring, not model spend. This alone moves English from 12
visible forms to ~43 and every legacy language similarly.

### Stage B — the depth top-up (1,578 drills, generated → reviewed)

The machinery exists end to end: `generate_drills` (the Gym's own
on-demand generator, chart-aware), the maker–checker CLI, the flagged
recheck path, and the Review Inbox. One new CLI mode, `-k drills-topup`:
for every exposed form under floor, generate up to the floor, seeded with
the form's existing drills so new ones differ in frame (the
example-diversity lesson applies here verbatim — the generator must see
what it is diversifying against, and the checker rejects a batch that
adds drills without adding shapes).

Order: **he, la, fa, tl, id first** (the thin five, 771 of the 1,578),
then ru/pt/nl/en (their 44–86), then the rest. Everything lands
unreviewed in the Review Inbox, per the standing rule.

Cost: ~1,578 drills at maker+checker ≈ **$30–60 total**, drawn on the
operator key like all shared content.

### Stage C — names and hover copy (the "by name" half)

While stage A adds entries, a copy pass over EXISTING entries brings the
early manifests up to the later house style: specific names ("Future
with *will* vs *going to*", not "Future"), a real usage line, a real
example. English's current "Future / Conditionals" rows are the ones the
owner compared unfavorably — they get the Portuguese treatment.

### Stage D — the standing fullness report

The audit script from this plan becomes
`backend/services/seeder/audit_gym.py`, with two consumers:

- an admin-panel table (language × forms shown × hidden drilled points ×
  min/avg drills × deficit) — the metric that would have caught this drift
  years earlier;
- a CI check: a language's gym below floor, or carrying hidden drilled
  points without an `excluded` marker, fails the content check the same
  way the quality-program checker (task #121) already gates other content.

## Sequencing

| PR | Ships | Proves itself by |
| --- | --- | --- |
| 1 | audit_gym.py + admin fullness table + the en manifest exposure (12 → ~43 forms, new columns, full copy) | The English picker shows every drilled point; audit reports 0 hidden for en |
| 2 | Exposure pass for the other 14 legacy languages | Audit reports 0 unmarked-hidden everywhere |
| 3 | `-k drills-topup` + run over the thin five (he, la, fa, tl, id) | Every exposed form in those five ≥ 10 unique drills, all via Review Inbox |
| 4 | Top-up for the remaining deficit + CI floor check | Global deficit 0; CI fails on regression |

Stages are independent; stopping after 1 already transforms the screen in
the owner's screenshot.

## What this deliberately does not do

- **No auto-approval**: every generated drill goes through the Review
  Inbox; the thin five are also the newest content and least reviewed.
- **No manifest auto-generation**: labels and grouping are product copy;
  the script proposes, a human disposes. (The one exception: the audit
  may emit a draft entry block to edit, since title/level/example can be
  pulled from the grammar point itself.)
- **No new forms invented by the model**: breadth comes from the grammar
  paths, which are already reviewed. If a language's grammar path itself
  lacks forms (none of the twenty currently does for Gym purposes —
  ko/he/fa/la's rich manifests came from their paths), that is
  grammar-path work, out of scope here.
