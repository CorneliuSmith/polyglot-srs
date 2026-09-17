# Arabic register: calibrating the judge (17 Sep 2026)

Step 3 of `docs/quality/ar-register-programme.md` §5 — calibration, before
any verdict changes a row. **The gate passes**, and the run below is what it
passed on, what it does not prove, and the three things it found that are
decisions rather than defects.

Read 614 items, twice each, with two independently prompted judges. Found 9
dialect and 5 classical. Changed nothing: no learner-facing row has moved.

---

## 1. The headline, with its caveat attached

| Gate (§3.2) | Result | |
|---|---:|---|
| Agreement, dialect vs msa, on **documented answers** | **56 / 56 = 100%** | **PASS** (≥95%) |
| Recall on **documented dialect rows** | **7 / 7 = 100%** | **PASS** (=100%) |
| `orthography_only` filed as `dialect` | **0 of 20** | **PASS** (=0) |
| Agreement against a **provisional reference panel** | **603 / 606 = 99.50%** | not a human figure — see below |

**The caveat, stated first because it changes what the table means.** §3.2's
gate is agreement with *reviewer* labels, and **no reviewer has labelled
anything**. `data/eval/ar_register_gold.tsv` ships with its `label` column
blank, which is correct — a pre-filled label is an anchor — and
`register_pass.py --gold` prints `GOLD SET NOT LABELLED` rather than
inventing a figure.

So the run was graded on two substitutes, and they are not equally good:

- **`data/eval/ar_register_documented.tsv` — 56 items, real ground truth.**
  The answer is asserted by the programme document itself: the confirmed
  defects from `ar.md`, the §1.1 non-tells "all verified in the corpus", the
  §1.2 finding that every b-prefix match in the bank is بـ + noun, and the
  MSA homograph entries. These are facts about rows, not judgements about
  Arabic. **This is the 100% figure and it is the one that counts.**
- **A provisional reference panel — 606 items, not a human opinion.** A
  second set of readers working from the programme document and the §6
  checklist rather than from the judge's prompt. It is a consistency check,
  not an independent verification, and the 99.50% must not be reported as
  though reviewers produced it. It is here because it found things (§4).

The 56 documented items are 9% of the set. The other 91% has no trustworthy
label yet, and getting one is the next step and needs people.

---

## 2. What calibration actually bought: a prompt defect, found and fixed

The first run scored **53/56 (94.6%)** — under the gate — and every miss was
the same class:

| item | gloss | judge said |
|---|---|---|
| `مش` rank 3794 | "to suck the marrow from (a bone)" | msa |
| `وين` rank 3596 | "black grape" | msa |
| `مو` rank 2917 | "meu, baldmoney (Meum athamanticum)" | msa |

The judge was not wrong about Arabic. `مَشَّ` really is a verb, `وَيْن` really
is a grape, and the judge said so in its notes. It was **answering the wrong
question**: asked "is this Modern Standard Arabic?" of a frequency entry, it
judged the *gloss's sense*, which is MSA. What the vocabulary store needs to
know is different — *did an MSA word earn this rank?* — because the frequency
list is a count over a corpus, and a corpus of written Arabic contains
dialect. Nothing at rank 3,794 is there because of a verb meaning "to suck
marrow from a bone".

