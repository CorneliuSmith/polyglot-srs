# Hausa (ha) — Content Quality Standards

## Language profile

Latin script (Boko), left-to-right, with four letters English lacks: the **hooked consonants `ɓ ɗ ƙ`** and
**`ƴ`/`ʼy`**, plus the modifier apostrophe `ʼ` for glottalisation. **The authoritative variety is Standard
Hausa on the Kano dialect**, written in Boko — the variety of the FSI/Live Lingua courses cited in every
point's `references`. **Out of scope:** Ajami (Arabic-script) Hausa, the western Sokoto and eastern
Bauchi/Zaria varieties, and Niger's slightly different Boko conventions. Tone (H/L/falling) and vowel length
are **phonemic but unwritten**, and this course follows the standard orthography in not writing them.

**Hausa has grammatical gender: masculine and feminine, in the singular only**, neutralised in the plural.
Gender is not predictable from meaning and shows up everywhere the learner can get it wrong — the identity
copula `ne` (m./pl.) vs `ce` (f.), the genitive linker `-n` (m./pl.) vs `-r` (f.), demonstratives and relative
pronouns (`wanda` / `wadda` / `waɗanda`). There are no noun classes.

Three features dominate drill quality:

1. **The hooked letters are hard-graded.** `ɓ ɗ ƙ ƴ` are single codepoints with no decomposition, so
   `_strip_marks` in `backend/services/nlp/base.py` leaves them intact: typing `dan` for `ɗan` is not an accent
   slip, it falls through to `WRONG` (FSRS *Again*) with "Close, but that's a different word". Unlike Yoruba
   tone or Turkish rounding, this contrast **is** testable — so drills may and should test it.
2. **Person and aspect are fused into one pre-verbal word.** `na/ka/ya/ta` (completive), `ina/kana/yana`
   (continuous), `nakan/yakan` (habitual), `suka/muka/aka` (relative completive). The answer is that portmanteau,
   so the hint must name both halves — person *and* aspect — or it under-determines the blank.
3. **Plurals are irregular and unpredictable.** `HausaNLP.get_morphological_family` deliberately returns only
   the normalised surface form, and `lemmatize` does nothing: there is no safe stemmer. Every irregular plural
   a drill should accept has to be in the card's `alternatives`.

**The course had 885 nouns and no copula (fixed 20 Aug 2026).** `data/ha_frequency.tsv`
held 1,188 rows of which **885 were nouns and 171 proper names — 89% of the course** —
against 44 verbs and 11 pronouns. The grammatical spine was simply absent: the drills use
`ne` and `ce` (the masculine and feminine copulas) 43 and 44 times with no card for either,
`da` 98 times, and `ya`/`yana`/`na`/`ta`/`ba`/`yi` likewise. A Hausa course without its
copulas cannot form a sentence.

**285 rows added**, each a word the course's own drills already use, glossed from those
sentences and their English translations, then adversarially checked. 1,188 → 1,473. TAM
markers name person, number **and** aspect, because English cannot separate them:
`ya` "he (3sg m.), completive" against `yana` "he (3sg m.), continuous".

**Wiktionary was the wrong source here and the course was the right one.** kaikki has an
entry for only 6 of the 316 gaps, and where it has one it can mislead: it glosses `a` as
*"the first letter of the Hausa alphabet"* while every course sentence uses it as the
locative preposition (*Akwai ruwa **a** gida*). That is the `wrong_sense_gloss` trap, and
the repair used course usage over the dictionary wherever they disagreed.

### Hooked letters: the source files contradict each other

`ɓ ɗ ƙ ƴ` are hard-graded — this page forbids writing them as `b d k y`, because a card
headed `kasa` drills a misspelling of the `ƙasa` the course already teaches. Measured
20 Aug, **eight words are spelled both ways across the course's own files**:

| | spellings | where |
| --- | --- | --- |
| `kuɗin` / `kudin` | 1 / 3 | grammar file hooks it, `ha_sentences.tsv` does not |
| `ƙafa` / `kafa` | 4 / 3 | grammar hooks it, the sentence bank does both |
| `baƙi` / `baki` | 2 / 9 | grammar hooks it, the sentence bank does not |
| `ƴan` / `yan`, `zaƙi` / `zaki`, `ɗari` / `dari`, `ƙabila` / `kabila`, `ɗa` / `da` | | mixed |

Four vocabulary rows are the plain twin of another row (`kafa`, `baki`, `dari`, `kabila`).

