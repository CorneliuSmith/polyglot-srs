# Persian (fa) — Content Quality Standards

## Language profile
Perso-Arabic script, right-to-left, cursive with positional letter forms; four letters
Persian does not share with Arabic (پ چ ژ گ), plus its own kaf `ک` U+06A9 and yeh `ی`
U+06CC.
**The authoritative variety is standard formal-written Persian (فارسی معیار نوشتاری)** —
books, news and official prose, where the copula is `است`, the verb is `می‌روم` and the
object marker is written `را`. Explicitly out of scope as *unlabelled* content in
`sentence`, `answer`, `translation` and `hint`: colloquial Tehrani (`میرم`, `میخوام`,
`میگه`, `اینو`, `رو` for `را`, `un` for `آن`, the suffixed copula `ـه`), plus Dari and
Tajik forms. Spoken Persian appears in exactly two places, both of which name it: the B2
point "Written vs. colloquial Persian (recognition)" and the C2 point "Register shifting:
deference and distance". The grader backs this up — `میرم` for `می‌روم` returns `WRONG`.
**Persian has no grammatical gender and no noun class**; `او` covers he and she, and
adjectives never agree. Nothing here should mark gender on a Persian noun.
Three things dominate drill quality:
1. **The ezafe is mostly unwritten.** `کتاب من` is read *ketab-e man*; the linking vowel
   appears only as ٔ after silent ه (`خانهٔ`) or ی after ا/و. Drills that "test the
   ezafe" usually test word order instead — see the gradeability trap below.
2. **The ZWNJ (U+200C) lives inside ordinary words** — `می‌روم`, `نمی‌دانم`, `بزرگ‌تر`,
   `کتاب‌ها`. `base.py` strips it on both sides (`_INVISIBLE`), so `نمیدانم` grades
   `CORRECT`; invisible characters are never coached. The data must still spell it right,
   because the ZWNJ is what the learner reads.
3. **Look-alike folding.** `PersianNLP.fold_lookalikes` runs `fold_arabic_script`: Arabic
   kaf ك ↔ Persian keheh ک, all yeh shapes, the heh family, alef seats, hamza carriers,
   tatweel, Arabic-Indic digits. A learner on an iOS Arabic keyboard gets
   `CORRECT_SLOPPY`, so a drill whose only contrast is ک↔ك or ی↔ي cannot be failed.

## Hint standards
Universal rules, once: a hint narrows the answer without containing it. Never the answer
as a whole word; never a gloss that already sits in the drill's own `translation`; never
the `answer — explanation` template; one hint resolves to exactly one answer inside a
point (allomorph sets excepted where the sentence disambiguates); hints are written in
English — quoting a base form in Persian script is fine, whole Persian sentences are not.

Persian-specific:
- **Do not quote both halves of a word split at the ZWNJ.** Two fragments that reassemble
  into the answer are a leak no whole-word regex catches. BAD, live in the file three
  times: `"answer": "نمی‌دانم", "hint": "don't know — نمی‌ prefixed onto می‌دانم"` —
  `نمی‌` plus `دانم` is the answer, printed in pieces. GOOD `don't know — the present of
  دانستن, negated`.
- **Never mark gender.** GOOD `the owner — "him/her"; the ezafe vowel is not written` for
  `او`. BAD `he (m.)` — Persian has no such category, and the invented contrast teaches a
  wrong fact.
- **Name person and number on any conjugated answer**, since that is the only thing the
  ending carries. GOOD `go — 2nd person singular, -ی ending`. BAD `go` in a point where
  `می‌روم`, `می‌روی` and `می‌رود` are all answers.
- **Label register whenever the answer is not neutral.** GOOD `is — the bureaucratic
  substitute for است` for `می‌باشد`; GOOD `said — the deferential verb that replaces
  گفتید` for `فرمودید`. BAD `is` / `said`, which make an administrative form look like
  the default.
- **Quote at most two Persian tokens, counting the ZWNJ as part of one token.** A scanner
  that splits on U+200C reads `نمی‌ … می‌دانم` as three tokens and mis-reports a
  hint-language violation; with the ZWNJ inside the token class the count is two — which
  is why the crawl's "3 Persian hints drift into target language" figure is an artefact.

## Question / drill standards
- **Formal written register, every field.** Full `است`, full `را`, full `می‌` forms,
  `آن`/`این` written out. The colloquial equivalent may appear only inside the two
  register points, and only as the thing being contrasted, never as the answer.
- **Exactly one blank**, on a whole word — **the blank cannot sit at a ZWNJ boundary.**
  `{{answer}}` is surrounded by spaces when rendered, so blanking a bound suffix forces a
  spelling the standard rejects: `کتاب {{answer}}.` with answer `ها` renders `کتاب ها.`,
  not `کتاب‌ها`. Blank the whole word (`کتاب‌ها`) instead.
- **The sentence must force the answer after folding.** Never build a drill whose only
  contrast is ک↔ك, ی↔ي, a hamza seat or the presence of a ZWNJ: all fold or strip, so the
  card cannot be failed.
- **Beware the ezafe gradeability trap.** `"answer": "خانهٔ"` grades `CORRECT_SLOPPY`
  against a plain `خانه` (the hamza is a combining mark, folded at layer 2.5), while
  `خانه‌ی`, the equally standard variant, comes back `WRONG` — the drill accepts the
  omission it exists to prevent and rejects a correct spelling. Add the variant as an
  accepted answer, or move the blank to a link that is a whole word.
- **Watch homographs before choosing a blank.** `در` is both "door" and the preposition
  "in": `"answer": "در", "hint": "door — the middle link…"` in `رنگ {{answer}} خانه سفید
  است.` is disambiguated only by its English.
