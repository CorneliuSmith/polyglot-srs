# The top band's relation-only definitions, repaired (19 Sep 2026)

CHECKS §43 corrected a predicate that could not see its own class and found
**3,072 rows in the top 2,000** whose definition gives a grammatical relation
and no meaning. This is those rows repaired.

**After: 154.** The class the owner reported themselves — "coche as the
definition for coches" — is effectively gone from the band the programme
committed to.

## 1. What was done

| | |
|---|---:|
| rows in the top 2,000 reading as a bare relation | 3,072 |
| rewritten (one agent per 40 rows) | 3,072 |
| confirmed by an independent checker for that language | 2,930 |
| applied after the mechanical gates | **2,918** |
| **remaining in the band** | **154** |

In session, maker–checker, **no API key spent**. 22 courses: ru 750, el 714,
nl 180, de 160, es 146, fr 124, ca 120, he 119, hi 108, pt 105, it 102, ro 86,
ar 81, fa 56, tr 30, ko 13, sw 11, ha 9, th 2, yo 1, tl 1.

## 2. The house shape, and the one thing that goes wrong

Meaning first, relation in parentheses — the form this programme settled on:

| was | now |
|---|---|
| `de sagt` — "third-person singular present" | "he/she/it says, tells (third-person singular present of sagen)" |
| `ru работает` — "third-person singular present indicative imperfective of работать" | "he/she/it works, is working; it runs, functions (third-person singular present of работать)" |
| `el θέλετε` — "second-person plural present of θέλω" | "you want, you would like — plural or polite (second-person plural present of θέλω)" |
| `he מימי` — "plural construct state form of מַיִם" | "waters of, the water of (plural construct of מַיִם, water)" |
| `ro idei` — "indefinite plural" | "ideas (indefinite plural of idee)" |

**The failure mode is glossing the lemma instead of the form**, and both the
maker's charter and the checker's said so in as many words: a third-person
singular is "he/she needs", never "to need"; a plural is "weeks", never
"week". The checkers caught it and also corrected source analyses that were
simply wrong — Hindi `देंगे` was stored as a *singular* future and is a plural.

`de sagt` and `ro idei` are worth looking at twice: their old definitions named
**no target word at all**. That is the shape §43's predicate was blind to, so
these rows have been teaching nothing for as long as the corpus has existed
and no instrument could say so.

## 3. The gates, and the 248 good repairs they refused on the first run

Five mechanical gates, the decisive one being that **a rewrite still tripping
`is_relation_only` is refused as not-a-repair** — nothing else in the pipeline
would catch a repair that did not repair.

The first run refused 251 rows and **248 of them were good**. Two gates were
wrong, both for the same reason: they tested the whole line when the house
shape puts the relation in parentheses and the relation is *allowed* to name
the lemma.

- `es debe` → "he/she/it must, ought to; owes (third-person singular present
  of deber)" was refused as circular. `deber` is in the parenthesis, which is
  where the learner needs it.
- `ru сына` → "(of) a son, a son's" was refused for "leading with the
  parenthesis". It leads with a parenthesised optional English word, which is
  how a genitive is glossed.

Both gates now run on the definition with parentheticals stripped. After the
fix, 12 refusals stand: 6 genuinely circular, 3 with nothing outside the
parentheses, 2 still bare relations, 1 carrying a citation. **Quality rule 19
earned its place again: verify every hit before it becomes a number** — the
hits here were the rule's own refusals.

Also applied: 15 definitions had double quotes normalised to single ones,
because a `"` in a TSV field csv-escapes into `""..""` noise (rule 28). 123
rows in the file already carry that noise from before it was noticed; they are
not this pass's to rewrite.

## 4. What is left

**19,169 rows in ranks 2,001–6,000**, untouched, because the rule's band stops
at 2,000 and §43 deliberately left that scope question open rather than
bundling it with a bug fix. This pass is the argument for taking it seriously:
the band it did cover went from 3,072 to 154, and the same repair at the same
quality is what the next band would need.

**154 in the band**, the residue of long-tail phrasings the predicate reaches
but the pass could not confidently rewrite — mostly rows where the checker did
not know the word and correctly said so rather than guessing.

## 5. Measured afterwards: 97.7%

2,918 definitions shipped on two model opinions and a set of gates, with no
human reading any of them. "Maker-checker" is not a precision figure, and rule
30 says state verification honestly — so a **third** agent, shown the old and
new definitions but neither earlier agent's reasoning, audited a 10% random
sample (304 rows, every course, at least 12 each where they existed). It was
told to expect errors and that a wrong "correct" is worse for the measurement
than an honest "unsure".

| verdict | n |
|---|---:|
| correct | 296 |
| wrong inflected form | 4 |
| shape | 2 |
| wrong meaning | 1 |
| unsure | 1 |

**97.7% precision on the 303 rows it was willing to judge** (95% CI roughly
95–99%). Projected over the pass: around 70 of the 2,918 carry a defect of some
kind, and about 10 a wrong meaning.

**All seven problems share one cause, and it is a rule this pass did not
have.** The charter told the maker to make the meaning match the FORM. It did
not tell it to leave the card's stored RELATION alone — so where the stored
relation was ambiguous or wrong, the model helpfully re-analysed it, and
sometimes re-analysed it into a different lexeme:

- `es cree` / `creen` — the card records a present subjunctive, which for
  *creer* would be `crea`/`crean`; `cree`/`creen` as subjunctives belong to
  *crear* "to create". The repair read them as *creer*'s indicative and glossed
  "he/she believes".
- `el κινητό` — recorded as the accusative masculine of the adjective
  *κινητός* "movable"; the repair led with the substantivised neuter noun,
  "mobile phone".
- `tr köpeği`, `kralı` — the repair widened the relation to "accusative or
  3rd-person possessive" and glossed only the accusative, so a learner meeting
  the possessive ("his/her dog") is misled.
- `pt façam` — a subjunctive glossed with indicative English.
- `it preoccupi` — a usage example smuggled into the parenthesis.

**Four were corrected.** Three were not, and the reason is worth keeping: for
`es cree`, `es creen` and `el κινητό` the card's stored relation and the sense
a learner actually meets **genuinely disagree**. At rank 438 Spanish `cree` is
overwhelmingly "he/she believes"; the stored relation says it is a subjunctive
of *crear*. Restoring the stored reading would make the card correct about
morphology and useless about meaning. Both readings are recorded in
`data/eval/relation_only_audit_2026-09-19.jsonl`; this is a call for a human
who can say which word the card is meant to teach.

**The rule for next time** (now quality rule 81): a repair glosses the form the
card names. It does not re-analyse the relation — and when the relation looks
wrong, that is a finding to report, not a thing to quietly fix, because
changing it changes which word the card teaches.

## 6. What this does not say

- **Not human review.** Maker–checker with mechanical gates, measured at
  **97.7%** by an independent third pass over 10% of it (§5). Every row's
  rewrite, the checker's verdict and reasoning, and whether it was applied are
  in `data/eval/relation_only_repair_2026-09-19.jsonl` — 3,072 rows, one per
  line — and the audit in `relation_only_audit_2026-09-19.jsonl` (quality
  rule 30).
- **Nothing is live.** These are `gloss_overrides.tsv` rows; they reach
  learners at the owner's next `reconcile --apply` / `seeder.run`.
- **The meanings are a model's.** The confidence floor was 0.7 on both sides
  and a checker that did not know a word was asked to refuse rather than
  guess, which is where most of the 142 dropped rows went.
