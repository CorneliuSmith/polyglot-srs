# Russian (ru) — Content Quality Standards

## Language profile

Cyrillic, left-to-right, 33 letters. Two cause most of the mechanical trouble: **ё** (written, not
optional, in this course) and **й**, a letter and not a diacritic — the grader disagrees, see *Current
measured state*. Stress is never written in learner-facing text; the acutes in the
`data/ru_morphology.json` charts (`або́рта`, 2640 of 5374 entries) are display-only.

**The authoritative variety is standard contemporary Russian** — Moscow literary norm, post-1918
orthography, neutral everyday register, what the file already writes from A1 (`Мне нравится`, `У меня
нет времени`) through C2 participial style. **Explicitly out of scope:** pre-reform orthography (ѣ, і,
final ъ), Church Slavonic, Ukrainian/Belarusian and surzhyk forms, regional and émigré norms, and the
obscene layer (мат) with prison/gaming slang.

**Gender:** three — masculine, feminine, neuter — plus **animacy**, a sub-gender surfacing as a
distinct accusative (`вижу брата`, its own A2 point). `ru_morphology.json` carries a `Gender` chip on
3913 entries and an `Animacy` chip beside it; plural neutralises gender, but the lemma's gender rules.

Three features dominate drill quality: (1) **case government** — six cases keyed to gender, animacy
and stem type, so a hint naming the case but not the lemma has done half the job; (2) **aspect** —
nearly every verb drill is an aspect choice, and the sentence must carry the adverbial that forces it
(`вчера наконец`, `но уже закрыл`); (3) **ё/й orthography**, which breaks grading and transliteration
invisibly to a skim-reading reviewer.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss
already sitting in the drill's own translation; never the `answer — explanation` template; one hint
resolves to exactly one answer inside a point (allomorph sets excepted where the sentence
disambiguates); hints are written in English, and quoting a base form in Cyrillic is fine while whole
Russian sentences are not.

