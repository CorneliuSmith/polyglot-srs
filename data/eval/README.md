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

---

## The content judge's other four questions — sets to be built (18 Sep 2026)

`backend/services/quality/content_judge.py` asks five questions of a row; the
register question above is the first and the only one with a gold set. The
other four cannot pass their gates until reviewers label one each. This
section is the specification of those files, so a reviewer can build one
without reading the code.

Grade a set with

    python -m backend.services.quality.content_judge --question sense --gold

which prints the three gates (agreement on the finding-versus-clean split at
95%, recall on the labelled findings at 100%, the near-miss class never filed
as the finding) and exits 2 below them. It spends the API key unless
`--base-url` names a local endpoint, and says so first.

**Every set is a UTF-8 TSV with these columns, in this order:** `id`,
`store`, `field`, `label`, `category`, `evidence`, `note`, `stratum`, and then
the question's own item columns listed below. `id`, `store`, `field`,
`stratum` and the item columns are machine-written when a builder exists and
hand-written otherwise; the `id` is how a label finds its row again, so it
must be stable (a database row's `es:<uuid>` / `tr:<uuid>`, or
`<code>-vocab-<rank>` for a frequency-list entry — the judge reads the rank
from that id when the set has no `rank` column, which is how the register
set works). Reviewers fill `label`, `category`, `evidence` and `note`, and
leave the rest alone. `unsure` and `broken` are legal in every set: `unsure`
routes the row to a second opinion, `broken` means the row is defective for
some other reason and should not be compared.

Every set needs both halves. A set of findings measures recall and nothing
else; the rows that LOOK like findings and are not — each question's
near-miss label below — are what measure precision, and a false alarm has
cost this programme more than a miss every time.

### `sense_gold.tsv` — does the English definition give the sense a learner meets?

Item columns: `word`, `rank`, `pos`, `definition` (the English definition as
the card shows it). Stratify by frequency band the way
`docs/quality/en-sense-ar-gloss-2026-09-18.md` §2 did — 60 rows in each of
1–500, 501–1,000, 1,001–2,000, 2,001–4,000, 4,001–6,000, 6,001–10,000 — and
seed it from `en_sense_ar_gloss_2026-09-18.jsonl`, whose 358 rows already
carry a machine opinion (`sense_verdict`) a reviewer can confirm or
overturn.

| `label` | meaning |
|---|---|
| `primary` | the sense most learners meet first and most often |
| `secondary` | a real, common sense that is not the one this rank was earned by — **the near-miss label**; acceptable on a card, never a finding |
| `rare` | a genuine but rare, technical, dated, regional or slang sense that cannot have earned this rank (`runner` the smuggler) |
| `wrong` | not a usable sense: a different word, the wrong part of speech, or a grammatical relation with no meaning ("first-person singular of X") |

`category` for `rare`/`wrong`: `technical`, `dated`, `slang`, `regional`,
`relation_only`, `wrong_pos`, `not_a_sense`. Put the short everyday
definition you would expect in `note`.

### `gloss_gold.tsv` — does the locale gloss render THAT sense, in the same part of speech?

