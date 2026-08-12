# Greek (el) — Content Quality Standards

## Language profile

Greek alphabet, left-to-right, 24 letters, **monotonic** orthography — one accent (τόνος) on the
stressed vowel, nothing else. Two script facts drive everything below. First, **sigma has two shapes:
σ everywhere, ς word-finally** — a position rule, not a letter contrast, and `GreekNLP.normalize()`
folds `ς → σ` before grading, so *the grader cannot tell them apart and no drill or hint may depend on
the difference* (`τέλοσ` grades CORRECT against `τέλος`, pinned by
`backend/tests/test_typed_input.py::TestGreekFinalSigma`; the keyboard finalises it). Second, **the grader also folds the tonos** — layer 2.5 of `check_answer` strips
combining marks, so `πως` against `πώς` returns CORRECT_SLOPPY ("check the accents") *even on grammar
cards*, where every other form error returns WRONG.

**The authoritative variety is Standard Modern Greek** — demotic-based, Athens standard, monotonic,
neutral everyday register, what the file writes from A1 (`Είμαι από την Αθήνα`) to C2. The learned
Katharévousa layer is in scope **only as C2 register vocabulary** (`εντούτοις`, `οφείλω`, `καθότι`,
fixed `εν` phrases), never as the norm. **Out of scope:** Ancient and Koine Greek, polytonic
orthography, Katharévousa as a target grammar, Cypriot and other dialects, and Greeklish.

**Gender: three** — masculine, feminine, neuter — carried by the article (ο / η / το) and echoed by
every adjective, participle and demonstrative in the phrase; `data/el_morphology.json` holds 6158
entries, 5687 with a `Gender` chip, the best gender coverage in the repo. Three features dominate
drill quality: (1) **three-way agreement**, so a hint naming a form but not its gender has done half
the job; (2) **politeness** — the 2nd-person plural is also the polite singular (`εσείς`, `είστε`,
`έχετε`), so "you (plural)" is often wrong; (3) **the two folded contrasts above**, which silently
make some drills ungradeable.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss
already sitting in the drill's own translation; never the `answer — explanation` template; one hint
resolves to exactly one answer inside a point (allomorph sets excepted where the sentence
disambiguates); hints are in English, and a quoted base form in Greek is fine, whole sentences not.

**1. A "fixed phrase" gloss is not a licence to print the answer.** All three leaks are this shape.
- BAD: `in (fixed phrase εν πάση περιπτώσει)` for `εν` — GOOD: `learned preposition, dative only`
- BAD: `although (αν και)` for `αν` — GOOD: `pairs with the following και to mean 'although'`

**2. Mark gender with the citation article, not a letter code.** `ο/η/το` *is* the gender marker and
cannot collide with the English translation — the house convention, which the checker under-counts.
- GOOD: `friends (ο φίλος)`, `doors (η πόρτα)`, `books (το βιβλίο)` — the whole *Plural of nouns* point
- BAD: `opinion (fixed phrase)` for `γνώμη` — no article, no gender, "opinion" is in the translation

**3. Person hints on verbs must separate plural from polite.** The 2pl form is both; the file's
`you — plural/formal` for `Εσείς` is the model, its verb hints are not.
- BAD: `to have, you (plural)` for `έχετε` — GOOD: `to have — 2nd plural, also the polite singular`

**4. Never gloss a closed-class answer with the English word standing in the translation.** 37 drills
do; for pronouns, question words and prepositions that gloss *is* the answer key.
- BAD: `she` for `Αυτή` under *She is my sister.* — GOOD: `3rd person feminine — pronoun for emphasis`
- BAD: `from` for `από` under *I came from Athens yesterday.* — GOOD: `origin — takes the accusative`

**5. One hint, one answer inside a point.** *Reported speech* maps `that (statement)` to `ότι` **and**
`πως`, both grammatical in both sentences.
- BAD: `that (statement)` twice — GOOD: `that — the ότι form` / `that — the shorter πως, after νομίζω`

**6. Never build a hint on a distinction the grader folds.** `where — with the accent` (πού vs που) or
`when, not never` (πότε vs ποτέ) promises a strictness `check_answer` does not deliver: both spellings
return CORRECT_SLOPPY. Teach the accent in the explanation; never write `remember the final form`.

## Question / drill standards

A good drill is a sentence a Greek would actually say, one blank whose filler is fixed by sentence plus
hint, and a translation of the *completed* sentence in natural British English — the file is already
British (*centre*, *cinema*, *neighbours*). All 287 drills carry a `transliteration` and exactly one
single-word `{{answer}}`; keep it that way. Pitfalls:

- **Do not split a fixed collocation across the blank.** `{{answer}} και ήταν αργά…` for `αν` drills
  half of `αν και`, forcing the hint to leak the other half.
- **The sentence must be Greek before it is a drill.** `Θα το κάνω {{answer}} ώρας.` → `εν` is not
  Greek: `εν` governs the dative (`εν ώρα`, `εν καιρώ`, `εν πάση περιπτώσει`), never genitive `ώρας`,
  and the English *in due course* renders `εν ευθέτω χρόνω` — which appears only in the hint.
- **The translation must translate.** `Προσέξτε προσεκτικά όταν περνάτε τον δρόμο.` is tautological
  Greek ("be careful carefully") and the English drops `προσεκτικά` — write `Προσέχετε όταν περνάτε
  τον δρόμο.`
