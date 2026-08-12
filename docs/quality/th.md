# Thai (th) — Content Quality Standards

## Language profile

Thai script, left-to-right, **written with no spaces between words**. An alphasyllabary: vowels wrap the
consonant (before it — เ, แ, โ, ไ, ใ — after, above, below, or several at once) and four tone marks
(่ ้ ๊ ๋) sit on the initial. **The authoritative variety is Standard (Central/Bangkok) Thai in polite
conversational register** — what a learner uses with a stranger, ครับ/ค่ะ available. **Out of scope:**
Isan, Northern (คำเมือง) and Southern varieties; crude pronouns (กู/มึง) as a *production* target; and
romanization as content — the seeder ships `reading: None` for every word on purpose
(`backend/services/seeder/seed_thai.py`), so no romanized tone spelling belongs in a gloss or hint.

**No gender and no noun class**, and no inflection at all: `ThaiNLP.lemmatize` is the identity function.
Two systems carry the load gender carries elsewhere — **classifiers** (a noun's counter is a lexical
property, as gender is in Spanish) and **speaker-indexed politeness** (ครับ/ค่ะ/คะ and pronoun choice
encode the *speaker's* gender, not any noun's). Those two plus **tone marks** dominate drill quality: a
space in a Thai sentence is a claim about clause structure, a wrong classifier is instantly audible, and
a contrast living only in a tone mark is coached by the grader, never enforced.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss
already sitting in the drill's own translation; never the `answer — explanation` template; one hint
resolves to exactly one answer inside a point (allomorph sets excepted where the sentence disambiguates);
hints are in English, and quoting a base form in Thai script is fine while whole Thai sentences are not.

**1. Politeness-particle hints name the speaker's gender *and* the sentence type.** Three particles live
in one point and ค่ะ/คะ differ only by tone mark, so "the polite particle" resolves to three answers.
- GOOD: `female QUESTION particle — high tone` for `คะ`; `the male politeness particle` for `ครับ`
  (both real, *Polite particles: ครับ and ค่ะ*). BAD: `the polite ending` — underdetermined across
  ครับ / ค่ะ / คะ, and the grader cannot break the tie.

