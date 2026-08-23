# Yoruba (yo) — Content Quality Standards

## Language profile

Latin script, left-to-right, with two orthographic layers on top of the base letters: **three tones** written
with the acute (high, `á`), the grave (low, `à`) and nothing at all (mid, `a`), and the **underdot** that marks
distinct phonemes `ẹ ọ ṣ`. Both are spelling, not decoration — the A1 point *Tones change meaning* teaches
`ọkọ́` (hoe) / `ọkọ` (husband) / `ọkọ̀` (vehicle) on exactly that basis. **The authoritative variety is Standard
Yoruba**, the literary standard built on Ọ̀yọ́ with Lagos-press vocabulary, fully tone-marked. **Out of scope:**
undotted or untoned "internet Yoruba", the Ijebu / Ekiti / Ijesha dialects, and Caribbean/Brazilian liturgical
Lucumí — culture-note material at most.

**No gender and no noun classes.** Yoruba is isolating: verbs never inflect, plurality is a separate word
(`àwọn`), and `YorubaNLP` has no lemmatiser in the usual sense — its `lemmatize` just strips tone.

Three features dominate drill quality:

**The course carries its own tone evidence, and the vocabulary file does not use it
(measured 20 Aug 2026).** This was recorded as blocked pending a verified external tone
source. Two in-repo sources exist:

| | tone-marked |
| --- | --- |
| `data/grammar/yo_grammar.json` drills | **182 of 279 word types (65%)** |
| `data/yo_frequency.tsv` headwords | **6 of 1,644 (0.4%)** |

The dot-below survived at 40% (`ẹ ọ ṣ` on 661 rows), so this is not diacritic loss in
general — **tone specifically was stripped** while the dots came through. That is the
signature of a corpus that normalised tone, not of an unmarked source.

- **130 untoned rows have exactly one tone-marked form attested in the drills**, and they
  are the ranks that matter: 1 `ti`→`tí`, 2 `ni`→`ní`, 3 `o`→`ó`, 4 `a`→`á`, 7 `ko`→`kò`,
  8 `awọn`→`àwọn`, 12 `bi`→`bí`, 15 `lati`→`láti`.
- **17 rows state their own tone in the gloss** — the file already knows: rank 34 reads
  "a, a certain; one (after the noun: ọjọ́ kan …)" while its headword is bare `kan`.
- **Three rows are D1d homonym sets stated outright.** Rank 3 `o` is glossed "he, she, it
  (ó); you (o, subject); not (ò, short for kò)" — three words on one card, and the file
  says so. Same at rank 7 (`kò`/`kó`) and rank 9 (`sì`/`sí`).

**What this does and does not unblock.** The top band is repairable from evidence the
repo already contains, which is a stronger basis than the Māori pass had. The remaining
~1,491 rows have no in-repo attestation and still need an external source.

**And the attested form does not settle the row.** Rank 20 `to` is attested as `tó` in the
drills, but its gloss reads "to arrange, to line up" — which is `tò`, a different word. The
drills supply *candidates*; the gloss decides which word the rank belongs to. Applying the
attested tone mechanically is precisely the mistake that got the Māori macron pass
discarded (see `docs/quality/mi.md`), and it must not be repeated here.

1. **Tone is the answer, and the grader cannot see it.** `check_answer` layer 2.5 folds all combining marks
   before the strict-form gate, so `ọkọ` typed for `ọkọ̀` returns `CORRECT_SLOPPY` — FSRS *Hard*, a pass — with
   the message "Almost — check the accents", **even on a grammar card**. 179 of the 246 drill answers (73%)
   carry a tone mark, so most of the file is gradable only down to its toneless skeleton.
2. **Pre-verbal particles do all the grammar** (`ń`, `ti`, `yóò`, `máa`, `kò`, `bá`, `ni`). The answers are
   short function words, which is exactly the shape that invites a one-word English gloss for a hint.