- **Pronoun scaffolding is allowed, sparingly.** Every 2pl drill opens `Εσείς …` to fix the person,
  while point 1 teaches that Greek drops the pronoun except for emphasis. A crutch, not a model.
- **Accents go on every Greek word, capitals included** (`Πού`, `Πώς`, `Εγώ`), and the transliteration
  must track the answer. **Vary the answer**: *Comparative & superlative* answers `πιο` in all six
  drills, so the hint carries the entire load — alternate the adjective or the `από` complement.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `πότε` is *when* and `ποτέ` is *never*; `μπορεί`
  is *he can* and *maybe*; `που` is *that/which* and, accented, *where*. Gloss the sense the drill uses.
- **Noun definitions carry gender**, written as the article: `ο δρόμος — street`, `η πόρτα — door`,
  `το παιδί — child`. The morphology knows this for 5687 entries; the gloss layer rarely says it.
- **No metalinguistic non-glosses.** `data/el_frequency.tsv` rank 2 glosses `το` as *"inflection of ο
  (o, "the"):"* — a parse, not a meaning — and rank 11 `την` as *"feminine accusative singular of ο"*.
  Worse, rank 1: `να` is glossed only as the deictic *"there, here"*, omitting the subjunctive particle
  that is nearly every occurrence of the word in this course.
- **Register consistency:** everyday demotic in A1–C1, the learned layer glossed *as* formal
  (`οφείλω — I ought (formal for πρέπει)`). British English throughout.

## Current measured state

From `data/grammar/el_grammar.json`: **41 points, 287 drills** — A1 12, A2 11, B1 7, B2 6, C1 3, C2 2.
Every drill has a transliteration, every point is `reviewed: true`, 39 of 41 have an empty
`culture_note`. Support data: `el_sentences.tsv` 10 919 rows, `el_frequency.tsv` 10 000,
`el_morphology.json` 6158 entries (5687 with gender). Fail-level counts, re-checked against the file:

| Rule | Count | Note |
| --- | --- | --- |
| `leak_hard` | 3 | all "fixed phrase" hints |
| `self_answering` | 0 | no `answer — explanation` template here |
| `giveaway_by_gloss` | 37 | pronouns, question words, prepositions, possessives |
| `duplicate_hint` | 1 | plus 2 capitalisation pairs (`Υπάρχει`/`υπάρχει`) that are not real |
| `empty` | 0 | — |

Warn level: **52 one-word hints, the most in the repo**; gender marked on **7 of 21** noun-answer
hints (33%, the repo's best rate and still low — and it misses the six article-convention hints in
*Plural of nouns*). Worst offenders, quoted:

1. *Register & fixed expressions*, drill 6 — `Θα το κάνω {{answer}} ώρας.` / `εν` / `in (fixed phrase
   εν ευθέτω χρόνω / εν ώρα)`. Leaks the answer, quotes a phrase the sentence lacks, is ungrammatical.
2. *Subordinating connectors*, drill 3 — `{{answer}} και ήταν αργά, συνεχίσαμε τη συζήτηση.` / `αν` /
   hint `although (αν και)`. The collocation is split by the blank, so the hint has to give it away.
3. *Reported speech*, drills 1 and 3 — `that (statement)` for both `ότι` and `πως`; nothing in either
   sentence chooses between them.

**Correction to the crawl.** The crawl calls `πωσ` in *Reported speech* a typo "missing its accent".
The file is right and the crawl wrong twice: the stored answer is `πως` (U+03C0 U+03C9 U+03C2 — the
final sigma is there; the crawl's scanner folded `ς → σ` before printing), and tonos-less `πως` is the
**correct** conjunction, since `πώς` means *how*. The defect there is the duplicate hint; the crawl's
`duplicate hints 1` also under-reports a raw 3, the other two being capitalisation pairs.

## Testing checklist

```bash
# mechanical audit (lands with this change; may not exist in an older tree)
python -m backend.services.quality.audit_content --language el

# no test_nlp_greek.py exists — sigma folding and the shared accent pipeline live here
.venv/bin/pytest backend/tests/test_typed_input.py -k Greek -q
.venv/bin/pytest backend/tests/test_nlp_base.py -q
# el is in TRANSLIT_LANGS: typing + final-sigma finalisation
cd frontend && npx vitest run src/__tests__/translit
```

What a human reviewer spot-checks — 10 random drills, asking of each:

1. Could I answer it from the hint alone, without Greek? `she`, `where`, `from`, `my` fail (37 drills).
2. Does the hint quote the answer, or the phrase the answer belongs to? Fails (3 drills).
3. Does a noun / adjective / participle hint name the gender via `ο/η/το`? Fails 14 of 21 noun drills.
4. Is a 2nd-plural verb hinted "plural" only, where the sentence also reads as polite singular? Fails.
5. Would another Greek word fit blank and hint equally well (ότι/πως, θα/να, τη/την)? Fails.
6. Is the Greek natural (no tautology, no split collocation, no preposition on the wrong case) and
   does the English translate the whole completed sentence, in British English?
7. Is every accent present, capitals included, and does the transliteration match the answer?
8. Does the drill hinge on the tonos or on σ/ς? Then it is ungradeable — rewrite it.
