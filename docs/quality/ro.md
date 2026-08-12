# Romanian (ro) — Content Quality Standards

## Language profile

Latin script, left-to-right, five diacritics: `ă â î ș ț`. **`ș` and `ț` must be the comma-below
characters U+0219 / U+021B, never the Turkish cedillas `ş`/`ţ`** — `data/grammar/ro_grammar.json`
is clean today (68 `ș`, 72 `ț`, zero cedillas) and must stay so; a cedilla is a near-identical glyph
that silently forks every string comparison outside the folding path.
**The authoritative variety is standard literary Romanian** as codified by the Academy and
`dexonline.ro`, the reference the file cites in every point. It commits: `sunt` (37 uses, never the
older `sînt`), `dumneavoastră` as the formal you, and the *perfectul simplu* quarantined at C2 as
"the literary layer". **Explicitly out of scope:** the Moldovan variant and Cyrillic orthography;
the Oltenian everyday *perfectul simplu* (the course drills *perfectul compus*); the pre-1993
`sînt`/`â`-restricted spellings.

**Gender: three classes — masculine, feminine, and a genuine neuter** that is masculine in the
singular and feminine in the plural (`un scaun` → `două scaune`), as the A1 point *Gender and
number — including the neuter* teaches. **The definite article is a suffix** — `scaun → scaunul`,
`casă → casa`, `carte → cartea`, `cafea → cafeaua` — which is why `RomanianNLP.leading_articles` is
empty in `backend/services/nlp/latin_base.py`: nothing to strip, and everything a Romance course
usually puts *before* the noun is inside the answer string. Three features dominate drill quality:
(1) **the suffixed article and its allomorphs** (`-ul / -le / -a / -ua / -ea`), unhintable the way
`el`/`la` are; (2) **`să` as the universal subjunctive trigger** — Romanian avoids the infinitive
after another verb, so `să` is the single most-drilled answer in the file; (3) **genitive-dative
case and clitic doubling** (`pe Ion îl văd`, `îi dau Mariei`).

### The morphology file's gender encoding is inconsistent — read this before trusting a chip

`data/ro_morphology.json` (7005 entries: 4161 nouns, 1736 adjectives, 1108 verbs) uses two labels
that both say "feminine" and mean different things. On **nouns** `Gender` is a *category*
(`{"label": "Gender", "value": "feminine"}` on `casă`); on **adjectives** `Feminine` is a *form*
(`{"label": "Feminine", "value": "abandonată"}` on `abandonat`) — all 1728 `Feminine` chips are
adjectives, no noun has one, so anything reading chips by label alone conflates a category with an
inflected form. Worse, **the neuter is missing**: only **2** entries carry `Gender: neuter` (`câmp`,
`tatuaj`) while **1186 nouns carry no `Gender` chip at all** — 1113 with a `-uri`/`-e` plural, the
neuter signature (`scaun/scaune`, `tren/trenuri`, `măr/mere`). `Gender` was evidently written only
for masculine and feminine, hence the skewed 2194 feminine to 779 masculine, and a gym card for
`scaun` shows a plural and no gender in the one language of the group with three. **Fix: one label,
three values, on every noun; until then treat a missing chip on a `-uri`/`-e` noun as "probably
neuter".**

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss
already in the drill's own translation; never the `answer — explanation` template; one hint
resolves to exactly one answer inside a point (allomorph sets excepted where the sentence
disambiguates); hints are in English, and quoting a Romanian base form is fine while whole Romanian
sentences are not.

1. **`a <infinitive>, <person>` is house style — but it self-destructs when the drilled cell equals
   the citation form**: Romanian `tu` forms and many imperatives are spelled like the infinitive
   stem, so the convention prints the answer.
   - GOOD: `a auzi — you (sg.)` for `auzi` in `Tu {{answer}} muzica?`; BAD: `a auzi, tu`, and
     `a deschide, tu` → `deschide`. Elsewhere the convention is safe (`a avea, tu` → `ai`,
     `a vedea, el/ea` → `vede`), so reword only the colliding cells.
