# Hebrew (he) — Content Quality Standards

## Language profile
Hebrew script, right-to-left, no case distinction, five letters with mandatory word-final
forms (כ מ נ פ צ → ך ם ן ף ץ).
**The authoritative variety is Modern Israeli Hebrew in its standard written register** —
newspapers, notices, textbooks — spelled *ktiv male* (full spelling, unpointed), which is
what `HebrewNLP` in `backend/services/nlp/latin_base.py` grades.
Explicitly out of scope in `sentence`, `answer`, `translation` and `hint`: Biblical and
Mishnaic Hebrew as *live* material (the C2 point "The vav-conversive in quotation and
idiom" quotes it deliberately, and says so), niqqud-bearing answers, and slang spellings.
Colloquial forms belong only inside a point that names the contrast — "Formal and
colloquial register" and "Switching register inside one text" do exactly that, and no
unlabelled spoken form appears elsewhere in the file.
Gender is two-way (m./f.), running through nouns, adjectives, numerals, present-tense
verbs, past/future persons and 2nd/3rd-person pronouns; there is no neuter and no noun
class. Three things dominate drill quality:
1. **Niqqud is invisible to the grader.** Vowel points are Unicode combining marks, so
   layer 2.5 of `check_answer` folds them: `בית` for `בַּיִת` returns `CORRECT_SLOPPY`
   ("Almost — check the accents"). A contrast carried only by niqqud cannot be failed.
2. **Final forms fold too, but are coached.** `HebrewNLP.fold_lookalikes` maps
   ךםןףץ → כמנפצ, so `שלומ` for `שלום` grades amber with the right form named — deliberate,
   since final forms *are* mandatory spelling. Amber is not a fail: don't rest a drill's
   only contrast on one.
3. **Prefixed particles are part of the word.** `leading_articles = ()` — nothing is
   stripped, so `בית` for `הבית` grades `WRONG`. The ה־ / ש־ / כש־ / ל־ points are
   genuinely gradeable; don't weaken them by blanking a bare stem.

**929 → 3,000 rows (24 Aug 2026).** Same story as `id`, `fa` and `tl`: hand-added by `2d7ce7f`, no pipeline. Now built from `heb_wikipedia_2021_100K` (Leipzig, CC-BY) plus the Hebrew kaikki extract, through the repo's own parser. 134 proper nouns dropped — a Wikipedia corpus is full of them. First additions: `לאחר`, `אך`, `זו`, `אשר`, `כאשר`, and the past-tense forms of `היה`.

Note for whoever works this next: the vocabulary is stored **unvocalized**, which is correct and matches how Hebrew is written — the collision guard already has a test for it (`test_a_vocalized_rendering_of_the_stored_word_stays_sloppy`).

## Hint standards
Universal rules, once: a hint narrows the answer without containing it. Never the answer as
a whole word; never a gloss that already sits in the drill's own `translation`; never the
`answer — explanation` template; one hint resolves to exactly one answer inside a point
(allomorph sets excepted where the sentence disambiguates); hints are written in English —
quoting a base form in Hebrew script is fine, whole Hebrew sentences are not.

Hebrew-specific:
- **Never spell out affix + base.** Hebrew builds words by prefixing, so a hint that names
  the prefix *and* quotes the stem hands over the whole answer while passing every
  whole-word leak check. BAD (real, `הבית`): `the house — ה־ prefixed directly onto בית`.
  BAD (real, `קטנה`): `small, feminine — add ה־ to קטן`. GOOD: `the house — definite; the
  article rides on the noun` / `small — agrees with a feminine noun`.
- **Mark gender and number on every inflecting answer.** The vowel that distinguishes them
  usually isn't written and never survives normalization. GOOD (real, `שלוש`): `three,
  feminine — the short form, with no ending`. BAD: `three` in a point where `שלוש` and
  `שלושה` are both answers.
- **Don't restate the translation.** BAD (real, `יש` under "There is a good book."):
  `there is`. GOOD (its sibling drill): `there is — states existence`.
- **Quote at most one Hebrew base form, and never the answer's own stem.** GOOD (real,
  `אין`): `there isn't — the negative of יש`. BAD: quoting `הולך` under answer `הולכים`.
- **Naming a final form is legitimate coaching, not a leak.** GOOD: `ends in a final mem`.
  What is not allowed is a hint that hinges on niqqud, which the grader cannot fail.
- **Transliteration is a field, not a hint.** Romanization belongs in `transliteration`;
  hints stay English prose (currently 0 violations, 18/191 quote Hebrew script — keep it
  around that level).

## Question / drill standards
- **Standard written Hebrew in every field.** No `יאללה`, `סבבה`, `אח שלי`, no dropped
  ה־ in `הבית` → `בית` "as people say it", no spoken future-for-imperative unless the point
  is one of the two register points and the drill labels it.
- **Exactly one blank, and the sentence must force the answer after normalization.** A blank
  whose only competitor differs by niqqud or by a final/non-final letter is not gradeable —
  both land on `CORRECT_SLOPPY`. Prefix contrasts (ה־, ש־, ל־) *are* gradeable and are the
  right thing to drill.
- **The English must carry the gender the Hebrew forces.** `האישה {{answer}}.` → "The woman
  is good." forces `טובה` honestly. Where English is genderless, the translation must say so:
  "Are you (m.) going home?" — only 5 of 191 translations currently do this, and every
  pronoun/present-verb drill needs it.
- **Watch את.** It is both the object marker and "you (f.)". Inside a point the sentence must
  make one reading impossible; across points, keep the two uses in their own drills.
- **No copula blanks.** The present tense has no "to be"; a drill must not blank a word the
  language doesn't write. Use the pronoun-as-copula framing that point 2 already uses.
- **Repeating one answer is allowed only if each hint teaches a different trigger.** "The
  object marker את" answers `את` five times — acceptable, because the hints separate definite
  noun, proper name, plural definite and so on. Five drills, one hint, one answer would not be.
- **Transliteration must be readable as Hebrew, not as English.** `hair yafa` for
  `העיר יפה` reads as an English noun; write `ha-ir yafa`. The romanization also mirrors the
  typing scheme in `frontend/src/features/keyboards/translit.ts`, so a sloppy field teaches a
  wrong keystroke.

## Translation & definition standards
- **No bare one-word gloss for a polysemous word.** `ספר` is book/scroll/barber depending on
  vowels; `שם` is name and there. 45 of the 90 rows in `data/he_frequency.tsv` are one-word
  glosses. A gloss carries the sense plus a distinguishing word, e.g. `book (a printed one)`.
- **Every noun definition states gender**, because Hebrew has no article to reveal it and the
  ending lies: `לילה` (night) is masculine despite ending in ה, `עיר` (city) and `ארץ`
  (land) are feminine with no feminine ending, `מים` (water) is plural-only. Write
  `city (f.)`, not `city`.
- **Irregular plurals belong in the definition** — `שם` → `שמות`, `אישה` → `נשים` — since
  there is no morphology file to look them up in.
- **Register consistency.** Gloss the standard written sense first; a colloquial sense is
  labelled ("colloquial: …") or left out.
- **A translation translates.** It renders the whole sentence, marks the gender English
  drops, and does not become a usage note.

## Current measured state
From the crawl and re-verified against `data/grammar/he_grammar.json` (2026-08-12):

- **41 grammar points / 191 drills**, A1 10 · A2 10 · B1 9 · B2 6 · C1 3 · C2 3.
  Every point is `"source": "ai"` and **`"reviewed": false` — 0 of 41 human-reviewed.**
- **Fail-level violations: 0 whole-word hint leaks, 0 empty hints/translations/explanations,
  0 one-word hints, 0 duplicate hints within a point, 0 `answer — explanation` templates.**
  Mechanically this is one of the cleanest files in the repo.
- **1 gloss-repeat**: `Existence: יש and אין` — hint `there is` under translation
  "There is a good book." The hint adds nothing the learner can't read off the English.
- **7 hints quote a Hebrew token that is part of the answer; 4 of those hand over the whole
  answer**: `הבית` ← `the house — ה־ prefixed directly onto בית`; `הספר` ←
  `the book — ה־ prefixed onto ספר`; `העיר` ← `the city — ה־ prefixed onto עיר`; `טובה` ←
  `good, feminine — add ה־ to טוב`. The leak regex misses these because the answer never
  appears as one token — this is the file's real hint debt.
- **Gender marked in 65 of 191 hints (34%)**, and in only 5 translations. No gender source
  exists anywhere: no `he_morphology.json`, and 0 of the 23 noun rows in
  `data/he_frequency.tsv` mention gender.
- **Spelling is clean**: across all 191 resolved sentences, 0 non-final letters at word end
  and 0 final letters mid-word; 25 answers contain a final form; 0 answers or sentences carry
  niqqud (24 of 41 explanations do, which is correct — explanations are read, not typed).
- **Structural debt (the honest headline).** No sentence bank (`he_sentences.tsv` exists
  neither in `data/` nor `data/sentences/`), no `he_morphology.json`, and
  `data/he_frequency.tsv` is **90 rows** where a real course wants thousands. Everything a
  learner sees beyond the 191 drills is generated on demand.
- **Correction to the brief:** he was described as having no gym. It does —
  `data/gym/he.json` carries 41 entries in 3 columns (Verb forms 15, Nouns & agreement 11,
  Constructions 15) and every `point` resolves to a real grammar-point title. The gym gap is
  not real; the sentence/morphology/frequency gaps are.

## Testing checklist
- `python -m backend.services.quality.audit_content --language he` — the automated checker
  (lands with this change; may not exist in your tree yet).
- There is no `test_nlp_he.py`; the Hebrew backend is covered by
  `.venv/bin/pytest backend/tests/test_nlp_latin.py -q -k Hebrew`,
  `.venv/bin/pytest backend/tests/test_typed_input.py -q -k "Hebrew or BareMarks"` and
  `.venv/bin/pytest backend/tests/test_csv_importer.py -q -k hebrew`.
- Hebrew is in `TRANSLIT_LANGS` (`frontend/src/features/keyboards/translit.ts`):
  `cd frontend && npx vitest run src/__tests__/translit` — the Hebrew cases live in
  `src/__tests__/translitHebrewPersian.test.ts`.
- Human spot-check. A reviewer pulls **10 random drills** and asks, per drill: does the hint name a prefix
*and* quote its stem (the הבית pattern)? Does the hint repeat words already in the
translation? Is the answer's gender and number recoverable from the sentence or stated in the
translation — and if English is genderless, does it say "(m.)"? Would a niqqud-only or
final-form-only contrast be the thing under test (it can only grade amber)? Is any spoken
form present outside the two register points? Does the transliteration read as Hebrew rather
than as an English word (`hair` → `ha-ir`)? Any "yes" to the first five, or "no" to the last,
fails the drill.

## Wrong-lexeme sweep, top 2000 (25 Aug 2026)

**27 rows reglossed, 8 of them fatal** — the card named a genuinely
different word. This course was not in the first sweep of the 16 well-resourced courses; it
was screened afterwards so that every course with a kaikki extract is covered. Found by
`audit_wrong_lexeme`, decided by a maker–checker pass against each row's full kaikki sense
inventory and the course's own sentences. See `docs/quality/CHECKS.md` §3b.

| rank | word | now reads |
| --- | --- | --- |
| 1255 | `טובה` | good — f. sg. of טוב (עבודה טובה = 'good work'); also, as a noun (f.), a |
| 1368 | `מתאר` | describes, depicts (m. sg. present of תיאר) — הספר מתאר את 'the book des |
| 1397 | `יצר` | created, made, formed (3rd m. sg. past of יצר) — יצר קשר 'made contact', |
| 1413 | `צריכה` | needs to, has to, must (f. sg. of צריך; before an infinitive) — היא צריכ |
| 1431 | `חיות` | animals (f. pl. of חיה) — חיות בר 'wild animals', חיות מחמד 'pets', גן ח |
| 1459 | `מטה` | headquarters, (military) staff (m.) — ראש מטה 'chief of staff', קצין מטה |

Fixes are in `data/gloss_overrides.tsv` as well as `data/he_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit is undone by the next seed.
