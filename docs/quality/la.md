# Latin (la) — Content Quality Standards

## Language profile

Latin script, left-to-right. Modern editorial conventions: `u`/`v` are distinguished (`venerunt`,
`vidi` — 42 word types use `v`), `i`/`j` are **not** (no `j` anywhere in the corpus), `ae` is a
digraph, never `æ`.

**The authoritative variety is Classical Latin of the late Republic and Augustan age** — the
Latin of Cicero, Vergil, Horace and Catullus, all four quoted directly in the C1/C2 points, with
Allen & Greenough (Dickinson College Commentaries) as the grammar of record. **Explicitly out of
scope:** Ecclesiastical / Church Latin in both pronunciation and spelling (`caelum` never
`celum`, `mihi` never `michi`), Medieval and Neo-Latin, Vulgar Latin reconstructions, and
macronised pedagogical spelling (below). Colloquial register **is** in scope, but only where the
C2 register point marks it as such — `Quid agis?`, `si vales, bene est, ego valeo` are taught
beside the Ciceronian period, labelled.

**Macron policy: macrons everywhere, all-or-nothing** (reversed 19 Aug 2026 — see below).
Every Latin surface carries them: `data/la_frequency.tsv` (557 rows), `data/grammar/la_grammar.json`
(41 points, 189 drills) and `data/gym/la.json`. Vowel length is phonemic, it is what distinguishes
`liber` from `līber` and the nominative `puella` from the ablative `puellā`, and this course has no
other way to show it.

The learner is never required to type them. `LatinNLP` in `backend/services/nlp/latin_base.py` is
`AccentFoldingNLP`, so `puella` against a `puellā` card returns **`CORRECT_SLOPPY`** — full credit
plus "Almost — check the accents." That is the behaviour we want: read the length, type what you
like, get nudged.

> **This page argued the opposite until 19 Aug, and the argument was faulty.** It read: "macrons
> are usually omitted in a learner's typed answer — a half-macronised file grades identically to an
> unmacronised one", and concluded that the content should carry none. That is an argument about
> **input** applied to **display**. Tolerant grading already existed and already solved the input
> problem; it never required stripping the marks a learner reads. The second argument — that
> classical editions print unmacronised text — is true of editions and irrelevant to a teaching
> text, which is what this is. Wheelock and Lingua Latina both print macrons.
>
> The policy was also simply not being followed: the frequency file sat at 285 macronised rows
> against 310 plain, seeding 40 duplicate cards that `AccentFoldingNLP` graded identically. The
> dedup was real work and survives; only the direction changed.

**What the macrons buy, stated plainly.** Length is the only thing separating these pairs, so
without the marks each collapses into one spelling and a single gloss has to carry both senses.
With them, each is its own card:

| | | |
| --- | --- | --- |
| `liber` (librī, m. 2nd) | book | rank 180 |
| `līber` (lībera, līberum) | free — an ADJECTIVE, not a noun | rank 213 |
| `os` (ossis, n.) | bone | rank 254 |
| `ōs` (ōris, n.) | mouth, face | rank 246 |

The same holds where only one member is in the file but a learner meets both: `hic` "this" vs
`hīc` "here" (the highest-traffic pair); `venit` "comes" vs `vēnit` "came"; `malum` "evil" vs
`mālum` "apple"; `latus` "side" vs `lātus` "wide"; `populus` "people" vs `pōpulus` "poplar";
`levis` "light" vs `lēvis` "smooth". And the endings that carry the grammar: 1st-declension
nominative `puella` against ablative `puellā`, and the `-is` syncretism below — genitive
singular short, dative/ablative plural `-īs` long.

**Still name the case in the hint.** The macron shows length; it does not tell a learner which
case is wanted when several share a form. Naming the tense matters for the same reason: a hint
reading "plain indicative" does not separate `venit` from `vēnit`, so write "present indicative".

**Three genders (m/f/n), grammatical and unpredictable** for the third declension; `corpus`,
`tempus`, `nomen` are neuter and nothing in the meaning says so. What dominates drill quality:

