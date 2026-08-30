# The layers of a card — the spec

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
| `mi` | **240/240, normalised 26 Aug** | done. Distinct labels 301 → 270, case collisions 2 → 0, and every lowercase grammatical category uppercased. The 24 multi-word cells now split, so `mi` is on the strict contract too |
| `yo` `xh` `ha` | **761/761, authored 26 Aug** | done — see below |
| `sw` | **442/442, converted to positional 26 Aug** | done. The earlier "keep the self-labelling form" call was WRONG: the gloss renders as flat text, where `u-ta-rudi (2SG-FUT-return) ___ kutoka (from)` reads worse than `2SG.FUT.return · ___ · from`, and `xh` had already proved the positional form works for a Bantu language with the same noun-class machinery. 107 of 131 converted mechanically; 24 multi-word cells and 311 blanks were authored |
| every other course | **0%** | author with this spec |

### What normalising Māori settled — disambiguate, do not flatten

`mi`'s glosses were analytically sound and written many different ways. One
pronoun, `mātou`, appeared as "we-excl", "we(excl)", "we", "us" and
"we(excl.)"; `ia` as "he/she", "she", "her", "he", "him", though Māori `ia` is
gender-neutral. Every grammatical category was lowercase against Rule 3.

The instructive part is the particles. `i` carried five labels — "at" 28,
"past" 23, "obj" 12, `PAST/OBJ` 10, `T/A` 3 — and the obvious fix, collapsing
to a majority label the way Hausa's aspect labels were collapsed, would have
been WRONG. Māori `i` genuinely marks past tense before a verb, the object
before a noun, and location. So the pass was told to decide per sentence, and
it did: OBJ 36, PST 28, at 18, and a handful of PROG/by/from. The `PAST/OBJ`
hedge is gone — a hedge is not a gloss.

The same for `e` (by 14, PROG 9, FUT 8, VOC 5, IMP 3) and `a` (PERS 15, plus
one genuine possessive "of"). And `ia` came out `3SG` 33 times plus one
"every", which is correct — Māori `ia` is also the distributive "each".

**The test for whether to unify a label is whether the language makes one
distinction or several**, not how many spellings there are. Hausa's `ya`
carrying COMPL and PFV was one morpheme with two names. Māori's `i` carrying
OBJ and PST is one form with two functions. The first is a defect; the second
is the language.

Result: 301 distinct labels → 270, two case collisions → zero, and the 24
multi-word cells split so `mi` meets the strict one-cell-per-token contract.

### Where the remaining gloss work is — and where it is NOT

The gloss is only shown to courses whose `LAYER_ORDER` includes it
(`frontend/src/features/review/hintLayers.ts`). `DEFAULT_ORDER` is
`['translation', 'hint']` — **no gloss slot at all**. So of the 6,610 drills
still unglossed:

| | drills | is the layer reachable? |
| --- | --- | --- |
| `ko` `ru` `el` `ar` `hi` `th` `he` `fa` | **3,001** | yes — SCRIPT_FIRST, gloss is layer 2 after the reading |
| `es` `it` `ca` `fr` `de` `ro` `tr` `pt` `en` `nl` `jam` `la` `id` `tl` | 3,609 | **no — never shown** |

Author the 3,001 first, largest first (`ko` alone is 1,217 drills, and Korean
word order and particles are exactly what a word-by-word line explains).
Authoring any of the other 3,609 writes content into a route that does not
exist — the same defect as a layer with no write path (CHECKS.md §12), just
approached from the other end.

**Two of those 14 look mis-assigned rather than deliberately excluded, and
that is a separate decision to make before writing anything:**

- **`tr` is agglutinative** — Turkish stacks suffixes the way Swahili stacks
  prefixes, and `sw` is GLOSS_FIRST for exactly that reason.
- **`la` has free word order and carries its syntax in case endings**, which is
  the canonical argument for an interlinear line.

The Romance and Germanic courses are a defensible exclusion: their word order
tracks English closely enough that the translation carries the same
information. `jam` is English-lexified, so likewise. But `tr` and `la` sitting
in the same bucket looks like an oversight, not a judgement.

