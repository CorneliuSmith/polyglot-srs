# Xhosa (xh) — Content Quality Standards

## Language profile

Latin script, left-to-right, plain ASCII — no diacritics at all. The three **click** consonants are written
with ordinary letters: `c` (dental), `q` (post-alveolar) and `x` (lateral), with the nasal and voiced series
built from them (`nc ngc`, `nq ngq`, `nx ngx`). `XhosaNLP.normalize` is lowercase-and-strip precisely because
nothing else is needed. **The authoritative variety is Standard isiXhosa**, the written standard of South
African education and media, in the current orthography — the variety `IsiXhosa.click`, cited in the points'
`references`, documents. **Out of scope:** the Mpondo, Thembu and Bhaca varieties; Zulu and Ndebele, however
close; and the deep hlonipha lexicon beyond the single C2 point that introduces it.

**No gender; fifteen noun classes**, and they are the language. The course teaches 1/2 (um-/aba-), 1a (u-/oo-),
3/4, 5/6 (i-/ama-), 7/8 (isi-/izi-), 9/10 (in-/izin- ~ iin-), 11, 14, 15 and the locatives. Class is not a
label on the noun — it is a concord that reappears on the verb, the adjective, the possessive, the
demonstrative, the relative and the numeral.

Three features dominate drill quality:

1. **Concord agreement is the whole syllabus.** Almost every answer in the file is a concord-bearing form
   (`entle`, `ezinkulu`, `lakhe`, `ziyabaleka`), so a hint that names the class and the slot teaches, while a
   hint that spells the concord answers.
2. **Clicks are ordinary graded letters.** `cwaka`, `qatha`, `nqa`, `Uxolo`, `iqanda`, `isiXhosa` are graded
   exactly, character for character; there is no leniency layer that folds `c`/`q`/`x` together. Clicks can be
   drilled honestly — and mistyping one is a real error, not a typography slip.
3. **Prefix allomorphy across class 9/10** (`izin-`, `iin-`, `iim-`, `izim-`) is the one place where the
   learner must compute a shape, and it is where the file's hint conventions currently disagree with themselves.

**The word list was Bible-derived, and a Leipzig corpus now supplements it (24 Aug 2026).**
`data/xh_frequency.tsv` was built from `data/raw/xh_bible.xml`, the only Xhosa corpus the
repo had. That is why rank 2 is `uThixo` "God" and rank 3 `unyana` is glossed "the Son of
God in Christian texts", while `okanye` "or", `kwaye` "and", `kodwa` "but" and `kufuneka`
"must" had **no cards at all**.

`xho_community_2017` (Leipzig Corpora, CC-BY, 23,993 sentences) is now registered in
`source_data.py` as `xh_leipzig`. The register difference is the whole point:

| | top words |
| --- | --- |
| bible | `na, uThixo, unyana, phakathi, abantu, yena, phezu, mna` |
| Leipzig | `ukuba, ke, okanye, kunye, kwaye, xa, kuba, na, le, abantu` |

**837 of Leipzig's top 1,000 were absent from the course.** 62 have been added — the
conjunctions and discourse particles first, each glossed from the course's own translated
drills where they exist and from Leipzig sentences otherwise.

**A corpus cannot supply the teaching core, and this is worth stating plainly.** In
Leipzig, `molo` "hello" ranks **#58,883** and `enkosi` "thank you" **#42,478**, because
greetings are spoken far more than they are written. No web corpus will ever rank them.
A course therefore needs an authored courtesy core *on top of* a good frequency list;
neither substitutes for the other. That core is now added — 17 rows: the greetings
`molo`/`molweni` (distinguished by how many people you are addressing), `enkosi`,
`kunjani`/`unjani`, `ndicela`, the question words `ngubani`/`nini`/`yintoni`, `utata`,
`umama`, and the verb stems `funda`, `nceda`, `dlala`, `va` that the file lacked.

**Ten carry a Wiktionary gloss; seven are authored and have NOT been through a checker** —
`enkosi`, `kunjani`, `unjani`, `ndicela`, `ngubani`, `nini`, `yintoni`. They are among the
best-documented words in the language, but the verification that every other batch got did
not happen here (the checking pass failed repeatedly on an environment fault), and that is
recorded rather than implied away. A reviewer should read those seven first.

**Surface forms are not headwords.** 169 of the 247 candidates were skipped for this, and
the reasoning is the one this page should enforce: `zabo`, `yakhe`, `wakhe` are possessive
concord cells; `kule`, `kulo`, `kweli` are locative-plus-demonstrative contractions;
`ziya`, `iya`, `baya`, `uya` are subject concord plus tense marker. **Teach the concord
table, not its 15 × 6 output.** Only forms that have lexicalised — `ukuba`, `ukuze`,
`kufuneka` — earn a card.

