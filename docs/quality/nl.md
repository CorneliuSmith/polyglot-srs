# Dutch (nl) — Content Quality Standards

## Language profile

Latin script, left-to-right; the only diacritics are the trema (`ië`, `coördinatie`) and the accents on `één`
and loanwords. **The authoritative variety is Northern Standard Dutch — the Netherlands norm** codified by the
Taalunie's *Algemene Nederlandse Spraakkunst* (`e-ans.ivdnt.org`), cited in the `references` of the points in
`data/grammar/nl_grammar.json`. The course says so itself: the C2 point *Netherlands vs Flanders* notes that
"official register ('VRT-Nederlands') aligns with the north". **Out of scope as production targets:** Belgian
`gij`/`ge` and *tussentaal* (`Wat zijt gij daar?`, `goesting`, `plezant`, `hesp`) — recognition-only at C2, and
they must never leak into an A1–B2 drill; Afrikaans; the `-t`-less spelling reforms and pre-1996 orthography.

**Gender: two noun classes** — `de` (common, roughly 75% of nouns and *all* plurals) and `het` (neuter,
including every diminutive). **Nothing in the repository stores which is which.** There is no
`data/nl_morphology.json`, `data/nl_frequency.tsv` has only `rank / word / pos / en`, and **0 of its 4580 noun
rows** name the article in the gloss. The single hardest lexical fact in Dutch is unrecorded, so no checker can
verify a `de`/`het` claim and the gym cannot show one.

Three features dominate drill quality: (1) **`de`/`het`**, which controls the article, the adjective `-e`, the
relative pronoun (`die`/`dat`) and the diminutive rule, so hints are permanently tempted to state it; (2)
**English cognacy** — `is`, `was`, `had`, `warm`, `drink` are the same string in the translation, which turns an
ordinary English gloss into a giveaway; (3) **word order** (V2, subclause verb-final, the *tang*), which is
tested by where the blank sits rather than by what fills it.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already
sitting in the drill's own translation; never the `answer — explanation` template; one hint resolves to exactly
one answer inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and
quoting a Dutch base form is fine while whole Dutch sentences are not.

1. **Never name the noun's gender when the article, the relative pronoun or the adjective ending is the
   answer.** `neuter article` picks `het` out of `{de, het, een}` unaided, and `neuter — kind is het` prints the
   answer outright. GOOD: `the definite article — which class is this noun?` → `Het`; `the relative pronoun —
   follow the noun's class` → `dat`. BAD: `neuter — kind is het`; `neuter article`; `het-word`; `de-word`.
2. **Never spell out the rule that the drill exists to make the learner apply.** GOOD: `big — mind the article
   before it` → `groot`. BAD: `een + het-word: NO -e` → `groot`; `een + het-word (idee) — bare form` → `goed`;
   `een + de-word keeps the -e` → `sterke`.
3. **No bare English gloss for a Dutch–English cognate.** `is`, `was`, `had`, `warm`, `mag`, `kan` are the
   translation. GOOD: `3rd person singular of zijn` → `is`. BAD: `is` → `is` (twice in *Zijn — present*, the
   only two hints in the file where hint and answer are the same string).
4. **Fused `er`/`daar`/`waar` + preposition hints blank the drilled half.** GOOD: `trots … → er…▮` → `op`;
   `the preposition that fuses to -mee` → `mee`. BAD: `trots op → er…op` → `op`.
5. **Functional labels beat translations.** `existence` → `er`, `upright` → `staat`, `contained` → `zit`,
   `whether` → `of` are good one-word hints because they name a job, not a word. `my`, `her`, `who`, `where`,
   `when`, `what`, `why` are not — they are lifted straight out of the translation.
6. **One hint, one answer inside a point.** Dutch has **zero** duplicate-hint violations today; the closest
   risk is `singular`/`plural` in *Er is / er zijn*, which is fine because the subject disambiguates.

## Question / drill standards

A good drill is a sentence a Dutch speaker would say, one blank whose value the sentence and hint fix together,
and a translation of the *completed* Dutch. Pitfalls:

- **The English translation must not contain the Dutch answer.** Nine do: `drink`/*I drink coffee.*,
  `is`/*The weather is nice.*, `warm`/*The coffee is warm.*, `was`/*It was cold that winter.*,
  `had`/*I had already eaten when she came.*, `u`/*To an older customer you say u, not je.*,
  `g`/*The 'soft g' colours the southern accent.* Rewrite the English (*I have a coffee*, *the weather's
  lovely*) or move the drill to a non-cognate item.
- **The stem must not print the answer.** `Zijn er nog kaartjes? — Ja, ▮ zijn er nog vijf.` (answer `er`),
  `Verveel je ▮?` (answer `je`), `Wat zou je doen als je de loterij ▮ winnen?` (answer `zou`).
- **No Dutch metalanguage inside the sentence field.** The C2 Flanders drills read `Vlaams voor 'zin': Ik heb ▮
  in frieten.` and `Vlaams informeel 'jij': ▮ zijt gij daar?` — the sentence field holds the sentence; the
  framing belongs in the point explanation.
- **Single letters are not answers.** `De zachte ▮ kleurt het zuidelijke accent.` (answer `g`) tests nothing and
  the translation prints it.
- **Never a multi-word answer beginning with an article.** `DutchNLP.leading_articles` strips `de `, `het `,
  `een `, so `het boek` and `de boek` grade identical. The file's one multi-word answer (`zonnig is`, in
  *Conditionals*) is safe but still brittle — two tokens, two chances to mistype; prefer one.
- **`een` vs `één` cannot be graded.** Layer 2.5 folds the acute away, so the indefinite article and the numeral
  are one string. Never build the contrast into a drill.
- **Word-order points need the blank at the position under test** — for V2 and the *tang*, blank the finite verb
  or the participle, not the adverb, or the learner can satisfy the sentence without moving anything.

## Translation & definition standards

- **Every learner-facing noun gloss carries `de` or `het`.** Nothing does today. Until a gender source exists,
  the grammar-point hints and vocab glosses are the only place a learner can meet the fact, so write
  `huis (het) — house`, `bank (de) — bench; sofa; bank`. This is the top data gap for Dutch.
- **No bare one-word gloss for a polysemous word.** `data/nl_frequency.tsv` has **904** single-word noun
  glosses. **Three of these are FIXED (25 Aug 2026, see the wrong-lexeme sweep below), and
  all three had been recorded here and left unexecuted:** `meer` read *lake* where it is the
  everyday *more*; `wil` read *will*, which an English learner takes as the future auxiliary —
  a function the Dutch word does not have — where it is *I want*; `geef` read *gift*, mis-tagged
  `noun`, where it is *I give* / *give!*. **Still open:** `bank` → *bench; couch, sofa* misses
  the financial *bank* (same article, same spelling) — a missing SENSE rather than a wrong
  lexeme, so the sweep did not catch it.
- **Circular glosses are not definitions:** `meisje` → *diminutive of meid* tells an English speaker nothing —
  `meisje (het) — girl` does.
- **Register:** the `u`/`je` split is itself a C1 point, so keep one register inside a point; Flemish lexicon
  stays labelled *Flemish* wherever it appears.

## Current measured state

From the crawl, re-verified by opening `data/grammar/nl_grammar.json`.

- **42 points, 252 drills**, A1→C2 (12/10/8/6/4/2), 6 drills per point throughout. **Every point is
  `source: "ai"` with `reviewed: false`** — the only course in this group with no human sign-off anywhere, while
  German and Turkish are 100% `contributor` / `reviewed: true`. No point carries a `culture_note` or `related`
  block. Corpus: `nl_sentences.tsv` 23,704 rows, `nl_frequency.tsv` 10,000, gym manifest `data/gym/nl.json`;
  **no morphology file and no seeder module.**
- **Hint leaks: 4** — `Het | neuter — kind is het`; `is | is` ×2 (hint identical to the answer, the strictest
  class of leak); `op | trots op → er…op`.
- **Giveaway-by-gloss: 19** (hint ≤3 words present verbatim in the drill's own translation) — 5 in *Questions:
  inversion and question words* (`Waar`/*where*, `Wie`/*who*, `Wanneer`/*when*, `Wat`/*what*, `Waarom`/*why*),
  2 in *Possessives*, 2 in *Modal verbs*, 2 in *Zijn — present*, and the rest scattered. Worst: answer `Waarom`,
  hint `why`, translation *Why are you tired?* — answerable with no Dutch at all.
- **One-word hints: 29.** The crawl says 27; the file says 29 — trust the file. Roughly half are legitimate
  function labels (`existence`, `upright`, `contained`, `whether`, `informal`, `de-word`, `het-word`,
  `singular`, `plural`), the rest are the glosses above.
- **Answer printed in the English translation: 9**, listed under drill standards. This class is
  Dutch-specific — the crawl's cross-language rules do not look for it, and it is the largest real leak surface
  in the file.
- **Duplicate hints: 0. Empty hints/translations/explanations: 0. Vague translations: 0.** Genuinely clean.
- **Gender data: absent everywhere.** 0 of 4580 noun rows in `nl_frequency.tsv` mention `de`/`het`; there is no
  `data/nl_morphology.json` to hold an `Article` chip the way `data/de_morphology.json` does for 3690 German
  nouns. Every `de`/`het` claim in the course is unverifiable by machine.
- **Register and variety mixing:** the C2 Flanders point puts `gij`/`zijt` and Flemish lexicon into drill
  *sentences*; it is correctly fenced at C2, and must stay fenced.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language nl
.venv/bin/pytest backend/tests/test_nlp_latin.py backend/tests/test_nlp_base.py -q
```

There is no `test_nlp_dutch.py`; `DutchNLP` lives in `backend/services/nlp/latin_base.py` with
`leading_articles = ("de ", "het ", "een ")` and is covered only through shared `AccentFoldingNLP` behaviour. A
Dutch case belongs there, asserting that `het huis` / `de huis` collide (so nobody adds an article-initial
multi-word answer) and that `een`/`één` collide. Dutch is not in `TRANSLIT_LANGS`, so the transliteration suite
does not apply. A human reviewer pulls 10 random drills (`--sample 10`) and asks:

1. **Could I answer this from the English translation alone?** 19 fail on the gloss, 9 more because the answer
   is literally in the translation.
2. **Does the hint tell me the noun is a `de`-word or a `het`-word?** If yes it has replaced the skill — fails.
3. **Does the hint restate the rule instead of cueing it?** The three *Adjectives: the -e rule* hints fail.
4. **Is the answer visible in the sentence?** Three fail (`er`, `je`, `zou`).
5. **Is the sentence pure Dutch, no metalinguistic preamble?** Two C2 Flanders drills fail.
6. **Would a Fleming and a Dutchman both accept this as standard?** Anything below C2 must be northern standard.
7. **Is this point reviewed by a human yet?** Today the honest answer is no for all 42 — say so when reporting.

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**43 rows reglossed**, of which **23 were fatal** — the card named a
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
| 37 | `weet` | know: I know; you know in weet je; he/she/it knows (present of weten); as a  |
| 41 | `kan` | can, to be able to: I can; he/she/it can; you can in kan je (present of kunn |
| 49 | `wil` | want: I want; he/she/it wants; you want in wil je (present of willen); also  |
| 78 | `kom` | come: I come; come! (present and imperative of komen); also a noun, bowl, ba |
| 80 | `meer` | more (comparative of veel); niet meer — not anymore, no longer; also a noun, |
| 133 | `zit` | sit; be (located, contained): I sit; he/she/it sits (present of zitten); as  |
| 136 | `hou` | keep, hold: I keep, I hold (present of houden); ik hou van je — I love you ( |
| 138 | `kijk` | look, watch: I look; look! (present and imperative of kijken); also a noun,  |

Fixes are in `data/gloss_overrides.tsv` as well as `data/nl_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang nl --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.

### Extended to rank 2000 (25 Aug 2026)

The sweep above covered the top 500. Ranks 501-2000 added **84 rows, 39 fatal**, so the
course total is **127 repaired (62 fatal) through rank 2000**.

The keep rate rose with rank — roughly 30% of candidates were kept in the top 500 against
about 50% below it — which is the expected shape and a check on the pass: deeper in a
frequency list the lexical sense genuinely is more often right, and an over-eager rewrite
would replace a correct gloss with a wrong one.

| rank | word | now reads |
| --- | --- | --- |
| 525 | `erop` | on it, on top of it (the pronominal adverb er + op — het lijkt erop dat, |
| 711 | `leg` | put, lay: I put, I lay; put!, lay! (present and imperative of leggen — l |
| 727 | `stuur` | send: I send; send! (present and imperative of sturen — stuur mij een fo |
| 767 | `hoef` | need, have to: I need; you need in hoef je (present of hoeven, used main |
| 771 | `loop` | walk, run: I walk; walk! (present and imperative of lopen — loop niet zo |
| 787 | `leek` | seemed, looked (like): I/he/she/it seemed (singular past of lijken — ze  |