1. **Six cases across five declensions**, and **syncretism everywhere**: neuter nominative =
   accusative; `-is` is genitive singular *and* dative/ablative plural; and without macrons the
   1st-declension nominative singular `aqua` is spelled exactly like the ablative `aquā`.
2. **Free word order.** Position carries no grammatical information, so a drill cannot rely on
   the slot to disambiguate — the ending and the hint carry all of it.
3. **Thin footprint.** 189 drills, 557 vocabulary rows, **no sentence bank at all** — every
   sentence the learner sees comes from the grammar file. Not in `TRANSLIT_LANGS`.

## Hint standards

Universal rules, once: a hint **narrows** the answer without containing it. Never the answer as a
whole word. Never a gloss already sitting in the drill's own translation. Never the
`answer — explanation` template. One hint resolves to exactly one answer inside its point
(allomorph sets excepted where the sentence disambiguates). Hints are English; quoting a citation
form (`sum`, `agere`, `tu`) is fine, a whole Latin sentence is not.

**The house template here is `English gloss — grammatical cell`, and it is safe.** `loves — 3rd
person singular`, `is — 3rd person singular of sum`, `king — accusative -em`. Note what it is
*not*: the destructive pattern in other courses is `answer — explanation`, where the **Latin**
form opens the hint. Here the **English** gloss opens it and the Latin never appears. Do not
"fix" these into something else; do not let a rewrite flip the order.

| GOOD (real, in the file) | answer | Why it works |
| --- | --- | --- |
| `captured — ablative participle agreeing with the city` | `capta` | gloss + case + agreement |
| `time — neuter; the object looks like the subject form` | `tempus` | names the syncretism outright |
| `our patience — ablative, because uti-compounds govern the ablative` | `patientia` | states the governing rule |
| `city — ablative after in (location)` | `urbe` | separates in+abl from in+acc |
| `of the beech tree — genitive singular` | `fagi` | gloss + exact cell |

**Name the case whenever a length-only contrast is doing the work.** This is the macron policy's
bill. BAD in principle: `the water` for `Aqua` in `{{answer}} portata, puer venit.` — unmacronised,
`Aqua` is spelled exactly like the nominative and nothing outside the hint says ablative. The
file already gets this right — `the water — the ablative noun of the absolute phrase` — and that
is the rule: **1st-declension `-a`/`-ā`, 5th-declension `dies`/`diē`, 3rd-conjugation `-eris`
forms and any other quantity-only pair must have the case or the cell spelled out.**

**Never let the English gloss alone be the whole hint** when it also appears in the translation.
Zero drills do this today; the risk lives in verb points, where `loves` under "The girl loves
the boy" would be a giveaway if the grammatical cell were dropped. Keep both halves.

## Question / drill standards

- Genuine classical sentences where the point allows it, and plausible schoolroom Latin
  otherwise: `Urbe capta, milites venerunt.`, `Rege dicente, populus tacet.`, `O tempora, o
  mores!`. The poetry point uses real lines (Vergil, Horace, Catullus); those must be quoted
  correctly or not at all.
- **Exactly one blank, always a whole word.** 189/189 today; no in-word blanks, no multi-word
  answers, and the answer is never printed elsewhere in its own sentence. This is the cleanest
  drill set in the repo and it is the baseline to hold.
- **Word order must not be the only clue.** `Puella puerum videt.` works because `puerum` is
  unambiguously accusative; a drill blanking a 1st-declension noun in a position that "looks
  like" a subject is testing English word order, not Latin.
- Capitalisation follows the sentence (`Aqua`, `Carpe`); grading lowercases, so this is
  presentation, not a trap. Translations translate: `Bello confecto, laeti eramus.` → "With the
  war finished, we were happy." An ablative absolute may be rendered with "with", "after" or
  "when" — pick one and let the point's explanation carry the others.

## Translation & definition standards

