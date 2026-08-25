# German (de) — Content Quality Standards

## Language profile

Latin script, left-to-right, with `ä ö ü` and `ß`; every noun is capitalised. **The authoritative variety is
the standard German of Germany** — the norm described by *grammis* (Leibniz-Institut für Deutsche Sprache),
cited in the `references` of all 43 points in `data/grammar/de_grammar.json`. The drills commit to it: `ß` is
taught and drilled (`größer`, `heißen`), the perfect is the spoken past (`Ich habe gegessen`) while the
Präteritum is framed as narrative/written. **Grading (measured 20 Aug 2026).** `GermanNLP` accepts the substitution German itself
prescribes when the umlaut keys are missing — ä→ae, ö→oe, ü→ue, ß→ss. It did not, and the
result was backwards: `schoen`, the only sanctioned way to write `schön` on an English
keyboard, graded **WRONG** ("a different word"), while `schon` — which really is a different
word — was credited. The digraph is now amber, with the umlaut spelling named; dropping the
umlaut *entirely* (`schon` for `schön`, `musste` for `müsste`, `ass` for `aß`) is failed by
the collision guard, because it lands on another card. The fold sits in `fold_lookalikes`,
not `normalize()`, precisely so the guard can still see it (`docs/quality/CHECKS.md` §3).

Swiss `ss` rides along: out of scope as a *production* target is a statement about what the
course teaches, not about what a learner may type. 24 rows removed to make that work — 7
self-identified "Switzerland and Liechtenstein standard spelling of X", 6 identical-gloss
ß/ss twins, 9 **pre-1996 spellings** (`daß`, `muß`, `bißchen`, `wußte`, `mußte`, `paß`,
`laßt`, `mußt`, `schoß`) whose post-reform forms already sat at far better ranks, and 2
digraph duplicates (`fuer`, `caesar`). `strasse` is in `data/vocab_exclusions.tsv`: its
frequency is Swiss text writing *Strasse* for street, but kaikki joined it to the plural of
*Strass* (rhinestone), so a rank-7512 jewelry term was blocking the ss spelling of rank-721
`straße`.

**Out of scope:** Swiss orthography (`ss` for `ß`) as a *production*
target; Austrian and Swiss lexicon (`Jänner`, `Sackerl`, `Velo`, `Grüezi`); dialect morphology and clitics
(`hab's gsehn`, `des`); the doubled perfect (`ich habe gehabt gehabt`). Recognising them in a culture note is
fine; drilling them is not.

**Gender: three** — `der` / `die` / `das`. `data/de_morphology.json` holds 5614 entries (3740 noun, 1215 verb,
659 adj) and puts an `Article` chip on **3690 of 3740 nouns** (`der` 1505, `die` 1427, `das` 758); 50 nouns have
none (`alias`, `blog`, `eltern`, `ferien`, `dschungel`…). Gender × four cases is the article table every other
point hangs off, and it is not guessable from the noun's shape.

Three features dominate drill quality: (1) the **lemma==answer collision** — the house `infinitive, person`
hint convention destroys itself at the `wir`/`sie` cells, where the form *is* the infinitive; (2) **case +
gender stated in the hint**, which resolves the article without the learner ever knowing the noun's gender;
(3) **umlaut folding in the grader** — `hatte`/`hätte`, `waren`/`wären`, `warst`/`wärst`, `wurden`/`würden`
are one string to layer 2.5 of `backend/services/nlp/base.py`.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already
sitting in the drill's own translation; never the `answer — explanation` template; one hint resolves to exactly
one answer inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and
quoting a German base form is fine while whole German sentences are not.

1. **`lemma, person` is the house style — except where the cell equals the citation form.** German `wir` and
   `sie` present forms *are* the infinitive, so the convention prints the answer. This is 8 of the 18 leaks.
   GOOD: `have — you sg. (auxiliary)` → `hast`; `to listen, I — verb stays second` → `höre` (both already in
   the file). BAD: `haben, wir` → `haben`; `hören, wir` → `hören`; `arbeiten, sie` → `arbeiten`; `spielen, sie`
   → `spielen`. Fix by switching those cells to the English gloss plus person.
2. **Construction quotes blank the drilled token.** GOOD: `in order (… zu)` → `um`; `wait for (warten … +
   acc.)` → `auf`. BAD: `in order (um … zu)` → `um`; `to (sein + zu)` → `zu`; `one/you (man-passive)` → `Man`.
3. **A verb + preposition hint never prints the preposition.** GOOD: `sich freuen … — which preposition?` →
   `auf`. BAD: `to (sich freuen auf)` → `auf`; `of (denken an)` → `an`; `in (sich interessieren für)` → `für`.
4. **Never state the case-and-gender pair the drill exists to test.** `the (dative, fem.)` picks `der` out of
   `{dem, der, den}` on its own — the learner never has to know `Frau` is feminine, which is the entire skill.
   10 drills do this. GOOD: `the — indirect object (who receives?)` → `dem`. BAD: `the (dative, masc.)`,
   `the (genitive, plural)`, `the (accusative masc. — motion)`.