2. **Never quote the Romanian construction that contains the answer** — nine drills, and in the
   worst the sentence prints the other half of the frame too.
   - GOOD: `correlative — pairs with the atât clause that follows` for `cu` in `Cu cât citești mai
     mult, {{answer}} atât înveți mai bine.`
   - BAD: `(cu cât … cu atât)` — the hint prints `cu`, and so does the sentence. Same shape:
     `as (la fel de … ca)` → `fel`, `as (la fel de)` → `la`, `(tot atât de)` → `tot`,
     `while (în timp ce)` → `în`, `although (cu toate că)` → `cu`, `so that (ca să)` → `să`,
     `(o să + subjunctive future)` → `să` (whose sentence shows `O`), `(impersonal se-passive)` → `se`.
3. **Noun answers mark gender — and in Romanian that means naming the neuter.** The A1 point does
   this for its neuter and masculine drills and drops it for the feminines.
   - GOOD: `chair — neuter: două, not doi` → `scaune`; `brother, plural — doi for masculine` → `frați`
   - BAD: `book, plural` → `cărți`, `sister, plural` → `surori`, `cat, plural` → `pisici` — the three
     feminine drills in the point whose subject is that there are three genders.
4. **Suffixed-article hints name the noun and its class, not just "+ the article".** `book + the
   suffixed article` is one hint form used for six answers; none says why `carte` takes `-a` →
   `cartea` while `cafea` takes `-ua` → `cafeaua`. GOOD: `book (f.) + the definite suffix (-e nouns
   take -ea)` → `Cartea`; BAD: `book + the suffixed article`
5. **`să` drills hint the trigger, not the particle** — with ten `să` answers in the file, the hint
   has to say what *forces* it. GOOD: `the particle required after an impersonal expression` for
   `să` in `E posibil {{answer}} plouă diseară.`; BAD: `(o să + subjunctive future)`, `so that (ca să)`.

## Question / drill standards

A good drill is a sentence a Romanian would actually say, one blank fixed by sentence + hint
together, and a translation that renders the *completed* sentence in natural English. Pitfalls:

- **Diacritic-only answers cannot be failed.** `RomanianNLP` inherits `AccentFoldingNLP`, so —
  verified by running it — `sa` for `să`, `ca` for `că`, `in` for `în` all grade `CORRECT_SLOPPY`.
  These are real minimal pairs (`sa` "his/her", `ca` "as", `in` "flax"), and **15 drill answers are
  in this position**, every `să` included: a point whose whole content is `să` cannot fail a learner
  who never types the breve.
- **The suffixed article partly evades grading too.** `casă` against expected `Casa` folds to the
  same string and grades amber, as does `ușă` against `Ușa`: two of the six drills in *The definite
  article is a suffix* accept the article-less noun (`Cartea`, `Cafeaua`, `Scaunul`, `Profesorul`
  are safely wrong). Prefer `-ul` / `-ea` / `-ua` nouns for that point.
- **Watch what the predicate adjective gives away.** `{{answer}} este nou.` says masculine/neuter
  before the learner picks `Scaunul`; `{{answer}} este interesantă.` says feminine. `Casa este mare.`
  (invariable adjective) and `Profesorul lucrează aici.` (none) are the good shapes.
- **A subjunctive point must drill the mood, not only the particle.** *Subjunctive after
  impersonals* has `să` as five of its six answers, and its one form answer, `venim`, is spelled
  identically to the indicative — as is `știu` in *The subjunctive*. Only the 3rd person (`meargă`,
  `facă`) and `a fi` (`fim`) show the mood, so those are the cells worth blanking.
- **The fronted topic must not print the answer** — `Îl cunosc pe Ion; {{answer}} văd în fiecare zi.`
  shows `Îl` before asking for `îl`. **Keep answers single words** (only `De ce` is multi-word) and
  keep the comma diacritics.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `data/ro_frequency.tsv` has **2072** one-word
  noun glosses — by far the worst in the group — and some are wrong: `masa` is tagged `verb` "to
  massage" though it is the definite form of `masă` "the table"; `mare` is glossed only as the
  adjective "big", missing the noun `marea` "the sea".
- **Noun definitions carry gender, with the neuter named** — `(m.)`, `(f.)`, `(n.)` on every
  learner-facing gloss. Today `data/ro_frequency.tsv` (`rank / word / pos / en`, no gender column)
  marks gender in **1 of 5210** noun rows, and the morphology behind it cannot supply the neuter.
