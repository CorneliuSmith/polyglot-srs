# Hindi (hi) — Content Quality Standards

## Language profile

Devanagari, left-to-right, an **abugida**: a consonant carries an inherent *a*, every other vowel is a matra
hung on it (क + ी = की). Text is NFC, which *decomposes* the precomposed nukta letters, so ज़ always arrives
as ज + U+093C (`backend/services/nlp/hindi.py` says so explicitly).

**The authoritative variety is Standard Modern Hindi** — Delhi/Khari Boli standard, Devanagari, neutral
everyday register, what the file teaches from SOV word order at A1 to izāfat at C2. **Explicitly out of
scope:** Urdu in Perso-Arabic script (verified — zero Arabic-script codepoints in
`data/grammar/hi_grammar.json`, including the C2 point that *teaches* izāfat); Roman Hindi / Hinglish as an
answer form; regional varieties (Bhojpuri, Awadhi, Braj, Dakhini); Sanskrit, as against the C1 तत्सम layer.

**Gender: two — masculine and feminine, no neuter.** No separate word for *he* and *she* (यह/वह cover both),
so **gender rides on the verb, the adjective and even the infinitive** (दवा लेनी है), never on the pronoun.
There is **no machine-readable gender source at all**: no `data/hi_morphology.json` (the checker's
`structural` warning), no gender column on the 4760 noun rows of `data/hi_frequency.tsv`, and `hi` is absent
from the checker's `GENDERED` set — so its `gender_marking` line is empty and the figure below is hand-counted.

Three features dominate drill quality: (1) **gender agreement at a distance** — under ने the verb agrees
with the *object* (मैंने चाय पी), so "feminine" without naming the controller explains nothing; (2)
**postposition + obligatory oblique** (कमरा → कमरे में), two points that are one skill; (3) **the three-way
formality system** आप/तुम/तू, propagating into plural agreement for one respected person (पिताजी आए हैं).

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already
sitting in the drill's own translation; never the `answer — explanation` template; one hint resolves to
exactly one answer inside a point (allomorph sets excepted where the sentence disambiguates); hints are
written in English, and quoting a base form in Devanagari is fine while whole Hindi sentences are not.

**1. Never print the answer in Devanagari while explaining it.** All four Hindi leaks are this.
- BAD: `बात करना takes ने; की agrees with बात (fem.)` for `की` — GOOD: `बात करना takes ने; the verb agrees
  with बात (fem.)`
- BAD: `honorific — fem. plural गईं/गई for one elder` for `गई` — GOOD: `honorific: one elder takes the
  feminine plural participle`

**2. Name the controlling noun in Devanagari, never its English gloss** — the gloss is in the translation.
- GOOD: `watched — agrees with फ़िल्म (fem.)` for `देखी`; `infinitive agrees with दवा (fem.)` for `लेनी`
- BAD: `book is feminine` for `की` under *Sita's book is new.* — GOOD: `the possessed noun किताब is fem.`

**3. Postposition and question-word hints are not their English translation** — nine of the twelve
gloss-giveaways sit in these two points.
- BAD: `in` under *We are in the house.* — GOOD: `containment, on a noun in the oblique`
- BAD: `what` under *What is your name?* — GOOD: `asks about a thing, not a person`

**4. Formality hints name the relationship, not the English pronoun.** Every *Pronouns and politeness*
translation already tags `(respectful)`/`(informal)`, so `respectful 'you'` is a gloss repeat in parentheses.
- GOOD: `the 'you' for teachers and elders` — BAD: `respectful 'you'` under *How are you? (respectful)*

**5. Devanagari budget: one or two quoted base forms, never three.** Four hints read as Hindi prose.
- BAD: `भूलना avoids ने — stem before the जाना vector` — GOOD: `भूलना never takes ने; use the bare stem`
- BAD: `किए जाना pattern — stem of जाना` — GOOD: `the keep-on-doing pattern needs the bare stem`

**6. Quotation marks do not launder a gloss.** `'if'`, `'half'`, `'that'`, `'like'`, `'I'` each sit verbatim
in their own translation; the quotes are the only reason the checker does not count them.
- BAD: `'half'` under *I need half a kilo of sugar.* — GOOD: `fraction agreeing with किलो (m.)`

## Question / drill standards

A good Hindi drill is a sentence someone would actually say, verb last, one blank whose filler is fixed by
sentence + translation + hint, and a translation of the *completed* sentence. Pitfalls:

- **The sentence must supply the gender cue the answer needs.** The convention is a parenthetical in the
  sentence — `मैं चाय पीत{{answer}} हूँ। (a woman speaking)` — plus `(female speaker)` in the translation.
  Eleven drills use it; **one carries the cue only in the English** (`… फल {{answer}}।` → `लाया`, *"(male)"*).
- **Prefer blanking the whole word over a bare matra.** Fifteen blanks sit inside a word, **seven a lone
  matra** (`ा`, `ी`, `े`). Per `encodeHi` in `frontend/src/features/keyboards/translit.ts` the translit IME
  cannot emit one (`aa` gives आ, not `ा`), so those seven need the on-screen InScript keyboard or a system
  IME. Blank `पीती`, not `ी`.
- **An ergative drill must contain the object that governs agreement**, and any को-marked object must be
  visible, since it flips the verb to neutral masculine singular.
- **तू is receptive-only:** taught in the A1 explanation, named in the point title, the answer to nothing —
  0 occurrences in 252 drills, against आप 10 and तुम 16. New drills default to आप; तुम needs a peer cue.
- **Punctuation and nukta.** Sentences end in a danda (।) or `?`, never a Latin `I` or `|` (21 such rows in
  the sentence bank, none in the grammar file). Nukta discipline there is perfect today — मेज़, रोज़, बाज़ार,
  फ़िल्म, दफ़्तर, 0 bare spellings; do not regress it.
- **One blank, one word** — 246 of 252 answers are single tokens; the six multiword ones are all in *Word
  order: subject–object–verb*, where the verb phrase **is** the point. That is the only licence.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `data/hi_frequency.tsv` glosses `सोना` (rank 550) as
  *gold* only — it is equally *to sleep*; `आम` (1071) as *mango* only — it is also *ordinary*. `कल` (220) is
  done right: *yesterday; tomorrow*, the two senses tense resolves.
- **Noun definitions must carry (m.)/(f.)** — with no morphology file and no gender column, the gloss layer
  is the *only* place a learner learns that ट्रेन is feminine and फ़ोन masculine. Effectively none of the 4760
  noun rows do; 24 mention *female* lexically, which is not the same thing.
- **A parse is not a meaning.** 2490 of 9096 frequency rows read *"inflection of होना (honā):"* — trailing
  colon, no content — ranks 1, 2, 9 and 17 among them; and rank 18 `कर` is glossed *hand; arm; tax*, the
  literary noun, when the rank-18 token is the conjunctive participle of करना.
- **Register consistency:** neutral standard Hindi; तत्सम/Perso-Arabic doublets are labelled in the C1
  register point, not sprinkled through A1. No Hinglish in target text.

## Current measured state

`python -m backend.services.quality.audit_content --language hi`, re-verified against the file:

- **42 points, 252 drills**; A1 12 / A2 10 / B1 8 / B2 6 / C1 4 / C2 2. Every point is `source: contributor`
  and **`reviewed: false` — all 42; nothing in the Hindi path has had a native review.** 7 points carry a
  `paradigm`, 6 a `culture_note`, 42 drills a `cell`; no drill has a `transliteration` field (Russian's 348
  all do) though `hi` is in `TRANSLIT_LANGS`.
- **`leak_hard`: 4**, all self-quotes in Devanagari, worst first: `की` — *"बात करना takes ने; की agrees with
  बात (fem.)"* (also the worst `hint_language` hit, five tokens); `मन` — *"मन ___ना = to feel at home"*;
  `रही` — *"feminine (respect plural takes रही + हैं)"*, the lone `construction_quote`; `गई` — *"honorific —
  fem. plural गईं/गई for one elder"*.
- **`giveaway_by_gloss`: 12** — 4 in *Postpositions* (`on`, `in`, `from`, `in`), 5 in *Questions* (`what`,
  `where`, `when`, `why`, `who`), 2 in *Comparisons*, 1 in *the subjunctive* (`shall we sit` under *Shall we
  sit here?*). **Five more escape on a technicality**: `'I'`, `'if'`, `'like'`, `'that'`, `'half'` are quoted.
- **`hint_language`: 4** (≥3 Devanagari tokens beyond the answer) — the `की` hint above, `किए जाना pattern —
  stem of जाना`, `number + वाँ→वीं (fem. for मंज़िल)`, `भूलना avoids ने — stem before the जाना vector`.
  **`duplicate_hint`, `empty`, `self_answering`, `vague_translation`: 0.**
- **`structural`: 1 — `data/hi_morphology.json` missing.** With `hi` also outside `GENDERED`, a two-gender
  language has **zero** automated gender coverage. Hand-counted, **74 of 252 hints (29%) mark masc./fem.**
