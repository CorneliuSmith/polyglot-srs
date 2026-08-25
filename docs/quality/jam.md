# Jamaican Patois (jam) — Content Quality Standards

## Language profile

Latin script, left-to-right, no diacritics. **The authoritative orthography of this course is
Cassidy–JLU** — Frederic Cassidy's phonemic system as standardised by the Jamaican Language Unit
at UWI Mona, used by *Di Jamiekan Nyuu Testiment* (2012) and cited by every grammar point. Not a
preference to re-litigate per drill: it is already declared in code, in the `JamaicanNLP`
docstring at `backend/services/nlp/jamaican.py` — "the app teaches the Cassidy/JLU (Jamaican
Language Unit) phonemic spelling". **The ambiguity is itself the quality risk**: Patois has no
single everyday orthography, so an unstated convention lets each author drift toward English
spelling until the corpus is no longer one language in one system. The rules, in full, because
they are checkable:

- Consonants `b ch d f g h j k l m n ng p r s sh t v w y z`. **No bare `c`, `x`, `q`, `ck`, `ph`
  or `th`** — `vex` is `veks`, `lack` is `lak`.
- Vowels `i e a o u`; length by doubling (`ii aa uu`); diphthongs `ie uo ai ou`. **No `ea`, `ei`,
  `oo`, `ay`, `ey`, `oa`** — `near` is `nier`, `neiba` is `neba`, `all` is `aal`. **No doubled
  consonants, no silent final `-e`** — `likkle` is `likl`, `granny` is `grani`, `riddim` is
  `ridim`. One spelling per word corpus-wide: `we` not `weh`, `se` not `seh`.

**Explicitly out of scope as *content*:** anglicised "popular" spellings (`me a guh`, `pickney`,
`likkle`), Rasta Talk beyond the one Iyaric point, Jamaican Standard English beyond the two
register points that contrast it deliberately. Out of scope as content, **not** as input:
`JamaicanNLP.lemmatize` folds English spellings toward the Cassidy skeleton (`ck→k`, `c→k`,
`oo→u`, `ea/ee→ii`, `ai/ay→ie`, doubled letters collapsed), and 347 of 384 rows in
`data/jam_frequency.tsv` carry the anglicised variant in an `alt` column. A learner typing `him`
for `im` is graded correct; **a drill that *prints* `him` is a defect.** No gender and no noun
class. The three features that dominate drill quality:

1. **Everything is a bare particle.** `a`, `de`, `fi`, `se`, `did`, `don`, `wi`, `no` carry
   copula, aspect, tense, complementiser and negation. Answers are one or two letters, so a
   one-word English gloss hands the answer over outright — the largest debt here.
2. **Copy constructions.** Predicate cleft (`A tiif im tiif di moni`) and reduplication
   (`swiit-swiit`) both print the answer a second time inside the same sentence.
3. **The continuum.** Basilect to acrolect is a gradient, taught explicitly in two points. Every
   drill must sit at a stated point on it, or "correct" has no meaning.

## Hint standards

Universal rules, once: a hint **narrows** the answer without containing it. Never the answer as a
whole word. Never a gloss already sitting in the drill's own translation. Never the
`answer — explanation` template. One hint resolves to exactly one answer inside its point
(allomorph sets excepted where the sentence disambiguates). Hints are English; quoting a base
form (`fi`, `naa`) is fine, a whole Patois sentence is not.


**Never the `answer — explanation` template.** BAD (real — all four leaks in the file):
`go — bare form` (answer `go`); `yes — say + se together` (`se`); `shouldn't = no fi` (`fi`);
`after naa, the 'go' part` (`go`). GOOD: `the verb of motion, with no English ending`; `the
complementiser after a verb of speech`; `the preverbal particle in the negative obligation
frame`; `the movement verb the future marker is built on`.

**Never the bare English gloss when it is already the translation.** 41 of 192 drills — 21%,
the highest rate in the repo relative to size. BAD (real): hint `is` for answer `a` under "He is
my neighbour."; `are` for `a` under "They are farmers."; `tired` for `taiyad` under "I'm really
tired today."; `work` for `wok` under "We work hard every day." GOOD (real, same points):
`equative marker`; `the noun-linking word`; `the Patois 'eat'` (for `nyam`); `see — the adverb
carries the past` (for `si`). The repair for a copula drill is to name the *role*: `links two
nouns` distinguishes `a` from `de` and from zero.