3. **Serial verbs and `ni`-focus** mean word order carries meaning that English word order does not, so the
   translation has to be written with care or it stops constraining the blank.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already
sitting in the drill's own translation; never the `answer — explanation` template; one hint resolves to exactly
one answer inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and
quoting a Yoruba base form is fine while whole Yoruba sentences are not.

1. **Never state the tone pattern of the answer.** The tone marks are the thing being written; naming them is
   dictation. BAD, both in the file: `vehicle — the low-tone twin` → `ọkọ̀`; `money — mid-high tones` → `owó`;
   `time/season — low-low tones` → `Ìgbà`. GOOD: `the one you ride in, not the one you marry`,
   `what you pay with`, `the noun in 'childhood', not the verb`. If the point is *Tones change meaning*, the
   hint's whole job is to pick the right member of the minimal pair by meaning; the learner supplies the marks.
2. **Never leave two answers in one point that fold to the same string.** Five points do today (see below), and
   in each the grader accepts the sibling answer as amber-correct. GOOD: keep `ọkọ̀` and `ọkọ` in the same
   *explanation* but drill only one of them, or move the contrast to a multiple-choice presentation that does
   not go through `check_answer`.
3. **A pronoun hint must name a grammatical slot, not repeat the English pronoun.** BAD: `we` → `A` under *We
   want cold water.*; `us` → `wa` under *They saw us at the market.*; `their` → `wọn`. GOOD: `1pl subject,
   before the verb`; `1pl object, after the verb`; `3pl possessive, after the noun`.
4. **A function word needs its function named, not its English translation.** BAD: `that` → `pé` (four drills),
   `must` → `gbọ́dọ̀`, `where` → `Níbo`, `how` → `Báwo`. GOOD: `complementiser after a speech/thought verb`;
   `obligation modal, before the verb`; `question word for a place`.
5. **One hint, one answer inside the point.** BAD, in the file: `quality word used as a verb` maps to both
   `dára` and `tóbi` in *Adjectives are verbs* — and the same point's other four hints (`to be cold`,
   `to be tall`, `to be clean`, `to be small`) simply gloss the English adjective already in the translation.
   GOOD for that point: `the general 'be good' quality verb` / `the size quality verb`, with the glossing
   hints rewritten to name the syntactic fact ("adjective as main verb, no copula").

## Question / drill standards

A good drill is a natural Standard Yoruba sentence, fully tone-marked, one blank, and a translation of the
completed sentence. Pitfalls specific to Yoruba:

- **The tone-contrast point cannot be drilled as free text.** *Tones change meaning* is six fill-in-the-blank
  drills whose entire contrast is invisible to the grader. Until the checker or the grading layer treats
  tone as significant for Yoruba grammar cards, write these as recognition items or accept that they teach
  without testing — and say so, rather than pretending the card passes.
- **Do not put the answer in the translation.** `Ó dàbọ̀ {{answer}}!` → `o`, translated *Goodbye o! (warm)*,
  prints the answer. Translate the effect ("Goodbye — said warmly").
- **Short answers collide with English function words.** Answers `o`, `a`, `i` will match inside any English
  hint or translation; a checker needs the English-function-word exemption, and an author needs to remember
  that a one-letter answer is under-constrained unless the frame is tight.
- **Keep diacritics in NFC and consistent.** All 984 text fields in the file are already NFC, and Yoruba's
  underdot-plus-tone combinations (`ọ̀` = U+1ECD + U+0300) have no single-codepoint form, so any length or
  character comparison must work on grapheme clusters, not `len()`.
- **One blank per drill; the numeral or particle in the frame should disambiguate** the way `Mo rí ọmọ
  {{answer}}.` / *I saw two children.* does.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word, and no gloss at all without tone.** `ọkọ` is "husband",
  `ọkọ̀` is "vehicle", `ọkọ́` is "hoe" and `oko` is "farm"; a definition that writes any of them undotted or
  untoned is a different word. `ṣe` (do/make) and `sè` (cook) are the same trap in the C1 band.
