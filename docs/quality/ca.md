# Catalan (ca) — Content Quality Standards

## Language profile

Latin script, left-to-right; `·` (punt volat, `l·l`) and the apostrophe of elision
(`l'amic`, `d'aquí`) are the characters authors get wrong most.

**The authoritative variety is standard Central Catalan as codified by the IEC** —
what the grammar file already cites (`GIEC — Gramàtica de la llengua catalana`)
and already writes: `soc` (post-2016, unaccented), `vaig anar`, `vosaltres`,
`el meu / la meva`. **Explicitly out of scope:** Valencian (`sóc`, `la meua`, the
*passat simple* as a living everyday tense) and Balearic (`jo cant`, the article
salat `es/sa`). Valencia may appear as a *place* — `Els meus pares són de
València` — never as a form to produce; a course variant would get its own code.

**Gender:** two classes, masculine and feminine, no neuter; `ca_morphology.json`
encodes exactly these two values. Gender is not deducible often enough to skip
marking: `-a` is a leaky cue (`el dia`, `el problema`), consonant-final nouns
split both ways (`la sal`, `el sol`), and elision hides the article precisely
where it is needed (`l'escola` f. and `l'home` m. look identical). Three features
dominate drill quality: (1) **gender agreement across the whole phrase** —
article, noun, adjective and the weak pronouns `el/la/els/les` all line up;
(2) **elision and contraction** — `l'`, `d'`, `al/del/pel`, `t'espero`, `me'l`,
`se'n` make "exactly one blank" hard to keep clean; (3) **the two past systems** —
*passat perifràstic* (`vaig anar`), the default spoken past, vs the *passat
simple* (`anà`), C1 literary only.


**The course had no correct card for “I am” until 20 Aug 2026.** `soc` (rank 924) — the post-2016 IEC standard spelling — was glossed “stump (of a tree)”, while the deprecated `sóc` at rank 63 carried only a pointer describing itself as superseded. Reglossed; see `docs/quality/CHECKS.md` §3b. `mamà` and `papà` were likewise glossed as the passat simple of *mamar* and *papar* (a tense this page restricts to C1 literary narrative) rather than as “mum” and “dad”.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word;
never a gloss already sitting in the drill's own translation; never the `answer —
explanation` template; one hint resolves to exactly one answer inside a point
(allomorph sets excepted where the sentence disambiguates); hints are in English,
and quoting a base form in Catalan is fine while whole sentences are not.

**1. Every noun hint marks gender, `(m.)` or `(f.)`** — the centerpiece, and the
owner's complaint. Applies to plural noun answers too (mark the lemma's gender).
- GOOD: `house (f.), plural (-a → -es)` for `cases`
- BAD: `house, plural (-a → -es)` — the current text; drills the plural, teaches
  nothing about `la casa`

**2. Never quote a Catalan multiword construction containing the answer** — the
whole of Catalan's leak debt, six drills, all this shape.
- GOOD: `since — formal causal connector, follows 'ja'` for `que`
- BAD: `since (ja que)` — the parenthesis prints the answer

**3. Never state the agreement feature the drill exists to test** — the noun's
gender is the thing being examined, so the hint must not supply it. `feminine
singular` picks exactly one of `{el, la, els, les}`, and the learner never has
to know that `casa` is feminine. No string leaks; the *reasoning step* does.
Identical to the rule in `es.md`, `fr.md` and `it.md` — the Romance courses
are held to one standard, so their debt is comparable.
- GOOD: `the definite article` for `La` in `{{answer}} casa és gran.`
- BAD: `feminine singular`; `the (the house is feminine)`

**4. Weak-pronoun hints mark gender and number, never the bare English gloss** —
English `them` covers `els` and `les`; `him/her` collide with the articles.
- GOOD: `direct object — masculine plural` for `els`
- BAD: `him` for `el` — it appears verbatim in that drill's own translation

**5. Elided forms say so:** `t'`, `l'`, `m'` get `(elided)`, as the file already does.