**English function-word collisions are not leaks.** `a`, `no`, `de`, `we`, `im`, `fi`, `di` are
Patois words that are also English strings; a hint containing English "a" or "no" as prose is a
false positive. Flag it only when the hint casefolds to exactly the answer, or when the English
word sits inside a quoted Patois phrase.

## Question / drill standards

- Natural basilectal speech with a plausible speaker: `Mi de ya, man.`, `Yu waan kom wid wi?` The
  acrolect appears **only** in *The continuum* and *Written Patwa*, where it is the subject.
- **Exactly one blank** — 192/192 today. But **the answer must not also be printed in the
  sentence**, and 16 drills break this. Six are the predicate-cleft point (`A {{answer}} im tiif
  di moni.` with answer `tiif`, the copy three words later); five are the reduplication point
  (`Di mango {{answer}}-swiit.` with answer `swiit`, the second copy right after the hyphen).
  Blank *both* copies, or blank the copy that is not recoverable — a drill the learner solves by
  reading rightwards tests nothing.
- Nine drills blank part of a hyphenated word — fine for reduplication *if* the visible copy is
  removed; `answer` must be exactly the characters in the gap.
- Every sentence, answer and translation is spelled Cassidy–JLU. The only licensed exceptions
  are proper nouns (`Cassidy`, `Louise Bennett`, `Miss Lou`, `Jamiekan Nyuu Testiment`) and
  metalinguistic quotation in the two register points, where the anglicised form is the point:
  `Popular spelling 'likkle' a Cassidy 'likl'.` / `Raiz di rejista: 'ting' bikom 'thing'.`
  Translations are Jamaican Standard English, not a calque: `Wanti wanti kyaan getti.` →
  "Those who want can't get." is right; a gloss chain is not.

## Translation & definition standards

- No bare one-word gloss for a polysemous item, and Patois function words are almost all
  polysemous. `data/jam_frequency.tsv` already does this well — `wi | we; us; our; will (future
  marker)` — and every new row must match it. The grammar file agrees: "This little `a` is one of
  the busiest words in the language".
- No gender or noun class to mark. Mark **particle class** instead: a definition says whether the
  item is a copula, aspect marker, complementiser or preposition, because `a` alone is useless.
- The `alt` column is where anglicised spellings live (`me`, `yuh`, `him`, `will`) — 347 of 384
  rows. Adding a variant there is the right answer to "but people write it this way"; the
  headword stays Cassidy. Register: Iyaric (`I-an-I`, `Iditation`, `downpressor`) and proverbs
  must be labelled, so Rasta vocabulary is never deployed as neutral Patois.

## Vocabulary: 384 → 485 rows (25 Aug 2026)

**The evidence problem, stated plainly.** Leipzig has no `jam` corpus and kaikki has no
Jamaican Creole extract — both checked, both 404 — and Wiktionary coverage of the gap list
was zero for all of it. So unlike every other course in this repo, the vocabulary here
cannot be grown from an external source at all. The only evidence is the course's own
drills and curated sentences, and the one thing that makes them usable is that they carry
English translations: `Wi a nyam dina inna di iivnin` / "We eat dinner in the evening"
fixes `inna` without a dictionary.

**What was done.** 208 words that the course's own sentences use but had no card were
glossed from those sentences by a maker pass and reviewed against the same sentences by a
separate adversarial checker.

**Verification, honestly.** 31 were skipped by the makers (proper names, English
metalanguage quoted inside register drills). Of the 207 glossed, **the checkers rejected 61
— 35%** — and the apply gate dropped 4 more as already-carded alts. **101 rows landed, all
of them checker-reviewed; none is maker-only.** The rejections were not rubber-stamping:
the checkers caught the maker inverting `hab`/`av` (the course teaches `av` — it titles a
B2 point — while `hab` appears only in curated sentences), and refused `it` as a weather
dummy subject because the B2 explanation teaches the opposite, that weather runs on verbs
*without* it (`Rien a faal`).

