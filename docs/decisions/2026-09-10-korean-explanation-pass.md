# Korean: the 27th course through the explanation pass — 10 September 2026

The last course. Korean was held from the 7–8 September batches because
decision C might merge points away, and formatting a point that is then
retired is wasted reading. Decision C shipped on 8 September (#447), so the
pass ran on the 151-point file that decision left behind.

| read | rewritten | left alone | render as markdown | carry a table |
|---:|---:|---:|---:|---:|
| 151 | 140 | 11 | 140 (93%) | 86 |

**159 content defects corrected** — the highest rate of any course, and the
pass's whole point. The formatting is the occasion; the read is the value.

## Why Korean formats higher than any other course

93% against 47–90% elsewhere. That is the language, not the pass: 86 of 151
points hold a real paradigm — 받침 allomorphy (은/는, 이/가, 을/를, 이에요/예요,
(으)세요, (으)ㄹ), irregular stems (ㅂ, ㄷ, ㅅ, 르, ㅎ, ㄹ), and four speech
levels of the same sentence. Greek tripped an earlier version of the
restraint guard at 83% for the same reason and was found innocent.

The guard that survived those calibrations measures the PASS, not the
language: does a bold name the form the point actually teaches? Korean scores
**183 of 204 (89%)**, above the 26-course average of 87%. With Korean in, all
27 courses read **391 of 442 (88%)**.

## The defects were the same class every time: a rule its own drills falsify

- *Polite requests (으)세요* gave only the vowel and consonant stems, so its
  own rule derived 살으세요 for a drill whose answer is 사세요. The ㄹ row was
  missing, and so was 말하다 → 말씀하세요, which is another drill's answer.
- *Pure Korean vs Sino-Korean numbers with time counters* claimed a
  Chinese-origin time word always takes Sino-Korean numbers, then listed
  시(時), 시간(時間) and 번(番) — all Sino-Korean — under pure Korean. The rule
  is lexical per counter, not etymological.
- *Superlatives with 가장/제일* said they cannot go with a plain verb without
  an adverb, naming 좋아하다 as the only exception — and the point's own second
  drill is 저는 겨울을 제일 싫어해요.
- *직전에 / 직후에* restricted them to a time expression while two of its own
  six drills attach them to event nouns (시험 직전에, 졸업 직후에).
- *아무 + ~나 / ~도* opened "아무 is placed before a noun", which its own
  answers 아무나 and 아무도 falsify.

## Two adversarial passes, and the second one was not redundant

Every proposal was judged by a checker against the point's own drills. It
refused **4**: a ㅂ-irregular rule that derived *사랑스러원 for two drill
answers; an 으-linking rule that derived *길으며 against the drill answer 길며;
two examples trimmed while their English glosses were kept, so a table row
taught that 올 means "rain"; and "dropping 요 gives the casual form
throughout", which is wrong for 거예요 (반말 거야) and for the plain style
추워진다. All four were repaired to the checker's instruction and re-verified.

**Then a second pass re-read all 136 accepted edits under one narrow lens —
is every claim about Korean true? — and found 9 more.** Four matter:

- *아/어 주세요* enumerated the stem changes its drills need but omitted 하다,
  so the text derived 말하 주세요 against the drill answer 말해 주세요.
- *번째* said numbers from five upwards are unchanged before the counter;
  스물 shortens to 스무 (스무 번째), and the neighbouring point says so.
- *Questions ~니* said the ㄹ irregular is "the only irregular that applies";
  the ㅎ-irregular applies too (어떻다 → 어떠니, not 어떻니).
- *Questions ~ㄴ/은가(요)* stated the 받침 rule without the ㄹ exception, so it
  over-generated *길은가요 for 긴가요.

Four of the nine are the same shape: **a ㄹ-final stem exception left out of
an otherwise correct 받침 rule.** ㄹ is the consonant that behaves like a
vowel, and a rule stated as a clean consonant/vowel split is wrong for it
every time.

**The lesson, and it is new.** One adversarial pass has been enough for 26
courses. It was not enough here: 9 defects survived a checker that had
checked every 받침 against every drill and had refused four other points on
exactly this ground. The difference is that the second reader had ONE
question instead of six — formatting, faithfulness, renderer safety and
correctness were the first reader's job at once. For the hardest material,
narrowing the lens found what breadth missed. None of the nine was a
ship-blocker, which is the honest qualifier: the first pass caught everything
that would have broken a card, and the second caught what would have taught a
learner a rule that is false in one corner.

## Delivery

`data/grammar/ko_grammar.json` only — `explanation` fields, nothing else.
Reaches production through **one** `seed_grammar -l ko`, the same run that
carries decision C's five retirements. Korean is the only course not yet
level with its file (11 of 151); the other 26 landed on 10 September.