5. **Gloss + full feature spec is the same leak wearing two hats.** GOOD: `old — after the definite article`
   → `alte`. BAD: `old (after 'der', nom. m.)`, `big (after 'einem', dat. n.)`, `hot (no article, acc. m.)`.
6. **Noun answers carry gender.** GOOD: `Tisch (der), plural` → `Tische`. BAD: `book, plural (umlaut)` →
   `Bücher` (says nothing about `das Buch`). Only 2 of the 8 lexical-noun answers mark gender today.
7. **Capitalisation is not a second answer.** Layer 2 lowercases, so `Haben`/`haben` and `Hast`/`hast` are one
   answer to the grader; one hint covering both is correct, not a duplicate-hint violation.

## Question / drill standards

A good drill is a sentence a German speaker would actually say, one blank whose value is fixed by sentence and
hint together, and a translation that renders the *completed* German in natural English. Pitfalls:

- **The stem must not print the answer.** All four *Relative clauses* drills echo the antecedent's article:
  `Der Mann, ▮ dort steht, ist mein Lehrer.`, `Das Buch, ▮ ich lese, ist spannend.`, `Die Kinder, ▮ draußen
  spielen, sind laut.`, `Das Auto, ▮ er gekauft hat, ist rot.` Copying the visible article scores every one and
  teaches a rule that collapses at `dem`, `den`, `dessen`. Use a proper name or a bare plural as the
  antecedent, or drill a non-nominative relative.
- **No German metalinguistic tag inside the sentence.** `Ich gehe in ▮ Küche. (Bewegung)` / `Die Katze schläft
  auf ▮ Tisch. (Ort)` — the parenthetical does the teaching, in German, inside an English-hinted drill. Put
  *motion* / *location* in the hint and let the verb carry the contrast.
- **Never let an umlaut be the only thing under test.** Layer 2.5 strips combining marks and grades
  `CORRECT_SLOPPY` *even on grammar cards*. `hatte` typed for `hätte` (and `waren`/`wären`, `warst`/`wärst`,
  `wurden`/`würden`) passes amber — so *Konjunktiv II* vs *Simple past* and *passive past* cannot be graded as
  written. Give those drills an unambiguous trigger (`Wenn …`, `an deiner Stelle`) and expect the amber.
- **Never a multi-word answer beginning with an article.** `GermanNLP.normalize` strips a leading
  `der/die/das/den/dem/ein/eine/einen `, so `den Mann` and `dem Mann` grade equal. There are **zero** multi-word
  answers today; keep it that way.
- **`Sie` vs `sie` cannot be typed-tested** (layer 2 lowercases). Contrast formal and 3pl in the explanation and
  the hint, never as two answers to be distinguished.
- **ß:** `GermanNLP._fold` maps `ß → ss` at layer 3, so `grosser` for `größer` returns *right word, wrong form*
  on a grammar card. Acceptable, but do not build a point whose only contrast is `ss`/`ß`.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `data/de_frequency.tsv` has **748** single-word noun
  glosses. Wrong by omission today: `bank` → *bench (which people sit on); pew* (misses the financial *Bank*,
  which differs in plural: `Bänke` vs `Banken`); `buch` → *books (accounting records)* for the ordinary word
  *book*; `see` → *lake* with no hint that `der See` is a lake and `die See` is the sea.
- **Noun definitions carry gender, and gender-distinguishes-meaning pairs carry both.** `der See` (lake) /
  `die See` (sea), `das Tor` (gate) / `der Tor` (fool), `die Kiefer` (pine) / `der Kiefer` (jaw) — all three are
  glossed with one gender-free sense today. Format: `Tor (das) — gate; (der) — fool`.
- **Register:** neutral written standard. Keep `du`/`Sie` consistent inside a point; C1–C2 particles (`doch`,
  `mal`, `ja`, `eben`, `wohl`, `schon`) stay at C1–C2 and keep their function labels rather than a translation.

## Current measured state

From the crawl, re-verified by opening `data/grammar/de_grammar.json`.

- **43 points, 304 drills**, every point `source: contributor`, `reviewed: true`, A1→C2 (12/13/7/6/3/2).
  Zero empty hints/translations/explanations, zero vague translations, zero `answer —` templates. Corpus:
  `de_sentences.tsv` 27,936 rows, `de_frequency.tsv` 10,000, gym manifest `data/gym/de.json`.
- **Hint leaks: 18** — the highest of the 27 languages, in three classes.
  - *lemma==answer collision (8):* `haben | haben, wir` ×2, `Haben | haben, sie`, `haben | haben, sie`,
    `hören | hören, wir`, `arbeiten | arbeiten, sie`, `kochen | kochen, wir`, `spielen | spielen, sie`.
  - *construction quote (6):* `um | in order (um … zu)` ×2, `Man | one/you (man-passive)` ×2,
    `zu | to (sein + zu)` ×2.
  - *verb + preposition (4):* `auf | for (warten auf + acc.)`, `auf | to (sich freuen auf)`,
    `an | of (denken an)`, `für | in (sich interessieren für)`.
