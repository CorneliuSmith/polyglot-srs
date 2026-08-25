# Persian (fa) — Content Quality Standards

## Language profile
Perso-Arabic script, right-to-left, cursive with positional letter forms; four letters
Persian does not share with Arabic (پ چ ژ گ), plus its own keheh `ک` (U+06A9) and yeh `ی`
(U+06CC).
**The authoritative variety is standard formal-written Persian (فارسی معیار نوشتاری)** —
books, news, official prose: the copula is `است`, the verb is `می‌روم`, the object marker is
written `را`. Explicitly out of scope as *unlabelled* content in `sentence`, `answer`,
`translation` and `hint`: colloquial Tehrani (`میرم`, `میخوام`, `میگه`, `اینو`, `رو` for
`را`, `اون` for `آن`, the suffixed copula ـه), plus Dari and Tajik forms. Spoken Persian
appears in exactly two places, both of which name it: the B2 point "Written vs. colloquial
Persian (recognition)" and the C2 point "Register shifting: deference and distance" — and a
sweep for the usual colloquial spellings finds none anywhere else in the file.
**Persian has no grammatical gender and no noun class**: `او` covers he and she, adjectives
never agree, and nothing in this course should mark gender on a Persian noun (currently 0
hints do — keep it that way). Three things dominate drill quality:
1. **The ezafe is mostly unwritten.** `کتاب من` is read *ketab-e man*; the linking vowel
   surfaces only as ٔ after silent ه (`خانهٔ`) or ی after ا/و. A drill that claims to test
   the ezafe usually tests word order — see the gradeability trap below.
2. **The ZWNJ (U+200C) lives inside ordinary words** — `می‌روم`, `نمی‌دانم`, `کتاب‌ها`,
   `بزرگ‌تر`. `check_answer` strips invisibles on both sides (`_INVISIBLE` in
   `backend/services/nlp/base.py`), so `نمیدانم` grades `CORRECT` and is never coached. The
   data must still spell it correctly, because the ZWNJ is what the learner *reads*, and any
   tooling that scans this file must include U+200C in its token class or Persian words split
   into pieces.
3. **Look-alike folding.** `PersianNLP.fold_lookalikes` runs `fold_arabic_script`: Arabic kaf
   ك ↔ Persian ک, every yeh shape, the heh family (including ۀ), alef seats, hamza carriers,
   tatweel, Arabic-Indic digits. A learner on an iOS Arabic keyboard gets `CORRECT_SLOPPY`,
   so a drill whose only contrast is ک↔ك, ی↔ي or ه↔ۀ cannot be failed.

**584 → 2,996 rows (24 Aug 2026).** Hand-added by `2d7ce7f`, no pipeline; now built from `pes_wikipedia_2021_100K` (Leipzig, CC-BY) plus the Persian kaikki extract. 152 proper nouns dropped.

**Two high-frequency rows were resolved to the wrong lexeme and are corrected**: rank 586 `کرد` came back glossed simply **"Kurd"**, when at that frequency it is the past stem of `کردن` "to do" — the commonest verb in the language. Rank 585 `شد` was a bare form-of pointer. Both now name the verb and keep the secondary sense. Same class as English `be`/beryllium and Tagalog `isang`/Isabel.

**Four rows removed**, recorded in `data/vocab_exclusions.tsv`: `مثلاً` and `سؤال` are tanwin- and hamza-seat spellings of `مثلا` and `سوال`, the same words twice; `راس` was a pointer carrying no meaning; and `ابی` was glossed with a slur by Wiktionary when at rank 2951 in a Wikipedia corpus it is the unpointed form of `آبی` "blue". The collision ratchet is 5 — all genuine contrastive pairs (`آن`/`ان`, `آبی`/`ابی`, `رأی`/`رای`).

## Hint standards
Universal rules, once: a hint narrows the answer without containing it. Never the answer as a
whole word; never a gloss that already sits in the drill's own `translation`; never the
`answer — explanation` template; one hint resolves to exactly one answer inside a point
(allomorph sets excepted where the sentence disambiguates); hints are written in English —
quoting a base form in Persian script is fine, whole Persian sentences are not.

Persian-specific:
- **Never name the affix and quote the base in the same hint.** Persian negates and
  aspect-marks by prefixing, so this pattern reconstructs the answer while passing every
  whole-word leak check. BAD (real, `برفت`): `went — the literary form of رفت, with its بـ
  prefix` — ب + رفت is exactly the answer. GOOD: `went — the older narrative form of this
  verb, one letter longer than the modern past`.
