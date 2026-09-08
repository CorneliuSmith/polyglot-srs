# Korean: the duplicate grammar points, judged and merged — 8 September 2026

**Owner:** "choose the best korean point over the other."

Seven groups of Korean grammar points share a form in their title. A reader of Korean judged each group against `docs/quality/ko.md` and the drills themselves; a second reader tried to overturn every verdict. The two agreed on all seven.

| group | verdict | keep | retire | why, in one line |
|---|---|---|---|---|
| 가 는 은 이 | **duplicate** | ~는/은 and ~이/가 revisited: nuance and form | ~이/가 and ~는/은 Revisited, ~는/은 vs ~이/가: general statements and immediate experience | All three are the same B1 point: given a noun and a context, pick 는/은 or 이/가, decided by 받침 plus the general-fact-vs-just-noticed nuance |
| 것이다 을 | **distinct** | — | — | These are the two senses of one ending that a learner has to choose between, not one point written twice |
| 동안 | **duplicate** | 동안: 'for' a time and 'during' a noun | 동안 – 'for' a period of time | Same question twice |
| 스럽다 | **duplicate** | Korean suffix: ~스럽다 | Adjectives with ~스럽다 | Same question twice |
| 아 어 있다 | **duplicate** | ~아/어 있다: being in a state | Passive verbs with ~아/어 있다 (describing a state) | Same construction, same sense, different illustrating verbs — not two senses a learner must choose between |
| 아 어지다 | **distinct** | — | — | These share the ending ~아/어지다 and nothing else |
| 아니다 이다 | **distinct** | — | — | Index 48 is the PRESENT tense of the copula (이야/야, 이에요/예요, 입니다, and the negatives 아니야/아니에요/아닙니다); index 49 is the PAST (이었어/였어, 이었어요/였어요, 이었다/였다, 이었습니다/였습니다, 아니었어/아니었습니다) |

## The three that are NOT duplicates, and must stay

- **`~ㄹ/을 것이다`, future against conjecture.** Two senses of one ending, and a learner has to choose between them — the drills for each are answerable only by knowing which. Distinct.
- **`~아/어지다` on a verb against on an adjective.** Passive against inchoative: 만들어지다 "to be made" is not 예뻐지다 "to become pretty". Distinct.
- **`이다 / 아니다`, present against past.** Two tenses of the copula. Distinct.

Calling any of these a duplicate would have deleted something a learner needs, which is the failure the second reader was told to hunt for.

## What the readers found inside the duplicates

The decisive finding was not which point was longer. **Point 96, one of the two `은/는` points retired, gets its own rule wrong three times in eleven drills.** The point exists to teach the 받침 condition — `은` after a consonant, `는` after a vowel — and it answers `라면는` (면 has a ㄴ 받침, so `은`), `다이아몬드은` (드 is open, so `는`) and `청구서이` (서 is open, so `가`), each filed in a cell that asserts the opposite. It also answers `은` after 다이아몬드 in one drill and `는` after the same noun in another. Every 받침 in all three points was checked by hand, not sampled.

**The keeper had an error of its own**, which the readers said must go in the same change or the merge leaves the single surviving point teaching the rule backwards: `여름 날씨은 좋다` (씨 is open, takes `는`), with a hint stating "consonant-final noun". Replaced by the one clean comparison drill from a retired point, `문법은 어렵고 단어는 쉬워요`, which answers `은` correctly after 법 and covers a use the keeper listed but never drilled.

## Salvage — what moved rather than being lost

| into | from | drill | why |
|---|---|---|---|
| 136 | 96 | 바나나는 값이 싸요 | the general-fact 는 in 해요체, with the 는…이 pattern the explanation discusses and never drilled |
| 136 | 96 | 밥이 너무 딱딱해요 | a plain immediate-experience 이 after a consonant; the keeper's two consonant-final 이 drills were both special environments |
| 89 | 91 | 그것은 만족스러운 대답이었어요, 우리 딸은 사랑스러운 여자예요 | the ~ㄴ/은 modifier form, a cell the keeper never tested |
| 89 | 91 | 일기에 '이번 결과는 만족스럽다'라고 썼어요 | the bare dictionary form, likewise |
| 98 | 74 | 가게 문이 닫혀 있었어요 / 닫혀 있을 거예요 | past and future of the state form — all fifteen of the keeper's drills were present tense |

**One salvage was refused by a mechanical check.** The reader named 96's `이` drill by its answer string, but 96 has two drills answering `이`, and the first the key matched was `청구서이 어제 왔어요` — one of the three wrong answers that retired the point. The batchim check caught it before it moved; the drill the reader meant, `밥이`, was taken by its sentence instead. Rule 28: assemble by a stable key, and an answer string is not one.

## The retire path this needed

A grammar point could not be retired. `seed_grammar` is add-only for points, so removing a point from the file left it live in production for ever — the gap vocabulary closed with migration 20261016. Migration **20261017** adds `grammar_points.retired_at`; `data/grammar_exclusions.tsv` is the source of truth in both directions; the reconcile sets and clears it and prints a `gp-ret` column; every place a point is OFFERED (Learn, the next-level peek, deck counts, the two path listings) filters on it, probed so a database behind the migration degrades to "nothing retired"; fetch-by-id does not filter, so a learner part-way through a retired point keeps the card they already have.

Korean: 156 points → 151. Owner-run, in order: `supabase db push` (20261017) · `seed_grammar -l ko` (the salvaged drills and the corrected keeper) · `reconcile -l all --apply` (retires the five).

## What else names a grammar point — the checklist the guards produced

Removing the five titles broke four other committed things, each caught by an
existing test before it reached the repo: the Gym manifest `data/gym/ko.json`
(five cells; the keepers were already present, so the entries were removed),
the `audit_gym` picker that reads it, nine `prerequisites` / `related` links
in other Korean points (remapped to the keepers, duplicates and
self-references dropped), and the tutor bundle `REFERENCE.md` (regenerated).
The next retirement, in any course, touches the same four.

