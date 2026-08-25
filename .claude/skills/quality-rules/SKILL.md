---
name: quality-rules
description: The working rules of the language-quality program. Load before any content, definition, sentence, gloss, grammar, or guideline work on any course — they encode every failure this program has already paid for once.
---

# Quality program rules

The long forms live in `docs/quality/CHECKS.md`, `docs/quality/README.md` and
`docs/plans/quality-parity.md`. This is the digest to hold in context while
working. Each rule exists because its absence already shipped a defect.

## Scope — the rule the owner has had to repeat

1. **Every check applies to all 27 courses until decided otherwise.**
   A defect found in one language is a *class*; measure the other 26 before
   fixing one. A check is not finished until its row in `CHECKS.md` says
   all / parameterised / scoped-with-reason. (English's circular glosses,
   Latin's collisions, Māori's gloss were each "one language's quirk" — none
   was.)
2. **Fix the class, not the example the owner happened to screenshot.**
3. **A finding is not shipped until the guidelines say so.** Every fix updates
   `docs/quality/<code>.md` for each language it touched, `CHECKS.md` (status
   row), and the plan. Record what was measured, what changed, and what it
   COST — including decisions you did not take. A repair whose reasoning lives
   only in a commit message is invisible to the next session and to the owner.
   When a fix reveals that a standing owner decision has a price (the ar yeh
   fold merging 84 cards), write the price into the doc and leave the decision
   alone — surfacing it is the job, overruling it is not.

## Order of work (owner decision, 20 Aug 2026)

**Low-frequency courses first — clean AND populate** (`mi` step c, `ha`, `xh`,
`yo`, `jam`, `id`, `tl`, `he`, `fa`). Several are not yet real courses: `tl`
has 90 rows, `jam` 384. **Then** the deep pass on the well-resourced courses
to `en`/`la` standard. **Then** sentences, for all 27 at once — no course
reaches the sentence stage ahead of the others.

The expectation is that the deep pass will be lighter on the big courses
because their data is better. Treat that as a prediction to test, not a fact:
`ca` had no correct card for "I am" with 9,996 rows, and `es` had rank 79
`creo` glossed as the wrong verb. If the deep pass finds defects at English's
rate, say so — that result matters more than the phase closing quietly.

## Content

4. **One card per written form; the gloss names the senses** (D1c) — but where
   orthography CAN distinguish (macron, tone, accent), distinct words get
   distinct rows. **Re-marking is not decoration**: an unmarked row may stand
   for several words; decide which owns the rank, add rows for the rest, sweep
   for missing members after (D1d, CHECKS §8).
5. **A card has SIX layers; check every one, and name them precisely**
   (owner directive, 25 Aug 2026). **hint** (narrows the answer) · **sentence**
   (the example) · **translation** (its English) · **interlinear gloss** (the
   word-by-word line UNDER the sentence) · **romanisation** (non-Roman scripts
   only) · **definition** (the card's English meaning). "Gloss" named two of
   these for weeks — the interlinear line AND the definition — which is how
   `mi`'s shifted word-by-word survived an entire deep pass on definitions.
   Say which layer you mean; a fix to one is not a fix to another. Measured
   25 Aug: interlinear gloss is 100% on `mi` drills, 30% on `sw`, **0%
   everywhere else**; romanisation is absent from `hi` and `th` ENTIRELY, and
   from the `ru`/`ar`/`hi`/`th` sentence banks (see `CHECKS.md` §9).
6. **Examples must exercise the sense the gloss leads with** (D2c2). Definition
   and sentences are fixed in different files by different passes — a fix in
   one is not a fix in the other. On mismatch: fix the sentence, the gloss
   ORDER, or the coverage — decide which.
7. **Orthography and word list before sentences; sentences before glosses.**
   Everything downstream of a toneless headword is wrong at birth.
8. **A gloss never spells the answer; a wrong gloss is worse than none.**
   Mechanical glosses never overwrite authored ones, never serve GLOSS_FIRST
   courses. Not every sentence gets a gloss — 4,974 GLOSS_FIRST rows are the
   target, not 484k.
9. **A declared policy that nothing checks is being violated — two for two.**
   `la.md` asserted "macrons everywhere, verified" while `la_frequency.tsv`
   was 48% non-compliant; `jam.md` asserted Cassidy–JLU while 12 headwords
   broke it, three of them words the doc names as drift itself. Express the
   policy as a character set and test it (`test_orthography.py`). Necessary,
   not sufficient: `friend` breaks no Cassidy letter rule and is still English.
10. **A fold may excuse a mark; it may never launder a word.** Settled and
   shipped: a fold-only match grades WRONG_FORM when the typed string is
   itself another course word, sloppy otherwise (`test_nlp_collisions.py`
   ratchets per-language ceilings). Before folding anything new, ask what the
   mark DOES in that language — and check the fold-image of the vocabulary.

## Sources & spend

11. **Facts yes, sentences regenerated** — paradigms/vocab from licensed
   courses may inform; verbatim sentences may not ship.
12. **Never the API key.** Maker–checker runs in-session (Workflow tool).
13. **Fixes land in committed files** (`gloss_overrides.tsv`, TSVs, JSON) —
    a DB-only repair is undone by the next re-seed. Same logic one level up:
    a TSV-only deletion is undone by the next regeneration — durable
    deletions go in `data/vocab_exclusions.tsv` (typo-mass rows like `citta`
    "Tuscan girl", rank inherited from `città`).

## Verification

14. **Verify agent output mechanically before writing it back**: structural
    validators, spot-checks against known ground truth, and assembly by stable
    key, never by index (a rank drift once nearly filed `luna`'s gloss under
    `stella`). After writing a TSV, eyeball it: text containing `"` gets
    csv-escaped into `""..""` noise — reword the text instead.
15. **Re-measure any agent-reported number before acting on it** — two of five
    sampled claim-audit figures did not reproduce.
16. **State verification honestly**: "275 of 557 checker-verified, rest
    maker-only" — never round up to "verified".
17. **Never freeze a count the audit computes** — cite the rule name; the tool
    says the number. Hand counts carry date + method. "Verified" names every
    file the claim covers.
18. **Baseline ratchet**: equal is fine, worse needs `--update-baseline` and a
    written reason. Run `audit_content` before pushing content.

## Ship

19. Green = `npm run build` (not `tsc --noEmit`), `vitest`, backend pytest at
    baseline (7 known environment failures), `ruff`, audit PASS, CI green,
    then merge — standing authorization. Say plainly what was left out.
20. **When adding words to fill a homonym gap, add only members a learner
    meets** (`hīc`, `mālum` yes; `pōpulus` "poplar" no) and gloss each naming
    its false twin — "here (distinct from hic: this)".
21. **Nothing of value stays only on this machine** (owner directive, 20 Aug
    2026). After every merge — and before any long-running job — fast-forward
    `feat/phases` to the current head and push it:
    `git branch -f feat/phases HEAD && git push origin feat/phases`.
    This is a multi-week project on hardware that has already slept mid-run
    and killed a workflow; remote is the only durable copy. Workflow outputs
    and analysis scripts live in the session scratchpad under `/private/tmp`
    and do NOT survive — promote anything worth keeping into the repo.

## Maintaining this skill (owner directive, 19 Aug 2026)

This is a living document. When new work teaches a rule, **add it here in one
or two lines** — if it improves quality and does not bloat the digest. Keep it
small enough to load in every content session; long rationale goes in
`CHECKS.md` or the plan, with only the rule itself here. Prune a rule only
when the class it guards is mechanically checked everywhere.
