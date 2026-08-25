# Spanish (es) — Content Quality Standards

## Language profile

Latin script, left-to-right. Authors drop `ñ`, the acute vowels, `ü` (`vergüenza`), and the opening `¿` / `¡` —
a sentence missing the opening mark is malformed, not a style choice. **The authoritative variety is peninsular
standard Spanish** — the RAE/ASALE norm sequenced by the *Plan Curricular del Instituto Cervantes*, both cited
in `data/grammar/es_grammar.json`'s own `references`. The drills commit to it: `vosotros` is taught and drilled
10 times (`¿Vosotros habláis español?`, `Vosotros vivís cerca de la playa.`), and the lexicon is `coche`,
`móvil`, `autobús`. **Out of scope:** *voseo* (`vos sos`, `vos tenés`) and the Rioplatense paradigm;
Caribbean/Andean regional morphology; the Latin American lexical set (`carro`, `celular`, `computadora`, `jugo`)
as a *production* target. `ustedes` is not out of scope — drilled twice, hinted `you all — formal / Latin
America`: recognised, glossed, never a parallel system.

**Gender:** two noun classes, masculine and feminine — `data/es_morphology.json` carries a `Gender` chip on 4159
of 4231 nouns (2129 m / 2030 f) and nothing else. A residual **neuter** survives off the noun in
`esto/eso/aquello`, `lo` + adjective, `ello` (the demonstratives point already hints `neuter — an unknown thing`
for `esto`). Gender is not guessable: `-a` lies (`el día`, `el problema`, both drilled), `-o` lies (`la mano`).
Three features dominate drill quality: (1) **agreement chains** — article, noun, adjective, participle, clitic
all line up, so hints are permanently tempted to state the feature under test; (2) **the written accent as the
sole distinguisher of tense and mood** (`hablé`/`hable`, `llegarán`/`llegaran`), which the grader forgives by
design; (3) **clitics under topic-fronting** (`¿Las llaves? No las veo.`), where the fronted phrase prints a
homograph of the answer.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already in the
drill's own translation; never the `answer — explanation` template; one hint resolves to exactly one answer
inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and quoting a
Spanish base form is fine while whole Spanish sentences are not.

0. **`lemma, person` is legitimate and is the house style.** 179 hints use it (122 comma, 57 em dash) and **zero
   collide** — no Spanish hint quotes a lemma equal to its own answer, the failure that costs German and
   Romanian real leaks. The checker must use lookarounds, not `\b`: `trabaja` sits inside `trabajar`. GOOD:
   `trabajar, él/ella` → `trabaja`; `haber, yo` → `he`; `escribir, participle agrees with novela` → `escrita`.
1. **Never state the agreement feature the drill exists to test** — the owner's complaint in its true Spanish
   form: no string leaks, the *reasoning step* does. `feminine singular` picks exactly one of `{el, la, los,
   las}`, so the learner never has to know `casa` is feminine. 18 drills. GOOD: `the definite article` for `la`
   in `{{answer}} casa es grande.` BAD: `feminine singular`.
