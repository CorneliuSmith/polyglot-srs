# Italian (it) — Content Quality Standards

## Language profile

Latin script, left-to-right. The accents authors drop are the grave (`è à ì ò ù`) and the acute on
`é`/`perché`; the elision apostrophe (`c'è`, `l'ombrello`, `un'amica`) is ASCII `'` (U+0027) in all
28 places `data/grammar/it_grammar.json` uses it, and must stay ASCII — grading folds a phone's
curly `’` back (`_TYPOGRAPHY_MAP` in `backend/services/nlp/base.py`), but the data should not lean
on that.

**The authoritative variety is standard Italian** — the norm of the *Treccani* grammar the file
cites in nearly every point, sequenced A1→C2. It commits: `Lei` is the formal you (25 mentions,
with the culture note "grammatically 'she', even for a man"), `voi` is plural-you only, and the
*passato remoto* is quarantined at C1 as "the literary past". **Explicitly out of scope:**
regional and dialect forms (Romanesco, Napoletano, Siciliano); the southern/older courtesy `voi`
for one person; the spoken-only `gli` for feminine `le` and plural `loro`; and the southern
everyday *passato remoto* — the course teaches `passato prossimo` for that, and a regional course
would get its own code.

**Gender:** two classes, masculine and feminine, no neuter. `data/it_morphology.json` carries a
`Gender` chip on 4441 of its 4491 nouns (2385 m / 2056 f) and a `Plural` chip on 3943. Gender is
not guessable from the ending: `-e` nouns split both ways (`il fiore`, `la notte`, as the A1 point
itself says), `-a` lies (`il problema`), `-o` lies (`la mano`).

Three features dominate drill quality: (1) **article allomorphy driven by sound, not gender** —
`il/lo/l'`, `i/gli`, `un/uno/un'` are chosen by what follows, so a hint saying only "masculine
plural" both leaks the gender and fails to pick between `i` and `gli`; (2) **elision and clitic
clusters** — `c'è`, `l'ho`, `glielo`, `me lo`, `ce le` — which make "exactly one blank" hard to
keep honest; (3) **the three `si`** (riflessivo, passivante, impersonale), where all of Italian's
hint leaks live.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss
already in the drill's own translation; never the `answer — explanation` template; one hint
resolves to exactly one answer inside a point (allomorph sets excepted where the sentence
disambiguates); hints are in English, and quoting a Italian base form is fine while whole Italian sentences
are not.

0. **`lemma, person` is house style and is legitimate.** `essere, io` → `sono`; `amare, tu` →
   `ami`; `andare — io` → `vado`. Italian has **zero** collisions of the kind that cost Romanian
   real leaks (no hint quotes a lemma equal to its own answer), so the checker must match with
   lookarounds, not `\b` — `ami` sits inside `amare`.
1. **Never quote the Italian construction that contains the answer, and distinguish the three `si`
   by function rather than by label.** All three mechanical leaks are this shape.
   - GOOD: `impersonal — "one says", no stated subject` for `Si` in `{{answer}} dice che l'inverno
     sarà freddo.`; `passive — the subject is what gets sold` for `si` in `Qui {{answer}} vende
     pane fresco.`
   - BAD: `(impersonal si)`, `(si passivante)`, `them (ce + le)` for `le`.
2. **Article hints name the trigger, not the gender.** `feminine singular` picks exactly one of
   `{il, lo, la, i, gli, le}`, so the learner never has to know `casa` is feminine.
   - GOOD: `the definite article` for `La` in `{{answer}} casa è grande.`; `the definite article —
     the noun starts s + consonant` for `Lo` in `{{answer}} studente è bravo.`
   - BAD: `feminine singular`, `masculine plural`, `the — masculine plural` — eight of the twelve
     *Definite articles* drills, and `masculine plural` does not even separate `I` from `Gli`.
