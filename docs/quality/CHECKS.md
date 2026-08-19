# Every check, and which languages it applies to

**This file exists because the checks kept being written for one language.**

Each one below was found by looking at a single course — English's beryllium
definition, Portuguese's `a`, Latin's macrons, Māori's gloss — and each turned
out to be a *class* present in others that nobody had looked at. A check that
lives only where it was discovered is not a check; it is an anecdote.

**The rule: a check is not finished until its applicability to all 27 courses
is decided and written in this table.** "Applies everywhere", "applies to these
eight for this reason", and "applies only here, because X" are all acceptable
answers. Silence is not — an undecided language is an unchecked language.

The 27: `ru ar en sw tr yo ha xh es it fr de ca mi ro el pt hi jam nl th ko la
id tl he fa`.

---

## Status legend

| | |
| --- | --- |
| **all** | runs on every course, no per-language configuration |
| **parameterised** | runs everywhere, but needs a per-language value (which mark, which policy) |
| **scoped** | deliberately limited, with the reason stated — the limit is a decision, not an omission |
| **UNDECIDED** | found, not yet generalised. **This is debt.** |

---

## 1. `circular_gloss` — a definition that explains the word with the word

`have` → "have or possess"; `paint` → "make a painting". 80 of English's first
1000 were circular; all rewritten.