- **Case+gender feature hints: 10** — 4 in *The dative case*, 4 in *The genitive case*, 2 in *Two-way
  prepositions*. Worst offender: answer `der`, hint `the (dative, fem.)`, sentence `Sie hilft ▮ Frau mit den
  Taschen.` — the hint alone picks the article.
- **Giveaway-by-gloss: 17** (hint ≤3 words appearing verbatim in the drill's own translation) — 12 in *Subject
  pronouns* (`Ich`/`I` under *I live in Berlin.*), 4 in *Question words*, 1 `trotzdem`/`nevertheless`.
  **One-word hints: 29**, matching the crawl.
- **Duplicate hints: 3 real.** A raw scan says 8; five are capitalisation-only pairs (`Haben`/`haben`,
  `Hast`/`hast`, `Habt`/`habt`, `Bist`/`bist`, `Seid`/`seid`) that are one answer to the grader. Real:
  `the more (correlative)` → `Je`, `desto`; `e → i in the du form` → `isst`, `sprichst`; `du imperative — e → i
  survives` → `Hilf`, `Sprich`.
- **Answer visible in its own sentence: 4** — the *Relative clauses* set quoted above.
- **Umlaut-fold collisions where both members are answers in the file: 4** — `hatte`/`hätte`, `waren`/`wären`,
  `warst`/`wärst`, `wurden`/`würden`. Each pair spans two points (*Simple past* vs *Konjunktiv II* /
  *Unreal conditions*; *Past perfect* vs *Konjunktiv II past*; *The passive voice* vs *Konjunktiv II*), so the
  contrast the later point exists to teach is ungradable.
- **Gender on noun-answer hints: 2 of 8.** The crawl's "2/42 (5%)" comes from joining answers against
  `de_morphology.json`, which inflates the denominator: `ich`, `du`, `es`, `habe`, `hast`, `mal`, `ja`, `wohl`
  are all recorded as nouns (they *are* real German nouns — `das Ich`, `die Habe`, `die Hast` — but they are
  homographs of the function words actually being drilled, so the join mis-attributes chips and would show
  `das Ich` in the gym for the pronoun). Trust the file: the genuinely lexical noun answers are the eight
  plurals in *Gender and number of nouns*, and only `Tische` and `Hunde` say `— masculine`.
- **Vocab gloss layer: gender on ~0 of 3937 noun rows** in `data/de_frequency.tsv` (4 rows merely mention an
  article inside prose), while morphology knows the article for 3690 words. The data exists and is never
  surfaced — the same gap Spanish has.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language de
.venv/bin/pytest backend/tests/test_nlp_latin.py backend/tests/test_nlp_base.py -q
```

There is no `test_nlp_german.py`; `GermanNLP` lives in `backend/services/nlp/latin_base.py` and is covered only
through shared `AccentFoldingNLP` behaviour — a German case belongs there (`hatte`/`hätte` must be asserted as
`CORRECT_SLOPPY`, and `den Mann`/`dem Mann` must be asserted to collide, so the fact is pinned rather than
rediscovered). German is not in `TRANSLIT_LANGS`, so the transliteration suite does not apply; check instead
that `ä ö ü ß` survive the answer box. A human reviewer pulls 10 random drills (`--sample 10`) and asks:

1. **Could I answer this knowing no German?** 17 fail on the gloss alone.
2. **Does the hint contain its own answer?** 18 fail — check `lemma, person` cells first.
3. **Does the hint state the case *and* the gender?** 10 fail; that hint replaces the skill being taught.
4. **Is the answer already printed in the sentence?** The four relative-clause drills fail.
5. **Would the answer typed without umlauts be a different real form?** If yes (`hatte`, `waren`, `warst`,
   `wurden`), the drill cannot grade its own contrast.
6. **Answer is a noun — does the hint give `der`/`die`/`das` and the plural?** 6 of 8 fail.
7. **Is the sentence something a speaker would say, with no German metalanguage in it?** Two *Two-way
   preposition* drills fail on `(Bewegung)` / `(Ort)`.

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**20 rows reglossed**, of which **7 were fatal** — the card named a
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
| 59 | `ihn` | accusative of er; him, it (direct object) |
| 70 | `weiß` | I know; he/she/it knows (first/third-person singular present of wissen); (ad |
| 122 | `soll` | should, is to, is supposed to (first/third-person singular present of sollen |
| 129 | `würde` | would (first/third-person singular Konjunktiv II of werden, forming the cond |
| 178 | `glaube` | I believe (first-person singular present of glauben); Glaube (der) — belief, |
| 259 | `warte` | I wait; wait! (first-person singular present and imperative of warten); Wart |
| 412 | `gerne` | gladly, willingly, with pleasure (alternative form of gern; ich hätte gerne  |

Fixes are in `data/gloss_overrides.tsv` as well as `data/de_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang de --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.
