# The 1,231 English headwords the course never taught, classified (19 Sep 2026)

`CHECKS.md` §42 measured the class and named its three treatments without
knowing their sizes — the split there was a regex guess. This is the
measurement, and the one treatment that needed no decision, applied.

## 1. What the rows are

Every English frequency row that **nothing can define**: blank in the committed
file, unresolvable by `wordnet_sense.best_synset`, minus `seed_english`'s own
noise list. 1,231 rows, every one past rank 2,000, none carrying even a part of
speech — the extractor gave up on these entirely.

**They are not cards. They are absent.** This page first called them "cards
with no definition"; checked against production afterwards, **0 of the 1,231
are in `vocabulary`** (which holds 9,062 English rows). `seed_english` appends
an unresolvable row to `unglossed` and `continue`s, so the word never reaches
the course. A learner cannot meet `via`, `etc`, `café` or `coworker` at all —
which makes the finding worse than stated and the repair cheaper, because the
90 definitions below **add 90 cards** rather than fixing 90, and the proper
nouns are rows to stop counting as a gap rather than cards to delete.

Classified in session, maker–checker, **no API key spent**: 31 agents at 40
rows each, then an independent checker on every row proposed as definable.

| class | n | share | treatment |
|---|---:|---:|---|
| given name | 730 | 59.3% | the owner's 25 Aug rule |
| surname | 154 | 12.5% | the owner's 25 Aug rule |
| other proper noun | 51 | 4.1% | the owner's 25 Aug rule |
| place name | 13 | 1.1% | **kept** — the 25 Aug rule keeps places whatever the spelling |
| **ordinary word** | **74** | **6.0%** | **defined — this pass** |
| **interjection** | **51** | **4.1%** | **defined — this pass** |
| fragment | 68 | 5.5% | retirement candidate |
| misspelling | 32 | 2.6% | retirement candidate |
| unsure | 58 | 4.7% | routed to a human |

**948 of the 1,231 (77%) are proper nouns**, and 935 of those meet the 25 Aug
criterion. That is the number the owner's decision needs, and it is now
measured rather than estimated.

## 2. What was applied: 90 words the course did not teach

Of the 125 rows classified as ordinary words or interjections at confidence
≥ 0.7, **100 reached the checker and 90 survived it**; the checker judged 2
not definable after all and the rest fell below the confidence floor either
side. Every one then passed the sense pass's mechanical gates
(`scripts/apply_en_sense_fixes.py`).

These are not obscure, and until this lands a learner cannot meet any of them
in the English course:

| | |
|---|---|
| `via` (4,000, prep) | "by way of a place on a journey, or by means of a particular route" |
| `etc` (6,328, adv) | "and other things of the same kind, added at the end of a list" |
| `aka` (8,751, adv) | "also known as; used before another name" |
| `café` (5,878, noun) | "a small restaurant serving coffee, other drinks and light meals" |
| `fiancé` (5,344, noun) | "a man who is engaged to be married" |
| `coworker` (9,872, noun) | "a person employed at the same place as you" |
| `whichever` (8,124, det) | "any one or ones of a group, no matter which" |
| `mic` (6,838, noun) | "a device you speak or sing into so your voice can be amplified" |
| `thy` (2,176, det) · `thine` (9,191, pron) | the archaic second person, which WordNet does not carry |
| `heck`, `blimey`, `golly`, `oops`, `shhh`, `erm` | ordinary interjections a spoken corpus ranks high and no dictionary path reached |

**The count the guard reports fell from 1,231 to 1,141**, which is the check
that these landed. It will show as 90 NEW rows the next time the owner runs
`seeder.run -l en` — nothing changes in production until then.

**Each row gained a part of speech as well as a definition**, because these
rows had none. `seed_english` treats an override's `pos` as *pinned* — a
hand-authored part of speech is a decision, not a guess, and spaCy reading a
bare `via` would otherwise relabel it.

## 3. What was NOT applied, and why

- **The 948 proper nouns.** The 25 Aug rule retires a name "with no English
  equivalent named, unanswerable from a definition", and these have no
  definition at all, so they meet it with room to spare. The decision is
  smaller than it first looked: none of them is a card, so this is not
  deleting learner-facing content but adding exclusions so they stop being
  counted as a gap — the treatment `seed_english`'s own comment recommends.
  It is still the owner's, because the rule was applied once to a table they
  read.
  **The 13 place names stay regardless** — the same rule keeps places "whatever
  the spelling", on the owner's reasoning that a learner needs to recognise the
  word is the same but said differently.
- **The 100 fragments and misspellings.** `mustn` from *mustn't*, `nothin`,
  `gettin`, `iike` for *like*. `seed_english` already hand-drops four of these
  (`ain`, `isn`, `de`, `mm`), so the class is established as droppable — but
  extending a hand-list of 4 to 104 by machine classification is a content
  deletion, and this pass adds definitions rather than deleting cards. The
  list is in the evidence file, ready.
- **The 58 unsure.** Routed to a human, as the charter requires.

## 4. What this does not say

- **Not human review.** Maker–checker plus a mechanical gate. Every row's
  classification, both sides' reasoning, and whether it was applied are in
  `data/eval/en_blank_definitions_2026-09-19.jsonl` — 1,231 rows, one per line
  (quality rule 30).
- **The classification of a name is easier than its retirement.** Calling
  `susan` a given name is safe; deciding that the card should go is the part
  this pass does not do.
- **Only English.** It is the only course whose definitions are resolved at
  seed time rather than committed, and `empty_definition` reads 0 on the other
  26.
