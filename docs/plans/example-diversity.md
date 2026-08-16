# Example sentences: generating for the thin words

A plan, not an implementation. The owner asked for "option 2" — find the
vocabulary whose examples collapse to one or two patterns and generate
replacements with the strengthened prompts — scoped and costed before it
runs across all languages.

Measured 16 August 2026 against `data/*_sentences.tsv`.

---

## What is actually wrong

The earlier sentence-diversity work strengthened the **generation** prompts.
That was correct and it changed nothing a learner sees, because the examples
they meet are not generated: they are harvested Tatoeba rows sitting
verbatim in `data/<code>_sentences.tsv`. Strengthening the prompt for
sentences we weren't writing improved sentences nobody reads.

So "I'm not seeing the diversity" is not a regression and not a prompt
problem. It is a **supply** problem, and it has two distinct shapes:

| Shape | What the learner sees | Corpus-wide |
| --- | --- | --- |
| **Thin** — one example, ever | The same sentence every time the word comes round | 13,127 words |
| **Monotone** — several examples, one pattern | «Он идёт.» «Он ест.» «Он спит.» | 11,576 words |

Together ~24,700 of 113,216 word-entries, or **22%**. Structural redundancy
*within* a word's set was measured at 0.6% earlier — that number was right
and it was measuring the wrong thing. The problem isn't duplicates; it's
that high-frequency function words attract short, frame-identical sentences
and nothing else, because that is what a parallel corpus contains for them.

### Where it hurts

Corpus-wide totals are the wrong scope. Ranked against each language's own
frequency list, restricted to the **top 1,000 words** — the ones a learner
actually meets in their first year:

| | thin | monotone | needs work |
| --- | --- | --- | --- |
| ko | 150 | 135 | **285** |
| ca | 141 | 129 | **270** |
| sw | 148 | 108 | **256** |
| hi | 58 | 144 | **202** |
| th | 122 | 74 | **196** |
| el | 27 | 93 | 120 |
| ha | 93 | 27 | 120 |
| mi | 73 | 22 | 95 |
| it | 2 | 69 | 71 |
| ro | 26 | 42 | 68 |
| ru | 0 | 62 | 62 |
| yo | 41 | 9 | 50 |
| pt, de, fr, ar, tr, es, nl, xh, jam, en | ≤5 | ≤40 | 4–45 |
| | | **total** | **2,090** |

That table is the plan. This is **not** a corpus-wide regeneration — it is
mostly a low-resource-language gap. English, Spanish, French, German,
Russian, Turkish, Dutch and Portuguese are essentially healthy where it
counts (4–45 words each); Korean, Catalan, Swahili, Hindi and Thai carry
half the total between them, because Tatoeba never covered them.

Doing the top-1000 band across every language is **2,090 words**. Doing the
whole corpus is 24,700 — twelve times the cost for words a beginner will
not meet for years.

---

## The detector

One module, `backend/services/seeder/audit_examples.py`, because the same
measurement has to serve three callers: the report, the generation queue,
and the after-check.

```
thin(word)     := count(examples) < 2
monotone(word) := distinct_shapes(examples) <= 2
shape(sentence, word) := (token_count, first 3 tokens excluding the word)
```

`shape` is deliberately crude. It catches the failure the owner reported —
same length, same frame, one slot swapped — and it does not pretend to
measure semantic variety, which needs a model and would make the detector
cost as much as the fix. Anything cleverer belongs in the checker below,
where a model is already in the loop.

Two known limits, stated because a silent cap reads as coverage:

- It reads the **seed TSVs**, not the database. The DB also carries
  AI-generated and reviewer-edited examples, so the real per-language
  numbers will be lower than the table above. The first thing to build is
  the DB-backed version of this query; the TSV numbers are the upper bound
  and the scoping argument, not the work order.
- It is monolingual and orthographic. For Korean and Thai, token counts
  mean something different than they do for Spanish, so the thresholds
  need a per-language sanity read before the queue is trusted.