**Status: scoped — English only, and the scope is load-bearing.** Everywhere
else the gloss is in a *different language* from the headword, so a headword
inside its own gloss is either a deliberate collocation example (`na` — "and;
with (kuwa na, to have)") or a loanword that honestly glosses to itself
(`hotel`, `internet`). Measured across the other 26: 500+ hits, none a defect.
Content-word POS only — a preposition cannot be glossed without being used.

**The analogous check for the other 26 is different and is NOT yet built:** does
the English gloss actually *gloss*, rather than restate the foreign word in
transliteration? See `wrong_sense_gloss` for the part of this that is covered.

---

## 2. `wrong_sense_gloss` — the gloss describes the wrong thing entirely

A top-1000 word glossed as a letter of the alphabet or an ISO region code —
French `ne` glossed as a Swiss canton.

**Status: all 27**, top-1000 band, first sense only.

---

## 3. Grader collisions — two cards, one gradable answer

Two different vocabulary rows that normalise to the same string under **that
language's own grader**, so the learner is graded on a word the card is not
teaching.

Found in Latin (40 pairs, from a half-macronised file). **It is not a Latin
problem.** Measured 19 Aug 2026 with each language's real NLP class:

| | collisions | grader |
| --- | --- | --- |
| `fr` | 511 | AccentFoldingNLP |
| `ro` | 502 | AccentFoldingNLP |
| `es` | 270 | AccentFoldingNLP |
| `ar` | 199 | ArabicNLP |
| `de` | 152 | AccentFoldingNLP |
| `pt` | 137 | AccentFoldingNLP |
| `ca` | 126 | AccentFoldingNLP |
| `el` | 117 | AccentFoldingNLP |
| `it` | 60 | AccentFoldingNLP |
| `la` | 40 | fixed — macronised |
| `nl` | 8 | AccentFoldingNLP |
| the other 16 | 0 | |
| **total** | **2,122** | |

Spanish `el`/`él`, `se`/`sé`, `te`/`té`, `que`/`qué`; French `a`/`à`,
`la`/`là`, `ne`/`né`; Romanian `sa`/`să`, `in`/`în`. Typing either against the
other returns **`CORRECT_SLOPPY`** — full credit plus "Almost — check the
accents" — so a learner shown `él` (he) who types `el` (the) is told they were
nearly right, and the SRS schedules the card as known.

**Status: all 27 for the measurement; parameterised for the fix.** The check
runs everywhere including the sixteen at zero, so a new course cannot introduce
the class silently. The *fix* differs and must be decided per language:

- **Latin** — marks are all-or-nothing policy, so the data was normalised.
- **Spanish** — the mark is the *tilde diacrítica*, whose only job is to
  separate homographs. Folding it destroys exactly the information it carries.
  A data fix is wrong here; both spellings are real, distinct words.
- Each remaining language needs its own answer, because German umlaut, Greek
  tonos, Arabic tashkeel and French accent do not behave alike.

---

## 4. Orthography policy compliance — across every file the policy covers

`la.md` declared "no macrons, anywhere, all-or-nothing" **verified**, having
checked only `data/grammar/la_grammar.json`. Nobody re-checked
`data/la_frequency.tsv`, which had gone 48% non-compliant and seeded 40
duplicate cards.

**Status: parameterised — every course with an orthography policy, over every
file it covers** (`<code>_frequency.tsv`, `grammar/<code>_grammar.json`,
`gym/<code>.json`, both sentence banks).

Known policies and their state:

| | policy | state |
| --- | --- | --- |
| `la` | macrons everywhere, all-or-nothing | **compliant**, 5 guards |
| `mi` | macrons are the 16th letter, non-negotiable | **0 of 791 headwords** carry one |
| `yo` | tone is phonemic, Standard Yoruba fully marked | **1,638 of 1,644** carry none |
| `ar` `he` `fa` | vocalisation marks | not yet stated as a testable policy |
| others | — | **UNDECIDED — needs a policy statement before it can be checked** |

---

## 5. Definition ↔ example sense agreement

Does a card's example set demonstrate the sense its gloss *leads with*?

Portuguese rank 2 `a` is glossed "**the (feminine singular)**; to, at — also
estar a + verb; her, it" and all three of its sentences are `está a fazer` —
the third sense. The gloss was repaired and the examples were never rechecked
against it.

**Status: all 27 — and NOT YET BUILT.** `audit_polysemy` compares the gloss to
the dictionary; `audit_examples` counts and varies sentences; neither joins the
two. It becomes mechanical once sentences carry glosses (a gloss states the
word's role), which is why it is sequenced with the gloss work. Until then the
maker–checker performs it by hand, on every language, not only the ones with a
reported example.

---

## 6. Interlinear gloss coverage

**Status: scoped — the 9 courses wired for the layer** in
`frontend/src/features/review/hintLayers.ts`: `mi sw yo xh ha` open on it,
`ru ar el hi` reach it after romanization. The other 18 have no gloss step and
need none.

374 of 8,049 drills carry one (4.6%) — `mi` 240, `sw` 134, everyone else zero.
`yo`, `xh`, `ha` are GLOSS_FIRST **with zero glosses**, so their ladder opens on
an empty layer and drops to English.

Not every sentence gets one, by design: 4,974 rows in the GLOSS_FIRST courses
are the target, out of 484,754 total.

---

## 7. Frozen counts in the guidelines

Never assert a number the audit already computes. 118 defects found across the
27 files — 45 outright false.

**Status: all 27.** Rules in `README.md`.

---

## 8. The homonym lexicon gap — the other word is not merely under-glossed, it is ABSENT

The frequency pipeline builds **one row per surface form**. When two words share
a spelling — or shared one because the source text carried no marks — only the
corpus-dominant word got a row. The other is not a missing sense on a card; it
is **a missing word in the lexicon**.

Measured in Latin (19 Aug 2026), immediately after macronisation made the gap
visible: `hic` "this" present, `hīc` "here" **absent** — while `ibi` "there"
and `ubi` "where" both have rows, so the slot plainly exists; `lātus` "wide"
present, `latus` "side" absent; `populus` "people" present, `pōpulus` absent
(fine — poplar is not first-year); `malum`/`mālum` both absent.

**Where it concentrates: exactly the courses whose marks were stripped or never
present.** In accent-keeping courses the corpus distinguishes the pair, so both
usually have rows (`es` has `el` AND `él`, `fr` has `a` AND `à`). But `yo` is
1,638 toneless rows in a language where tone separates whole lexemes — so each
skeleton row potentially stands for SEVERAL words, and the lexicon is missing
every non-dominant member. Same for `mi` before its macron repair.

**The rule this adds to every orthography repair (Phase 2a): re-marking is not
decoration.** When a row gains its marks, the pass must decide *which word the
rank belonged to* and whether the other members of the collapsed set merit rows
of their own. A re-marking pass that just decorates the existing row with one
mark pattern silently keeps the gap.

**Status: all 27.** Concretely: after any orthography repair, sweep for
high-frequency homonym members with no row (the Latin sweep is the model);
in unmarked-script courses (`th`, no spaces; `ar`/`he`/`fa`, unvocalised) the
same gap hides behind spelling rather than diacritics and needs the
dictionary's homograph entries checked against the file.

## Adding a check

1. Measure it on the language that surfaced it.
2. **Run the same measurement on the other 26 before writing any fix.**
3. Decide the status: all / parameterised / scoped — and if scoped, state why,
   with the measurement that justifies the limit.
4. Add a row here. A check absent from this file does not exist.
