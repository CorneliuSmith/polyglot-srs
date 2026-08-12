# Swahili (sw) — Content Quality Standards

## Language profile

Latin script, left-to-right, no diacritics — `SwahiliNLP.normalize` is lowercase-and-strip and nothing else,
so what you type is what is graded. **The authoritative variety is Standard Swahili (Kiswahili sanifu)**, the
Unguja-based standard of East African schooling and media that the 50 grammar points and the 3,405-row
`data/sw_sentences.tsv` already teach. **Out of scope:** Sheng (the Nairobi youth register), Congolese Swahili
/ Kingwana, the coastal dialects Kimvita and Kiamu, and the Arabic-script tradition — mentionable in a culture
note, never drilled. The file does not declare a variety anywhere today; this document sets it.

**No grammatical gender whatsoever.** `yeye` is "he" and "she", and the point *Personal pronouns and ni*
says so in its culture note. What replaces gender is the **noun-class system**: the course teaches 1/2
(M-/Wa-), 5/6 (Ma-), 7/8 (Ki-/Vi-), 9/10 (N-), 11/14 (U-), 15 (Ku-) and the place classes 16–18.

Three features dominate drill quality:

1. **Class agreement reaches everything.** A single class choice fixes the adjective prefix, the demonstrative,
   the possessive stem, the -a of association and the verb's subject prefix. A hint that names the class is
   teaching; a hint that spells the resulting concord is answering.
2. **The verb is a slot template** — subject prefix, tense/aspect marker, optional object infix, root,
   extensions, final vowel. Answers are whole built words (`tulipangua`, `hatunywi`), so the hint convention is
   a gloss of the root plus the names of the slots.
3. **Extensions stack and change meaning** (passive, causative, applicative, stative, reciprocal, reversive).
   The B2 band is entirely this, and it is where the file's best hints live.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already
sitting in the drill's own translation; never the `answer — explanation` template; one hint resolves to exactly
one answer inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and
quoting a Swahili base form is fine while whole Swahili sentences are not.

1. **"Root gloss + slot names, in order" is the house convention — and it is the reference bar for the whole
   repo.** 143 of 308 hints (46%) are built this way. GOOD: `to close + reversive = its opposite (command)`
   → `fungua`; `to arrange + reversive + past (we)` → `tulipangua`; `to drink + present negative, we (final
   vowel changes)` → `hatunywi`. Each names every morpheme the answer contains, in the order they are glued,
   and spells none of them. Copy this shape into any new point.
2. **Name the class; make the learner derive the concord.** GOOD: `-angu with ki- class` → `changu` (the
   learner has to know ki- + -angu becomes `ch-`); `how many — agrees with the noun class (miaka → mi-)` →
   `mingapi`; `class 1a takes oo- in the plural` is the Xhosa equivalent of this move. BAD: any hint that
   writes the finished concord, e.g. `ch- + angu` for `changu` — that is the exercise.
3. **Do not spell the answer morpheme-by-morpheme.** Three hints in the file today reconstruct their own answer
   by concatenation, which the whole-word leak regex cannot see. BAD, all real: `ha + a + end + i` → `haendi`;
   `si- + -la with final -i` → `sili`; `u- + soma + -e` → `usome`. GOOD rewrites: `to go + present negative
   (he)`, `to eat + present negative (I)`, `to read + subjunctive (you)`.
4. **A one-word English gloss is not a hint.** BAD: `who` → `Nani` under *Who is coming?*; `when` → `lini`;
   `which` → `gani`; `although` → `Ingawa` under *Although it rained, we travelled.* GOOD: `question word for
   a person`, `question word for a point in time`, `concessive opener + indicative`.
5. **Culturally untranslatable words must not be quoted in the translation.** BAD, in the file: hint `the
   elder's reply to shikamoo` → `Marahaba`, translation *Grandmother replied: 'Marahaba, my child.'* — the
   answer is printed on the card. GOOD: translation *Grandmother gave the customary reply, my child.* with the
   same hint.

## Question / drill standards

A good Swahili drill is a sentence a Standard-Swahili speaker would say, one blank, and a translation of the
completed sentence. The number frames in the noun-class points are the model: `Kitabu kimoja, {{answer}}
viwili.` — the agreement word `viwili` fixes the class and the number before the learner reaches the hint.

- **Grammar drills are graded strictly, and that is what makes class contrasts teachable.** With
  `card_type == "grammar"`, layers 3–4 of `check_answer` return `WRONG_FORM` (FSRS *Again*), so `amefika`
  typed for `wamefika` fails rather than passing amber. Six points contain two answers that share a lemma
  (`amefika`/`wamefika`, `ukisoma`/`wakisoma`, five forms of `kuwa`) and all of them grade correctly.
