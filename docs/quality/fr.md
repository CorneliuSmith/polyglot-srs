# French (fr) — Content Quality Standards

## Language profile

Latin script, left-to-right. Authors drop the accents (`é è ê à ù ô î`), the cedilla (`ç`), and the
ligature `œ` (`sœurs`, spelled correctly in the file); the elision apostrophe is ASCII `'` (U+0027)
in all 93 places `data/grammar/fr_grammar.json` uses it, and must stay ASCII.
**The authoritative variety is standard metropolitan French.** The file commits: `vous` is the
polite singular, `on` is taught as the spoken "we" alongside `nous`, and the full `ne … pas` frame
is the production target — the A1 culture note says the spoken drop of `ne` comes "later, like the
locals", so `je parle pas` is recognised, never drilled. **Explicitly out of scope:** the Belgian
and Swiss numerals (`septante`, `huitante`, `nonante`), Québécois morphology and lexicon, and
`ne`-less negation as a form to produce. The *passé simple* is quarantined at C1, the
`subjonctif littéraire` / `ne explétif` at C2.

**Gender:** two classes, masculine and feminine, no neuter. `data/fr_morphology.json` carries a
`Gender` chip on 4576 of its 4652 nouns (2517 m / 2059 f) and `Plural` on 4293. **Adjectives carry
only a `Plural` chip — no feminine form at all** (1022 entries), so the gym cannot show
`blanc → blanche` even though the A1 point drills exactly that. Gender is unguessable and usually
invisible: elision hides it (`l'école` f. and `l'homme` m. look identical) and the plural `-s` is
silent, so the article is the only audible carrier of both gender and number. Three features
dominate drill quality: (1) **elision** — `l'`, `d'`, `j'`, `n'`, `qu'`, `t'` — which makes
"exactly one unambiguous blank" genuinely hard; (2) **gender agreement across the phrase**,
including the past participle after a preceding direct object (`les photos que j'ai prises`);
(3) **the clitic zoo** — `le/la/les`, `lui/leur`, `y`, `en`, two-pronoun order — where the hint is
permanently tempted to quote the pattern it is testing.


**Wrong-lexeme glosses corrected 20 Aug 2026** (`CHECKS.md` §3b): rank 235 `dû` was glossed as the noun “what is owed” rather than the past participle of *devoir*; rank 1099 `fut` as “post-1990 spelling of fût” (a cask) rather than the passé simple of *être* — the file's own rank 4682 `furent` proves the lemma. Also `bouge`, `téléphoné`, `chassé`, `doublé`, each glossed from a rare noun sense.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss
already in the drill's own translation; never the `answer — explanation` template; one hint
resolves to exactly one answer inside a point (allomorph sets excepted where the sentence
disambiguates); hints are in English, and quoting a French base form is fine while whole French sentences
are not.

0. **`lemma, person` is house style and legitimate** (`être, il` → `est`), so the checker must match
   with lookarounds, not `\b` — `as` sits inside `passé`.
1. **Never quote the French construction that contains the answer** — the whole of French's leak
   debt, 10 drills, every one this shape.
   - GOOD: `causal connector — links two clauses, more formal than parce que` for `car` in
     `Je reste ici {{answer}} j'attends un ami.`
   - BAD: `because (car)` — the parenthesis literally prints the answer. Same failure in
     `while (en + participle)` → `en`, `some (y + en)` → `en`, `what (ce qui, subject)` → `qui`,
     `(expletive ne after avant que)` → `ne`.
2. **Article hints name the trigger, not the gender.** `feminine singular` picks exactly one of
   `{le, la, les}`, so the learner never has to know `maison` is feminine.
   - GOOD: `the definite article` for `La` in `{{answer}} maison est grande.`
   - BAD: `feminine singular` / `masculine singular` / `masculine` / `feminine` — six drills
     across *Definite articles* and *Indefinite articles*.