- **Register:** neutral standard Romanian; formal items stay labelled (`dumneavoastră`), and the C2
  *perfectul simplu* drills already tag their translation `(literary)` — keep that.

## Current measured state

From the crawl, re-verified by opening `data/grammar/ro_grammar.json`.

- **42 points, 296 drills**, every point `source: contributor`, `reviewed: true`, A1→C2
  (12/12/7/6/3/2 by level). **Zero** empty hints, translations or explanations; zero vague
  translations; zero `answer — explanation` templates; zero duplicate hints.
- **`leak_hard`: 2** — the lemma-equals-answer collisions `ans='auzi' hint='a auzi, tu'` and
  `ans='deschide' hint='a deschide, tu'`. **`construction_quote` (warn): 9** (hint rule 2); worst is
  `ans='cu' hint='(cu cât … cu atât)' sent='Cu cât citești mai mult, {{answer}} atât înveți mai
  bine.'`, which prints the answer twice.
- **`giveaway_by_gloss`: 29 and one-word hints: 38 — both the highest in the Romance group.** Worst:
  `ans='Ea' hint='she' trans='She sings very beautifully.'`; `ans='dacă' hint='if'` (×3 in
  *Conditional sentences*); `ans='în' hint='in'`. Six more are `Este / sunt` drills hinted only
  `singular` / `plural`, four are `Indefinite articles` drills hinted `masculine` / `feminine`.
- **Diacritic-only-distinct answers: 15** — `să` ×10, `că` ×2, `în` ×2, `fără` ×1, all amber on the
  bare-Latin spelling. **Answer printed in its own sentence: 2.**
- **Gender marking on noun-answer hints: 4 of 7 in the point that teaches gender.** The crawl
  reports 3 of 39 (8%); **the file disagrees and the file wins** — that join counts verb forms
  `ro_morphology.json` mis-records as nouns (`ai`, `joacă`, `bei`, `vede`). `scaune`, `frați`,
  `mere`, `copii` name their class; `cărți`, `surori`, `pisici` do not.
- **Morphology (detailed above): `Gender` on 2975 of 4161 nouns, `Gender: neuter` on 2, `Feminine`
  used as a form-label on 1728 adjectives** — the largest data defect, sitting directly under an A1
  teaching point. Corpus: 12,123 sentences plus 180 curated in `data/sentences/ro_sentences.tsv`
  (the thinnest bank in the group), 10,000 frequency rows, gym manifest at `data/gym/ro.json`.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language ro
.venv/bin/pytest backend/tests/test_nlp_latin.py -q   # RomanianNLP lives here
```

There is no `test_nlp_romanian.py`; `RomanianNLP` is in `backend/services/nlp/latin_base.py`,
covered only through shared `AccentFoldingNLP` behaviour. Two Romanian cases belong beside the
Catalan one: that nothing is stripped from the front of a noun (the article is a suffix), and that
`sa` against `să` is amber, not green. Romanian is not in `TRANSLIT_LANGS`
(`frontend/src/features/keyboards/translit.ts`), so that suite does not apply; check instead that
`ă â î ș ț` survive the answer box **and that the keyboard emits comma-below `ș`, not cedilla `ş`**.
A reviewer pulls 10 random drills (`--sample 10`) and asks:

1. **Could I answer this knowing no Romanian?** 29 fail — `she` under *She sings very beautifully.*
2. **Does the hint quote a Romanian phrase containing the answer, or a lemma equal to it?** 11 fail;
   `a auzi, tu` and `(cu cât … cu atât)` are the templates to stop copying.
3. **Answer is a noun — does the hint name masculine, feminine or neuter?** Three feminine drills in
   the gender point fail, and every noun in the suffixed-article point fails.
4. **Would the diacritic-free spelling be a different real word?** 15 fail, including every `să`.
5. **Does the sentence's adjective reveal the noun's class?** Three of six suffixed-article drills
   do. **Does a subjunctive drill test the mood?** `venim` and `știu` match their indicative forms.
6. **Is the register standard literary Romanian?** `sînt`, Cyrillic, or a *perfectul simplu* used as
   an everyday past below C2 is out of scope and fails. **Does the morphology agree?** A missing
   `Gender` chip in `data/ro_morphology.json` is not evidence of anything — the neuter is unencoded.