3. **Noun answers mark gender, `(m.)` or `(f.)`, including plural answers** (mark the lemma's).
   - GOOD: `book (m.), plural (-o → -i)` for `libri`
   - BAD: `book, plural` — the current text in all six *Gender and number of nouns* drills
4. **A gerund/conjugation rule hint names the verb too.** One hint must pick one answer.
   - GOOD: `giocare → -ando` for `giocando`, `preparare → -ando` for `preparando`
   - BAD: `-are verbs → -ando` for both — Italian's only duplicate hint.

## Question / drill standards

A good drill is a sentence an Italian would actually say, one blank fixed by sentence + hint
together, and a translation that renders the *completed* sentence in natural English. Pitfalls:

- **The fronted topic must not print the answer.** `Le mele? {{answer}} compro al mercato.` shows
  `Le` before asking for `le`; same in `Le chiavi? Ce {{answer}} ho io.` and `Le chiavi? Ce
  {{answer}} ha date lui.` Use a proper noun or a bare plural as the topic.
- **Never let the accent be the only thing tested.** Five drills answer `è`, and grading folds
  accents (`ItalianNLP` inherits `AccentFoldingNLP`), so a learner typing the conjunction `e`
  gets `CORRECT_SLOPPY` amber on a drill whose whole point is `è`. Keep such a drill only where
  the sentence makes `e` impossible, and say so in the hint.
- **Do not straddle an elision with the blank.** `Il libro, l'{{answer}} già letto.` and `Era
  possibile che lei l'{{answer}} dimenticato.` split `l'ho` / `l'avesse` across the boundary; put
  the whole elided form in the answer or pick a consonant-initial verb.
- **Never put an article inside a multi-word answer.** `ItalianNLP.leading_articles` strips a
  leading `il/lo/la/i/gli/le/un/uno/una/l'`, and a *different* article now grades `WRONG_FORM` on
  grammar cards ("Wrong article — check the gender") — but `il` vs `l'` is an elision error, not a
  gender one, and gets that same misleading message. Italian has zero multi-word answers; keep it so.
- **Keep `ci sono` agreeing** (never `*c'è due caffè`), and keep `Lei` capitalised as the formal you.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `data/it_frequency.tsv` has 622 one-word noun
  glosses, several wrong by omission: `radio` → *radius* (but `la radio` is the radio), `porta` →
  *gate; door* (also *he/she carries*), `banco` → *desk; counter* (also *bank*). Where the gender
  selects the sense — `il capitale` money / `la capitale` city, `il fine` purpose / `la fine` end —
  both go in.
- **Noun definitions carry gender.** `(m.)` or `(f.)` on every learner-facing noun gloss. Today
  the vocab layer marks gender in **2 of 3939** noun rows while `data/it_morphology.json` knows it
  for 4441 words: the data exists and is never surfaced.
- **Register:** neutral standard Italian. Formal items stay labelled (`Lei` hints say *formal*);
  the C2 *registro formale* idioms (`a mio avviso`, `in ogni caso`) and the C1 *passato remoto*
  stay in their level and are marked literary/formal in the hint.

## Current measured state

From the crawl, re-verified by opening `data/grammar/it_grammar.json`.

- **42 points, 310 drills**, every point `source: contributor`, `reviewed: true`, A1→C2
  (12/14/7/6/3/2 by level). **Zero** empty hints, translations or explanations; zero vague
  translations; zero `answer — explanation` templates; zero multi-word answers.
- **`leak_hard`: 0. `construction_quote` (warn): 3** — every mechanical leak is the parenthesis
  class: `si` → `(si passivante)`; `Si` → `(impersonal si)`; `le` → `them (ce + le)`.
- **`giveaway_by_gloss`: 23.** Worst offenders, all answerable with no Italian at all:
  - `ans='Lei' hint='she' trans='She sings very well.'`
  - `ans='Dove' hint='where' trans='Where do you live?'`
  - `ans='lo' hint='him' trans='Do you know Marco? Yes, I know him well.'`
- **One-word hints: 26** (crawl agrees). Ten are the subject-pronoun glosses above; `singular`,
  `masculine`, `feminine`, `plural` name a feature rather than a translation and fall in the
  agreement-leak class instead.
- **Agreement-feature-only hints: 8 in *Definite articles*, 4 in *Indefinite articles*** — the
  largest quality problem here, and the mechanical checker sees none of it.
- **`duplicate_hint`: 1** — `-are verbs → -ando` maps to both `giocando` and `preparando` in
  *Stare + gerundio*; only the English translation names the verb.
- **Answer printed in its own sentence: 3**, all fronted-clitic topics (quoted above).
  **Accent-only-distinct answers: 5**, all `è`; the accentless `e` grades amber.
- **Gender marking on noun-answer hints: 0.** The crawl reports 10 of 68 (15%); **the file
  disagrees and the file wins** — that join counts verb forms and pronouns that
  `it_morphology.json` mis-records as nouns (`Io`, `sono`, `sei`, `vado`). Six drills have a
  genuinely lexical noun as the answer (`libri`, `case`, `sorelle`, `giardini`, `gatti`,
  `macchine`) and none marks gender; the seven scored "marked" are article and adjective drills
  where the feature *is* the answer.
- **Vocab gloss layer: gender on 2 of 3939 noun rows** in `data/it_frequency.tsv` (columns
  `rank / word / pos / en` — no gender column at all), both incidental (`una — feminine singular
  of uno`). Corpus otherwise healthy: 27,381 sentences plus 186 curated in
  `data/sentences/it_sentences.tsv`, 10,000 frequency rows, gym manifest at `data/gym/it.json`.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language it
.venv/bin/pytest backend/tests/test_nlp_latin.py -q   # ItalianNLP lives here (test_italian_article)
```

There is no `test_nlp_italian.py`; `ItalianNLP` is in `backend/services/nlp/latin_base.py`, covered
only by `test_italian_article` plus shared `AccentFoldingNLP` behaviour — an `è`/`e` case and an
`il`-for-`lo` case belong beside it. Italian is not in `TRANSLIT_LANGS`
(`frontend/src/features/keyboards/translit.ts`), so the transliteration suite does not apply; check
instead that accents survive the answer box. A human reviewer pulls 10 random drills
(`--sample 10`) and asks:

1. **Could I answer this knowing no Italian?** 23 drills fail — `she` under *She sings very well.*
2. **Does the hint state the gender or number under test?** 12 article drills fail.
3. **Answer is a noun — does the hint say `(m.)` or `(f.)`?** All six fail.
4. **Is the answer visible in the sentence?** Three fronted-clitic drills fail.
5. **Does the hint quote an Italian phrase containing the answer?** Three fail; `(impersonal si)`
   is the template to stop copying.
6. **Would the accentless spelling be a different real word?** Five `è` drills accept `e` amber.
7. **Is the register standard Italian?** Dialect forms, courtesy `voi`, or a *passato remoto* used
   as an ordinary past below C1 are out of scope and fail.