3. **Noun answers mark gender, `(m.)` or `(f.)`, including plural answers** (mark the lemma's).
   - GOOD: `book (m.), plural — the -s is silent` for `livres`
   - BAD: `book, plural` — the current text in all six *Gender and number of nouns* drills.
4. **Elided answers say so, and say what the full form is.** The file already does this well:
   `you (sg., elided)` → `t'`; `it (elided before a vowel)` → `l'`; `that (object, elided before
   il)` → `qu'`. Keep it, and keep the apostrophe on the same side of the blank throughout a point.
5. **A conjugation hint names the person when the point drills more than one.**
   - GOOD: `avoir — ils` → `aient`, `avoir — vous` → `ayez`
   - BAD: `have (past subjunctive of avoir)` for both — French's only duplicate hint.

## Question / drill standards

A good drill is a sentence a French speaker would actually say, one blank fixed by sentence + hint
together, and a translation that renders the *completed* sentence in natural English. Pitfalls:

- **The blank must not split an elision — and the file is inconsistent about this today.** In
  *Reported speech* the apostrophe sits in the sentence and the answer is bare: `Il dit
  {{answer}}'il est fatigué.` (answer `qu`). In *Relative pronouns* and *Emphasis* it sits in the
  answer: `La voiture {{answer}} il a achetée est rouge.` (answer `qu'`). A learner who types the
  other one is graded **`WRONG`** — verified by running `FrenchNLP`: `'` is not in
  `_TRAILING_PUNCT`. **Pick one convention: the apostrophe belongs to the answer.** Fourteen drills
  place a blank against an apostrophe (`J'{{answer}}`); that is fine where the elision is on a
  *different* word, `{{answer}}'il` is not.
- **The fronted topic must not print the answer.** `Nous sommes là; tu {{answer}} entends?`,
  `Vous {{answer}} amusez à la fête?`, `La lettre, je {{answer}} lui ai déjà envoyée.` all show a
  capitalised homograph of the answer.
- **Never put an article inside a multi-word answer.** `FrenchNLP.leading_articles` strips a leading
  `le/la/les/un/une/des/du/l'`, and a *different* article now grades `WRONG_FORM` on grammar cards
  — but the message says "Wrong article — check the gender", which is wrong for `le école` →
  `l'école`: `l'` encodes no gender at all. French has zero multi-word answers today; keep it so.
- **Be consistent about the French space before `? ! ; :`.** 30 drill sentences have it
  (`{{answer}} habites-tu ?`), 39 do not (`Tu {{answer}} fini tes devoirs?`) — inside one file.
- **Keep `il y a` invariable**, and keep `tu`/`vous` consistent within a point.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word** — and in French the gender often *is* the
  disambiguator. `data/fr_frequency.tsv` has 843 one-word noun glosses; the ones that hurt:
  `livre` → *book* (but `la livre` is a pound), `voile` → *veil* (but `la voile` is a sail),
  `vase` → *silt, mud* (which is `la vase`; `le vase` is the vase, and the gloss says neither).
- **Noun definitions carry gender.** `(m.)`/`(f.)` on every learner-facing noun gloss; where the
  gender selects the sense (`le livre` / `la livre`, `le tour` / `la tour`, `le poste` / `la poste`)
  both go in. Today the vocab layer marks gender in **8 of 4363** noun rows while
  `data/fr_morphology.json` knows it for 4576 words.
- **Register:** neutral standard French. Formal items stay labelled (`(formal)`, `(literary)`, as
  the C2 point already tags its translations); `on` for `nous` stays marked informal.

## Current measured state

From the crawl, re-verified by opening `data/grammar/fr_grammar.json`.

- **42 points, 306 drills**, every point `source: contributor`, `reviewed: true`, A1→C2
  (12/11/8/6/3/2 by level). **Zero** empty hints, translations or explanations; zero vague
  translations; zero `answer — explanation` templates; zero multi-word answers.
- **`leak_hard` and `construction_quote`** — the largest such class in the Romance group. The
  same drills score under both rules, because a quoted construction containing the answer is
  also a hard leak; the audit reported 10 and 10 on 19 Aug 2026. *This line read "`leak_hard`: 0"
  until 19 Aug, contradicting the tool.* Run `python -m backend.services.quality.audit_content --language fr` for the current figure; this page previously froze one and it drifted.:
  - `ans='car' hint='because (car)' sent="Je reste ici {{answer}} j'attends un ami."`
  - `ans='ne' hint='(expletive ne after avant que)'` in `Partez avant qu'il {{answer}} soit trop tard.`
- **`giveaway_by_gloss`: 24.** Worst: `ans='Elle' hint='she' trans='She sings very well.'`;
  `ans='Où' hint='where' trans='Where do you live?'`; `ans='les' hint='them'`.
- **One-word hints: 27** (crawl agrees). Eight are subject-pronoun glosses; `plural`, `masculine`,
  `feminine` fall in the agreement-leak class instead.
- **`duplicate_hint`: 1** — `have (past subjunctive of avoir)` maps to `aient` and `ayez` in *The
  past subjunctive & sequence of tenses*; the sentence disambiguates (`ils` vs `vous`), so it is
  borderline, but it breaks the file's own `lemma — person` style.
- **Answer printed in its own sentence: 4. Elision split across the blank: 2** (`{{answer}}'il`,
  answer `qu`), against 2 drills that put `qu'` in the answer. **Accent-only-distinct answers: 2** —
  `Où`/`où` (vs `ou` "or"); folding grades `ou` amber.
- **Gender marking on noun-answer hints: 0.** The crawl reports 17 of 81 (21%); **the file
  disagrees and the file wins** — that join counts verb forms and pronouns `fr_morphology.json`
  mis-records as nouns (`Elle`, `est`, `as`, `a`, `pas`). Six drills have a genuinely lexical noun
  as the answer (`livres`, `maisons`, `sœurs`, `jardins`, `chats`, `voitures`) and none marks
  gender; the twelve scored "marked" are article/adjective drills where the feature *is* the answer.
- **Vocab gloss layer: gender on 8 of 4363 noun rows** in `data/fr_frequency.tsv` (columns
  `rank / word / pos / en` — no gender column), all incidental (given names). Corpus otherwise
  healthy: 27,849 sentences plus 180 curated in `data/sentences/fr_sentences.tsv`, 10,000 frequency
  rows, gym manifest at `data/gym/fr.json`.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language fr
.venv/bin/pytest backend/tests/test_nlp_latin.py -q   # FrenchNLP lives here (test_french_elision_article)
```

There is no `test_nlp_french.py`; `FrenchNLP` is in `backend/services/nlp/latin_base.py`, covered by
`test_french_elision_article` plus shared `AccentFoldingNLP` behaviour — a `qu` / `qu'` case and a
`le école` → `l'école` message case belong beside it. French is not in `TRANSLIT_LANGS`
(`frontend/src/features/keyboards/translit.ts`), so the transliteration suite does not apply; check
instead that `é è ç œ` survive the answer box. A reviewer pulls 10 random drills (`--sample 10`)
and asks:

1. **Could I answer this knowing no French?** 24 drills fail — `she` under *She sings very well.*
2. **Does the hint quote a French phrase containing the answer?** 10 fail; `because (car)` is the
   template to stop copying.
3. **Does the blank split an elision, and is the apostrophe on the same side as elsewhere in the
   point?** Two `{{answer}}'il` drills fail.
4. **Does the hint state the gender or number under test?** Six article drills fail. **Answer is a
   noun — does the hint say `(m.)` or `(f.)`?** All six fail.
5. **Is the answer visible in the sentence?** Four fail.
6. **Is the typography consistent** (space before `? !`, ASCII apostrophe, `œ` not `oe`)? 39 drills
   fail the first.
7. **Is the register standard metropolitan French?** `septante`, Québécois forms, or a *passé
   simple* below C1 are out of scope and fail.