### What authoring 761 of them settled

The three courses the hint order already declares **gloss-first** — `yo`, `xh`,
`ha`, where the word-by-word line is shown BEFORE the translation because their
syntax does not map onto English — had zero glosses between them. All 761 now
have one, written by a maker–checker pass (74 agents, one checker per batch of
22 reading the course's own frequency file and grammar explanations).

**Rule 2 resolves cleanly for new work: use `.`, not `-`.** The rule is that
hyphens in the cell must equal hyphens in the word, and these sentences write
their words unsegmented, so `Ndifunda` is `1SG.PRES.study`. The `.`/`-`
question only looked hard while `sw`'s pre-segmented heads were in view.

**Rule 1 is tightened for new work: cells must EQUAL tokens, not merely not
exceed them.** `cells <= tokens` cannot catch a shift, which is the exact
failure the owner found by reading one Māori card — every position after the
shift teaching the wrong word. Exact equality makes alignment mechanically
provable, and that provability is the only reason to prefer a positional
format over a self-labelling one. Enforced for these three by
`test_an_authored_gloss_has_exactly_one_cell_per_token`.

**A gloss whose only cell is the blank is deleted, not stored.** Seven existed
— four one-token `{{answer}}.` sentences and three `sw` rows the answer-leak
fix had emptied. They render as a disclosure step that reads `___`.

Mechanical result over all 761: zero cell-count mismatches, zero blank errors,
zero answer leaks, zero label case-collisions. The eight case flags the
validator raised were its own false positives — `top` (of the table) and
`pass` (an exam) are lexical glosses that collide with the Leipzig category
NAMES TOP and PASS, so ordinary English words came out of the validator's
grammatical set.

---

## 1c. The English course cannot take the gloss layer as designed — open decision

The interlinear gloss's lexical cells are English, the program's metalanguage.
That works for 26 courses and is CIRCULAR on the 27th: an English sentence
glossed word-by-word into English ("the · dog · barks" → `the · dog · bark`)
tells a learner nothing — and en is a gloss-leads course, so that empty line
would sit ABOVE the translation that actually helps. Glossing en usefully
means lexical cells in the learner's own language, and nothing today can hold
that: `drill.gloss` and the sentence bank's `gloss` column are single strings
with no locale dimension, and the auto-translate loop has no gloss kind.

**Until the owner picks one of these, en's 266 drills stay unglossed**
(tripwire: `test_english_glosses_are_not_authored_before_the_locale_decision`):

1. a locale dimension for glosses (schema + loop kind + authoring per locale);
2. exempting en from the layer — its hint order then leads with the
   translation, which for an es-locale learner is the Spanish rendering and
   already the right first help.

The same locale question exists in miniature for every OTHER course viewed in
a non-English locale — a Spanish learner of Swahili reads English gloss cells
under a Spanish "Palabra por palabra" label — but there the cells still carry
real information; on en they carry none. Decide en first.

## 1b. Phonetics — how to say it, under how to spell it

A romanisation says which letters; **phonetics says how to say them**. They are
different layers and the second only exists where the first cannot carry the
whole pronunciation.

**Thai is the case that forced it.** RTGS carries no tone at all, and Thai is
tonal — คำ and ค่ำ are both *kham* — so the reading tells a learner how to
approximate a word rather than how to pronounce it. Wiktionary's Paiboon form
has the tone, but 32% of its entries use IPA letters (`gɔɔ-rá-nii`) no learner
reads. Neither is usable alone.

The layer is the RTGS spelling **with Paiboon's tone marks transferred onto
it**, syllable by syllable: `kot-mai` + `gòt-mǎai` → `kòt-mǎi`. Both forms are
hyphenated by syllable and all 4,045 rows align one-to-one, so the transfer is
positional and exact. It lives in a fourth column of `data/th_readings.tsv`.

**Built general, not as a Thai special case** (owner decision, 26 Aug 2026 —
other courses are expected to follow). `PHONETICS_LANGS` in
`backend/services/readings.py` is the roster; `hintLayersFor` places the layer
directly beneath the reading, and a course without one skips it rather than
rendering a blank.

Candidates when it rolls out: Mandarin-style tone languages obviously, but
also **stress** — Russian and Greek both write no stress mark and both have
unpredictable stress, which is exactly the class of information a romanisation
drops silently.

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

Five of the eight now have a reading, so their reading costs no
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

### Where the eight actually stand, 26 Aug

| | words | sentences | reading |
| --- | --- | --- | --- |
| `ru` | 9,962 | 28,935 | computed, all |
| `hi` | 9,385 | 8,130 | computed, all |
| `el` | 9,997 | 10,919 | computed, all |
| `ko` | 7,214 | 3,897 | computed, all |
| `he` | 3,000 | 7,483 | authored, 194 sentences (3%) |
| `fa` | 2,996 | 4,003 | authored, 199 sentences (5%) |
| `th` | 3,754 | 4,376 | looked up — 99% words, 88% sentences |
| `ar` | 8,928 | 14,671 | none, by design |

Four of eight are covered end to end — 51,881 sentences and 36,558 words —
at no authoring cost and no storage. What is left is genuinely three things,
not one backlog:

- **`he` and `fa` need authoring.** Both scripts drop vowels the reader has
  to supply, so no romanizer can be written; 393 rows are hand-done and the
  rest is work.
- **`th` took two attempts, and the second one ships.** The first COMPUTED
  RTGS with pythainlp's engines and failed adversarial verification: 38
  defects over 60 corpus sentences in seven classes, 6/18 on the confirmed
  set, missing `สุขภาพ` (health), `อิสระ` (freedom), `ฝรั่งเศส` (France) and
  `ไหม`, the question particle, as two syllables *haimai*.

  **Reading WHICH words failed is what solved it.** They were lexical
  failures, not rule failures — Pali-derived compounds whose linking syllable
  no rule predicts, and the silent leading ห that marks tone class rather than
  a sound. A dictionary fixes exactly that class, and one was already on disk:
  the Thai Wiktionary extract carries a Royal Institute (RTGS) reading for
  17,289 words. `data/th_readings.tsv` is the 4,045 the course uses, 149 KB,
  regenerated by `scripts/build_th_readings.py`.

  Segmentation is a longest-match walk over that same table, so **there is no
  runtime dependency** — pythainlp is an optional extra used only to
  regenerate. Coverage is 99% of the vocabulary and 88% of sentences, and the
  rule is **full coverage or no reading**: a line with a hole in it is read as
  a whole by someone who cannot see the hole.

  Three adversarial rounds took it from 38 defects to a dispute over one
  loanword. What each round found is the useful part:

  | round | found | what it actually was |
  | --- | --- | --- |
  | 1 | 38 in 7 classes | the computed engines; rejected outright |
  | 2 | 2 | a corrupt corpus row, and Wiktionary spelling loanwords from the SOURCE language (`บราซิล` *bra-sil*) instead of transcribing them |
  | 3 | 1 word | `ออสเตรเลีย`: the epenthetic syllable a medial ส forces. Refuters split 2–2, so the row is withheld |

  Round 2 also exposed the table poisoning its own segmenter: Wiktionary's
  single-consonant entries are letter NAMES (`ณ` → "no"), and longest-match
  used them as filler for words it lacked, so `ฉันไม่รู้จักคุณ` came apart
  into `รู้` plus a meaningless `cho` and produced a confident, wrong line.
  Dropping all 15 makes the segmentation fail instead, which is the honest
  outcome.

  **Tone is still missing and that is the standard's limit, not the data's.**
  RTGS carries none: `คำ` and `ค่ำ` are both *kham*. The tone-marked Paiboon
  form sits in the third column of the table — but 34% of Paiboon entries use
  IPA letters (`gɔɔ-rá-nii`) a learner cannot read, so making a shippable
  notation from it is its own piece of work, and still the one thing here that
  may want a native reviewer.

- **`ar` stays excluded.** Unvocalized script has no short vowels to romanize;
  a computed Arabic reading would invent sounds.

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
