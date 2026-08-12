# Korean (ko) — Content Quality Standards

## Language profile

Hangul, left-to-right, written in **syllable blocks**: an initial consonant, a medial vowel and an
optional final consonant (**받침**) fuse into one character. Blocks, not letters, are what a learner
types, reads and is graded on. **The authoritative variety is Standard Korean as codified in Seoul
(표준어)**, in the polite **해요체** as the default production register. **Explicitly out of scope:**
North Korean 문화어, regional dialects (경상/전라/제주), Hanja beyond words that require it, and
반말/해체 as a *production* target — learners read it (the C1 plain-style point, the sentence corpus)
but are never asked to produce it.

**No gender and no noun class.** Korean marks nothing on nouns for gender; the axis that replaces it is
**speech level**, and every drill implicitly picks one. Three features dominate drill quality:
(1) **받침-conditioned allomorphy** — 은/는, 이/가, 을/를, 이에요/예요, (으)세요, (으)면, (으)러 choose by
whether the preceding word ends in a final consonant, so a hint giving the meaning but not the condition
has taught nothing (31 of 240 hints name it, and that is the model); (2) **speech level** — 해요체 /
합니다체 / 한다체 / 반말 are four ways to say one sentence, and the translation must show which;
(3) **typing** — `ko` is in `TRANSLIT_LANGS`, and the IME's batchim decisions are *provisional*.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss
already sitting in the drill's own translation; never the `answer — explanation` template; one hint
resolves to exactly one answer inside a point (allomorph sets excepted where the sentence
disambiguates); hints are in English, and quoting a base form in Hangul is fine while whole Korean
sentences are not.

**1. Allomorph hints name the 받침 condition, not just the meaning.** Two drills may share an answer, but
the hint must let the learner *derive* which one the sentence needs. Say 받침 — the grader says it too.
- GOOD: `subject marker — 물 ends in a consonant` for `이` (real, *Subject particle 이/가*)
- BAD: `subject marker` alone for `이` and `가` — underdetermined, and the batchim coaching cannot fire
  on this pair (은/는, 이/가 differ in the medial, not the final), so there is no second chance.

**2. Quote the dictionary form, never the drilled form, and stop at two Hangul tokens.** Citing `마시다`
teaches the lemma → form step; three or more (jamo included) is drift — 13 hints are over the line.
- BAD: `to study (공부하다) — 하다 becomes 해요` — GOOD: `to study — a 하다 verb in the polite present`
- BAD: `돕다 — the ㅂ melts into 오/와` for `도와요` (4 tokens) — GOOD: `돕다 — a ㅂ-irregular: the final
  consonant turns into a vowel`

**3. Never quote the morpheme being drilled.** Both leaks are this.
- BAD: `the longer negative: verb stem + 지 않아요` for `지` — GOOD: `the longer negative — one syllable
  joins the stem to 않아요`
- BAD: `있다 stays bare in the plain style` for `있다` — GOOD: `the existence verb keeps its dictionary
  shape in the plain style`

**4. Closed-class answers get a grammatical description, not the English word already sitting in the
drill's translation** — eight hints fail this, and three more are an unfinished `?` placeholder
(`'one' shortens before a counter (하나 → ?)`, `the catch-all causative: 게 + ?`).
- BAD: `'where'` for `어디` under *Where are you going?* — GOOD: `the place question word, used with 에`
- BAD: `'than'` for `보다` under *The subway is faster than the bus.* — GOOD: `attaches to the loser in
  a comparison`

**5. Honorific hints say which direction the respect runs** — raise the subject (께서, 시) or lower the
speaker (드리다, 뵙다), never both in one breath.
- GOOD: `주다 lowered to its humble form, past` for `드렸어요` (real, *Honorific machinery*)
- BAD: `말하다 upgraded twice: 말씀 + 시, past` for `말씀하셨어요` — GOOD: `말하다 with the honorific noun
  and 시, past`

## Question / drill standards

A good drill is a sentence a Korean would say, verb-last, with one blank fixed by sentence plus hint.

- **Default register is 해요체.** Another level is allowed only in a point *about* that level: 합니다체
  in *Formal style ㅂ니다/습니다* and the formal 겠 drills; 한다체 in *Plain written style*, *Formal
  written connectives*, and inside quoted clauses (`온다고 해요`). 반말 is never the answer. **A
  non-해요체 drill says so in its translation** — as the file does: *"(formal)"*, *"(news style)"*.
- **The sentence must force the choice, not merely permit it.** `다리를 다쳐서 {{answer}} 가요.` forces
  못 over 안 because the cause clause rules out choice; a bare `{{answer}} 가요` admits both.
- **One blank, one constituent.** Particle blanks attach to the noun with no space
  (`저{{answer}} 학생이에요.`); verb blanks take the whole inflected word, not a fragment.
- **The register contrast is not strictly graded.** `KoreanNLP.lemmatize` folds polite and formal
  endings onto one lemma, so `먹어요` typed for `먹습니다` returns `CORRECT_SLOPPY` while `가요` for
  `갑니다` returns `WRONG` — asymmetric between consonant and vowel stems. A register point cannot lean
  on the grader; the hint must name the register in words.