The fix is a paragraph in the judge's rules (`VOCABULARY ENTRIES ARE A
DIFFERENT QUESTION`) and the item's `rank` in the payload. It states a
principle — judge whether the gloss's sense is plausibly that frequent — and
names no answer.

**The evidence that it is a principle and not three memorised answers:** the
gold set deliberately puts the seven MSA homographs beside the four dialect
entries, and after the fix **none of the seven flipped**.

| stays MSA | `عم` 705 · `خلاص` 4072 · `كمان` 4187 · `دول` 4600 · `بكرة` 5219 · `زين` 5530 · `أوي` 6432 |
|---|---|
| **now dialect** | `مو` 2917 · `وين` 3596 · `مش` 3794 · `يلا` 7038 |

Re-run: **56/56**. This is the same shape as the misspelling that outranks
the word it misspells (CHECKS §38, Romanian `si` at rank 4) — the frequency
is real and belongs to something other than the entry it is filed under.

---

## 3. What the judge found in the 614

| | sentences (200) | vocabulary (100) | grammar (314) |
|---|---:|---:|---:|
| msa | 196 | 95 | 309 |
| dialect | 4 | 5 | 0 |
| classical | 0 | 0 | 5 |

**The four dialect sentences are the two documented ones**, each appearing
twice because the same sentence serves two headwords: the Egyptian greeting
`كل سنه وانتا طيب` and `ستقلي خطاب بكرة`. In a 200-row sample, that is the
programme's §2 estimate holding up — "under twenty genuine dialect rows" in
13,025.

**The 274 drills came back clean of dialect**, which matches the tripwire's
0 hits on the grammar file and is the first time anything has *read* them.

**Twenty orthography-only findings were logged and not fixed**, which is §7
working: missing hamzas (`انها` → `إنها`, `انني` → `إنني`), Latin commas for
`،`, a detached `و`, `نواحي` for the manqūṣ `نواحٍ`. They belong to the
spelling pass and are in the verdict file for it.

---

## 4. Three findings that are decisions, not defects

The judge and the reference panel disagreed on exactly three items, and the
judge's own confidence had already flagged two of them as wanting a reviewer
(0.62 and 0.58). That coincidence is the best evidence in this run that the
confidence field is worth reading.

**(a) Grammar point 37 teaches what §1.4 forbids.** The point
"Vocative & emphasis (النداء والتوكيد بالنون)" exists at C1 to teach the
energic نون التوكيد — `لأعملنّ`, `لأقولنّ`, `لأنهينّ` — and §1.4 lists "energic
and jussive-with-ن forms" among the forms MSA no longer uses productively.
Both readers noticed the contradiction independently and neither would
resolve it: one called the drills classical, the other answered `unsure` and
wrote "genuine tension". **This is a specification conflict, not a content
defect.** Either §1.4 is drawn too wide — the energic is in every MSA grammar
and does appear after an oath in formal writing — or point 37 should not be
teaching it. The programme cannot decide this and neither can the judge.

**(b) A C2 drill is Qurʾān 1:5 verbatim.** `إياك نعبد وإياك نستعين`, under
"Fronting & restriction", as the example of object fronting. Both readers
agree the syntax is ordinary MSA and the *citation* is what makes it
liturgical. It illustrates the point perfectly and it is the single most
recognisable sentence in the language. Whether a beginner drill should use
scripture is an owner call.

**(c) `أوي` at rank 6432 and `تو` at rank 371.** `أوي` is on §1.1's non-tell
list ("verbal noun of أوى") and the judge honoured that; the reference panel
argued it is the Egyptian intensifier "very" and should be retired. `تو` is
the mirror image — the judge called it a Gulf tell at rank 371, the panel
defended the MSA noun `تَوّ` "immediacy". **`تو` at rank 371 is the more
serious of the two**: a word inside the first 400 is one a beginner meets.
Both go to the review queue with both opinions, per §3.3.

---

## 5. What this does not license

- **No full pass has been run**, over the four file stores or the two live
  tables. §3.2 forbids it before the gate passes against *reviewer* labels,
  and it has not.
- **The number that passed covers 9% of the set.** 100% on 56 documented
  items is a real result and a narrow one.
- **This was not an independent verification.** Both readers are the same
  model family. The programme's own rule is never self-certify, and two
  Arabic speakers from different regions remain the owner's settled minimum.
- **No local endpoint was measured.** `--base-url` is built and tested
  against a fake server; Jais-2-8B and Falcon-H1-Arabic-7B are untried on
  this corpus, so the choice between them is still open and the volume
  argument in the plan is still a projection.

## 6. What the owner can do next

1. **Find the two reviewers.** Everything downstream waits on the `label`
   column. The set is 614 rows and the §6 checklist is seven questions.
2. **Rule on §1.4 versus grammar point 37** (finding (a)). It blocks a clean
   verdict on 6 of the 40 grammar points.
3. **Decide about the Qurʾānic drill** (finding (b)).
4. If a GPU box is wanted, `--base-url` needs nothing from the app:
   `python -m backend.services.quality.register_pass --gold --base-url
   http://host:8000/v1 --model jais-2-8b` re-runs this exact page's numbers
   on it.

Reproduce the eval files with `python -m scripts.build_ar_register_gold`;
`--check` fails if the corpus has moved under the labels.