Three more were rejected for a defect this page should also carry: `ukufunda` and
`ukuqinisekisa` were carded as verbs with the `uku-` infinitive prefix, but **all 279 verbs
in this file are bare stems** (`hamba`, `thetha`, `khangela`) and every one of the 14
`uku-` headwords is tagged `noun`. A deck that grades exact-match cannot leave the learner
guessing which shape to type. Two real gaps surfaced in the process: **`funda` "read,
learn" is absent entirely**, and so is the singular lemma `isikolo` "school".

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already
sitting in the drill's own translation; never the `answer — explanation` template; one hint resolves to exactly
one answer inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and
quoting an isiXhosa base form is fine while whole isiXhosa sentences are not.

1. **"Class number + slot" is the house convention — keep it.** GOOD, all from the file: `class-9 possessive +
   'my'` → `yam`; `class 5 la- + him` → `lakhe`; `beautiful + class-9 concord` → `entle` (the learner must know
   `in-` + `-hle` surfaces as `entle`); `class 1a takes oo- in the plural` → `ootitshala`. The class is named,
   the concord is not spelled.
2. **Pick one name per alternation and use it across the whole point.** The class 9/10 plural point uses four
   conventions in six drills — BAD: `izin- plural` → `izinja`, `long ii- plural` → `iincwadi`, `imoto → iin-
   plural` → `iimoto` (the answer has no `n` in it — the hint names the underlying prefix and the learner is
   left to guess the surface one), `indlu → izin- plural` → `izindlu`. GOOD, one convention: `inja → class 10
   plural`, `incwadi → class 10 plural`, `imoto → class 10 plural`, `indlu → class 10 plural`, with the
   `izin- / iin- / iim-` rule stated once in the explanation.
3. **A pattern hint shared by two proper-noun answers is legitimate when the translation names the person or
   place.** `ngu- + name` → `NguThemba` (*This is Themba.*) and `NguSipho` (*That is Sipho.*); `e- + place
   name` → `eKapa` (*I live in Cape Town.*) and `eGoli` (*Mum lives in Johannesburg.*). The hint teaches the
   prefix, the translation supplies the noun, and each drill still resolves uniquely. A checker must exempt
   this class — pattern-plus-proper-noun — or it flags good pedagogy. The exemption does **not** cover two
   different constructions sharing a hint.
4. **A one-word English gloss is not a hint.** BAD, all real: `when` → `nini` under *When do you arrive?*;
   `where` → `phi`; `if` → `Ukuba` under *If you want to succeed, study.*; `that` → `ukuba` under *I am glad
   that you have arrived.* GOOD: `question word for a time`; `question enclitic for a place`; `conditional
   opener, clause-initial`; `complementiser after a verb of emotion`.
5. **Never print the answer in the translation.** BAD, in the file: hint `the ritual salute/acknowledgement` →
   `Camagu`, translation *When giving ritual thanks in a homestead, we say 'Camagu!'* GOOD: *…we give the
   ritual acknowledgement.*

## Question / drill standards

A good Xhosa drill is a natural Standard isiXhosa sentence, one blank, and a translation of the completed
sentence. The counting frames are the model: `Inja enye, {{answer}} ezimbini.` — the numeral `ezimbini` carries
class-10 agreement, so the frame fixes the class before the hint says anything.

- **Grammar cards grade concords strictly, and that is what makes them teachable.**
  `XhosaNLP.get_morphological_family` generates the singular/plural partner (`umntu`↔`abantu`,
  `isitya`↔`izitya`, `inja`↔`izinja`), but with `card_type == "grammar"` a family match returns `WRONG_FORM`
  (FSRS *Again*). A plural typed for a singular fails on a grammar drill and is amber on a vocabulary card,
  which is the right split. Note the pair table has no `iin-` entry, so long-`ii` plurals get no partner —
  do not assume symmetry when writing a test.
- **`isiXhosa` and `isixhosa` are one answer.** Normalisation lowercases, so the internal capital in language
  names is a display convention, not a second answer — and never a reason for a second drill.
- **A point whose six drills all have the same answer is not a grammar drill.** *Conditions with ukuba* asks
  for `ukuba` six times with the hints `'if' opener`, `'that' complementizer`, `if`, `whether/that`, `if`,
  `that`. It teaches one word's four functions but tests nothing but its spelling; split it, or contrast
  `ukuba` with `xa` (when-clauses) so the blank has something to choose between.
