# Topic Lens, the first three courses (17 Sep 2026)

Phase 7 of `docs/plans/quality-parity.md`. The feature shipped complete in
October; what had never run is the classification itself — **209,693
vocabulary rows, every one `topic IS NULL`**. This is the first 3,159 of them.

Nothing is applied. The output is three files the owner feeds to a command
that already exists.

## Why these three, and only the top band

The plan's order is "the courses whose top band is already settled (`tr`,
`en`, `ru` — the three at override depth), then the small courses that fit
entirely inside their top 1,000". A topic is derived from the English gloss,
and Phase 2d is still deepening glosses elsewhere; classifying a word whose
gloss is about to change spends the human confirmation twice. These three are
the ones whose glosses are settled.

| course | band | classified |
|---|---:|---:|
| Turkish | top 1,000 | 1,061 |
| English | top 1,000 | 1,034 |
| Russian | top 1,000 | 1,064 |

One Turkish word (`canlı`, rank 763) came back unclassified and is left for
the next run rather than guessed at.

## Maker, then checker

A maker classified all 3,159 against the frozen 24-slug taxonomy. A checker
then re-judged **1,621 of them (51%)** — every assignment the maker rated
below 0.7, plus **every `abstract_general` assignment**, because that bucket
is where a lazy classification hides and the maker was told so.

- The checker **disagreed on 85 (5%)** and its slug was taken on every one.
- The commonest corrections were `school_learning → emotions_mind` (15),
  `body_health → emotions_mind` (8) and `abstract_general → emotions_mind`
  (7) — the maker was filing feeling-words under where they are studied or
  where they are felt in the body.
- **1,098 are still below 0.6 after both passes.** That is not a failure; it
  is the queue. Topics land `topic_source='ai'` and a human confirms them
  bucket by bucket, so a flagged uncertainty is exactly what that review is
  for.

## The distribution, and the one number worth explaining

| course | words | hidden buckets | visible buckets used |
|---|---:|---:|---:|
| Turkish | 1,061 | 395 (37%) | 22 / 22 |
| English | 1,034 | 302 (29%) | 22 / 22 |
| Russian | 1,064 | 497 (47%) | 22 / 22 |

**Russian's 47% looks wrong and is not.** An inflected language spends its
top band on grammatical machinery: `сама`, `наши`, `всей` and `та` are each
a separate frequency row and each is a pronoun or determiner form. Sampling
twelve at random returns prepositions (`по`, `у`, `до`), conjunctions
(`если`), determiners (`этот`, `та`) and pronoun case forms. Turkish shows
the same shape for the same reason (`onu`, `beni`, `kadar`). English, which
inflects least, has the lowest hidden share — which is the pattern you would
predict, and it is the check that the number is the language rather than the
classifier.

Every one of the 22 visible buckets is used in all three courses, so nothing
collapsed into a dustbin.

## What the owner runs

Nothing here touches production. Per course:

```
python -m backend.services.seeder.generate_content -l tr -k topics --topics-file data/topics/tr.json
python -m backend.services.seeder.generate_content -l en -k topics --topics-file data/topics/en.json
python -m backend.services.seeder.generate_content -l ru -k topics --topics-file data/topics/ru.json
```

`--topics-file` applies a classification through exactly the same path as the
paid estimator: same provisional `topic_source='ai'`, same review queue, same
`WHERE topic IS NULL` resumability, same audit row. Only the paid call is
skipped. Slugs outside the frozen taxonomy are rejected rather than stored, so
the migration's CHECK cannot be violated by a hand-made file — replayed
against `valid_topic` here, all three files pass with **zero** rejections.

Then confirm them in Workspace › Review › Topic buckets. Under Strict policy
they stay out of learners' topic view until confirmed.

## Files

- `data/topics/{tr,en,ru}.json` — what the command reads: `{code: {word: slug}}`.
- `data/topics/_provenance.json` — per word, the confidence and whether the
  maker or the checker decided it. Not read by anything; it is what makes the
  1,098-row review queue sortable by how unsure the pass was.

## Next

The plan's order continues with the small courses that fit inside their top
1,000 and will not be deepened further: `jam` (483), `la` (559), `mi` (961),
then `xh`, `ha`, `yo`. Those six are ~3,000 more words and need no new
instrument. The remaining ~203,000 rows sit behind Phase 2d by design.