- **Quote at most one base form, and only if the answer is not built out of it.** GOOD (real,
  `بیاید`): `come — subjunctive of آمدن after شاید`. BAD (real, `نمی‌دانم`): `don't know —
  نمی‌ prefixed onto می‌دانم`, which prints both halves of the answer *and* is wrong: the ن
  attaches in front of the می that is already there, it is not stacked onto a second می.
- **Name person and number, never gender.** GOOD (real, `نمی‌تواند`): `can't — the negative,
  3rd person singular`. BAD: `can't — 3rd person feminine`; Persian has no such form and the
  hint invents a distinction.
- **Say which register the answer belongs to when the point is about register.** GOOD (real,
  `گردید`): `became — the formal counterpart of شد`. BAD: `became`, which leaves the learner
  choosing between `شد` and `گردید` with nothing to go on.
- **Ezafe hints describe position, not the vowel.** GOOD (real, `دوست`): `friend — the
  possessed thing comes FIRST, the owner second`. BAD: `friend-e`, mixing romanization into
  the hint.
- **Spell the ZWNJ correctly whenever a hint quotes a می-form**, and never make the ZWNJ
  itself the thing under test — it is stripped before comparison, so it can never be failed.

## Question / drill standards
- **Formal written Persian in every field**, including transliterations: `man farda be khane
  miravam`, not `miram`. No `رو` for `را`, no `ـه` copula, no `اون/این` spoken shortenings —
  outside the two labelled register points.
- **Exactly one unambiguous blank.** Persian's SOV order means a sentence-final blank is
  almost always the verb; if two verb forms fit the frame, the translation must choose
  between them ("I'm going home tomorrow" vs "I went home" resolves tense, not politeness —
  add "(deferential)" the way the C2 point does).
- **The gradeability trap: the ezafe.** `این کتاب {{answer}} است.` does not test the ezafe,
  it tests which pronoun owns the book. The only written-ezafe answer in the file is `خانهٔ`
  ("Ezafe chains", drill 1) — and `ٔ` is U+0654, a combining mark, so `_strip_marks` makes a
  bare `خانه` grade `CORRECT_SLOPPY`, and `ۀ` folds to `ه` besides. Write the ezafe correctly
  for display, but do not build a pass/fail contrast on it; test the *order* of the chain,
  which is what the existing drills actually do well.
- **Don't blank `را` more than the point needs.** All three drills in "Ra marks a definite
  direct object" answer `را` with near-identical hints; each drill must add something (after
  which noun, why the object counts as definite), or the point is one drill three times.
- **Light verbs are one unit.** `کار کردن`, `حرف زدن`: blank the verbal half or the nominal
  half, never half of the nominal half, and let the translation show the whole idiom.
- **Recognition points stay recognition.** The C1/C2 literary and classical points exist to be
  read; their drills must be answerable from context, and their explanations must say the form
  is not for modern writing (the current ones do).

## Translation & definition standards
- **No bare one-word gloss for a polysemous word.** `شیر` is milk, lion and tap; `دوست` is
  friend and (with `داشتن`) to like. 53 of the 90 rows in `data/fa_frequency.tsv` are
  one-word glosses — `کار | work; job` is the right shape, `غذا | food` needs "meal, dish"
  to be usable.
- **No gender marking on Persian nouns**, ever — it is the single most common
  cross-contamination when a course template is copied from Arabic or a Romance language.
  What a Persian noun definition *does* need instead: animacy where it selects the plural
  (`ـان` for people vs `ـها` generally) and the counter word where one is idiomatic (`تا`).
- **Arabic-origin plurals belong in the definition** (`کتاب` → `کتب` beside `کتاب‌ها`), since
  there is no `fa_morphology.json` to look them up in.
- **Register consistency.** Gloss the written-standard sense; a colloquial equivalent is
  labelled ("spoken: …") or omitted. A definition never mixes formal and Tehrani spelling.
- **A translation translates.** It renders the whole sentence, and where politeness is the
  point it says so — "(deferential)", "(intimate)" — because English cannot show it otherwise.

## Current measured state
From the crawl and re-verified against `data/grammar/fa_grammar.json` (2026-08-12):

- **41 grammar points / 188 drills**, A1 11 · A2 10 · B1 8 · B2 6 · C1 3 · C2 3.
  Every point is `"source": "ai"` and **`"reviewed": false` — 0 of 41 human-reviewed.**
- **Fail-level violations: 0 whole-word hint leaks, 0 empty hints/translations/explanations,
  0 one-word hints, 0 duplicate hints within a point, 0 gloss-repeats, 0 `answer —
  explanation` templates.** Mechanically the cleanest pair of files in the repo alongside he.