2. **Never state the controlling noun's gender either** — same leak, spelled out. GOOD: `indefinite article —
   check the noun's gender` for `un` in `Hay {{answer}} problema…` BAD: `problema is masculine!`, `mesa is
   feminine`, `idea is feminine`, `día is masculine!`.
3. **No bare English gloss when that gloss is in the translation.** GOOD: `asking about place` for `Dónde` in
   `¿{{answer}} vives?` BAD: `where` — and both sit in that one point today.
4. **Gloss + full feature spec is that leak wearing two hats:** `red — masculine singular` under *The car is
   red* specifies the answer completely. GOOD: `blanco, feminine singular` → `blanca` (lemma given, agreement
   earned). BAD: `red — masculine singular` → `rojo`; `the — feminine plural` → `Las`.
5. **Duplicate hints split by lemma or person.** GOOD: `estar — past-shifted` / `poder — past-shifted`. BAD:
   `present → imperfect` for both.
6. **Do not "fix" a hint that merely starts with English *a*.** All four mechanical leak hits are the
   personal-`a` point, answer `a` colliding with English `a`. `a specific person as object` is a good hint; the
   checker exempts ≤3-char English function words unless the hint equals the answer.
7. **Noun answers mark gender:** `libro (m.), plural` → `libros`. None of the six genuine noun-answer drills
   does this today.

## Question / drill standards

A good drill is a sentence a Spanish speaker would say, one blank fixed by sentence + hint together, and a
translation rendering the *completed* sentence in natural English. Pitfalls:

- **The stem must not print the answer.** `Pase lo que {{answer}}` (answer `pase`) tests copying; the C2
  reduplication *is* an echo construction, so blank the first copy instead. Likewise **topic-fronted clitic
  drills must not front the homograph**: `¿Las llaves? No {{answer}} veo.` shows the learner `Las` — use a
  proper-noun or bare-plural topic.
- **Never let the accent be the only thing tested.** `backend/services/nlp/base.py` layer 2.5 grades an
  accentless answer `CORRECT_SLOPPY` *even on grammar drills*, by explicit design ("coaches, never fails"), so
  `hable` for `hablé` passes amber and the point's contrast with the subjunctive evaporates.
- **Never put an article inside a multi-word answer.** `SpanishNLP.normalize` strips a leading
  `el/la/los/las/un/una/unos/unas `, so `el casa` grades `CORRECT` against `la casa` — verified by running the
  backend, `card_type: "grammar"` included. Spanish has no multi-word answers; keep it so. Capitalisation is
  likewise never tested (layer 2 lowercases): sentence-initial `La` and mid-sentence `la` are one drill to the
  grader, never a duplicate-hint hit.
- **Keep `hay` invariable** (never `*han*`), and keep `vosotros`/`ustedes` consistent within a point.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `data/es_frequency.tsv` has 752 single-word noun glosses,
  several wrong by omission: `pasa` → *raisin* (also *she passes*), `llama` → *flame* (also *llama*, *he
  calls*), `espera` → *wait* (also *she waits*).
- **Noun definitions carry gender.** `(m.)`/`(f.)` on every learner-facing noun gloss; where gender changes
  meaning (`el capital` money / `la capital` city, `el orden` order / `la orden` command) both go in. Nothing
  does this today.
- **Register:** neutral peninsular standard. Formal items stay labelled in the hint (`you — formal singular` for
  `Usted`); C2 literary forms (`-se` subjunctive, `digan lo que digan`) stay in C2.

## Current measured state

From the crawl, re-verified by opening `data/grammar/es_grammar.json`.

- **47 points, 324 drills**, all `source: contributor`, `reviewed: true`, A1→C2 (13/13/8/6/4/3). **Zero** empty
  hints/translations/explanations, zero `hint == translation`, zero vague translations, zero `answer —` templates.
- **Mechanical leaks: 4, all false positives** — *Personal a*, answer `a` inside `a specific person as object`,
  `a person as object`, `a beloved pet counts as a person`, `a specific person`.
- **Giveaway-by-gloss: 10** — `Ella`/`she` (×2), `Nosotros`/`we` (×2), `Él`/`he`, `Yo`/`I` in *Subject
  pronouns*; `Hay`/`there is`; `Qué`/`what`, `Dónde`/`where`, `Cuándo`/`when` in *Question words*. Worst: answer
  `Ella`, hint `she`, translation *She sings very well.* — answerable with no Spanish at all.
- **Gloss + feature spec: 5** — `rojo`/`red — masculine singular`, `pequeño`/`small — masculine singular`,
  `abiertas`/`open — feminine plural`, `Los`/`the — masculine plural`, `Las`/`the — feminine plural`.
- **Agreement-feature-only hints** — the largest leak class here. The `agreement_feature` rule reports 12 for es (19 Aug 2026); the 18 this page used to assert was a hand count on a wider definition. Breakdown below is indicative:
  — 8 *Definite articles*, 2 *Indefinite articles*, 6 *Direct object
  pronouns*, 2 *Double object pronouns*, plus the 4 controller-gender hints above. The largest leak class here,
  and the mechanical checker sees none of it.
- **Duplicate hints: 6 real.** A raw scan says 11, but `La`/`la`, `El`/`el`, `No`/`no`, `Les`/`les`, `Se`/`se`
  are one answer each to the grader. Real: `infinitive after ir a` → `comprar`, `organizar`; `present →
  imperfect` → `estaba`, `podía`; `future → conditional` → `llegarían`, `vendría`; `haber — pluperfect
  subjunctive` → `hubiera`, `hubieras`; `haber — conditional perfect` → `habríamos`, `habrías`; `echo the verb —
  subjunctive` → `pase`, `haga`.
- **Answer printed in its own sentence: 8** — `¿Las llaves? No ▮ veo.`, `¿La película? ▮ vimos anoche.`, `¿Los
  libros? ▮ compré ayer.`, `¿Las fotos? ▮ tengo en el móvil.`, `¿Las llaves? Se ▮ di al portero.`, `Digan lo que
  ▮, seguiré.`, `Pase lo que ▮, estaré contigo.`, `Haga el tiempo que ▮, saldremos.`
- **Accent-only-distinct answers: 4** — `hablé` (vs the real form `hable`), `llegarán` (vs `llegaran`),
  `aprobarás` (vs `aprobaras`), `Cómo` (vs `como`); all four accept the wrong form amber.
- **One-word hints: 14.** The crawl says 13; the file says 14 (the extra is `Se` / `impersonal`) — trust the
  file. Nine are the gloss leaks above; `cause`, `purpose`, `recipient`, `impersonal` name a function, not a
  translation, and pass.
- **Gender marking on noun-answer hints: 0.** The crawl reports 13 of 80 (16%); **the file disagrees and the
  file wins.** That join is inflated by `es_morphology.json` recording verb forms and function words as nouns —
  74 of the 80 are not noun answers. **Six drills have a genuinely lexical noun as the answer** (`libros`,
  `casas`, `hermanas`, `coches`, `mesas`, `gatos`, all in *Gender and number of nouns*) and **none marks
  gender**; the 13 scored "marked" are article/clitic/demonstrative drills where `feminine plural` describes the
  answer's own form.
- **Morphology bugs exposed by that join:** `yo` is a masculine noun with fabricated plural `yos`; `la` is a
  *masculine* noun with plural `las`; `las`, `a`, `somos`, `estáis` are masculine nouns; `es`, `eres` feminine —
  these surface as wrong gender chips in the gym.
- **Vocab gloss layer: gender on 2 of 3789 noun rows** in `data/es_frequency.tsv` (`mires`, `conde`) while
  morphology knows it for 4159 words; the 653 rows that do mention gender are articles and determiners. Data
  exists, never surfaced. Corpus otherwise healthy: 28,011 sentences, 10,000 frequency rows, gym manifest at
  `data/gym/es.json`.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language es
.venv/bin/pytest backend/tests/test_nlp_latin.py backend/tests/test_nlp_base.py -q
```