---

## The generation pass

Reuses the maker–checker path in `generate_content.py` rather than adding a
fourth generator. One new kind, `-k examples-diversity`:

1. **Select** — thin and monotone words in the target band, worst first
   (thin before monotone; within each, by frequency rank).
2. **Make** — one call per word, given the word, its gloss, its CEFR level
   and **its existing examples**, asked for N sentences that differ from
   those in structure, not just vocabulary: a question, a past tense, a
   subordinate clause, a different subject person, the word in a non-initial
   position. The existing examples in the prompt are the whole point — a
   generator that cannot see what it is diversifying against writes the
   same frame again.
3. **Check** — the existing checker, plus one added test: does the new set
   *raise* the shape count? A batch that adds three sentences and no new
   shapes is rejected as a no-op rather than filed as progress.
4. **File** — as `source='generated'`, `reviewed=false`, into the normal
   Review Inbox. Nothing reaches a learner unreviewed. This is the same
   rule the rest of the generation program runs under and there is no case
   for an exception here.

### Cost

At roughly one maker + one checker call per word, and 2,090 words in the
top-1000 band, this is on the order of **$25–60** depending on model, run
once. The whole-corpus version is $300–700. Both draw on the same allowance
line as every other generation kind, so they are visible in the admin panel
rather than appearing as an unexplained spike.

I would run it **one language at a time**, largest gap first — Korean,
then Catalan, Swahili, Hindi, Thai — and stop after the first to read what
actually landed in the inbox before committing to the other twenty-one.

---

## Sequencing

| Stage | What ships | Why this order |
| --- | --- | --- |
| 1 | `audit_examples.py` + a report per language, DB-backed | The numbers above are from the TSVs. Nothing should be generated against a count that hasn't been checked against what the database actually holds. |
| 2 | `-k examples-diversity` for ONE language (ko) | The riskiest assumption is that the model, given existing examples, writes structurally different ones. Find out on 285 words, not 2,090. |
| 3 | The remaining low-resource four (ca, sw, hi, th) | Half the total, same shape of problem. |
| 4 | The rest of the top-1000 band | Small per language; batch them. |
| 5 | *Optional* — beyond the top 1,000 | Only if the earlier stages show it matters. It probably doesn't. |

Stage 1 is worth having on its own: a standing per-language report of which
words a learner will meet the same sentence for, which is a content-quality
metric the project currently has no view of at all.

---

## What I would not do

- **Not regenerate the whole corpus.** 22% of word-entries look thin, but
  the words a learner meets are overwhelmingly fine in the big languages.
  Spending twelve times the cost to fix words nobody has reached is the
  wrong trade.
- **Not delete the harvested sentences.** They are real, attested and
  licensed. The fix is to *add* alongside them, so a word ends up with its
  Tatoeba sentence and two or three generated ones with different shapes.
- **Not auto-approve.** Every other generation kind goes through the Review
  Inbox and this one is not special. It is also the kind most likely to
  produce plausible-but-unnatural sentences, since it is explicitly asking
  for constructions the corpus didn't supply.
- **Not measure semantic diversity in the detector.** It would need a model
  per word to decide, which costs as much as generating the replacement.
  The checker already has a model in the loop; put the judgement there.

---

## Open questions for the owner

1. **How many sentences per word is "enough"?** I have assumed a floor of
   three with at least three distinct shapes. Higher is better content and
   linearly more money.
2. **Does this go through the trial-reviewer queue or straight to you?**
   2,090 words at 3 sentences each is ~6,000 rows to approve. That is a
   real amount of human time and the bulk-approve path exists, but bulk
   approval of the content type most likely to read as unnatural is
   arguably the wrong place to use it.
3. **Korean and Thai thresholds.** Their token counts are not comparable to
   the European languages'; the shape heuristic may over- or under-report
   there, and someone who reads them should look at fifty rows before the
   queue is trusted.