- **Correction to the crawl.** It reports "3 hints carry ≥3 Arabic-script tokens beyond the
  answer". Opening the file, that is a scanner artifact: the three hits are the `نمی‌`
  negation hints, and they only reach three tokens because the scanner's character class
  omits U+200C, splitting `می‌دانم` into `می` + `دانم`. With the ZWNJ included, no hint in
  the file exceeds **two** quoted tokens — the legitimate base-form convention. Trust the
  file; the crawl's own rule text already flags this guard.
- **The real hint debt is the affix+base pattern the leak regex cannot see: 12 hints quote a
  Persian token contained in their own answer, and 4 of them reconstruct it.** Worst
  offenders: `برفت` ← `went — the literary form of رفت, with its بـ prefix` (ب + رفت =
  the answer); `نمی‌دانم` ← `don't know — نمی‌ prefixed onto می‌دانم` (and the same shape for
  `نمی‌خواهم`, `نمی‌بینم`), which is also morphologically wrong as written.
- **ZWNJ discipline is good**: 47 answers and 29 sentences carry U+200C, spelled correctly;
  the grader strips it, so it is display-correctness, not gradeable content.
- **All 188 drills carry a `transliteration`**, and the sampled ones stay in the written
  register (`miravam`, not `miram`) — including inside the colloquial-recognition point,
  which is correct.
- **Structural debt (the honest headline).** No sentence bank (`fa_sentences.tsv` exists
  neither in `data/` nor `data/sentences/`), no `fa_morphology.json`, and
  `data/fa_frequency.tsv` is **90 rows** — 21 nouns, 17 verbs — where a real course wants
  thousands. Everything beyond the 188 drills is generated on demand.
- **Correction to the brief:** fa was described as having no gym. It does —
  `data/gym/fa.json` carries 34 entries in 3 columns (Verb forms 13, Attachments 9,
  Constructions 12) and every `point` resolves to a real grammar-point title.

## Testing checklist
- `python -m backend.services.quality.audit_content --language fa` — the automated checker
  (lands with this change; may not exist in your tree yet).
- There is no `test_nlp_fa.py`; the Persian backend is covered by
  `.venv/bin/pytest backend/tests/test_nlp_latin.py -q -k Persian`,
  `.venv/bin/pytest backend/tests/test_typed_input.py -q -k Persian` and
  `.venv/bin/pytest backend/tests/test_csv_importer.py -q -k farsi`.
- Persian is in `TRANSLIT_LANGS` (`frontend/src/features/keyboards/translit.ts`):
  `cd frontend && npx vitest run src/__tests__/translit` — the Persian cases live in
  `src/__tests__/translitHebrewPersian.test.ts`.
- Human spot-check. A reviewer pulls **10 random drills** and asks, per drill: does the hint name a prefix
(`بـ`, `نمی‌`, `می`) *and* quote the base it attaches to? Does any hint or field mark gender
on a Persian word? Is a colloquial spelling present outside the two register points, in any
field including `transliteration`? Does the drill claim to test the ezafe while blanking a
pronoun — or rest on `خانهٔ` vs `خانه`, which can only grade amber? Is `را` blanked three
times with the same hint? Are the ZWNJs present where standard spelling wants them? Any "yes"
to the first five, or "no" to the last, fails the drill.

## Wrong-lexeme sweep, top 2000 (25 Aug 2026)

**18 rows reglossed, 9 of them fatal** — the card named a genuinely
different word. This course was not in the first sweep of the 16 well-resourced courses; it
was screened afterwards so that every course with a kaikki extract is covered. Found by
`audit_wrong_lexeme`, decided by a maker–checker pass against each row's full kaikki sense
inventory and the course's own sentences. See `docs/quality/CHECKS.md` §3b.

| rank | word | now reads |
| --- | --- | --- |
| 607 | `داد` | gave — past stem of دادن (انجام داد "he carried out", نشان داد "he showe |
| 617 | `گرفت` | took, seized — third-person singular past of گرفتن (قرار گرفت "was situa |
| 676 | `رسید` | arrived, reached — third-person singular past of رسیدن (به قدرت رسید "ca |
| 771 | `دیده` | seen — past participle of دیدن (دیده می‌شود "is seen", آسیب‌دیده "damage |
| 790 | `رو` | face, surface; side — the short form of روی (رو به "facing, toward", روب |
| 905 | `بدست` | by, at the hands of (کشف شده بدست… "discovered by…"); by hand, into the  |

Fixes are in `data/gloss_overrides.tsv` as well as `data/fa_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit is undone by the next seed.