There is no `test_nlp_spanish.py`; `SpanishNLP` lives in `backend/services/nlp/latin_base.py`, covered only
through shared `AccentFoldingNLP` behaviour — a Spanish case (article stripping, `hablé`) belongs beside the
Catalan one. Spanish is not in `TRANSLIT_LANGS`, so the transliteration suite does not apply; check instead that
accented characters survive the answer box. A human reviewer pulls 10 random drills (`--sample 10`) and asks:

1. **Could I answer this knowing no Spanish?** 10 fail outright, 5 more via `gloss — features`.
2. **Does the hint state the gender or number under test?** 18 fail — `feminine singular` for `la` before `casa`
   is the template to stop copying. Does it name the controlling noun's gender? 4 more fail.
3. **Is the answer visible in the sentence?** 8 fail — five fronted-clitic drills, three C2 echoes.
4. **Answer is a noun — does the hint say `(m.)` or `(f.)`?** All six fail.
5. **Would the accentless spelling be a different real form?** `hablé`, `llegarán`, `aprobarás`, `Cómo` all
   accept the wrong form amber, so the drill cannot teach its contrast.
6. **Does each hint in the point pick exactly one answer?** Six do not.
7. **Is the variety consistent?** `vos sos`, `carro`, `celular` are out of scope; `vosotros`/`ustedes` must not
   swap mid-point.

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**29 rows reglossed**, of which **14 were fatal** — the card named a
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
| 38 | `esto` | this; this thing, this idea (for something unnamed or a whole situation) - n |
| 62 | `he` | I have (from haber - the helper before a past participle: he visto, I have s |
| 77 | `son` | they are; you are (ustedes) - from ser, for identity and lasting traits; son |
| 159 | `pasa` | happens, is going on (que pasa? - what's happening?); he/she/it passes, come |
| 170 | `estado` | been - past participle of estar (he estado aqui, I have been here); also el  |
| 205 | `dije` | I said, I told - preterite of decir (ya dije que no, I already said no); als |
| 278 | `van` | they go, they are going; you (ustedes) go - from ir; van a + inf. - they are |
| 291 | `primera` | first (feminine - la primera vez, the first time); also la primera: first ge |

Fixes are in `data/gloss_overrides.tsv` as well as `data/es_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang es --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.