**Not all of these are errors** — `da` "with, and" and `ɗa` "son" are different words, as are
`dari` "cold" and `ɗari` "hundred". What is an error is a card whose own gloss names a
different standard spelling; three proposals were refused for exactly that (`kudi` →
`kuɗi`, `daya` → `ɗaya`, `karfi` → `ƙarfi`), and the checker separately refused `kasa`,
`kudin`, `tuntube` and `kadawa` on the same ground, each time naming the source row to
repair.

**Outstanding, and it must precede any sentence work:** repair the sentence bank's
unhooked spellings so the files agree, then re-run the gap pass — several words have no
card only because the two files disagree about how to spell them.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already
sitting in the drill's own translation; never the `answer — explanation` template; one hint resolves to exactly
one answer inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and
quoting a Hausa base form is fine while whole Hausa sentences are not.

1. **"Stem gloss + the grammatical piece" is the house convention — keep it.** GOOD, all from the file:
   `book + masculine linker` → `Littafin`; `car + feminine linker` → `Motar`; `son + masculine linker + 'his'`
   → `Ɗansa`; `children-of — the plural prefix` → `ʼYan`. The gender word is doing the work the learner cannot
   get from English, and the linker itself is never spelled.
2. **Name gender by name whenever the answer encodes it.** GOOD: `daughter-of — the feminine prefix` → `ʼyar`;
   `plural relative` → `Waɗanda`. BAD: `linker` alone, which leaves `-n` and `-r` equally available;
   BAD: `gown + linker` → `Rigar`, which is the same defect one word short.
3. **Never write a hooked letter's plain twin as a stand-in.** Hints and explanations use `ɓ ɗ ƙ ƴ`, never
   `b d k y`, and never the digraph workarounds (`'b`, `'d`, `'k`). GOOD: `ɗalibi → plural` → `Ɗalibai`.
   BAD: `dalibi → plural`, which teaches a misspelling of the citation form.
4. **Give the person AND the aspect for a portmanteau answer.** GOOD: `they — subjunctive pronoun` → `su`;
   `he + continuous` for `yana`. BAD: `they` alone, or `continuous` alone — the point has six drills and they
   would each match several.
5. **A one-word English gloss is not a hint.** BAD, all real: `he` → `Shi` under *He is a student.*; `she` →
   `Ita`; `this` → `Wannan` under *This book is mine.*; `these` → `Waɗannan`; `that` → `cewa` ×3; `exceed` →
   `fi`. GOOD: `3sg m. independent pronoun, subject of a ne-clause`; `near demonstrative, before the noun`;
   `complementiser after a speech verb`.
6. **Quoting the gloss does not fix it.** `'what'` → `Me`, `'who'` → `Wa`, `'if'` → `Idan` read as careful
   style but are still the English word sitting in the translation.

## Question / drill standards

A good Hausa drill is a natural Kano-standard sentence, one blank, and a translation of the completed sentence.
Pitfalls:

- **A gender drill needs a noun whose gender the learner can be expected to know**, and the translation must
  not silently resolve it. `{{answer}} Audu sabuwa ce.` / *Audu's car is new.* is well built: `sabuwa ce`
  agrees feminine, so the frame itself confirms `Motar` — the learner is being tested on the linker, not on
  guessing `mota`'s gender.
- **Because nothing is lemmatised, the answer must be exactly the form you mean.** No family or aspect layer
  will rescue a near-miss: only layers 1, 2 (case/apostrophe folding) and 6 (`alternatives`) can accept an
  answer. Put every legitimate variant in `alternatives` explicitly.
- **Apostrophes must be canonical.** `HausaNLP.normalize` folds `ʼ` (U+02BC), `’`, `‘`, `ˈ` and `'` to one
  character, so grading is safe — but the *displayed* text is inconsistent today: `ʼYan`/`ʼyar` use U+02BC
  while `addu'a` and `Ko'ina` use ASCII U+0027, and U+0027 is also used as an English quotation mark around
  Hausa dialogue in the same file. Write glottalisation as U+02BC everywhere and use curly quotes for quoting.
- **Do not build a drill whose contrast is tone or vowel length**, since neither is written: `fàrī` (white)
  and `fárì` (drought) are the same string on the card. Such pairs belong in a culture/pronunciation note.
- **One blank, one token.** Multi-word answers should appear only where the construction is one unit
  (`ba … ba` is a discontinuous negation — drill one half and put the other in the frame).

## Translation & definition standards

- **Every noun definition must carry gender.** `gida (m.) house`, `mota (f.) car`, `littafi (m.) book`. Without
  it the learner cannot choose `-n`/`-r` or `ne`/`ce`, which are two of the first ten grammar points.