**2. When two answers in a point differ only by a tone mark, the hint must say the tone or the sentence
type in words.** `check_answer` layer 2.5 strips combining marks of non-zero canonical class — all four
Thai tone marks (U+0E48–0E4B) plus ุ/ู — and returns `CORRECT_SLOPPY` ("Almost — check the accents"),
*even on grammar drills*: `คะ` typed for `ค่ะ` is amber, not wrong.
- GOOD: `female statement particle` vs `female question particle — high tone` (the file's real pair).
- BAD: `the female particle` on both — the drill silently accepts either spelling.

**3. Classifier hints name the semantic class covered, never the noun in the sentence, never the number.**
- GOOD: `classifier for people` for `คน`; `classifier for books` for `เล่ม` (real, *Classifiers*).
- BAD: `the counter in เพื่อนสองคน` — quotes the answer inside a Thai construction; and `counter word`
  alone, which fits all four classifiers in the point.

**4. No bare English gloss that already sits in the translation.** Thai's largest defect class: 52
one-word hints, 29 of them verbatim in the drill's own English. Grammar labels are the fix and are
already used well — `benefactive`, `prohibitive`, `there-is`, `causative` all pass.
- BAD (real): `still` for `ยัง` under *He is still working.* — GOOD: `the not-yet marker, before the verb`.
- BAD (real): `where` for `ที่ไหน` under *Where are you going?* — GOOD: `the place question word, sentence-final`.

**5. Quoting Thai in a hint: one or two base forms, never a sentence.** Seven hints quote Thai, all legitimate.
- GOOD (real): `with พอ — enough` for `แล้ว`; `the pair-word of บ้าน` for `เรือน`. BAD:
  `ระวังนะ เดี๋ยวโดนรถชน — the misfortune passive`, a whole Thai clause inside an English hint.

## Question / drill standards

A good Thai drill is a sentence a Thai would actually say, SVO, one blank fixed by sentence plus hint.

- **Spaces are a structural claim.** Permitted only at a clause or sentence boundary, around Latin
  digits/loanwords, or before a cited word. **Never inside a phrase.** 39 of 240 drills contain an
  internal space; most are correct topic/conditional boundaries (`ถ้าฝนตก เราก็ไม่ไป`,
  `เรื่องนี้ ผมไม่รู้จริงๆ`), one is not: `ไปกิน ข้าวกันไหม` splits กินข้าว. **ๆ attaches with no space**
  — the grammar file is consistent (11/11: `เด็กๆ`, `เร็วๆเข้า`), `data/th_sentences.tsv` is not (53
  attached, 35 spaced: `เร็ว ๆ`), and the drills set the standard.
- **Stage directions go in the English translation, not the Thai sentence.** 19 drills carry Thai-script
  scene-setting the learner cannot yet read — `(ผู้ชายพูด)`, `(ผู้หญิงถาม)` at A1,
  `เรียกพนักงานหนุ่มในร้าน:` at C1. The Thai side holds only what someone would say.
- **A polite particle belongs in the sentence only when the point is about politeness, requests or
  register — or when the translation names the speaker.** 11 drills carry one. `น้องครับ คิดเงินหน่อย`
  fixes a male speaker its translation ("Calling a young waiter") never mentions; the A1 politeness point
  does it correctly with "(male speaker)".
- **One blank, one word.** 0 of 240 drills have two blanks — keep it. Single-glyph answers (`เ`, `ๆ`, `ฯ`,
  `๓`) are allowed **only** in *Written Thai*, where the glyph is the content. Every form named in the
  title must be drilled; five points fail (อัน, หรือเปล่า, หรอก and two title phrases used as labels).
- **The sentence must force the choice.** `เชิญ{{answer}}ข้าวก่อนนะคะ` forces ทาน over กิน because เชิญ +
  นะคะ set the register. A bare `{{answer}}ข้าว` admits กิน, ทาน and รับประทาน.
- **Check the answer can be typed.** 30 of 96 distinct answers contain a letter the romanization scheme
  in `frontend/src/features/keyboards/translit.ts` cannot produce — ค (so `ครับ`, `ค่ะ`, `คะ`, `คน`,
  `คุณ`), ฉ, ถ, ผ, ญ, ใ, ็, ึ, ฯ, ๆ, ๓ — leaving the on-screen Thai keyboard or a system IME as the only
  route (already-Thai text passes through the encoder unchanged).

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** ผม is *I (male)* and *hair*; ที่ is *at*, *that/which*
  and *place*; ถูก is *cheap*, *correct* and the misfortune passive. The seeder's `TH_CURATED` does this
  for 71 high-frequency entries; the other 3,533 rows do not — 734 glosses are a single English word.
- **A noun definition names its classifier.** This is Thai's gender field and it is missing: of 1,987
  noun rows in `data/th_frequency.tsv`, **36 mention a classifier**, and the TSV has no classifier column
  (`rank / word / pos / en`). Classifiers are glossed as such — `คน — person; (classifier for people)`.
- **Register-set words state their rung**: `ทาน — to eat (polite)`, `รับประทาน — to eat (formal)`,
  `เสวย — to eat (royal)`; particles carry speaker gender: `ค่ะ — (female polite particle, statements)`.
- **Wrong-sense glosses are the top-of-file debt.** rank 8 `แต่` — *"each and every (one of), every single
  (followed by a classifier)"* (that is แต่ละ; แต่ is *but*); rank 11 `พระเจ้า` — *"buddha:; person who has
  achieved a state of perfect enlightenment"* (it is *God/Lord*). 77 rows are raw dictionary-speak.
- **English translations translate, and never print the Thai answer** (three do). Register stays
  consistent across sentence and translation: a ครับ sentence is not rendered as slang.

## Current measured state

Verified by opening `data/grammar/th_grammar.json`, not taken from the crawl.

- **40 points / 240 drills**, six each — A1 12, A2 10, B1 8, B2 6, C1 2, C2 2. **Every point is
  `source: "ai"`, `reviewed: false`**: the whole Thai course is unreviewed generated content. No empty
  fields, no duplicate hints in a point, no multi-blank drills, no `answer — explanation` templates.
- **Hint leaks: 0.** Target-script drift **0** by the ≥3-token rule; the 7 hints quoting one or two Thai
  forms all read well. **One-word hints: 52** (crawl agrees; 72 by whitespace words, since `cold/cool`
  and `don't-have-to` split into several `\w+` tokens). **Gloss giveaways: 29** by the ≤3-word rule the
  crawl quotes, **23** by the checker's stricter ≥4-character rule — different rules, not a disagreement.
- **Thai-specific counts, measured here:** 39/240 drills contain an internal space (1 mid-phrase); 19
  carry a Thai stage direction; 3 translations print the Thai answer; 5 points name a form they never
  drill; 30/96 answers are unreachable by romanized typing; the one tone-minimal answer pair (ค่ะ / คะ)
  is folded by the grader to `CORRECT_SLOPPY`.
- **Corpora:** `data/th_sentences.tsv` 4,037 rows (236 with internal spaces, 38 ending in a polite
  particle); `data/th_frequency.tsv` 3,604 rows; **no morphology json** — right for an isolating
  language, but nothing backs a classifier check; **no Gym manifest**, as the crawl reports.
- **Worst offenders:**
  1. `ไปกิน ข้าวกันไหม — ตอบรับ: {{answer}}` (*Yes/no questions*, A1) — one drill breaking two rules: a
     space inside กินข้าว, and a Thai-script instruction (`ตอบรับ:`) inside an A1 sentence.
  2. `สระ {{answer}} เขียนหน้าพยัญชนะ เช่น เมา` → *"…the vowel เ- …"* — the translation prints the answer.
  3. `ยัง` hinted `still` in all three of its drills (*He is still working.*, *It is still raining.*,
     *Are you still angry with me?*) — one word, zero information beyond the translation.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language th
python -m backend.services.quality.audit_content --language th --sample 10
.venv/bin/pytest backend/tests/test_nlp_thai.py -q
cd frontend && npx vitest run src/__tests__/translit
```

`th` is in `TRANSLIT_LANGS`, so the transliteration suite is mandatory: it pins the wrapped-vowel
templates (`me` → เม, `mae` → แม, `mia` → เมีย), the digit-tone convention (`maa2` → ม้า) and idempotence
on already-Thai text; any answer must survive `convertTranslit`/`finalizeTranslit` unchanged.
`test_nlp_thai.py` covers the greedy longest-match segmenter — the only thing between a spaceless
sentence and the difficulty scorer. A human reviewer pulls 10 random drills and asks, in order:

1. **Is there a space, and does it sit on a clause boundary?** Anything mid-phrase fails
   (`ไปกิน ข้าวกันไหม`); a space before ๆ fails.
2. **Could I answer this knowing no Thai?** Cover the Thai and read hint + translation. `still` under
   *He is still working.* — yes, a failure; 29 drills fail this today.
3. **Is any Thai in the sentence not part of what the speaker says?** Stage directions and
   `(ผู้ชายพูด)`-style notes belong in the translation; 19 drills fail.
4. **Classifier drill — does the hint name the class, and is that classifier the only right one?**
5. **Politeness drill — do hint and translation together fix speaker gender *and* statement vs
   question?** If not, the tone-folding grader accepts the wrong particle. And does a polite particle
   already in the sentence match the speaker the translation implies?
6. **Can the answer be typed?** If it contains ค, ฉ, ถ, ผ, ญ, ใ, ็, ึ, ฯ, ๆ or a Thai digit, the
   romanization path cannot reach it — confirm the on-screen keyboard is the intended route.
7. **Does the point drill every form its title promises?** อัน, หรือเปล่า and หรอก currently do not.
