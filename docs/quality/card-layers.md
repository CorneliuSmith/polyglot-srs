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

`el` and `hi` in that table now read differently: both are computed at request
time, so the stored percentage understates what a learner sees.

**`th` and `ko` have none anywhere**, and Thai has no spaces between words —
the two hardest scripts to decode cold ship with no help at all. `ru` and `ar`
have romanised drills against 35k and 20k unromanised sentences.

**Schema first, authoring second.** `ru_sentences.tsv` has no
`transliteration` column at all while `ko`'s does. Agree the columns before
filling them or the work lands where half the courses cannot hold it.

### Computed vs authored — the layer does not have to be written by hand

Four of the eight have a deterministic romanizer, so their reading costs no
authoring and no storage: `hi` (Hunterian), `ru` (cyrtranslit) and, since
26 Aug, `el` (ELOT 743, `greek_reading.py`) and `ko` (Revised Romanization,
`korean_reading.py`). That leaves `he`, `fa` and `th` needing authoring, and
`ar` deliberately excluded even from that — unvocalized script drops the
short vowels a romanization would need, so a computed Arabic reading would
invent sounds.

**Transcription, not transliteration — this is the whole difficulty.** Both
new romanizers write how a word SOUNDS, not how it is spelled, because in both
languages the spelling lies. Greek «αυτό» is *afto*, not *auto*. Korean 신라 is
spelled sin-la and said *Silla*. A letter table alone gets both wrong in the
way a learner cannot detect: they have no way to know the spelling is not the
pronunciation. That is also why `ko`'s scope stops where it does — RR's
optional hyphenation, the sai-siot, and compound boundaries that block
assimilation need morphology or a lexicon, and still want a native reviewer.

**Both were verified the same way, and both needed it.** Two lenses (standard
conformance, and "would a learner reading this aloud be understood") over 60
high-risk corpus sentences, every claimed defect then put to independent
refuters, then a second round on 60 fresh sentences to confirm the fix and
look for more. Each language returned exactly one systematic defect in round
one and zero in round two:

| | found | why it survived my own testing |
| --- | --- | --- |
| `el` | `γκ` missing from the digraph table | right word-initially by accident (γκρίζος *gkrizos*), wrong everywhere else (έγκυος *egkyos* for *engyos*) |
| `ko` | `ㄹ`+`ㄹ` → `ll` missing | I had both rules that assimilate INTO that geminate (ㄴ+ㄹ, ㄹ+ㄴ) but not the geminate itself, so it emitted `lr` — a string RR can never produce |

Both are the same shape: a table with the neighbours of a rule filled in and
the rule itself absent, passing every example I happened to pick. Hand-chosen
smoke tests cannot find that; a sample drawn from the corpus and biased toward
the risky construct can.

Two lessons already paid for here:

1. **A romanizer is not a layer until something calls it.** `sentence_reading`
   covered `hi` and `ru` from the day it was written and had exactly one
   caller — the grammar page. The review card read only the stored column, so
   a learner met the same Russian sentence with a reading under the grammar
   point and as bare Cyrillic on the card, where they actually have to recall
   it. Fixed 26 Aug; the fallback lives in `_vocab_card`.
2. **Compute the reading from the CLOZE, never the raw sentence.** Romanising
   the raw text prints the hidden word in Latin letters directly above its own
   blank. That is the answer leak of CHECKS.md §11 regenerated per card, where
   no file guard can ever see it.

**Authored beats computed, always.** `he` and `fa` have hand-written rows and
`ko` has two hand-fixed time expressions; a fallback that overrode them would
discard the only reviewed romanisation in the corpus.

Measured in the committed banks, 26 Aug — and now a ratchet
(`test_the_gap_is_the_gap_we_think_it_is`) rather than a line in a document
that quietly goes stale:

| bank | rows | with romanisation |
| --- | --- | --- |
| `he` | 7,483 | 194 |
| `fa` | 4,003 | 199 |
| `ru` `ar` `el` `hi` `th` `ko` | 70,928 | **no column at all** |

`ru`, `hi` and `el` are covered live by the computed reading regardless, so
the real authoring gap is `he`, `fa`, `th` and `ko`.

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