## Question / drill standards

A good drill is a sentence a person would say, one blank whose filler is uniquely
determined by sentence plus hint, and a translation rendering the *completed*
sentence in natural English. Catalan pitfalls:

- **The blank must not straddle an elision.** `{{answer}}'escola` is two
  decisions. Put the whole `l'` in the answer or pick a consonant-initial noun.
- **Contractions are not free blanks.** `a + el = al`: a blank before a masculine
  noun forces `al`, so the drill tests contraction, not the preposition.
- **Watch homographs when picking the noun.** `set` (seven/thirst), `te`
  (tea/letter name), `seu` (his/cathedral), `sis` (six) all exist as nouns; a
  drill on one cannot be audited mechanically for agreement, and all four raw
  agreement flags in the file are exactly these.
- **No *passat simple* below C1** (point 37, narrative prose only), and **keep
  `hi ha` invariable** — `hi ha cases`, never `*hi han`, however people speak.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `cap` is *head*, *boss*,
  *none*, *toward*; `pot` is *jar* and *he can*. The gloss disambiguates, and the
  drill's translation matches the sense actually used.
- **Noun definitions carry gender.** Every learner-facing noun gloss states `(m.)`
  or `(f.)` — without it the vocab layer teaches a word the learner cannot put an
  article on. Where gender changes meaning (`el capital` / `la capital`), both go in.
- **Register:** neutral standard Catalan; formal items (`al meu parer`, `no obstant
  això`) stay in the C2 point, labelled formal in the hint as the file already does.

## Current measured state

From the crawl, re-verified against the files on disk.

- **`data/grammar/ca_grammar.json`: 42 points, 307 drills**, every one
  `source: contributor`, `reviewed: true`, A1→C2. No empty hints, translations or
  explanations; no vague translations; no duplicate hints (the five same-hint
  pairs are case variants of one answer — `Hi`/`hi`, `Has`/`has`).
- **`data/ca_morphology.json`: 4786 entries** — 3150 nouns, 912 adjectives, 724
  verbs. **A `Gender` chip sits on 3085 of 3150 nouns (98%)**, `masculine` (1511)
  / `feminine` (1574); `Plural` on 2977. *The gender data exists.*
- **`data/ca_frequency.tsv`: 10000 rows, columns `rank / word / pos / en` — no
  gender column at all.** Of 3992 noun rows, **4** mention gender in the gloss,
  all incidentally (`gossos — masculine plural of gos`). This is the real bug
  behind "Catalan has gender problems": the data exists and is never surfaced.
- **Gender marking on drill hints: 2 of 36 (6%)** by the crawl's exact-lemma
  join; folding in plural forms gives 3 of 46. Both are inflated by homographs
  (`soc`, `sou`, `vas`, `no`, `fem` are real nouns *and* the drilled verb forms).
  **Trusting the file over the join: 9 drills have an answer that is genuinely a
  noun in context, and 0 of the 9 mark gender** — the two the crawl scored as
  marked are article drills (`La` → `feminine singular`). The honest number is zero.
- **Article–noun agreement: 141 `article + known-noun` pairs checked, 4 raw
  mismatches, 0 confirmed wrong.** All four are homograph false positives —
  `a les set` / `a les sis` (elliptical `hores` vs the numerals recorded as
  masculine nouns), `Els seus resultats` (possessive vs `seu` = cathedral),
  `el te val poc` (tea vs the letter name). **No drill puts the wrong article on
  a noun.** But the check audits the morphology, and the morphology loses: `te`
  is recorded `Gender: feminine` only (tea is `el te`, masculine), `sis` is a
  masculine noun with the fabricated plural `sisos`, `seu` is feminine.
- **Hint leaks: 6, all construction-quote**, quoted: `que` → `since (ja que)`;
  `cas` → `case (en tot cas)`; `en` → `any (dislocation with en)`.