- **Know the lemmatiser's one blind spot.** `SwahiliNLP.lemmatize` strips subject-prefix + tense-marker
  whenever both appear, so a wa-class plural noun that starts `wa` + `na/li/ta/me/ki/hu/ka` is mistaken for a
  verb: `wanafunzi → funzi`. It cannot wrongly accept anything on a grammar card, but do not build a point
  where two noun answers reduce to the same fake stem.
- **Never leave the blank answerable two ways.** `{{answer}} kiko mezani` is fixed only because `kiko` carries
  class-7 agreement; a frame with no concord in it must get the class from the English translation instead.
- **Keep the answer to one token** unless the point is a multiword construction (`kuwa na`, `licha ya`).
- **Register:** Standard Swahili throughout. `shikamoo`/`marahaba` and the honorific plural belong in C2 where
  the file puts them; Sheng vocabulary belongs nowhere.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `-a of association` alone means "of"; the definition has to
  say which class it agrees with. `kupiga` is the extreme case — the C2 point drills `kupiga simu` (phone),
  `kupiga picha` (photograph), `kupiga hodi` (announce yourself); a vocabulary card glossing `piga` as "hit"
  is wrong more often than it is right.
- **Mark the class in every noun definition, and say which class the number refers to.**
  `data/sw_morphology.json` gives all 1024 nouns a `Plural` chip and a `Class` chip, but the chip carries only
  the *plural* class as a Roman numeral: the values in the file are `X` (475), `VI` (188), `II` (169), `IV`
  (100), `VIII` (92) — every value is even, and no singular class is ever named. A learner reading
  "kitabu · Class VIII" will reasonably think kitabu is class 8. Definitions should read `kitabu (7/8, pl.
  vitabu)`.
- **444 of the 1024 nouns have `Plural` identical to the singular.** For class 9/10 that is correct and worth
  saying out loud in the definition ("invariable, class 9/10"); silence reads as missing data.
- **Register consistency:** translations are neutral modern English, contractions allowed, no dialect colour.

## Current measured state

Measured directly from `data/grammar/sw_grammar.json`, `data/sw_morphology.json` and `data/`:

- **50 grammar points, 308 drills**, A1–C2. **18 of the 50 points are `reviewed: false`** — including the
  B2 extension band that contains the best hints in the repo.
- **Hint leaks (whole-word answer inside its hint): 0.** Empty hints, empty translations, empty explanations:
  **0**. Vague (under-length) translations: **0**. Duplicate hints inside a point: **0**. Answer echoed in the
  drill sentence: **0**. This matches the crawl exactly.
- **One-word hints: 4**, all also giveaway-by-gloss (the hint appears verbatim in the drill's own translation):
  `who`/`Nani`, `when`/`lini`, `which`/`gani`, `although`/`Ingawa`. Crawl says 4 and 4; the file agrees.
- **Morpheme-spelling hints: 3** — `ha + a + end + i` → `haendi`, `si- + -la with final -i` → `sili`,
  `u- + soma + -e` → `usome`. The crawl reports zero leaks for Swahili; these are leaks its whole-word regex
  cannot see, and the file wins. They are the only editorial defects at fail level.
- **Answer printed in its own translation: 3** — `hodi` (*The visitor called 'hodi' at the door.*), `Shikamoo`
  and `Marahaba` in the C2 respect-register point.
- **Infrastructure, not editorial, is the real gap.** `data/sw_frequency.tsv` 3,501 words and
  `data/sw_sentences.tsv` 3,405 rows are the healthiest of this group, but **there is no `data/gym/sw.json`**
  — Swahili has no gym manifest at all, in a language whose entire difficulty is paradigms.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language sw
.venv/bin/pytest backend/tests/test_nlp_swahili.py -q
.venv/bin/pytest backend/tests/test_seeder_swahili_turkish.py -q
```

Swahili is not in `TRANSLIT_LANGS` (`ru ar el he fa hi th ko`), so the transliteration suite does not apply;
there is nothing to transliterate. The assertion worth adding to `test_nlp_swahili.py` is that a noun such as
`wanafunzi` does not lemmatise into a verb stem that collides with another answer in its point.

A human reviewer pulls 10 random drills and asks:

1. **Does the hint name every slot in the answer, in order — or does it spell one of them?** The three
   morpheme-spelling hints fail here.
2. **Does the hint name a class, or write out the concord?** Naming passes; writing fails.
3. **Could I answer from the English translation alone?** The four one-word question-word hints fail.
4. **Is the answer printed anywhere on the card — sentence, translation or hint?** `hodi`, `Shikamoo`,
   `Marahaba` fail.
5. **Does something in the frame (an agreement word, a numeral) fix the class before the hint does?**
6. **Do two drills in this point share an answer lemma, and does the grammar card type still fail the wrong
   one?** It should — check the point is not being used as a vocabulary card.
7. **Is this Standard Swahili, not Sheng or a coastal dialect form?**