- **The translation must translate the whole sentence.** `Andazi ukuba uza kufika nini.` is rendered *I don't
  know when he is going to arrive.* while the hint says `whether/that` — the English "when" is `nini`, not the
  blank, and a learner reading top-down will fill in the wrong idea.
- **One blank, one token**, and let a concord elsewhere in the frame disambiguate wherever possible.

## Translation & definition standards

- **Every noun definition carries its class pair and its plural**: `incwadi (9/10, pl. iincwadi) book`;
  `umntwana (1/2, pl. abantwana) child`. Without the class number the learner cannot form a single agreeing
  word, which is most of the course.
- **No bare one-word gloss for a polysemous word.** `ukuba` is *if*, *that* and *whether* and must never be
  glossed as one; `xa` is *when/while* and not *if*; `nje` and `ke` are discourse particles with no clean
  English equivalent and need a function, not a word.
- **Ideophones need their event, not a translation.** `cwaka` (dead silence), `qatha` (a sudden popping-up),
  `nqa` (astonishment) are defined by what they depict; the file's hints already do this correctly.
- **Register consistency:** neutral Standard isiXhosa. The hlonipha register and `Camagu` are C2 material and
  their politeness should not leak into A1 sentences.

## Current measured state

Measured directly from `data/grammar/xh_grammar.json`, `data/xh_morphology.json` and `data/`:

- **40 grammar points, 249 drills**, A1–C2; **16 of 40 points are `reviewed: false`**.
- **Hint leaks: 0. Empty hints / translations / explanations: 0. Vague translations: 0.** Confirms the crawl.
- **One-word hints: 7.** The crawl says 5; the file says 7 (`when`, `where`, `who(m)`, `if` ×2, `that`,
  `whether/that`) — trust the file. **5 of them also appear verbatim in the drill's own translation.**
- **Duplicate hints: 2, and both are the legitimate pattern-plus-proper-noun class** — `ngu- + name` →
  `NguThemba`/`NguSipho` and `e- + place name` → `eKapa`/`eGoli`. Real violations: **0**. The crawl reads them
  the same way.
- **Answer printed in its own translation: 1** — `Camagu`, in *Hlonipha — the respect register* (a
  `reviewed: false` point).
- **Inconsistent allomorph naming: 4 hints in one point** (*Noun classes 9/10*), including one, `imoto → iin-
  plural` → `iimoto`, whose named prefix does not appear in its own answer.
- **`data/xh_morphology.json` is the weakest data file in this group.** 595 entries, **every one carrying a
  single `Plural` chip and nothing else — there is no class information anywhere**, in the language whose
  grammar *is* noun class. Worse: **336 of the 595 (56%) carry tone and length diacritics that isiXhosa
  orthography does not use** — the gym would show the plural of `ibala` as `ámábâla`, of `ibandla` as
  `ámábândla`, of `ibhokhwe` as `íibhókhwe`. And **44 entries are not nouns at all** (37 tagged `conj`,
  7 `adj`) yet still carry a "Plural": `hle → esibahle`, `banzi → esibanzi`, `bomvu → esibomvu` — these are
  malformed class-7 concord forms, not plurals of anything.
- **`data/xh_sentences.tsv` has 37 rows — the smallest sentence bank in the repository** (plus 81 curated),
  against 1,155 words in `data/xh_frequency.tsv`. There is no `data/gym/xh.json` manifest.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language xh
.venv/bin/pytest backend/tests/test_nlp_hausa_xhosa.py -q
.venv/bin/pytest backend/tests/test_seeder_hausa_xhosa.py -q
```

Xhosa is not in `TRANSLIT_LANGS` (`ru ar el he fa hi th ko`), so the transliteration suite does not apply —
every letter is on an ordinary keyboard. `test_nlp_hausa_xhosa.py` covers the concord stripper and the
class-pair family; the assertion worth adding is that a class partner (`abantu` for `umntu`) grades
`WRONG_FORM` when `card_type` is `grammar`, so the number contrast stays testable.

A human reviewer pulls 10 random drills and asks:

1. **Does the hint name the class number, or spell the concord?** Naming passes; spelling fails.
2. **Do all the drills in this point use the same name for the same alternation?** The class 9/10 point fails.
3. **Could I answer this from the English translation alone?** 5 drills fail today.
4. **Is the answer printed in the sentence or the translation?** `Camagu` fails.
5. **Does the frame carry a concord (numeral, adjective, verb) that fixes the class independently?**
6. **If two drills share a hint, does each translation still name its own answer?** `ngu- + name` passes;
   anything else sharing a hint should be rewritten.
7. **Are the clicks spelled correctly — `c`, `q`, `x` and their `nc/nq/nx/ngc/ngq/ngx` series — everywhere,
   including in hints and explanations?**
