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

## Content

4. **One card per written form; the gloss names the senses** (D1c) — but where
   orthography CAN distinguish (macron, tone, accent), distinct words get
   distinct rows. **Re-marking is not decoration**: an unmarked row may stand
   for several words; decide which owns the rank, add rows for the rest, sweep
   for missing members after (D1d, CHECKS §8).
5. **Examples must exercise the sense the gloss leads with** (D2c2). Definition
   and sentences are fixed in different files by different passes — a fix in
   one is not a fix in the other. On mismatch: fix the sentence, the gloss
   ORDER, or the coverage — decide which.
6. **Orthography and word list before sentences; sentences before glosses.**
   Everything downstream of a toneless headword is wrong at birth.
7. **A gloss never spells the answer; a wrong gloss is worse than none.**
   Mechanical glosses never overwrite authored ones, never serve GLOSS_FIRST
   courses. Not every sentence gets a gloss — 4,974 GLOSS_FIRST rows are the
   target, not 484k.
8. **A fold may excuse a mark; it may never launder a word.** Settled and
   shipped: a fold-only match grades WRONG_FORM when the typed string is
   itself another course word, sloppy otherwise (`test_nlp_collisions.py`
   ratchets per-language ceilings). Before folding anything new, ask what the
   mark DOES in that language — and check the fold-image of the vocabulary.

## Sources & spend

9. **Facts yes, sentences regenerated** — paradigms/vocab from licensed
   courses may inform; verbatim sentences may not ship.
10. **Never the API key.** Maker–checker runs in-session (Workflow tool).
11. **Fixes land in committed files** (`gloss_overrides.tsv`, TSVs, JSON) —
    a DB-only repair is undone by the next re-seed. Same logic one level up:
    a TSV-only deletion is undone by the next regeneration — durable
    deletions go in `data/vocab_exclusions.tsv` (typo-mass rows like `citta`
    "Tuscan girl", rank inherited from `città`).

## Verification

12. **Verify agent output mechanically before writing it back**: structural
    validators, spot-checks against known ground truth, and assembly by stable
    key, never by index (a rank drift once nearly filed `luna`'s gloss under
    `stella`). After writing a TSV, eyeball it: text containing `"` gets
    csv-escaped into `""..""` noise — reword the text instead.
13. **Re-measure any agent-reported number before acting on it** — two of five
    sampled claim-audit figures did not reproduce.
14. **State verification honestly**: "275 of 557 checker-verified, rest
    maker-only" — never round up to "verified".
15. **Never freeze a count the audit computes** — cite the rule name; the tool
    says the number. Hand counts carry date + method. "Verified" names every
    file the claim covers.
16. **Baseline ratchet**: equal is fine, worse needs `--update-baseline` and a
    written reason. Run `audit_content` before pushing content.

## Ship

17. Green = `npm run build` (not `tsc --noEmit`), `vitest`, backend pytest at
    baseline (7 known environment failures), `ruff`, audit PASS, CI green,
    then merge — standing authorization. Say plainly what was left out.
18. **When adding words to fill a homonym gap, add only members a learner
    meets** (`hīc`, `mālum` yes; `pōpulus` "poplar" no) and gloss each naming
    its false twin — "here (distinct from hic: this)".

## Maintaining this skill (owner directive, 19 Aug 2026)

This is a living document. When new work teaches a rule, **add it here in one
or two lines** — if it improves quality and does not bloat the digest. Keep it
small enough to load in every content session; long rationale goes in
`CHECKS.md` or the plan, with only the rule itself here. Prune a rule only
when the class it guards is mechanically checked everywhere.