Item columns: `word`, `pos`, `definition` (English), `gloss`, `locale` (the
gloss's language code). Judge the gloss against the DEFINITION: when the
English is itself a rare sense and the gloss carries it faithfully, the gloss
is `faithful` and the row belongs in the sense set. Seed from the same jsonl
(`ar_gloss`, `arabic`), and add a second locale before treating any rate as
Arabic's — the maker charter writes every support locale.

| `label` | meaning |
|---|---|
| `faithful` | a word or short phrase a native speaker would use for the definition's sense, same part of speech |
| `synonym` | faithful, and not the word you would have chosen — **the near-miss label**; compared as `faithful` |
| `diverges` | not the definition's sense, or the wrong word class |
| `absent` | empty, or not in the locale's language at all |

`category` for `diverges`: `sense_mismatch`, `wrong_pos`, `transliteration`,
`register`, `instance_not_class`. Put the gloss you would expect in `note`.

### `scripture_gold.tsv` — is this everyday example sentence scripture?

Item columns: `sentence`, `translation`, `language` (the course code). Seed
from the rows `docs/quality/ar-surfaces-2026-09-17.md` §3 found (Qurʾān 18:24,
the hadith), then add hard negatives: sentences ABOUT religion that are not
scripture, everyday formulae (إن شاء الله, "bless you"), proverbs and poetry,
MSA press register — and rows from at least one non-Arabic course, because
the class is not Arabic's.

| `label` | meaning |
|---|---|
| `scripture` | verbatim or near-verbatim scripture or fixed liturgy |
| `literary` | a proverb, a line of poetry, a famous speech, an anthem — **the near-miss label**; a quotation, not scripture |
| `plain` | an ordinary sentence |

`category` for `scripture`: `quran`, `hadith`, `bible`, `tanakh`, `hindu`,
`buddhist`, `liturgy`, `other`. Name the source in `note`.

### `card_shape_gold.tsv` — should this card carry an example sentence at all?

Item columns: `word`, `pos`, `definition`, `language` (the course code). Seed
from CHECKS §37's alphabet rows, DEBT.md's twelve held abbreviations and bare
stems, and Tatoeba's personal names; then add the 758-row class that looks
like a finding and is not — one-character WORDS such as Italian `e`, Russian
`а`, Portuguese `a`, Hebrew `ב`, Arabic `ب`, Māori `i`.

| `label` | meaning |
|---|---|
| `needs_sentence` | an ordinary word; the card should carry a sentence |
| `one_letter_word` | a real word one character long — **the near-miss label**; compared as `needs_sentence` |
| `no_sentence` | the entry stays, but a sentence can only match it inside other words; the card shows its definition prompt alone |
| `retire` | the entry should not be a card at all |

`category` for `no_sentence`: `letter`, `bound_stem`, `abbreviation`; for
`retire`: `proper_name`, `artefact`. A row whose `pos` is `letter` is
`no_sentence`/`letter` by rule (CHECKS §37) — include a few so the judge is
seen to honour it, and include single-character words with another `pos` so
it is seen not to over-apply it.

---

## `calibrated.json` — which (question, course) pairs the nightly judge may read

The plan's phase E gate is "each question clears the three gates on its
gold set before it can write anything but report"
(`docs/plans/quality-guardrails-telemetry.md` §7). This file is how the
loop knows. `backend/services/quality/judge_step.py` reads it once a cycle
through `content_judge.calibrated_pairs()`, and a (question, course) pair
that is not in it is listed in the cycle's stats as `not calibrated` and
never sent to a model, whatever the admin switches say. The switches decide
whether money is spent; this file decides on what.

Shape: question name → course code → the evidence.

```json
{
  "register": {
    "ar": {
      "date": "2026-09-17",
      "gold": "ar_register_gold.tsv",
      "documented": "ar_register_documented.tsv",
      "calibration": "ar_register_calibration_2026-09-17.jsonl",
      "agreement": "56/56 documented, 99.5% provisional vs the reference panel"
    }
  }
}
```

| key | what it is |
|---|---|
| `date` | the day the gates were run |
| `gold` | the reviewer set in this directory the question is graded against |
| `documented` | the machine-written subset whose answers the programme asserts (register only; omit elsewhere) |
| `calibration` | the jsonl of what the judge said on that run, in this directory |
| `agreement` | the gate figures, as the results page reports them |

Adding a pair means: a filled gold set, `content_judge --question <name>
--gold` with all three gates green, the run's jsonl copied here, a
`docs/quality/<name>-<date>.md` recording it, and then the entry. An entry
without those is a judge running uncalibrated, which is the thing the gate
exists to stop — so the evidence fields are not optional decoration.
`register`/`ar` is provisional: 56/56 on the documented subset, and the
614-row gold set is still unlabelled (see above); it is in the file because
the owner's decision was to run it at report level while the reviewers
label. A malformed file reads as empty, with a warning in the server log,
so a bad edit switches the judge off rather than on.

For the same reason the file ships in the API image by name: `.dockerignore`
excludes `data/*`, and an absent file reads as *off*, so without the
negation and the `Dockerfile` `COPY` the deploy would have shown the switch
on and a judge that never read. `backend/tests/test_runtime_data_ships.py`
fails if either drifts. Only the json ships — the gold TSVs and calibration
jsonls beside it are the evidence, read by hand, not by the API.