- **No gender or class to mark** — the precision burden here is entirely tone + underdot + part of speech.
  Mark the part of speech when the same skeleton is both (`ń` progressive marker vs `ni` copula vs `ní` "at").
- **Register consistency:** neutral modern Standard Yoruba. The respect register (`ẹ`, `ẹ̀yin`, plural for
  elders) is a C2 point, and its politeness should not leak into A1 sentences where the singular is expected.

## Current measured state

Measured directly from `data/grammar/yo_grammar.json`, `data/yo_morphology.json` and `data/`:

- **40 grammar points, 246 drills**, A1–C2; **16 of 40 points are `reviewed: false`**.
- **Hint leaks: 0. Empty hints / translations / explanations: 0. Vague translations: 0.** Confirms the crawl.
- **One-word hints: 27** (crawl says 26 — trust the file), of which **23 also appear verbatim in the drill's
  own translation**. The pronoun and question-word points carry most of them: `we` → `A` / *We want cold
  water.*, `where` → `Níbo` / *Where do you live?*, `that` → `pé` ×4.
- **Duplicate hints: 2 raw pairs.** One is real — `quality word used as a verb` → `dára` and `tóbi`. The other,
  `plural marker` → `Àwọn` / `àwọn`, is a capitalisation pair, i.e. one answer to the grader. The crawl counts
  1; the file's real violation count is also **1**.
- **Tone-collapse pairs: 5 points contain two answers that are the same string after mark-folding**, so the
  grader accepts the wrong one as amber-correct: `ọkọ` / `ọkọ̀` and `owó` / `ọwọ́` (*Tones change meaning*),
  `o` / `ó` (*Subject pronouns*), `rẹ` / `rẹ̀` (*Possession*), `sè` / `ṣe` (*How-clauses with bí … ṣe*).
  Typing "husband" where "vehicle" belongs scores FSRS *Hard* and the card advances. This is the single
  worst defect in the Yoruba course and it is a grading-plus-content problem, not an editorial slip.
- **`data/yo_morphology.json` is an empty object — 3 bytes, 0 entries.** The gym has nothing to show, and there
  is no `data/gym/yo.json` manifest either.
- **The sentence bank is the thinnest of the original languages: 109 rows** in `data/yo_sentences.tsv` (plus 63
  curated), against 1,469 words in `data/yo_frequency.tsv`. Roughly one example sentence for every 13 words.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language yo
.venv/bin/pytest backend/tests/test_nlp_yoruba.py -q
.venv/bin/pytest backend/tests/test_source_yoruba.py -q
```

Yoruba is not in `TRANSLIT_LANGS` (`ru ar el he fa hi th ko`), so the transliteration suite does not apply —
but the answer box must accept `ẹ ọ ṣ` plus tone marks from a plain keyboard, and that is worth a manual
check. The assertion missing from `test_nlp_yoruba.py` is the one that matters most: that `ọkọ` typed for
`ọkọ̀` on a **grammar** card does not pass, which today it does, at layer 2.5 and before `YorubaNLP` is
consulted at all.

A human reviewer pulls 10 random drills and asks:

1. **Does the hint tell me the tone pattern?** If yes it fails — the marks are the answer.
2. **Does any other drill in this point have an answer identical to this one once tones and dots come off?**
   If yes, the point cannot be graded as written.
3. **Could I answer from the English translation alone?** 23 drills fail this today.
4. **Is the hint a grammatical slot or an English pronoun?** `we`, `us`, `their` fail.
5. **Is the answer printed in the sentence or the translation?** `o` in *Goodbye o!* fails.
6. **Is every Yoruba word on the card fully dotted and toned, in NFC?**
7. **Is this Standard Yoruba, not a dialect form or an untoned shortcut?**