- No bare one-word gloss for a polysemous word. `data/la_frequency.tsv` handles function words
  well (`in | in; into; on`, `ad | to; toward; at`) but 309 of 557 rows carry no
  sense split at all. Anything with a second everyday sense must gain one: `dominus` is "master;
  owner; lord", `res` is "thing; matter; affair", `virtus` is "courage; excellence; virtue".
- **Gender must be marked on every noun, and today none of them are.** All 38 noun rows in
  `data/la_frequency.tsv` are bare (`puella | girl`, `bellum | war`, `pater | father`). Latin
  gender determines adjective agreement, which is drilled from A1 (*Adjective-noun agreement*),
  and it is unguessable for 3rd-declension nouns. The required form is genitive + gender, the
  standard dictionary citation: `puella, -ae f.`, `bellum, -i n.`, `pater, patris m.` Verbs
  should likewise carry their principal parts (`amo, amare, amavi, amatus`), because the perfect
  and the perfect passive participle are both drilled and neither is derivable.
- Register consistency: colloquial formulas (`Quid agis?`, `salutem dicit`) and poetic forms must
  be labelled, so a learner does not drop a Catullan turn into a prose exercise.

## Current measured state

Counted directly from `data/grammar/la_grammar.json`: **41 points, 189 drills**, every point
`source: "ai"` and `reviewed: false` — nothing has had a human pass. Levels A1 10 / A2 10 /
B1 8 / B2 7 / C1 3 / C2 3. Footprint: `data/la_frequency.tsv` **557 rows** (19 Aug 2026), **no
`data/sentences/la_sentences.tsv` and no `data/la_sentences.tsv` anywhere**, no
`data/la_morphology.json`, gym baseline present at `data/gym/la.json`.

| Rule | Count |
| --- | --- |
| `leak_hard`, `self_answering`, `giveaway_by_gloss`, `duplicate_hint`, `empty` | **0** |
| `vague_translation`, one-word hints, in-word blanks, answer-in-sentence | **0** |
| noun rows in `data/la_frequency.tsv` marking gender | **0 of 199** |
| points with 3 drills instead of 5, and with no `references` | **8 of 41** |

**This is the cleanest drill set in the repo** — the crawl says so and the file confirms it, on
every rule. The debt here is not hint quality; it is **volume and sourcing**, and the honest
entries are:

1. **No sentence bank.** Every other course has a `_sentences.tsv`; Latin has none, so reading
   practice has nothing to draw on outside the 189 drill sentences.
2. **557 vocabulary rows, zero gender marking.** The A1 agreement point drills `magna`/`magnus`
   against `puella`/`dominus`, and the vocabulary the learner meets alongside it does not say
   which nouns are which. This is the one fail-level content gap in Latin.
3. **The whole A1 band is thin and unsourced.** The same 8 points have both 3 drills instead of
   5 and no `references` array: *Nominative and accusative*, *First declension*, *Second
   declension*, *sum/esse*, *First conjugation*, *Adjective-noun agreement*, *Prepositions:
   in + acc vs abl*, *Word order*. Every point from B1 up carries Allen & Greenough or Wikipedia.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language la
.venv/bin/pytest backend/tests/test_nlp_latin.py -q -k Latin
.venv/bin/pytest backend/tests/test_content_quality.py -q
```

`backend/tests/test_nlp_latin.py` covers the whole accent-folding family, not Latin alone; the
Latin-specific class is `TestLatin`, and `TestFoldDiacritics::test_strips_macrons` is what makes
a macron-typing learner pass. Not in `TRANSLIT_LANGS`, so no translit suite.

A human reviewer pulls 10 random drills and rejects any that: turn on a length-only contrast
(`-a`/`-ā`, `dies`/`diē`) without naming the case in the hint; introduce a macron and so break
the all-or-nothing policy; flip the hint template so a Latin form opens it; leave a verb hint at
a bare English gloss with no person/number/tense cell; rely on word order to disambiguate a case;
misquote a classical line; or use an Ecclesiastical spelling. Then check five noun definitions
carry genitive + gender — today all five fail, and that is the top of the burn-down list.