- **Answers must be typeable and NFC-composed.** Learners type romanization (`hanguk` → 한국; aspirates
  are plain `k t p ch`, lax are `g d b j`, doubling tenses them) and a trailing consonant commits as the
  받침 **immediately** — `bap` renders 밥, and the next vowel re-opens it (`bapa` → 바바, `banga` → 반가).
  An aspirated initial after a closed syllable therefore needs `kha/tha/pha/cha` or the `-` syllable
  break (`ba-ka` → 바카; `han-a` → 한아 where `hana` is 하나), which disappears on submit. Keep answers to
  composed blocks — 0 of 240 contain a bare jamo; jamo in titles (`(으)ㄹ`) is prose and fine.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** 배 is *belly*, *boat* and *pear*; 쓰다 is *write*,
  *use*, *wear*, *bitter*; 타다 is *ride* and *burn*. The gloss names the sense in play.
- **No gender marking is required** — Korean has none, and `ko` is correctly outside the checker's
  `GENDERED` set. The equivalent obligation is **speech-level marking**: `뵙다 — to meet (humble, of a
  superior)`, `드시다 — to eat (honorific)`.
- **Verb definitions cite the 다 form** and add the polite present when the stem is irregular
  (`듣다 (듣 → 들어요) — to listen`); **counters name what they count** (`권 — counter for books`), and
  the native vs Sino-Korean numeral series is stated, never assumed. English translations stay neutral
  modern English; the Korean side stays 해요체 unless the point is about another level.

## Current measured state

- **`data/grammar/ko_grammar.json` — verified on disk: 40 points, 240 drills**, six each; A1 12 / A2 10
  / B1 8 / B2 6 / C1 2 / C2 2; register 217 해요체 / 12 plain / 10 합니다체 / 1 `-는데요`. **Every point
  is `source: "ai"`, `reviewed: false`** — the whole Korean course is unreviewed generated content, the
  largest single fact here. No empty fields, no duplicate hints, no self-answering or multi-blank drills.
- **Hint leaks: 2** — `지` hinted `the longer negative: verb stem + 지 않아요`; `있다` hinted `있다 stays
  bare in the plain style`. **Target-script drift: 13 hints with ≥3 Hangul tokens beyond the answer**,
  the course's worst: `돕다 — the ㅂ melts into 오/와` (4), `to study (공부하다) — 하다 becomes 해요`,
  `말하다 upgrades to 말씀하다 + 세요`. Nine are the ㅂ/ㄷ-irregular and 하다 families — one habit, not 13.
- **Correction to the crawl:** it reports `hint-in-translation 0`; on the file the real count is **8**.
  Every Korean gloss hint sits inside single quotes (`'where'`, `'who'`, `'than'`), and the quotes
  defeated the checker's word boundary. Strip them and *Question words* fails five of six (`'where'` /
  *Where are you going?*, `'who'`, `'when'`, `'why'`, `'how'`), *있어요/없어요* two, *Comparing* one —
  real giveaways, not an artefact. **One-word hints: 10** (crawl agrees): those five plus `'have'` ×2,
  `'also'`, `'more'`, `'than'` — no grammar labels among them, so all ten need rewriting.
- **Grading, verified by running `backend/services/nlp/korean.py`:** `_differs_only_in_batchim` fires on
  바/밥 and 안/않 (*"check the final consonant (받침)"*), not on 법/밥, never on 은/는 — hence hint rule 1.
- **Corpora:** `data/ko_sentences.tsv` 3771 rows, no curated `data/sentences/ko_sentences.tsv`;
  `data/ko_frequency.tsv` 7054 rows; `data/gym/ko.json` present; **no `data/ko_morphology.json`** at
  all, so nothing backs the Gym charts or a gloss-level check.
- **Corpus register mismatch (the biggest content risk).** Of 3771 sentences only **699 (19%) are
  해요체**; 1181 plain, 445 합니다체, and **1446 outside all three — sampled, they are 반말**:
  `난 고양이 동영상에 질렸어.`, `너는 여자가 좋아?`. The course teaches 해요체 from A1, then feeds A1
  readers unlabelled intimate speech.
- **Definition debt:** 1761 of 7054 frequency glosses (25%) are one word, and the top of the file is
  wrong: rank 2 `우리` *"cage, pen, coop, enclosure"* — the wrong homograph for the second commonest word
  in the language (*we/us*); rank 100 `자` *"10²⁴"*; rank 37 `게` *"crab"*.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language ko
python -m backend.services.quality.audit_content --language ko --sample 10
.venv/bin/pytest backend/tests/test_nlp_korean.py -q
.venv/bin/pytest backend/tests/test_typed_input.py -q -k Korean
cd frontend && npx vitest run src/__tests__/translit
```

The transliteration suite pins the provisional-batchim contract (`bap` → 밥, `bapa` → 바바, `banga` →
반가), the lax-final round trip (`gada` → 가다, not 가타) and the `-` break; every answer string must
survive `convertTranslit`/`finalizeTranslit` round-tripping it unchanged, and
`test_typed_input.py::TestKoreanBatchimCoaching` pins the 받침 message. A human reviewer pulls 10 random
drills (`--sample 10`) and asks, in order:

1. **Does the hint contain the answer, its morpheme, or ≥3 Hangul tokens?** `verb stem + 지 않아요` for
   `지` is the template to stop copying.
2. **Could I answer this knowing no Korean?** Cover the Hangul and read hint + translation: `'where'`
   under *Where are you going?* — yes, a failure; eight drills fail this today.
3. **Allomorph answer — does the hint name the 받침 condition?** `subject marker after a consonant`
   passes; `subject marker` alone does not.
4. **What speech level is it, and does the translation say so?** Not 해요체 and unmarked fails.
5. **Can the answer be typed?** Run the romanization in your head — needing `-` or `kha/tha/pha` is
   fine, a loose jamo in the answer field is not.
6. **Honorific drill — is the respect pointed the right way?** 시/께서 on the respected subject,
   드리다/뵙다 on your own action; never 시 on the learner's own verb.
