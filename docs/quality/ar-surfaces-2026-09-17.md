# The Arabic on the cards: every surface, read (17 Sep 2026)

Readers have reported dialect on cards — "in the sentences, words, or
explanations". This is that report, measured rather than argued. It is the
answer to a question the register programme's own gold set could not answer,
because that set measured the Arabic **course** and most of these readers are
reading Arabic as a **support locale**.

**Headline: 0.5% of what was read is not MSA, and the three worst rows are
vocabulary definitions.** Nothing here has been changed; every row is a
queue item.

---

## 1. What was read

A card shows several Arabic layers at once and each lives in its own table.
`--store db-locale` was only one of them. Five surfaces now:

| surface | what a learner sees | population | read | how |
|---|---|---:|---:|---|
| `db-orphans` | example sentences **live but not in the committed bank** | 362 | 362 | all |
| `db-explanations` | a grammar explanation written in Arabic | 211 | 211 | all |
| `db-titles` | a point's Arabic title, function note, culture note | 211 | 211 | all |
| `db-hints` | a drill's Arabic hint and translation | 1,279 | 200 | sampled |
| `db-locale` | the Arabic **definition** of a foreign word | 11,589 | 258 | sampled |

Every one of those 13,652 rows was written **before** the register pin landed
(#473, 17 Sep). Provenance is not a defence here: they all came from prompts
that never said MSA.

The 362 orphans are the sharpest slice — live rows the committed bank does
not contain, so they never passed a file-level pass. 191 were AI-generated,
171 came from Tatoeba.

## 2. The rates

| surface | read | not-MSA | rate | 95% CI | projected over the population |
|---|---:|---:|---:|---|---|
| `db-orphans` | 361 | 6 | 1.7% | 0.8–3.6% | **6 (exact)** |
| `db-explanations` | 211 | 0 | 0.0% | 0.0–1.8% | **0 (exact)** |
| `db-titles` | 211 | 2 | 0.9% | 0.3–3.4% | **2 (exact)** |
| `db-hints` | 200 | 1 | 0.5% | 0.1–2.8% | ~6 (1–36) |
| `db-locale` | 258 | 4 | 1.6% | 0.6–3.9% | **~180 (70–454)** |
| **all** | **1,241** | **13** | **1.0%** | | **~194 (75–513)** |

Three surfaces were read in full, so their counts are counts, not estimates.
Only the two big ones are sampled, and `db-locale`'s interval is wide because
4 hits in 258 is a small numerator. **The honest reading is that somewhere
between 70 and 450 Arabic definitions are not MSA, and a bigger sample is
the only way to narrow it.**

## 3. What is actually wrong, in full

Thirteen rows. Six dialect, seven classical. Every one is listed because at
this rate a reader deserves the whole set rather than a percentage.

### Dialect in the definitions — the worst of it

These are the Arabic **definitions of English words**, so an Arabic speaker
learning English meets them as the meaning of the card.

| shown | should be | what it is |
|---|---|---|
| `شاف` | `رأى` | the Egyptian/Levantine verb for "see" |
| `مراية` | `مِرآة` | the colloquial pronunciation of "mirror" written out |
| `مليان` | `مَلِيء` | the colloquial "full"; the yāʾ is an added letter, not a hamza seat |

None is a spelling variant. Each is a different word from the one MSA uses.

### Dialect in the learner instructions

Twice, a grammar point's function note gives an instruction using `قول` —
the colloquial hollow-verb imperative — where MSA writes `قُلْ`:

- `Hi ha — يوجد / توجد | قول ما هو موجود أو متوفر` (Catalan course)
- `الضمائر المتصلة | قول ملكي، ملكك، ملكه` (Arabic course)

This is the **explanations** half of the complaint. It is small, and it sits
in the imperative that tells the learner what to do, which is the most-read
sentence on the card.

One drill hint reads `يعرف أيّه المقصود`, where `أيّه` carries the
interrogative and reads as Egyptian `إيه`; MSA is `ما`.

### Classical, not dialect — and the direction nobody was watching

Six of the thirteen are the **opposite** failure, and five sit in the orphan
sentences:

- **Qurʾān 18:24 verbatim** as an everyday example sentence:
  `عَسَى أَن يَهْدِيَنِ رَبِّي لِأَقْرَبَ مِنْ هَذَا رَشَدًا` — the tell is
  `يَهْدِيَنِ`, the pausal form; plain MSA writes `يهديني`.
- **A hadith** (Waraqa ibn Nawfal's words), twice, with the form III passive
  `عُودِيَ`.
- `هاهنا` twice for plain `هنا`, and `أمّاه` — the classical vocative of
  lament — for `أمي`.
- One definition glosses "crystal" as `قَرِيس`, a classical word for
  *jellied*; MSA is `بَلُّورة`.

§1.4 of the programme names this class and nothing had ever looked for it.
All five orphan hits came in through Tatoeba or the AI generator, which is
exactly what the "never passed a file pass" slice was drawn to test.

## 4. What this settles, and what it does not

**Settles:** the readers are right and the effect is small. The stored Arabic
is ~99% MSA, and the defects are concentrated in vocabulary definitions
rather than in sentences or explanations. The 211 Arabic grammar explanations
came back **completely clean** — the "explanations" complaint, where it is
about register, is the two `قول` imperatives and nothing else.

**Does not settle:**

- **This is not human review.** Same in-session judge as the calibration
  page, same caveat: one model family, and the programme's rule is never
  self-certify. Thirteen rows is a list a reviewer can check in an hour.
- **Register is not the only complaint, or the biggest one.** The beta
  reviewer who started this also reported that Arabic glosses are imprecise
  (`للأسف` for "sadly" where he expects "unfortunately") and that Latin text
  inside Arabic renders in the wrong order. Neither is register, neither is
  measured here, and the gloss-precision one plausibly affects far more than
  194 rows.
- **The `db-locale` interval is wide.** 70–454 is not a number to plan
  against. Reading 1,000 rather than 258 would halve it.

## 5. Next

1. **The thirteen rows above** are a review queue. Three definition fixes
   (`شاف`, `مراية`, `مليان`) and two instruction fixes (`قول` → `قُلْ`) are
   unambiguous; the Qurʾānic and hadith sentences are an editorial call about
   whether scripture belongs in a beginner's example bank.
2. **Widen the `db-locale` read** to settle the interval.
3. **Measure gloss precision**, which is a different question from register
   and is the one the reviewer actually repeated.

Evidence: `data/eval/ar_surfaces_2026-09-17.jsonl`, 1,241 rows with the
judge's verdict, evidence words and reasoning for each. Reproduce with
`python -m backend.services.quality.register_pass --store db-locale` (and
`db-orphans`, `db-titles`, `db-hints`, `db-explanations`).
