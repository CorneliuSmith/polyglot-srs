# Evaluation sets

## `ar_register_gold.tsv` — for the two Arabic reviewers

614 items the register judge is graded against:
200 sentences, 100 vocabulary entries, all 274 grammar drills, all 40
explanations. The full brief is `docs/quality/ar-register-programme.md` — §1
for what "not MSA" looks like, §6 for the seven-question checklist. Results
so far: `docs/quality/ar-register-2026-09-17.md`.

**Fill four columns. Leave the rest alone.**

| column | what to write |
|---|---|
| `label` | one of `dialect`, `classical`, `msa`, `orthography_only`, `unsure`, `broken` |
| `variety` | for `dialect` only: `egyptian`, `levantine`, `gulf`, `iraqi`, `maghrebi`, `mixed` |
| `evidence` | the exact word or words that carry your label, space-separated |
| `note` | anything the label alone does not say — especially *why*, when it was close |

`id`, `store`, `field`, `text`, `translation` and `stratum` are machine-written.
Do not edit them; the `id` is how your label finds its row again.

**Three things worth knowing before you start.**

1. **Spelling is not register.** Word-final ى vs ي, ة vs ه, hamza seats,
   tashkeel, Arabic-Indic digits — the grader already folds all of these and
   the course treats them as coached, not failed. If that is the only oddity,
   the label is `orthography_only`, not `dialect`.
2. **A false alarm costs more here than a miss.** Several ordinary MSA words
   collide with dialect words: عم, دول, عمال, كمان, زي, مين, الحين (inside بين
   الحين والآخر), and بـ before a *noun* is the preposition, never the
   b-imperfect. A word is a tell only in its dialect sense, in this sentence.
3. **`unsure` is a real answer.** It routes the row to a second opinion, which
   is what it is for. Use it rather than guessing.

**The set is deliberately hard.** It contains the confirmed defects and, next
to them, the words that look like defects and are not — `بكرة القدم` is
football, `كمان` is a violin. That is what makes it able to measure anything.

Two reviewers from different regions is the settled minimum; where you
disagree, both opinions are kept (§3.3) rather than averaged.

Rebuild with `python -m scripts.build_ar_register_gold`. Run `--check` before
labelling: it fails if the corpus has moved under the ids.

## `ar_register_documented.tsv`

The 56 of those items whose answer the programme document already asserts —
the confirmed defects, the verified non-tells, the b-prefix rows, the MSA
homograph entries. Machine-generated from the same script, no judgement call
in it. It is what the judge was calibrated on while the gold set is unlabelled,
and it is **not** a substitute for the review.

## `ar_register_calibration_2026-09-17.jsonl`

What the judge said about all 614, before and after the prompt fix, beside an
independent reference panel's opinion. Evidence for the figures in
`docs/quality/ar-register-2026-09-17.md`; the reference labels are not human
review and the results page says so.