**1. Never quote the answer while explaining it.** Three of Russian's four leaks are this self-quote,
all in *Possessive pronouns*.
- BAD: `his — его never changes form` for `его` — GOOD: `male owner — one frozen form for all three
  genders` (the point's own twelfth drill already does it: `his — same frozen form for every gender`)
- BAD: `not X, а Y` for `а` — GOOD: `contrast between two parallel statements, not an objection`

**2. Quote the lemma, not the meaning.** *Genitive of absence* runs two conventions side by side:
`время in the genitive` and `car + genitive`. The Cyrillic citation form wins — it cannot collide with
the drill's own English translation, and it teaches the lemma → form step that *is* the drill. One or
two quoted Cyrillic forms is the convention; three or more is drift into Russian.
- GOOD: `машина in the genitive` for `машины` — BAD: `car + genitive` under *She doesn't have a car.*

**3. One hint, one answer inside a point.** Three points break this.
- BAD: `part of day — instrumental` for both `Утром` and `Вечером` — GOOD: `утро → instrumental, no
  preposition` / `вечер → …` (rule 2 doing double duty; `утро` ≠ `утром`, so no leak)
- BAD: `'on a date' → genitive ordinal` for `первого`/`второго`/`пятнадцатого` — GOOD: `1st (15th) —
  ordinal in the genitive`

**4. Aspect hints name the aspect *and* the agreement**, as the file's best already do: `process over
time — imperfective, feminine`, `result annulled → imperfective plural`. Quoting the pair is
legitimate — the partners are not the drilled form (`делать/сделать — result` for `сделал`).
- BAD: `result still holds → perfective` for both `взял` and `включил` — GOOD: `брать/взять — result
  still holds` / `включить — result still holds`

**5. Noun-answer hints mark gender where gender picks the ending.** Deliberately
weaker than the Romance rule, which is absolute: Russian gender is recoverable
from the nominative ending for most nouns, so marking it everywhere would be
noise — it earns its place only where the learner cannot read it off the word
(soft signs, indeclinables, and the -а masculines like `папа`). Only 8 of 54 do today.
- GOOD: `машина (f.) in the genitive` for `машины` — BAD: `job + genitive` for `работы`, no gender,
  and `job` sits in the translation

**6. Write ё as ё** everywhere, quoted lemmas included (`ёлка`, never `елка`); do not regress it.

## Question / drill standards

A good drill is a sentence a Russian would actually say, one blank whose filler is fixed by sentence
plus hint, and a translation of the *completed* sentence in natural English. Pitfalls:

- **The sentence must force the aspect, not merely permit it.** `Вчера я наконец {{answer}} эту книгу.`
  → `прочитал` works because `наконец` rules out the imperfective; `Вчера я {{answer}} книгу.` admits both.
- **The sentence must supply the governor for a case drill** — preposition, verb, or numeral (`Мне
  двадцать два {{answer}}` → `года`); an ungoverned case blank is a vocabulary question in costume.
- **Never drill `мой` against `мои` (or `свой`/`свои`) without the noun in the sentence** — the grader
  cannot currently tell them apart (see below), so the sentence must do the work.
- **Sentence-initial answers keep their capital** (`Утром`, `Кто`) and the `transliteration` must
  match; all 348 drills carry one. **One blank, one word**, unless the point *is* a construction.
  **Translations stay British-English**, as the file already is: *flat*, *cinema*, *theatre*, *mum*.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `язык` is *language* and *tongue*; `мир` is
  *world* and *peace*; `ключ` is *key* and *spring*. The gloss matches the sense the drill uses.
- **Noun definitions carry gender** — `(m.)`/`(f.)`/`(n.)`, plus animacy where the accusative depends
  on it. The morphology knows this for 3913 entries; the gloss layer almost never says it.
- **Verb definitions carry aspect and the partner**: `читать (impf.; pf. прочитать) — to read`. A gloss
  without the partner teaches half a lexeme, and `RussianNLP.get_aspect_partner()` reads it from
  curator data only — nothing computes it.
- **No metalinguistic non-glosses.** `data/ru_frequency.tsv` rank 24 glosses `все` as *"inflection of
  весь (vesʹ)"*, rank 49 glosses `всё` as *"nominative/accusative neuter singular of весь"* — a parse,
  not a meaning; the learner needs *all / everybody* and *everything*.
- **Register:** neutral standard throughout; bookish items (`имеющиеся`, `иметь`, C2 nominal style)
  stay in their C1/C2 point and are labelled formal in the hint.

## Current measured state

- **`data/grammar/ru_grammar.json` — crawl figures re-verified on disk: 55 points, 348 drills**, every
  point `source: contributor`, `reviewed: true`; A1 11 / A2 13 / B1 12 / B2 10 / C1 5 / C2 4. All 348
  have a `transliteration`, 54 carry a `cell`; no empty or vague hints, translations or explanations.
- **Hint leaks: 4.** Three self-quotes in *Possessive pronouns* — `his — его never changes form`,
  `her — её never changes form`, `their — их never changes form` — plus `not X, а Y` for `а`.
- **Duplicate hints: 3.** *Time expressions* (`part of day — instrumental` → `Утром`, `Вечером`),
  *Ordinals and dates* (`'on a date' → genitive ordinal` → three answers), and one the crawl did not
  quote: *Aspect nuance* — `result still holds → perfective` for both `взял` and `включил`.
- **Correction to the crawl:** it lists the time answers as `вечером`/`утром`; in the file they are
  sentence-initial `Утром`/`Вечером`, and both translations (*In the morning…*, *In the evening…*) do
  disambiguate — so the drill is answerable; the failure is a hint with no discriminating load.
- **Gender marking: 8 of 54 noun-answer drills (15%)** — unmarked include `столе` → `table +
  prepositional`, `книгу` → `book + accusative`, `работы` → `job + genitive`. The join is slightly
  dirty: the conjunction `а` is recorded in `ru_morphology.json` as a masculine inanimate **noun**.
- **One-word hints: 5** — `plural`, `permission`, `prohibition`, `necessity` are grammar labels and
  pass; `how` for `Как` under *How are things?* does not, and the whole *Question words* point has that
  shape (`who — asking about a person` under *Who is this?*). **≥3 Cyrillic tokens: 5**, all the
  base-form convention at threshold (`говорить, он/она`) — no action.
- **Grading hazard, verified in `backend/services/nlp/base.py`:** layer 2.5 folds combining marks via
  NFD, which is how ё→е is accepted — but **й also decomposes** (и + U+0306), so `мои` typed for `мой`
  returns `CORRECT_SLOPPY` with *"Almost — check the accents."*, and `свой`/`свои` collide the same way.
  ё-folding is intended; й-folding is not, and it lands on *Possessive pronouns* and *Свой*;
  `RussianNLP.normalize()` is lowercase+strip only, so nothing upstream catches it.
- **Transliteration is two schemes.** 110 drills render ы as `y'`, х as `h`, й as `j` (`My' zhivyom`,
  `u vhoda`); 5 use plain `y`, `kh`, `y` (`Posle ___ my idyom domoy`, `On priekhal iz ___`), all five
  in the four points appended at the file's end — *Adjective agreement*, *Question words*,
  *Conjunctions и, а, но*, *Genitive case*.
- **Corpora:** `data/ru_sentences.tsv` 28 935 rows, curated `data/sentences/ru_sentences.tsv` 348,
  `data/ru_frequency.tsv` 10 000 rows (`rank / word / pos / en`, no gender column; 3 of 4254 noun rows
  mention gender), `data/ru_morphology.json` 5374 entries. **ё discipline is good:** 249 `ещё` / 0
  `еще`, 75 `идёт` / 0 `идет`.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language ru
.venv/bin/pytest backend/tests/test_nlp_russian.py -q
cd frontend && npx vitest run src/__tests__/translit
```

Russian is in `TRANSLIT_LANGS`, so the transliteration suite applies — the typing scheme there (`yo →
ё`) is separate from the display `transliteration` field on drills, and both must survive a change to
either. A human reviewer pulls 10 random drills and asks, in order:

1. **Does the hint contain the answer?** `his — его never changes form` is the template to stop
   copying; three drills fail today.
2. **Could two drills in this point share this hint?** If yes it is underdetermined — `part of day —
   instrumental` is the canonical failure.
3. **Noun answer — does the hint name the case *and* the lemma or gender?** `table + prepositional`
   fails; `стол (m.) in the prepositional` passes.
4. **Verb answer — does the sentence force the aspect?** Find the adverbial (`наконец`, `но уже
   закрыл`); if removing it leaves both aspects true, the drill fails.
5. **Could I answer this knowing no Russian?** `how` under *How are things?* — yes, a failure.
6. **Is ё written everywhere it belongs, and the transliteration in the majority scheme** (`y'` for
   ы, `h` for х, `j` for й)?

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**4 rows reglossed**, of which **2 were fatal** — the card named a
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
| 34 | `есть` | there is, there are; у меня есть — I have (the one surviving present form of |
| 137 | `том` | that, it — тот/то in the prepositional (о том, что… — about the fact that…;  |

Fixes are in `data/gloss_overrides.tsv` as well as `data/ru_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang ru --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.

### Extended to rank 2000 (25 Aug 2026)

The sweep above covered the top 500. Ranks 501-2000 added **9 rows, 2 fatal**, so the
course total is **13 repaired (4 fatal) through rank 2000**.

The keep rate rose with rank — roughly 30% of candidates were kept in the top 500 against
about 50% below it — which is the expected shape and a check on the pass: deeper in a
frequency list the lexical sense genuinely is more often right, and an over-eager rewrite
would replace a correct gloss with a wrong one.

| rank | word | now reads |
| --- | --- | --- |
| 649 | `рада` | glad, pleased, happy — feminine short form of рад, said by or about a wo |
| 1083 | `семью` | family — семья (f.) in the accusative (защитить свою семью — to protect  |
