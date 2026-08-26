# The six layers of a card — the spec

Owner directive, 25 Aug 2026: check **hint · sentence · translation ·
interlinear gloss · romanisation · definition** — every one, on every course.
`CHECKS.md` §9 holds the measured state; this file holds the standard each
layer has to meet.

**Name the layer.** "Gloss" means three different things in this repo
(`gloss_overrides.tsv` = definitions; a drill's `gloss` = the interlinear line;
`giveaway_by_gloss` = a hint rule). That ambiguity is why "911 gloss fixes"
read as though the word-by-word layer had been repaired when nothing had
touched it.

---

## 1. Interlinear gloss — Leipzig Glossing Rules

The word-by-word line printed UNDER a sentence. **Adopted standard: the
Leipzig Glossing Rules**, because they are positional (so alignment is
checkable) *and* morpheme-aware (so agglutinative languages lose nothing).

**Rule 1 — one cell per word, separated by ` · `.**
A cell may cover a genuine multi-word unit (`Kei te` is one tense marker), so
cells ≤ tokens. Cells > tokens means a cell was invented.

**Rule 2 — inside a cell, two marks that mean different things.**
- `-` a boundary that IS in the word: `tu-ta-on-ana` → `1PL-FUT-see-RECIP`
- `.` several meanings in ONE unsegmented chunk: `mwana` → `CL1.child`

Hyphens in the cell must equal hyphens in the word. This is what makes
morpheme detail verifiable instead of decorative — today `sw`'s is
unverifiable, so a wrong segmentation looks identical to a right one.

**Rule 3 — UPPERCASE is a grammatical category, lowercase is a lexical
meaning.** `CONT`, `NEG`, `1PL`, `CL9` against `live`, `house`, `when`. This
settles the label mess by principle: `mi` currently has `NOT`(3)/`not`(15),
`PERS`(1)/`pers`(3), and three rival names for the present slot
(`PRESENT` 8, `prog` 23, `CONT` 2), across 302 distinct labels.

**Rule 4 — `___` marks the blank, exactly where `{{answer}}` sits.** Exactly
one per line.

**Rule 5 — the renderer stacks tokens above cells.** Today
`ReviewSessionPage.tsx:1077` prints the line as flat text, so a learner must
COUNT to map cells onto words — which is why a shifted Māori line went
unnoticed until the owner read one. Until that changes, positional glosses
carry risk that self-labelling ones do not.

### Migration

| | state | action |
| --- | --- | --- |
| `mi` | 100% of drills, already positional | settle the label casing per Rule 3 |
| `sw` | `u-ta-rudi (2SG-FUT-return)` — self-labelling | convert; **371 of 461 convert mechanically**, 90 need review; 1,094 of 1,938 segmented pairs need Rule 2's `.`/`-` distinction applied |
| every other course | **0%** | author with this spec from the start |

---

## 2. Romanisation — non-Roman scripts

A learner cannot recall a word they cannot sound out, which is why
`hintLayers.ts` puts romanisation FIRST for non-Latin scripts. Eight courses
need it: `ru ar el he fa hi th ko`.

**Standard:** the romanisation a learner will meet elsewhere for that
language, applied consistently within a course, and present on BOTH the drill
and the sentence bank — they are filled independently and diverge.

Measured in production 25 Aug:

| | drills | sentence bank |
| --- | --- | --- |
| `ar` `el` `fa` `he` `ru` | 94–100% | `el` 1%, `ru` 0%, `ar` 0%; `he`/`fa` have no bank |
| `ko` | 0% | 0% |
| `hi` | 0% | 74% |
| `th` | 0% | 0% |

**`th` and `ko` have none anywhere**, and Thai has no spaces between words —
the two hardest scripts to decode cold ship with no help at all. `ru` and `ar`
have romanised drills against 35k and 20k unromanised sentences.

**Schema first, authoring second.** `ru_sentences.tsv` has no
`transliteration` column at all while `ko`'s does. Agree the columns before
filling them or the work lands where half the courses cannot hold it.

---

## 3. Sentences — sourcing, per course

| source | courses | note |
| --- | --- | --- |
| Tatoeba (sentence + English translation) | 22 courses | the existing banks |
| Leipzig Wikipedia (sentence only, NO translation) | `id` 25.7k, `he` 32.9k, `fa` 32.3k, `tl` 16.5k learner-length candidates | encyclopedic and artifact-heavy; needs filtering AND an authored translation |
| **nothing** | **`la`** | no Tatoeba export, no Leipzig corpus |
| authored | `jam` | no corpus exists for Jamaican at all |

**A Leipzig sentence is not a learner sentence.** The 4–12-word filter above
still admits `Aang amat senang melihat Appa kembali` and Persian sentences
opening with `۰٫۱۶۵`. Treat it as a candidate pool, never as a bank.

**Facts yes, sentences regenerated** — the standing source rule. Vocabulary and
paradigms from licensed material may inform; verbatim sentences may not ship.