**A mechanical Cassidy–JLU gate now runs at apply time**, because the words were harvested
from sentences that are themselves known to drift: without it, `neiba`, `granny`, `lack`
and `riddim` would have been promoted from a grammar-file defect into headwords. It refused
`getti` (doubled consonant, from the proverb `Wanti wanti kyaan getti`). It is necessary but
**not sufficient** — `friend` passes every letter rule and is still English.

Two conventions were normalised on the way in: backticks were stripped from the new glosses
(no `jam` gloss has ever carried one, 0 of 384, and nothing markdown-renders a gloss —
`ReactMarkdown` is confined to the tutor — so a backtick prints literally on the card), and
where two batches glossed the same word the richer entry was kept, not the earlier one.

## Current measured state

Counted 20 Aug 2026 from `data/grammar/jam_grammar.json`: **32 points, 192 drills** — the fewest
points of any course — and **every point is `source: "ai"`, `reviewed: false`**. Nothing has
been through a JLU-connected reviewer, which the NLP module itself flags as pending. Levels
A1 10 / A2 8 / B1 6 / B2 4 / C1 2 / C2 2. Footprint: `data/jam_sentences.tsv` has only **15
rows** while curated `data/sentences/jam_sentences.tsv` has **356** — inverted versus every
other language; `data/jam_frequency.tsv` 384 rows at that date, **485 now** (see above); no `data/jam_morphology.json`; **no
`data/gym/jam.json`**; `seed_jamaican.py` present.

| Rule | Count | Share |
| --- | --- | --- |
| `giveaway_by_gloss` — ≤3-word hint verbatim in the translation | **41** | 21% |
| `leak_hard` — answer whole-word in its own hint | **4** | 2% |
| answer also printed in its own sentence (not a crawl rule) | **16** | 8% |
| orthography drift from Cassidy–JLU (see below) | **12 word types** | — |
| one-word hints (warn); `duplicate_hint`/`empty`/`vague_translation` all 0 | 48 | 25% |

**Corrections to the crawl.** It reports "one-word hints 38"; the file has **48 occurrences**
across 39 distinct strings (`is`, `are`, `not`, `the`, `who`, `where`, `tired`…). Its "duplicate
hints 0" is right, but only after casefolding — a case-sensitive scan sees `the` → `Di`/`di`,
one answer capitalised sentence-initially. It models neither the answer-in-sentence class nor
orthography drift; both are counted here from the file.

Worst offenders, verbatim:

1. `Im {{answer}} mi neiba.` / "He is my neighbour." / hint `is` — a one-word gloss lifted from
   the translation **and** an anglicised spelling (`ei` is not a Cassidy digraph), in one drill.
2. `Di mango {{answer}}-swiit.` / `swiit` / `double it to intensify` — answer printed after the blank.
3. Orthography drift, all verified in the sentences: `neiba`, `granny`, `lack` ("Mi ier se di
   maakit lack tide."), `bex` and `vex` in adjacent points, `near`, `all`, `hills` (English
   plural where the course teaches `dem`), `riddim`; doublets `weh`/`we` 1:3, `seh`/`se` 1:8,
   `nuh`/`no` 1:22.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language jam
# (no test_nlp_jamaican.py yet — see the note below)
.venv/bin/pytest backend/tests/test_content_quality.py -q
```

There is no `test_nlp_jamaican.py` in the tree yet — `JamaicanNLP` has a fold table and no
dedicated suite, so the spelling-tolerance path (`gud`/`good`, `kyaan`/`can't`) is untested;
adding it is the first backend task this doc implies. Not in `TRANSLIT_LANGS`.

A human reviewer pulls 10 random drills and rejects any that: open the hint with the answer;
hint a copula, negator or question word with a bare English gloss already in the translation;
print the answer a second time in its own sentence; spell a word outside Cassidy–JLU without
being a licensed metalinguistic quotation; mix `we`/`weh`, `se`/`seh` or `no`/`nuh` against the
corpus majority; or put an acrolectal sentence in a basilect point. Then check five vocabulary
rows carry both a sense split and an `alt` spelling.