- **Correction to the crawl:** it reports *"one-word hints 20"*; single-token hints counted on disk give
  **21** (`'I'`, `'if'`, `'also/too'` each count as one). Trust the file — its other figures reproduce
  exactly (4 leaks, 12 hint-in-translation, 0 duplicate hints).
- **Corpora:** `data/hi_sentences.tsv` 8130 rows, **no curated `data/sentences/hi_sentences.tsv`**,
  `data/hi_frequency.tsv` 9096 rows, Gym manifest present (13 entries, two columns). Bank hygiene: **11 rows
  end in a Latin `I` used as a danda**, 10 contain `|`, 41 lack terminal punctuation, and three duplicate
  rows read `… काम कर रहे है I` — `है` where plural `हैं` is required, the very error the course teaches against.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language hi
.venv/bin/pytest backend/tests/test_nlp_hindi.py -q
cd frontend && npx vitest run src/__tests__/translit
```

Hindi is in `TRANSLIT_LANGS`, so the transliteration suite applies. `HindiNLP` normalizes with strip+lower
only, and near-miss acceptance comes from `get_morphological_family`, which expands a -ना infinitive into
ता/ती/ते/या/ेगा/ेगी/ो — so **a wrong-gender verb form grades as "right word, wrong form"** and the hint, not
the grader, has to teach gender.

A human reviewer pulls 10 random drills and asks, in order:

1. **Does the hint print the answer in Devanagari?** `बात करना takes ने; की agrees with बात (fem.)` is the
   template to stop copying. Then count the *other* Devanagari tokens: three or more is drift into Hindi.
2. **Gendered answer — does the hint name the controller, and is that controller in the sentence?**
   `feminine` alone fails; `agrees with फ़िल्म (fem.)` passes.
3. **Could I answer knowing no Hindi at all?** Read the translation, then the hint: `in` under *We are in
   the house.* — yes, a failure. Quoted hints (`'half'`) count.
4. **Formality:** is तू the required answer anywhere (it must not be), and does an आप drill keep plural
   agreement throughout (आप … हैं, पिताजी आए हैं)?
5. **Is the blank a bare matra?** If so, blank the whole word — and check it is typeable with `aa`/`ii`.
6. **Postposition drill:** is the noun before it in the oblique (कमरे, लड़के, बच्चों), and does the hint say
   something the English preposition does not?
7. **Nukta and danda:** ज़/फ़/ड़/क़ written where they belong, sentence ends in ।, no Latin `I` or `|`.

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**8 rows reglossed**, of which **7 were fatal** — the card named a
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
| 18 | `कर` | do — the stem of करना, standing before रहा, सकना and the vector verbs (कर रह |
| 57 | `दिया` | gave — masculine singular perfective of देना (मैंने कुछ नहीं दिया — I gave n |
| 64 | `कहा` | said — masculine singular perfective of कहना (उसने कहा — he said; तुमने क्या |
| 138 | `दे` | give — the stem of देना, standing before सकना, रहा and the vector verbs (नही |
| 161 | `होता` | is, happens, tends to be — masculine singular habitual participle of होना (ऐ |
| 236 | `दी` | gave — feminine singular perfective of देना, agreeing with a feminine object |
| 245 | `पूरी` | whole, complete, full — feminine of पूरा, agreeing with a feminine noun (पूर |

Fixes are in `data/gloss_overrides.tsv` as well as `data/hi_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang hi --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.

### Extended to rank 2000 (25 Aug 2026)

The sweep above covered the top 500. Ranks 501-2000 added **9 rows, 7 fatal**, so the
course total is **17 repaired (14 fatal) through rank 2000**.

The keep rate rose with rank — roughly 30% of candidates were kept in the top 500 against
about 50% below it — which is the expected shape and a check on the pass: deeper in a
frequency list the lexical sense genuinely is more often right, and an over-eager rewrite
would replace a correct gloss with a wrong one.

| rank | word | now reads |
| --- | --- | --- |
| 505 | `पाया` | got, obtained; was able to — masculine singular perfective of पाना, and  |
| 522 | `सो` | sleep — the stem of सोना, before जाना, रहा and in the imperative (सो जाओ |
| 564 | `खाता` | eats, eat — masculine singular habitual participle of खाना, with हूँ/है  |
| 686 | `नई` | new — feminine singular of नया, agreeing with a feminine noun (मेरी नई ग |
| 1216 | `मान` | accept, agree, believe, obey — the stem of मानना, before लेना and जाना a |
| 1826 | `सीख` | learn — the stem of सीखना, standing before रहा, लेना and the vector verb |
