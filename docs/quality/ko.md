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

- **`data/grammar/ko_grammar.json` — 156 points, 1,217 drills** (measured 19 Aug 2026);
  A1 41 / A2 68 / B1 35 / B2 7 / C1 3 / C2 2 — an A1/A2-heavy course, not a pyramid. Drills per point
  vary; the old "six each" no longer holds. **Every point is `source: "ai"`, `reviewed: false`**
  *This line read "verified on disk: 40 points, 240 drills, six each" until 19 Aug, understating the
  course by a factor of five. The register split quoted below was counted against those 240 drills and
  has not been recounted — treat it as indicative, not measured.* — the whole Korean course is unreviewed generated content, the
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

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**11 rows reglossed**, of which **9 were fatal** — the card named a
genuinely different word, not merely an incomplete one. Found by
`audit_wrong_lexeme` and decided by a maker–checker pass against each row's full
kaikki sense inventory and the course's own sentences.

The cause is structural, not clerical: a rank is earned by whatever string appeared in
running text, and where a spelling is both an inflection of a common verb and a separate
dictionary word, the sense-picker could take the dictionary word. See
`docs/quality/CHECKS.md` §3b.

The worst of them, by rank:

| rank | word | now reads |
| --- | --- | --- |
| 14 | `좀` | a little, a bit (short for 조금); also the softener in a request or command, r |
| 37 | `게` | the fact that, the one that — 것이 contracted (거 plus the subject marker 이), a |
| 40 | `해` | do, does, do it — 하다 in the intimate style (다시 해, do it again), and the base |
| 51 | `걸` | the fact that, the one that, as object — 것을 contracted (거 plus the object ma |
| 164 | `와` | come, come here — 오다 in the intimate style; and, with (the particle after a  |
| 211 | `하면` | if one does, when one does — 하다 with the conditional -(으)면 (어떻게 하면, how can  |
| 252 | `본` | seen, that one saw — 보다 in the past determiner form; also the -아/어 본 적 있다 pa |
| 264 | `볼` | will see, to see — 보다 in the -(으)ㄹ determiner form (볼 수 있어요, can see); a che |

Fixes are in `data/gloss_overrides.tsv` as well as `data/ko_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang ko --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.

### Extended to rank 2000 (25 Aug 2026)

The sweep above covered the top 500. Ranks 501-2000 added **5 rows, 4 fatal**, so the
course total is **16 repaired (13 fatal) through rank 2000**.

The keep rate rose with rank — roughly 30% of candidates were kept in the top 500 against
about 50% below it — which is the expected shape and a check on the pass: deeper in a
frequency list the lexical sense genuinely is more often right, and an over-eager rewrite
would replace a correct gloss with a wrong one.

| rank | word | now reads |
| --- | --- | --- |
| 637 | `타` | get in, get on, ride — 타다 in the intimate style (차에 타, get in the car; 모 |
| 639 | `보기` | seeing, looking, the sight of something — 보다 nominalized with -기 (보기 좋아요 |
| 1149 | `드릴` | to give, to offer (humble, to someone senior) — 드리다 in the -(으)ㄹ determi |
| 1352 | `마실` | to drink, (something) to drink — 마시다 in the -(으)ㄹ determiner form, alway |

## Phase 2d–3 pass (7 September 2026)

Measured and changed in the quality-parity passes of 6–7 September; figures
re-measured from the repository on 7 September.

- **Definitions.** The top 200 were read by a reader of Korean and
  **73 repaired** through `scripts/apply_gloss_overrides.py`; a second
  reader accepted or corrected every one it saw. Faults found: wrong sense 27, reaches a synonym 25, not a definition 20.
  93 of the top 200 now carry a hand-written definition — a low
  count means the extracted glosses were already right, not that the band
  was skipped.
- **Hints.** **0 drill hints** that gave away their answer — sitting
  inside their own translation, or only the agreement feature the drill
  tests — rewritten through `scripts/apply_drill_hints.py`.
- **Headwords.** **8 removed** to `vocab_exclusions.tsv` (letters,
  punctuation, extraction debris, rare twins of common words). Production
  retires them on the next `reconcile --apply` (migration 20261016).
- **State.** 47% of the top 1,000 have a sentence the card can
  actually blank; 100% of drills carry an interlinear gloss;
  0 fail-level audit findings; a top-2,000 card is bad — no
  usable sentence, or a fragment drawn — 82% of the time.

**받침 allomorph pairs stay TWO cards, unlike Turkish harmony (7 Sep 2026).**
`이/가`, `은/는`, `을/를` are conditioned by the preceding syllable's final
consonant, and hint standard 1 already says the hint names that condition
("subject marker — 물 ends in a consonant"). A vocabulary card has no
sentence to point at, so its definition states the general condition
("the subject marker attached after a vowel") — knowing that rule IS
knowing the word, and the two members differ in the medial, not a vowel
class that harmony computes. Turkish `mi/mı/mu/mü` went the other way (one
card, the sentence fixes the shape, a wrong shape is the right word graded
sloppy — tr.md, CHECKS §30) because there the definition naming the vowel
class hands over the answer. Do not "harmonise" the two courses.

Rules this pass added, all 27 courses: CHECKS §24a (the prune reaches thin
rows whatever their source), §26 (the card rotates — a fragment's exposure is
its share of the pool), §28 (definition plus sentence must determine one
string), §29 (a sentence the card cannot blank is not coverage).

## Four topics were taught twice; five points are retired (8 Sep 2026)

Seven groups of points share a form in their title. Two readers judged
each against this file and the drills: four groups are duplicates, three
are not (`~ㄹ/을 것이다` future against conjecture, `~아/어지다` on a verb
against an adjective, present against past `이다/아니다` — a learner must
choose between the members, so each pair stays). Keepers: `~는/은 and ~이/가
revisited: nuance and form`, `동안: 'for' a time and 'during' a noun`,
`Korean suffix: ~스럽다`, `~아/어 있다: being in a state`.

**What decided it was answer accuracy, not size.** The retired
`~는/은 vs ~이/가: general statements…` point gets the 받침 rule it exists to
teach wrong in three of eleven drills (`라면는`, `다이아몬드은`, `청구서이`),
each filed in a cell asserting the opposite. The keeper had one such error
of its own (`여름 날씨은`) and was corrected in the same change. Every 받침
in the group was checked by hand.

Retiring a grammar point needed a path that did not exist — migration
20261017 and `data/grammar_exclusions.tsv`, mirroring vocabulary's. Full
record: `docs/decisions/2026-09-08-korean-duplicate-points.md`.

**The sixth duplicate, closed 10 Sep 2026.** Index 40 (`Topic particle
~는/은`, A1) was the same point as index 0 and got its own terminology
wrong: its function note read "Mark the subject (main person/thing) of a
sentence" and all seven hints said "subject-marking particle". 은/는 is the
TOPIC particle; 이/가 is the subject particle, and this course teaches the
distinction at `있다 with ~이/가` — where its own drill 나는 커피가 있어요 has
the topic 나는 and the subject 커피가 in one sentence. Retired on the same
criterion as the other five (answer accuracy, not size): the seven drill
answers were correct, so they were salvaged into the keeper with hints that
name each noun's own 받침, and 3 cross-references, the gym manifest and
`REFERENCE.md` were updated. Korean: 151 points → 150.

## The explanation pass, the last of 27 courses (10 Sep 2026)

151 explanations read, **140 rewritten, 159 content defects corrected** — the
highest rate of any course. 140 render as markdown (93%) and 86 carry a
table, which is the language: 받침 allomorphy, six irregular stem classes and
four speech levels are paradigms, and a paradigm belongs in a table. The
restraint guard that measures the pass rather than the language — does a bold
name the form the point teaches — reads **183 of 204 (89%)** here, above the
26-course average.

Every defect was the same shape: **a rule the point's own drills falsify.**
*Polite requests (으)세요* derived 살으세요 for its own 사세요 drill; *Pure Korean
vs Sino-Korean numbers* called the choice etymological when it is lexical per
counter, then listed three Sino-Korean words under pure Korean; *Superlatives*
made its own second drill ungrammatical.

**Four of nine second-pass defects were one class: the ㄹ-final stem left out
of a 받침 rule.** ㄹ is the consonant that behaves like a vowel — it drops
before ㄴ/ㅂ/ㅅ/(으) — so any rule stated as a clean consonant/vowel split is
wrong for it. Points 12, 82, 112 and 114 each stated one. When writing a
받침 rule for this course, name ㄹ explicitly or check that no ㄹ stem exists
in the paradigm.

Record: `docs/decisions/2026-09-10-korean-explanation-pass.md`.

## Definitions that gave a relation and no meaning (10 Sep 2026)

**2 definitions rewritten** in the rank 201–1000 band. Each stated a
grammatical relation to another word in this language and no English meaning —
the class the owner named ("coche as the definition for coches"), CHECKS §36.
The band boundary is the finding: Phase 2d repaired the top-200 and the defect
resumed at exactly rank 201.

- `미친` was "past adnominal of 미치다" → "crazy, mad, out of one's mind - the form that modifies the noun after it, as in a crazy person (past adnominal of 미치다, to go mad); coarse when thrown in as a slang intensifier"
- `없었다` was "Past tense of 없다" → "there was not, there were none; did not have, was missing - plain past of 없다; after ~을 수 it means could not"

The house shape is meaning first, relation in parentheses, and the English must
match the FORM rather than the lemma. Written by a maker and judged by an
adversarial checker; across all 19 courses 23 of 1,826 were refused, most for
hiding a person the form genuinely has. `relation_only_gloss` now measures
what remains in this course.

## Sentence authoring, wave 1 — the top-500 band (11 Sep 2026)

**528 of Korean's top-1,000 words had no sentence the card could blank**, rank
10 `있다` among them, so those cards fell back to a definition-only prompt.
Wave 1 covered the top-500: **540 sentences for 180 words, every row verified
clozable by the gate**, and the floor pass then dropped 120 fragments the new
sentences superseded. The band's gap went **188 → 8**.

Written to CHECKS §23 — three sentences per word, differing in kind, 7–14
어절, a finite verb and a real scene. The constraint that shapes Korean
authoring is that `find_cloze` needs the SURFACE form, so a dictionary-form
headword (`있다`, `없다`) must stand as its own 어절 — which the 한다체 plain
style does naturally (`학생이 도서관에 있다`), while 있어요 would never blank.

**What the checkers refused is the useful part:**

- **`남자 분` — a misspacing the gate cannot see.** 남자분 is one word
  (표준국어대사전), and it was the space itself that made the blank land on
  bare 남자. The row would have taught the wrong spacing in the only sentence
  a learner sees that word in. **The gate's silence on spacing is a blind
  spot, not a clearance** — every bare-어절 slot needs an orthography check by
  eye (집 앞 골목, 이름 석 자, 오 남매 and 하다 보면 all checked out; only this
  one did not).
- **`그녀` pointed at one's own grandmother** — translationese. A Korean
  writes 할머니의 젊은 시절, never pronominalising a close elder. Moved to song
  lyrics, where the literary pronoun actually lives.
- **`꼭 잠갔는지`** — off-gloss sense. 꼭 잠그다 is the set collocation for
  closing a valve *tight*, not "without fail", so the sentence taught a sense
  the definition does not name (rule 6). The adverb belongs on the checking
  verb: 잠갔는지 꼭 확인해 주세요.
- **Three `하다 보-` frames in one set** — one construction three times, which
  §23 names explicitly. 하다 만 N is a second bare-어절 slot that fixes the
  repetition and the objectless pro-verb together.

**One word was rightly skipped rather than authored:** `하` ("last, lowest
grade") is the Hanja 下 surfacing as an extraction fragment, and §28 fails
outright — a blank in `상 중 ___` is satisfied by 상 and 중 equally. It belongs
in `vocab_exclusions.tsv`, not in a later authoring attempt.

## Sentence authoring, wave 2 — ranks 501–1000 (11 Sep 2026)

**960 sentences for 320 words**, every row verified clozable by the gate; the
floor pass then dropped 157 fragments they superseded. Korean's **top-1000 gap
is 528 → 28**, and the top-500 holds at 8.

**The checkers raised their own bar this wave**, and two of the moves are worth
copying into other courses:

- **They cited 국립국어원 rather than judging spacing by eye.** 군 복무 (우리말샘
  lists it spaced; 군복무 is not a word), 살인 사건 (온라인가나다: `'절도
  사건/살인 사건'은 한 단어가 아니므로 띄어 쓰는 것이 원칙`), 새끼 고양이 (there
  is no native one-word kitten). Wave 1's only gate-invisible defect was a
  split compound, and it did not recur.
- **They applied rule 61's two-signal test to a collocation and found zero.**
  `죽다 만 얼굴` parses — V-다(가) 말다 is productive — but 죽다 is an
  achievement, not an interruptible activity, and no attestation exists.
  Replaced with `죽다 살아나다`, which the dictionary defines outright.

**A structural fact about Korean authoring, established here.** A Korean verb
headword has **no finite slot at all** — 한다체 gives 죽는다, not 죽다 — so the
entire inventory of blankable positions is the citation form, the -다(가)
reduction, and a serial idiom like 죽다 살아나다. Two rows of one verb sharing a
construction is therefore structural, not laziness, and should not be refused
as "same frame" the way a noun's three swapped frames would be.

**Two skips, both correct and both exclusion candidates rather than authoring
ones:** `가세` (564) is an extraction artefact of 가세하다 — the bare noun that
actually occurs is the homograph 家勢 (가세가 기울다), so any blankable sentence
teaches a sense the definition never names. Same shape as wave 1's `하`.

**One gloss-order note for later:** `역시`'s three rows all use "just as
expected" rather than the definition's leading "too, also". That sense IS
named, so it is not off-gloss — but it is the dominant one in real Korean, and
this is the card that argues for flipping the order (rule 6).

