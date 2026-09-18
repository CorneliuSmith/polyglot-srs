# "More than 15 words are wrongly translated": measured (18 Sep 2026)

The Arabic beta reviewer's third complaint, the one that was never about
register. He is an Arabic speaker learning English, and he said the Arabic
glosses on the English cards are wrong — naming `للأسف` for **sadly** where
he expects "unfortunately".

He is right, he under-counted, and **the defect he pointed at is not the one
that is biggest.**

---

## 1. The row he photographed

| | |
|---|---|
| headword | **sadly** (rank 4,975) |
| English definition | "in an unfortunate way" |
| Arabic gloss | `للأسف` |

The Arabic is a **correct translation of that English definition**. `للأسف`
really does mean "in an unfortunate way". The defect is upstream: *sadly*
primarily means "in a sad manner", and the definition took a secondary sense.
The Arabic then faithfully carried it into his language.

The same shape sits on the cards around it — `runner` defined as a smuggler,
`cub` as "an awkward and inexperienced youth", `tab` as "the bill in a
restaurant".

## 2. Two defects, measured separately

360 English rows, stratified across six frequency bands, judged on two
questions: does the English definition give the sense a learner meets, and
does the Arabic render **that** sense with a matching part of speech.

### The English definitions: 8.1% rare or wrong

| band | n | primary | secondary | rare | wrong | not-primary | projected |
|---|---:|---:|---:|---:|---:|---|---:|
| 1–500 | 60 | 51 | 8 | 1 | 0 | 1.7% | 8 |
| 501–1,000 | 59 | 47 | 10 | 2 | 0 | 3.4% | 18 |
| 1,001–2,000 | 60 | 42 | 14 | 3 | 1 | 6.7% | 70 |
| **2,001–4,000** | 60 | 33 | 18 | 8 | 1 | **15.0%** | 308 |
| **4,001–6,000** | 59 | 37 | 12 | 8 | 2 | **16.9%** | 289 |
| 6,001–10,000 | 60 | 47 | 10 | 2 | 1 | 5.0% | 160 |
| **all** | **358** | **257** | **72** | **24** | **5** | **8.1%** | **~853** (417–1,732) |

**The damage is in the middle, not the tail.** The top 2,000 was repaired by
Phase 2d and shows it. The deep tail is largely technical vocabulary where
the "rare" sense genuinely is the word. Ranks 2,001–6,000 are where an
ordinary word gets an extraordinary definition, and that is exactly the band
the reviewer was reading.

**Nothing in the repo looks for this.** `wrong_sense` in `audit_content.py`
fires only inside the top 1,000 and only for letter-names and region codes.
This class is unmeasured at every rank.

### The Arabic glosses: 24.6% diverge — and this is the bigger number

| band | n | diverges | rate | 95% CI |
|---|---:|---:|---:|---|
| 1–500 | 60 | 16 | 26.7% | 17–39% |
| 501–1,000 | 59 | 13 | 22.0% | 13–34% |
| 1,001–2,000 | 60 | 11 | 18.3% | 11–30% |
| 2,001–4,000 | 60 | 15 | 25.0% | 16–37% |
| 4,001–6,000 | 59 | 16 | 27.1% | 17–40% |
| 6,001–10,000 | 60 | 17 | 28.3% | 19–41% |
| **all** | **358** | **88** | **24.6%** | |

**Projected: ~2,329 of the 9,056 Arabic glosses on English cards**
(95% CI 1,483–3,441).

Unlike the English defect, this rate is **flat across every band**. It is not
a tail problem or a middle problem. It is systemic.

## 3. This is a breach of the app's own contract, not a matter of taste

`translate.maker_system` tells the model exactly what to produce:

> the single word or short phrase a native speaker would use for **THAT
> specific sense** (use the definition and example to disambiguate). **Match
> the part of speech.**

So "diverges" is not "the Arabic is poor Arabic". It is "the Arabic does not
render the sense the English names, or is the wrong word class" — which is
the one thing the prompt asks for. Classified by the judge's own reasoning:

| | | |
|---|---:|---|
| plain sense mismatch | 54 | 61% |
| **wrong part of speech** | **21** | **23%** |
| transliteration instead of translation | 9 | 10% |
| register (literary or over-familiar) | 3 | 3% |
| names one instance, not the class | 1 | 1% |

Worked examples:

- **`mate`** (rank 1,090, verb) — English "engage in sexual intercourse",
  Arabic `صَدِيق` ("friend"). Both sides are wrong and they are wrong in
  different directions.
- **`whistle`** (rank 1,405, verb) — Arabic `صَفَّارَة` is the *object* you
  blow. The verb is `صفَر`. Wrong word class, which the prompt forbids.
- **`father`** (rank 183) — Arabic `بابا`, the nursery vocative. At the 183rd
  commonest English word the gloss should be `أب` or `والد`.
- **`ufo`** (rank 7,075) — Arabic `يُو أَف أَو`, the three English letters
  spelled out phonetically. Not a translation at all.
- **`board`** (rank 968) — English gives the committee sense, Arabic gives
  `لَوْحَة`, a plank. The two sides of the card disagree about which word this
  is.

**In 16 of the 358 the English was rare-or-wrong and the Arabic translated it
faithfully.** That is precisely the reviewer's experience: he sees an Arabic
error and the fault is in the English.

## 4. What this does not say

- **Not human review.** Same in-session judge as the register work, and the
  same rule applies: never self-certify. 358 rows is a sample a bilingual
  reviewer could re-check in an afternoon, and the per-row reasoning is in
  `data/eval/en_sense_ar_gloss_2026-09-18.jsonl`.
- **The intervals are wide** because each band is 60 rows. The direction is
  not in doubt at 88 of 358, but "2,329" should be read as "between about
  1,500 and 3,400".
- **Only Arabic was checked.** The same maker charter writes every support
  locale, so the 24.6% is a rate for the *pipeline*, not for Arabic. Turkish
  has 1,815 glosses and Spanish 297 under the same prompt, unmeasured.
  Quality rule 1 says a defect found in one language is a class.
- **No row has been changed.**

## 5. What follows

1. **The English middle band is the cheaper fix and helps every locale at
   once.** ~600 rows in 2,001–6,000 carry a rare sense; repairing them fixes
   the card for English learners and removes the upstream cause for all nine
   support locales, including the reviewer's.
2. **The wrong-part-of-speech class is mechanically detectable.** 23% of the
   Arabic divergences are a noun glossing a verb or the reverse. The
   vocabulary row already carries `part_of_speech`, so this does not need a
   model — it needs a check.
3. **Extend `wrong_sense` past rank 1,000.** Its band was chosen for the
   letter-name defect and has been carried unexamined into a rule that now
   demonstrably has work to do at rank 4,975.
4. **Re-measure one more locale** before treating 24.6% as an Arabic number.
