# English (en) — Content Quality Standards

## Language profile

Latin script, left-to-right, no diacritics of its own: answers are plain ASCII, so the grader's typography
folds (curly→straight quotes, stripped trailing punctuation) are the only normalisation that ever fires.
**The authoritative variety is British-referenced standard English**:
`Cambridge Dictionary — English Grammar` is cited on all 43 points, the `British Council–EAQUALS Core Inventory
for General English` on 15, and the two places variety is named at all both name Britain (`at the weekend
(BrE)`, `British English often uses should instead`). The lexicon agrees quietly: `film` ×3 never *movie*,
`shop` ×2, `football` ×3 meaning soccer, `My birthday is on 12 March`. **Out of scope:** a second variety
taught in parallel; varieties with their own course (`jam`); dialect grammar (*ain't*, invariant *be*). Zero
drills contain an `-ise/-ize` or `-our/-or` word, so **American spellings must be accepted, never taught**.

**Gender: none.** English has no noun class; the only gender is the pronoun/possessive set, and it is *semantic*
— it lives in the sentence, not a chip. There is no `data/en_morphology.json` and there should not be one; the
audit's `structural` warn for it is accepted state, not debt.

**The feature that dominates drill quality here has no analogue in any other course: the target language is the
metalanguage.** Hints are written in English *about* English, so the leak check collides with ordinary hint
prose, and the `translation` field — everywhere else an English rendering of a foreign sentence — would have to
hold English-for-English. It does not; it holds a **usage note** (see below). Secondary: closed-class answers
(`a/an`, `in/on/at`, `do/does/did`) where a hint has nowhere to hide, and the auxiliary system, where one
description (`the present auxiliary`) covers two answers (`do`, `does`).

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already in the
drill's own translation; never the `answer — explanation` template; one hint resolves to exactly one answer
inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and quoting a
base form is fine while whole target-language sentences are not.

"Hints are in English" and "hints must not be in the target language" are the same sentence here, so **the rule
that survives is the functional one: a hint names the grammatical job, it never supplies the word to type.**

0. **The `translation` field is a usage note, by design — house convention, not a defect.**
   `data/grammar/en_grammar.json` carries `"Clock time."`, `"A year."`, `"Bare form — no -s."`, `"Positive →
   negative tag."` where other courses carry a sentence. The real translation lives one layer up:
   `data/grammar/en_drill_hints.<locale>.json` (19 locales × all 266 drills) gives the learner's own language —
   for `The meeting starts {{answer}} nine o'clock.` the `ru` file has `Совещание начинается в девять часов.`,
   merged onto the drill by `seed_grammar.py::_attach_hint_translations` keyed on the exact sentence. **The
   base `translation` is therefore free to be a note, and the checker exempts `en` from `vague_translation` for
   exactly that reason** — 46 of 46 hits were this convention. GOOD:
   `"He often studies {{answer}} night."` → `"The fixed phrase with 'night'."` BAD (and *not* what the file
   does): `"He often studies at night."` — an English "translation" of an English sentence hands over the
   answer.
1. **The exemption is scoped to that one rule, and must stay so.** A usage note is still text the learner sees,
   so it is still bound by `giveaway_by_gloss`: five hits are a short hint appearing whole in its own note.
   BAD: hint `a woman` under `"Introducing a woman in your family."` (`She`); `a thing` under `"Talking about
   a thing."` (`It`). GOOD: keep the note, move the hint off it — hint `third-person subject, female referent`.
2. **The English-function-word exemption is wider here than anywhere else — do not "fix" what it forgives.**
   Ten drills match the raw whole-word leak test; nine are collisions with ordinary hint prose, exempted
   because the answer is ≤3 characters and sits in `ENGLISH_FUNCTION_WORDS`. GOOD (exempt, and good hints):
   `a | before a consonant sound`, `You | the person you are talking to`, `The | identified by the phrase after
   it`. The seeder runs the same guard on localized hints (`if len(ans) > 3 and re.search(...)`). BAD, and the
   one that survives: `Her | belonging to her`.
3. **For pronoun and possessive answers, describe the referent's role, never restate it.** GOOD:
   `belonging to a thing — no apostrophe` → `its`; `it belongs to us` → `our`; `the man's name` → `His`.
   BAD: `belonging to her` → `Her` — sibling drills in that point get it right, so this is a slip.
4. **Never `answer — explanation`.** Three drills do it, all in one C2 point, all the same string. BAD:
   `be — bare` → `be`. GOOD, from the *same point*: `obey — bare form` → `follow`; `step down — bare form` →
   `resign`; `seek advice from — bare form` → `consult`. The fix is modelled next door — synonym plus form
   spec; for `be`, write `the linking verb — bare form`.
5. **Auxiliary hints must pin the person or the polarity, not just the slot.** BAD: `the flipped tag auxiliary`
   for `does`, `haven't` *and* `isn't`; `the present auxiliary` for both `do` and `does`. GOOD: `flipped tag —
   negative, present of have`; `present auxiliary — third person`. These are not allomorph sets: `do`/`does`
   differ by person, not harmony, so that exemption does not apply.
6. **A one-word hint is acceptable only as a grammar label the sentence cannot supply.** `singular` / `plural`
   for `is` / `are` in *There is / there are* passes: the number is visible in the noun, and the label names
   the choice without naming the word. All four one-word hints in the file are that pair.

## Question / drill standards

A good English drill is a sentence a competent speaker would actually say, with exactly one blank fixed by
sentence + hint together. The file is strong here: real discourse (`The lights are on — someone {{answer}} be
home.`, `That {{answer}} be Maria — she's in Brazil this week!`), contractions where a speaker would contract,
em-dash continuations supplying context. Keep that register — a bare `He {{answer}} to school.` is
grammatically sufficient and pedagogically dead. Pitfalls:

- **One blank, one filler.** `Not only {{answer}} she sing…` admits only `does`. But `{{answer}} me tomorrow,
  please.` (`Call`) admits *ring, phone, text*, surviving only on the hint `base verb` — which then collides
  with `sit` in the same point. Where the sentence does not force the verb, force it in the hint.
- **Grammar drills are graded strictly.** With `card_type == "grammar"`, layers 3–4 of the grader downgrade
  lemma and morphological-family matches to `WRONG_FORM` instead of accepting them, so `go` for `went` fails.
  Never write a drill whose answer is one cell of a paradigm the sentence also permits elsewhere.
- **Watch `normalize()`.** `EnglishNLP.normalize` strips a leading `the/a/an`, guarded so an answer that *is*
  the whole article survives (`test_normalize_does_not_strip_the_as_full_word`); a multi-word answer beginning
  with an article would be silently truncated, so keep article answers single-token. Apostrophe answers
  (`can't`, `brother's`) ride the grader's curly→straight fold — never store a typographic apostrophe.

## Translation & definition standards

- **The base `translation` is a usage note; it must be a *note*, not a paraphrase.** It answers "what is this
  sentence doing?" (`Clock time.`, `Past ability.`, `Negative → positive tag.`), never "what does it say?", and
  it must contain neither the answer nor (rule 1) the hint verbatim.
- **The real translation is per-locale and is held to the ordinary standard.** In
  `en_drill_hints.<locale>.json` the `translation` is a full, natural sentence in the support language
  rendering the *completed* drill; the `hint` is that locale's rendering of the grammatical description, with
  lemma cues left in English on purpose (the files say so) because the learner must produce the English word.
  All 19 are `"reviewed": false` — drafted scaffolding awaiting a native pass.
- **No bare one-word gloss for a polysemous answer.** `can` (ability / permission), `will` (future /
  willingness), `used to` (habit / accustomed) each need the sense named: `past ability`, not `could`.
- **Gender marking is not applicable** — English nouns have no class; never invent `(m.)`/`(f.)` annotations.
- **Register consistency:** neutral-to-informal spoken English at A1–B1, formal written English at C1–C2
  (`notwithstanding`, `albeit`, the mandative subjunctive). Never mix — a C2 subjunctive drill does not belong
  in a text message, and an A1 drill should not say *shall*.

## Current measured state

`python -m backend.services.quality.audit_content --language en` on this tree: **43 points, 266 drills**, all
`source: contributor`, all `reviewed: true`. Fail-level total **13**, matching `data/quality/baseline.json`
(`en.leak_hard 1`, `en.self_answering 3`, `en.giveaway_by_gloss 5`, `en.duplicate_hint 4`), plus one
`structural` warn for the missing `data/en_morphology.json` (accepted — no chips to carry). Zero `empty`; zero
`hint_language`; `vague_translation` **46 raw hits, all exempted** — the usage-note convention, correctly
forgiven.

Two crawl figures disagree with the file, and the file wins. The crawl reports **10 hint leaks**: that is the
raw whole-word count before the function-word guard, and the checker's count is **1**. The crawl says **17
per-locale scaffolds**; `ls data/grammar/en_drill_hints.*.json` returns **19**, each covering all 266 drills.

Worst offenders, quoted from `data/grammar/en_grammar.json`:

1. `[The mandative subjunctive (insist that he be)]` — hint `be — bare` on three of six drills. Self-answering
   *and* a leak, while the other three drills in the same point (`obey — bare form` → `follow`) show the fix.
2. `[Question tags and indirect questions]` — hint `the flipped tag auxiliary` for `does`, `haven't` and
   `isn't`: one hint, three answers, one point, underdetermined however well the learner understands tags.
3. `[Subject pronouns (I, you, he…)]` — hint `a woman` inside note `"Introducing a woman in your family."`
   (`She`); same shape for `a man` / `He`. The usage-note convention producing a giveaway — exactly why the
   `en` exemption stops at `vague_translation`. The one surviving hard leak: `[Possessives]` `belonging to her`
   for `Her`.

## Testing checklist

- `python -m backend.services.quality.audit_content --language en` — the mechanical gate. Expect 13 fail-level
  findings and one structural warn; **expect zero `vague_translation`**, and if that ever becomes non-zero the
  `en` exemption has been dropped or the file has switched conventions. Investigate, don't re-baseline.
- `.venv/bin/pytest backend/tests/test_nlp_english.py -q` — article stripping, lemmatisation, the
  strict-grammar gate. Five need the spaCy English model and fail in this container by design; see the
  known-failing list in `CLAUDE.md`.
- `.venv/bin/pytest backend/tests/test_content_quality.py backend/tests/test_grammar_seeder.py -q` — the
  guards themselves (including the function-word exemption English leans on hardest) and the locale-overlay
  merge, where a reworded drill sentence must fail the seed rather than silently drop 19 locales.
- Transliteration tests do not apply — `en` is not in `TRANSLIT_LANGS`
  (`frontend/src/features/keyboards/translit.ts`), so there is no `translit` suite to run for this course.
- **Human spot-check, 10 random drills** (`--sample 10`). For each: does the hint name the *job* rather than
  supply the *word*, and would it still be good if the answer were six letters instead of two (or is it passing
  only on the function-word exemption)? Is the `translation` still a usage note, or has someone "fixed" it into
  an English paraphrase of the English sentence? Does the note repeat the hint? Does any sibling drill share
  this hint with a different answer? Is the sentence something a person would say, at the point's CEFR
  register? Finally, open the drill in one locale overlay: that `translation` must be a real, natural sentence.
