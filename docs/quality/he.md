# Hebrew (he) — Content Quality Standards

## Language profile
Hebrew script, right-to-left, no case distinction, five letters with mandatory word-final
forms (כ מ נ פ צ → ך ם ן ף ץ).
**The authoritative variety is Modern Israeli Hebrew in its standard written register** —
the Hebrew of newspapers, notices and textbooks, written in *ktiv male* (full spelling,
no niqqud), which is what `HebrewNLP` in `backend/services/nlp/latin_base.py` grades.
Explicitly out of scope in `sentence`, `answer`, `translation` and `hint`: Biblical and
Mishnaic Hebrew as *live* material (the C2 point "The vav-conversive in quotation and
idiom" quotes it deliberately and is labelled as quotation), niqqud-bearing text as an
answer, and slang spellings. Colloquial forms belong only inside a point that names the
contrast — "Formal and colloquial register" and "Switching register inside one text" do
exactly that, and nowhere else in the file does a spoken form appear unlabelled.
Gender is two-way (m./f.) and runs through nouns, adjectives, numerals, present-tense
verbs, past/future persons and 2nd/3rd-person pronouns. Three things dominate drill
quality:
1. **Niqqud is invisible to the grader.** Vowel points are Unicode combining marks, so
   layer 2.5 of `check_answer` folds them: typing `שלום` for `שָׁלוֹם` returns
   `CORRECT_SLOPPY` ("Almost — check the accents"). A contrast carried only by niqqud
   cannot be failed.
2. **Final forms are folded too, but coached.** `HebrewNLP.fold_lookalikes` maps
   ךםןףץ → כמנפצ, so `שלומ` for `שלום` is amber, not green — deliberate, since final
   forms *are* mandatory spelling.
3. **Prefixed particles are part of the word.** `leading_articles = ()` — nothing is
   stripped, so `בית` for `הבית` grades `WRONG`. The ה־ / ש־ / כש־ / ל־ points are all
   genuinely gradeable; do not weaken them by blanking a bare stem.

## Hint standards
Universal rules, once: a hint narrows the answer without containing it. Never the answer
as a whole word; never a gloss that already sits in the drill's own `translation`; never
the `answer — explanation` template; one hint resolves to exactly one answer inside a
point (allomorph sets excepted where the sentence disambiguates); hints are written in
English — quoting a base form in Hebrew script is fine, whole Hebrew sentences are not.

Hebrew-specific:
- **Name gender and number on every agreeing answer** — adjective, numeral, present-tense
  verb, past/future person. The English translation usually cannot carry it.
  GOOD `small, feminine — add ה־ to קטן` for `קטנה`. BAD `small` for `קטנה` beside `קטן`
  in the same point: two answers, one hint, and neither the blank nor the English says
  which.
- **Quote the base form, never the built form.** The house convention "gloss — how the
  form is built" is good precisely because the quoted token is *not* the answer.
  GOOD `the house — ה־ prefixed directly onto בית` for `הבית` (בית ≠ הבית).
  BAD would be `the house — ה־ plus הבית`, which prints the answer.
- **Never write bare niqqud in a hint**, and never make niqqud the discriminator: the
  grader strips it, so the hint would be pointing at something the card cannot test.
  There is currently zero niqqud anywhere in `data/grammar/he_grammar.json` — keep it
  at zero.
- **Distinguish את from את.** The object marker and the 2nd-person feminine pronoun are
  the same string. A hint on either must say which. GOOD `the untranslatable marker that
  stands before a definite object`. BAD `you / object marker`.
- **Gloss the word in its sentence, not in isolation.** BAD, and live in the file:
  `"answer": "הספר", "hint": "the book — the second half of the compound…"` under
  translation *The children are going to school.* — inside בית הספר that half does not
  mean "the book", and the learner is told to think of a book.

## Question / drill standards
- **Standard written Modern Hebrew, every field.** No `אין לי מושג`-style slang, no
  spoken reductions, no transliterated English. Speech forms appear only in the two
  register points, and only opposite the written form they contrast with.
- **Exactly one blank**, and the blank must fall on a whole orthographic word including
  its prefixed particles. Hebrew fuses ה־ ו־ ב־ ל־ כ־ מ־ ש־ onto the next word; blanking
  a stem and leaving the prefix outside the blank produces a token no learner can type.
  Current file does this right (`שגר`, `כשהגעתי`, `שהבטיח` are blanked whole).
- **The sentence must force the answer after folding.** Because niqqud and final forms
  fold, a drill contrasting `שָׂפָה`/`שְׂפָה` or `שלומ`/`שלום` is untestable. Contrast
  letters, not points.
- **Unvocalized spelling is genuinely ambiguous — say so or avoid it.** `קראת` is both
  "you (m.) read" and "you (f.) read"; the file handles this honestly with
  `the unvocalized spelling covers both genders` plus an `(m.)` in the translation. Do
  that, or pick another cell.
- **Gender must be recoverable.** If the answer's gender is not visible in the Hebrew
  sentence, the English translation carries `(m.)` / `(f.)` — 5 translations do today.
  Otherwise the drill has two right answers.
- Every drill carries a `transliteration` (191/191 today) and it must match the answer
  as spelled, in the file's own scheme (`ch` for ח/כ, `ts` for צ, `kh` for fricative כ).

## Translation & definition standards
- No bare one-word gloss for a polysemous word. `ספר` is not "book" alone when it also
  heads בית ספר; `עיר` is "city, town (f.)"; `דין` is "law, judgement", not "law".
- **Mark gender on every noun definition** (`m.`/`f.`), and mark nouns that are plural in
  form — `מים` "water" is grammatically plural and takes plural agreement. This is the
  single largest gap: `data/he_frequency.tsv` has columns `rank word pos en` and **no
  gender column at all**, and 0 of its 23 noun rows mention gender in the gloss.
- Register consistency: neutral standard English against standard written Hebrew.
  A translation written in casual English ("gonna", "loads of") misrepresents a sentence
  that is neutral in Hebrew.
- **The translation must translate.** `הכניסה למנויים בלבד` → "Entry for subscribers
  only" is right; an idiomatic rewrite that drops בלבד would erase the drilled word.

## Current measured state
`data/grammar/he_grammar.json`: **41 points, 191 drills**, levels A1 10 / A2 10 / B1 9 /
B2 6 / C1 3 / C2 3. All 41 have `source: "ai"` and **`reviewed: false` — zero points have
been human-reviewed.** No point carries a `culture_note`. 191/191 transliterated.

Mechanical rules, re-run against the file (agrees with the crawl):
- Hint leaks: **0**. Self-answering `answer — …` template: **0**. Empty
  hint/translation/explanation: **0**. Duplicate hint → two answers inside a point: **0**.
  Hints drifting into Hebrew (≥3 Hebrew tokens beyond the answer): **0**.
- Giveaway-by-gloss: **1** — `"answer": "יש", "hint": "there is"` under translation
  *There is a good book.* The sibling drill in the same point does it properly
  (`there is — states existence`).
- Gender unmarked on noun answers: **18 of 19**. Only `הפסקה` ("a feminine action noun")
  names it. 65 of 191 hints name a gender overall, essentially all on verbs and
  adjectives.
- Niqqud in any field: **0**. Final-form spelling errors (a non-final כמנפצ at word end,
  or a final form mid-word): **0**. Both clean — record this as the baseline to hold.

**Structural debt — this is a thin course.** No `he_sentences.tsv` in either location.
`data/he_frequency.tsv` is **90 rows** (header + 90), against 8778 for Arabic. No
`he_morphology.json`, so there is **no machine-readable gender source anywhere** — the
gender rule above cannot be enforced by joining against data, only by reading. There is
no seed module. `data/gym/he.json` **does exist** (41 entries in 3 columns, every `point`
matching a real grammar title) — the group brief said Hebrew has no gym; the file
disagrees and the file wins.

Worst offenders:
1. `"explanation"` of "Personal pronouns and grammatical gender" reads
   `היא (she/it, masculine)` — the feminine pronoun is labelled masculine, in the point
   whose entire subject is gender, at A1.
2. `"answer": "הספר", "hint": "the book — the second half of the compound, and the only
   part that takes the article"`, translation *The children are going to school.* — the
   gloss contradicts the sentence.
3. `"answer": "יש", "hint": "there is"` / *There is a good book.* — the hint is a
   substring of its own translation and adds nothing.

## Testing checklist
- `python -m backend.services.quality.audit_content --language he` — the automated
  checker (lands with this change; may not exist in your tree yet).
- There is no `test_nlp_hebrew.py`; `HebrewNLP` is tested by `TestHebrew` inside
  `.venv/bin/pytest backend/tests/test_nlp_latin.py -q` (4 cases: niqqud omitted, exact
  match, wrong word, article not stripped), plus the shared layers in
  `.venv/bin/pytest backend/tests/test_nlp_base.py -q`. Nothing tests final-form folding
  or a gender-agreement rejection — open debt.
- Hebrew is in `TRANSLIT_LANGS` (`frontend/src/features/keyboards/translit.ts`):
  `cd frontend && npx vitest run src/__tests__/translit`
- Human spot-check — 10 random drills read against the standards above. A drill fails if:
  the hint omits gender on an adjective, numeral, participle or noun answer; the hint's
  English also appears in the translation; the gloss describes the word out of context
  rather than in the sentence; any field carries niqqud; a non-final כ מ נ פ צ sits at a
  word end; the blank splits a prefixed particle from its stem; the answer's gender is
  neither visible in the Hebrew nor marked `(m.)`/`(f.)` in the English; the
  transliteration disagrees with the spelling; or a spoken form appears outside the two
  register points. Type the plausible wrong-gender answer into the grader and confirm it
  is refused — `טוב` for `טובה` must come back `WRONG`, not amber.
