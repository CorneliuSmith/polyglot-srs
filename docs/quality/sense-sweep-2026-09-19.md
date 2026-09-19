# Rule 1 on the sense question: what 20 other courses look like (19 Sep 2026)

English's middle band was judged in full on 19 Sep and came back **13.0%**
rare-or-wrong. Quality rule 1 says a defect found in one language is a class
until the other 26 say otherwise. This is the other 26 asked the same question
— and the answer is not the one the headline numbers first suggested.

## 1. The measurement

A 60-row random sample from ranks 2,001–6,000 of every course that has the
band (20 of 26; `ha`, `jam`, `la`, `mi`, `xh`, `yo` have no rows there),
judged against `content_judge`'s `SENSE_RULES` with one agent per course, and
every finding re-judged by an independent checker told to refuse anything it
was not convinced by. In session, **no API key spent**.

| course | confirmed | course | confirmed | course | confirmed |
|---|---:|---|---:|---|---:|
| ru | 66.7% | it | 36.7% | he | 21.7% |
| es | 53.3% | de | 35.0% | tl | 16.7% |
| ca | 51.7% | nl | 35.0% | fa | 15.0% |
| el | 50.0% | hi | 31.7% | **en** | **13.0%** |
| pt | 46.7% | tr | 31.7% | id | 11.7% |
| sw | 45.0% | ar | 25.0% | th | 3.3% |
| fr | 40.0% | ro | 40.0% | ko | 1.7% |

Read that table and the obvious conclusion is that English is one of the
*healthiest* courses and Russian is four times worse. **That conclusion is
wrong**, and the category breakdown is why.

## 2. 90% of it is one already-named class

| category | n | share |
|---|---:|---:|
| **`relation_only`** | **355** | **90%** |
| dated | 17 | 4% |
| technical | 8 | 2% |
| not_a_sense | 8 | 2% |
| slang / wrong_pos / regional | 7 | 2% |

`relation_only` is CHECKS §36, the class the owner reported themselves
("coche as the definition for coches") and the largest one left. It is not a
new finding; the sweep re-found it.

**So the English defect — a definition that gives a real but rare sense,
which is what WordNet's sense ordering produces — is specific to English.**
Strip `relation_only` out and every other course sits at 0–5%. English's 13%
is the highest rare-or-wrong rate measured anywhere, and the pass that
repaired 236 of them was aimed correctly.

## 3. The finding that matters: the rule could not see its own class

`relation_only_gloss` already exists, is report-level, and is scoped to the
top `CARD_RULE_BAND` (2,000). Running its predicate `is_relation_only` over
every course:

| | rows |
|---|---:|
| what the rule reported inside its own band | **16** |
| what the corrected predicate finds inside that same band | **3,072** |
| what sits in 2,001–6,000, outside the band entirely | **19,169** |

The rule was reporting 16 rows while 3,072 in its own band carried the defect.
The cause is one anchor. The tail read `of <one token>` and then end-of-string,
and for a non-Latin script the extractor appends a romanisation:

> `third-person singular present indicative imperfective of нужда́ться (nuždátʹsja)`

Two tokens, so it never matched. That is the whole explanation for the shape of
the table in §1: **ru 0.1%, el 1.0%, he 2.3%, hi 0.1%, ar 0.1% against
ca 40.8%, pt 38.5%, es 37.2%**. Not a difference between the corpora — a
difference in what the regex could reach. The languages with the richest
morphology, where this defect is commonest, were the ones it was blind to.

Two more shapes escaped it: a relation naming no target at all
(`third-person plural present subjunctive`) and the Romance clitic form
(`infinitive of encontrar combined with lo`).

## 4. The correction, and how it was checked

The predicate now allows a trailing parenthetical, a `combined with` tail, and
a head that names no target. One line decides the hard case: **a parenthetical
is allowed only when it carries no meaning.**

- `of нужда́ться (nuždátʹsja)` — a romanisation. The row still teaches nothing.
- `of Geschenk ("gift, present")` — a translation. **A good row**, and it was
  the single false positive the first widening produced.

The quote marks are the discriminator. Measured against the 1,092 judged rows
from §1, using the judge's `relation_only` verdicts as positives and every row
it called `primary` as negatives:

| | |
|---|---|
| recall on confirmed `relation_only` | **87.9%** (312 of 355) |
| precision against rows judged `primary` | **100.0%** (0 false positives in 737) |

The 43 misses are long-tail phrasings — two parentheticals, `contraction of
war + es`, `strong/mixed nominative/accusative feminine singular`. Chasing
them would trade precision for recall on a report-level rule, which is the
wrong trade (rule 75).

## 5. What is deliberately NOT changed

**The rule's band.** The measurement says 19,169 rows sit in 2,001–6,000 where
the rule cannot look, and that band is one a learner reaches. But
`CARD_RULE_BAND` is a product decision about what a learner meets, the same
constant the card rules use, and §41 is a fresh reminder that changing a band
without a separate argument is how a fail-level rule goes red on correct
content. This ships the **bug fix** — a predicate that could not see its own
class — and leaves the **scope question** stated with its number attached.

Widening to 6,000 would take the reported figure from 3,072 to 22,241. That is
a decision about how much of the tail the programme intends to repair, not
about whether the rows are defective.

## 6. What this does not say

- **Not human review.** Maker–checker; 60 rows per course is a sample, not a
  census, so each course's percentage carries real interval width. The
  *direction* — that 90% of it is one known class — is not in doubt at 355 of
  395.
- **The 3,072 and 19,169 are mechanical**, reproducible, and independent of
  the judge. They are the number to act on; the sampled percentages are how
  the class was found.
- **Six courses have no rows in the band** and were not measured at all.