- **One-word hints: 24. Hint-appears-in-own-translation: 20** — `she` under *She
  is my sister.*, `where` under *Where do you live?*, `him` under *…I know him well.*
- **Grading gap, verified by running `CatalanNLP`:** `normalize()` strips a
  leading `el/la/els/les/un/una/uns/unes/l'`, so a wrong-gender article grades
  `CORRECT` — `la te` against `el te`, `el casa` against `la casa`, both pass
  silently. Stripping is right for a *missing* article; it must not launder a
  *wrong* one. A fix belongs in `backend/services/nlp/latin_base.py` with a test
  beside `test_catalan_article`.
- Corpus otherwise healthy: 5389 + 185 curated sentences, gym manifest present.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language ca
.venv/bin/pytest backend/tests/test_nlp_latin.py -q   # Catalan lives here (test_catalan_article)
```

Catalan is not in `TRANSLIT_LANGS`, so the transliteration suite does not apply.
A human reviewer pulls 10 random drills (`--sample 10`) and asks, in order:

1. **Answer is a noun — does the hint say `(m.)` or `(f.)`?** Every such drill
   fails this today; the six in *Gender and number of nouns* (`llibres`, `cases`,
   `germanes`, `jardins`, `gats`, `cadires`) are first to fix.
2. **Does the hint contain the answer inside a quoted Catalan phrase?** Six fail;
   `since (ja que)` is the template to stop copying.
3. **Could I answer this knowing no Catalan?** Hint `she` under *She is my
   sister* — yes, and that is a failure, 20 drills over.
4. **Does the article agree with the noun's real gender?** Check against
   `data/ca_morphology.json`; if it disagrees, suspect the morphology first —
   `te`, `sis`, `seu` are already known wrong there.
5. **Is the register standard Central Catalan?** Any `sóc`, `meua`, `es/sa`, or a
   *passat simple* below C1 is out of scope and fails. And does the blank straddle
   an elision or contraction without the hint saying so?

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**33 rows reglossed**, of which **23 were fatal** — the card named a
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
| 18 | `va` | did (third-person singular present indicative of anar; with an infinitive it |
| 60 | `era` | I/he/she/it was (first/third-person singular imperfect indicative of ser); a |
| 66 | `estic` | I am (first-person singular present indicative of estar — state, location, o |
| 81 | `fa` | he/she/it does, makes (third-person singular present indicative of fer); ago |
| 83 | `vas` | you go (second-person singular present indicative of anar; with an infinitiv |
| 94 | `pot` | he/she/it can, is able to (third-person singular present indicative of poder |
| 102 | `tens` | you have (second-person singular present indicative of tenir); also tense, t |
| 111 | `dit` | said, told (past participle of dir); also (m.) finger, toe |

Fixes are in `data/gloss_overrides.tsv` as well as `data/ca_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang ca --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.

### Extended to rank 2000 (25 Aug 2026)

The sweep above covered the top 500. Ranks 501-2000 added **56 rows, 38 fatal**, so the
course total is **89 repaired (61 fatal) through rank 2000**.

The keep rate rose with rank — roughly 30% of candidates were kept in the top 500 against
about 50% below it — which is the expected shape and a check on the pass: deeper in a
frequency list the lexical sense genuinely is more often right, and an over-eager rewrite
would replace a correct gloss with a wrong one.

| rank | word | now reads |
| --- | --- | --- |
| 509 | `creu` | he/she/it believes, thinks (third-person singular present indicative of  |
| 521 | `sola` | alone, on her own (feminine of sol): visc sola, I live alone; single, on |
| 593 | `posa` | he/she/it puts, places (third-person singular present indicative of posa |
| 612 | `surt` | he/she/it goes out, leaves, comes out (third-person singular present ind |
| 631 | `troba` | he/she/it finds (third-person singular present indicative of trobar); es |
| 639 | `feu` | you (plural) do, make (second-person plural present indicative of fer):  |