- **Plural in the definition too, spelled out**, because it cannot be derived: `ɗalibi (m., pl. ɗalibai)`.
- **No bare one-word gloss for a polysemous word.** `sai` has a whole C1 point to itself (until / then / only /
  except) and must never be glossed as one of them; `ɗan` is "son of", a profession/belonging prefix, and a
  diminutive — the file's three drills for it use three different hints, correctly.
- **Register consistency:** neutral standard Hausa. The elaborate greeting register (`Ranka ya daɗe`) is a C2
  point and stays there.

## Current measured state

Measured directly from `data/grammar/ha_grammar.json` and `data/`:

- **42 grammar points, 266 drills**, A1–C2. **20 of the 42 points are `reviewed: false`** — the highest
  unreviewed share of this group.
- **Hint leaks: 0. Empty hints / translations / explanations: 0. Vague translations: 0.** Confirms the crawl.
- **One-word hints: 31.** The crawl says 29; the file says 31 — trust the file. **24 of them also appear
  verbatim in the drill's own translation.** Worst offenders: *Independent pronouns* (`he` → `Shi` / *He is a
  student.*, `she` → `Ita` / *She is a teacher.*), *Demonstratives* (6 of 6 drills: `this`, `these`, `here`),
  *Object pronouns* (`her`, `me`, `them`, `you (plural)`), *Reported speech* (`that` → `cewa` ×3).
- **Duplicate hints: 0 real.** Two raw pairs exist — `this` → `Wannan`/`wannan` and `before (+ subjunctive)` →
  `Kafin`/`kafin` — but both are capitalisation pairs of one answer, which the grader folds. The crawl's 0 is
  right.
- **Hooked letters appear in 14 answers** and 51 times across the drill text (`ɗ` 26, `ƙ` 19, `Ɗ` 4, `ɓ` 2).
  Coverage of `ɓ` is thin enough that a learner can finish the course having typed it once.
- **Apostrophe inconsistency:** 3 in-word uses of U+02BC (`ʼYan`, `ʼyar`, `ʼYan`) against 3 in-word uses of
  ASCII U+0027 (`addu'a`, `Ko'ina` ×2), with 6 more U+0027 doing duty as quotation marks.
- **There is no `data/ha_morphology.json` at all** — the only language in this group with none — so the gym has
  no paradigm to display, and irregular plurals live nowhere except individual `alternatives`. There is no
  `data/gym/ha.json` manifest either.
- **Corpus: 319 rows in `data/ha_sentences.tsv`** (plus 105 curated) against 1,143 words in
  `data/ha_frequency.tsv`.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language ha
.venv/bin/pytest backend/tests/test_nlp_hausa_xhosa.py -q
.venv/bin/pytest backend/tests/test_seeder_hausa_xhosa.py -q
```

Hausa is not in `TRANSLIT_LANGS` (`ru ar el he fa hi th ko`), so the transliteration suite does not apply —
but the answer box must emit `ɓ ɗ ƙ ƴ ʼ` from whatever keyboard the learner has, and that is worth a manual
check on mobile. `test_nlp_hausa_xhosa.py` already pins the apostrophe folding; the assertion worth adding is
that `dan` typed for `ɗan` grades `WRONG`, so the hooked-letter contrast is protected against a future
"be lenient with unusual letters" change.

A human reviewer pulls 10 random drills and asks:

1. **Could I answer this from the English translation alone?** 24 drills fail today.
2. **If the answer encodes gender, does the hint say masculine or feminine?** `gown + feminine linker` passes;
   a bare `linker` fails.
3. **If the answer is a person+aspect word, does the hint name both?** One half alone under-determines it.
4. **Are all hooked letters written as `ɓ ɗ ƙ ƴ`, in the sentence, the hint and the explanation?**
5. **Is every apostrophe the modifier letter `ʼ` (U+02BC), and is nothing else using that character?**
6. **Does the drill depend on unwritten tone or vowel length?** If yes it is unanswerable and must be rewritten.
7. **Are the irregular plurals this drill should accept actually listed in `alternatives`?** Nothing else will
   accept them.

## Wrong-lexeme sweep, top 2000 (25 Aug 2026)

**3 rows reglossed, 1 of them fatal** — the card named a genuinely
different word. This course was not in the first sweep of the 16 well-resourced courses; it
was screened afterwards so that every course with a kaikki extract is covered. Found by
`audit_wrong_lexeme`, decided by a maker–checker pass against each row's full kaikki sense
inventory and the course's own sentences. See `docs/quality/CHECKS.md` §3b.

| rank | word | now reads |
| --- | --- | --- |
| 22 | `wata` | some, a certain, another (f.) — the feminine of wani, before a feminine  |

Fixes are in `data/gloss_overrides.tsv` as well as `data/ha_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit is undone by the next seed.