- Every drill carries a `transliteration` (188/188) and it must match the *answer as
  spelled* — the plural point transliterates `ketabha.` over a sentence rendering
  `کتاب ها.`, so one of the two is wrong.

## Translation & definition standards
- No bare one-word gloss for a polysemous word. `شیر` is not "milk"; `کشیدن` is not
  "pull". Split the senses or name the one meant.
- **Gender is not marked, because Persian has none** — the field that must be carried
  instead is **register**: definitions for `نمود`, `گردید`, `می‌باشد`, `جهت`, `فرمودن`
  are wrong without "(formal/administrative)", and `فرمودید`/`تشریف` without
  "(deferential)". Arabic-origin broken plurals (`کتب`, `علما`) are glossed as plurals
  with their singular named.
- **Every translation must be a real sentence, not a citation form.** The plural point
  translates `کتاب {{answer}}.` as "books" — a bare noun against punctuated Persian.
- Register consistency: neutral English against neutral written Persian; deferential
  Persian gets a translation flagged "(deferential)", as the C2 point already does.

## Current measured state
`data/grammar/fa_grammar.json`: **41 points, 188 drills**, levels A1 11 / A2 10 / B1 8 /
B2 6 / C1 3 / C2 3, 188/188 transliterated. All 41 have `source: "ai"` and
**`reviewed: false` — zero points human-reviewed.** No `culture_note` on any point.

Mechanical rules, re-run against the file:
- Hint leaks (whole-word): **0**. Self-answering `answer — …` template: **0**. Empty
  hint/translation/explanation: **0**. Duplicate hint → two answers inside a point: **0**.
  Giveaway-by-gloss (≤3-word hint inside its own translation): **0**.
- **Hint-language rule: the crawl reports 3; the real count is 0 — trust the file.** All
  three are the `نمی‌دانم` / `نمی‌خواهم` / `نمی‌بینم` hints in "Negation with na- /
  nemi-". Tokenising without U+200C splits `نمی‌` and `می‌دانم` into three tokens and
  trips the ≥3 threshold; with the ZWNJ in the class it is two, the legitimate base-form
  convention. But these hints are **split leaks**, a separate and worse problem (`نمی‌` +
  `دانم` = the answer). Fix the hints, and fix the scanner's token class.
- ZWNJ discipline elsewhere is **good**: 65 `می‌`/`نمی‌` prefixes, all with U+200C, none
  spaced; `بزرگ‌تر`, `کوچک‌تر`, `بزرگ‌ترین`, `نامه‌ها` all correct.
- Ungradeable contrast: **1 point** — "Ezafe chains", whose `خانهٔ` answer cannot be
  failed (verified against `PersianNLP.check_answer`).

**Structural debt — this is a thin course.** No `fa_sentences.tsv` in either location;
`data/fa_frequency.tsv` is **90 rows** (its 21 noun rows carry no gender column — correct
for Persian, not a gap); no `fa_morphology.json`, no seed module. `data/gym/fa.json`
**does exist** (34 entries across Verb forms / Attachments / Constructions, every `point`
matching a real grammar title); the group brief said Persian has no gym — the file wins.

Worst offenders:
1. `"answer": "نمی‌دانم", "hint": "don't know — نمی‌ prefixed onto می‌دانم"` (plus the
   two siblings) — the answer handed over in two pieces, and the description is also
   wrong: `نمی‌` replaces `می‌`, it is not prefixed onto it.
2. `"sentence": "کتاب {{answer}}.", "answer": "ها", "translation": "books",
   "transliteration": "ketabha."` — a blank at a ZWNJ boundary forcing the spacing the
   point's own explanation calls the lesser variant, a bare-noun "translation", and a
   transliteration contradicting the rendered sentence. Two of its three drills also share
   the hint `plural — same suffix`, which says nothing.
3. `"sentence": "این خانهٔ {{answer}} است.", "answer": "ما"` ("Possession with ezafe") —
   shaped identically to its siblings, so only the English picks `ما` out of
   `من`/`تو`/`او`/`شما`; the hint `the owner — "us"` leans entirely on the translation.

## Testing checklist
- `python -m backend.services.quality.audit_content --language fa` — the automated
  checker (lands with this change; may not exist in your tree yet).
- There is no `test_nlp_persian.py`; `PersianNLP` is tested by `TestPersian` inside
  `.venv/bin/pytest backend/tests/test_nlp_latin.py -q` (3 cases: harakat, exact match,
  wrong word). It shares `arabic_script.py` with Arabic, so
  `.venv/bin/pytest backend/tests/test_nlp_arabic.py -q` covers the folding too. Neither
  file tests the ZWNJ or the ezafe hamza — open debt, and exactly where the bugs are.
- Persian is in `TRANSLIT_LANGS` (`frontend/src/features/keyboards/translit.ts`):
  `cd frontend && npx vitest run src/__tests__/translit`
- Human spot-check — 10 random drills read against the standards above. A drill fails if:
  a colloquial form appears outside the two register points; the hint quotes fragments
  that reassemble into the answer; the hint marks gender; a conjugated answer's hint omits
  person and number; a formal or deferential answer is glossed as if neutral; a ZWNJ is
  missing, spaced or replaced by a plain space; the blank sits at a suffix boundary; the
  translation is a citation form rather than a sentence; or the transliteration disagrees
  with the rendered sentence. Type the colloquial variant into the grader and confirm it
  is refused (`میرم` for `می‌روم` must be `WRONG`), then type the answer without its ZWNJ
  and confirm it is accepted silently.
