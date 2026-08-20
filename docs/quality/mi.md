# Māori (mi) — Content Quality Standards

## Language profile

Latin script, left-to-right, a 15-letter alphabet (a e i o u h k m n p r t w, plus digraphs
`ng` and `wh`) — and **the macron is the sixteenth letter, not decoration**. Long vowels are
written ā ē ī ō ū and are lexically contrastive; the course already contains the minimal pairs
that prove it (`kainga` "eaten" vs `kāinga` "home"; `ata` "morning" vs `āta` "carefully";
`mau` "hold/take" vs `māu` "for you").

**The authoritative variety is modern standard te reo Māori** as codified by Te Taura Whiri i te
Reo Māori and described in the three sources every point cites — Te Aka Māori Dictionary, Te
Whanake, and Wikipedia's grammar article. **Explicitly out of scope:** iwi dialects (Ngāi Tahu
k for ng, Taranaki/Whanganui h-dropping), Cook Islands Māori, 19th-century missionary
orthography (double vowels `aa`/`ee` for length — mixing it with macrons is an error), Māori
English.

**The word list is macron-STRIPPED at source, and that is a bigger problem than missing
macrons (measured 20 Aug 2026).** A macronisation pass over all 791 headwords was authored,
adversarially checked, and then **discarded**; what it turned up matters more than what it
proposed.

1. **The commonest macronised words are not in the file at all.** `tēnei`, `tēnā`, `tērā`,
   `kāore`, `mātou`, `rātou`, `tātou`, `whānau`, `kōrero`, `mōhio`, `pēhea`, `āpōpō` — every
   one absent. A 791-row course missing "this", "not", "we", "family" and "speak" is missing
   its spine, and no macron pass can add them because there is no row to mark.
2. **Where a macronised word survived, it survived as its own misspelling.** Rank 7 read
   `nga`, glossed *"macronless spelling of ngā"* — the plural article present only as a
   pointer to a word the file did not contain. Fixed; it is now `ngā` with a real gloss.
3. **Glosses were assigned from whichever bare homograph the dictionary had.** Rank 24
   `tona` is glossed "wart, corn, nodule" and rank 30 `ra` as "Ra (Egyptian god of the Sun)"
   — both already named on this page. They are not wrong spellings, they are the wrong
   WORDS: the ranks belong to `tōna` "his/her" and `rā` "day, sun".

**So macronising in place is the wrong repair, and the discarded pass proves it.** Roughly
half its proposals put a macron on a row whose gloss describes the BARE word — `tōna`
glossed "wart", `kāinga` glossed "the refuse of a meal". That second one is the exact
minimal pair this page cites (`kainga` "eaten" vs `kāinga` "home"), inverted. Marking the
spelling without repairing the gloss produces a card that is wrong in a new way.

**The repair Māori actually needs, in order:** (a) restore the missing high-frequency
macronised words as their own rows; (b) re-gloss the rows whose meaning came from a bare
homograph; (c) only then mark the remainder. Plan D1d already states the governing rule —
re-marking is not decoration, and an unmarked row may stand for several words.

The discarded pass produced one thing worth keeping: a list of ~60 rows where the bare
spelling demonstrably covers more than one word, including the macron-only plurals
(`tangata`/`tāngata`, `wahine`/`wāhine`, `matua`/`mātua`, `teina`/`tēina`,
`tuakana`/`tuākana`, `whaea`/`whāea`). Each needs its own row, not a macron on the singular.

**No gender and no noun class.** What replaces them, and what dominates drill quality:

1. **Macrons.** The grader cannot help. `MaoriNLP` in `backend/services/nlp/latin_base.py` is
   `AccentFoldingNLP`, whose `lemmatize` folds combining marks, so a missing macron grades
   `CORRECT_SLOPPY`, never `WRONG` — deliberately ("diacritics coach, they don't fail you").
   Right for the learner's typing, disastrous for the data: nothing mechanical notices a macron
   missing from a sentence, hint or vocab row. Macron correctness is a **content policy** here.
2. **Two-letter particles as answers.** `i`, `ki`, `a`, `e`, `ana`, `kei`, `nō`, `hei`, `anō`
   carry the tense, case and purpose load. All nine hint leaks below are an author quoting the
   construction the particle lives in.
3. **The a/o possessive categories and the inclusive/exclusive, dual/plural pronoun grid**
   (`tāku` vs `tōku`; `mātou` vs `tātou`). English glosses cannot separate these, so the hint
   must name the category, never translate.

`MaoriNLP.leading_articles = ("te ", "ngā ", "nga ", "he ")` silently reduces a multi-word
answer opening with an article to its head noun — keep answers to one word. Not in
`TRANSLIT_LANGS`.

## Hint standards

Universal rules, once: a hint **narrows** the answer without containing it. Never the answer as
a whole word. Never a gloss already sitting in the drill's own translation. Never the
`answer — explanation` template. One hint resolves to exactly one answer inside its point
(allomorph and circumfix sets excepted where the sentence disambiguates). Hints are English;
quoting a base form (`kai`, `ako`) is fine, a whole Māori sentence is not.

**Never parenthesise the construction the answer sits in** — the entire leak class here, all 9.
The author believes the parenthetical is the convention; it prints the answer.

| BAD (in the file today) | answer | GOOD (rewrite) |
| --- | --- | --- |
| `in order to (ki te)` | `ki` | `the purpose preposition that opens a "to do X" phrase` |
| `because (nō te mea)` | `nō` | `opens the causal phrase that continues with te mea` |
| `(present negative: kāore … i te)` | `i` | `the particle that fills the gap between kāore and te` |
| `towards me (hōmai)` | `mai` | `the directional meaning "towards the speaker"` |

**Never a bare English gloss that is already in the translation.** 25 drills do this. GOOD
(real): `eaten (passive of kai)` for `kainga`; `we — not including you` for `mātou`; `my — a
category (controlled)` for `tāku`. BAD (real): `table` for `tēpu` under "The books are on the
table."; `where` for `hea` under "Where are you?"; `big` for `nui` under "The house is big.".
Rewrites: `the loanword for the thing you eat at`; `the interrogative that follows kei`; `the
stative for large size`.

**Macron-contrastive pairs are disambiguated by the hint, not by luck.** GOOD: `eaten (passive
of kai)` separates `kainga` from `kāinga`, which the course also teaches. BAD: `home` alone in
a point that also drills the passive.

**One hint, one answer inside a point.** BAD (real): `(progressive frame)` serves both `e` and
`ana` in *Relative clauses*. The circumfix exemption holds only because the sentence shows the
other half, so say so — `opens the progressive frame; its partner is already in the sentence`
vs `closes the progressive frame`.

## Question / drill standards

- Natural, everyday te reo with a plausible speaker: `Kei te pēhea koe?`, `Nau mai ki tō mātou
  kāinga.` Greeting and whakataukī points may be formal; A1 points must not be.
- **Exactly one blank, and the blank is a whole word.** 240/240 drills have one blank, but one
  splits a word: `Hō{{answer}} te kai ki a au.` with answer `mai`. Rewrite as
  `{{answer}} te kai ki a au.` / answer `Hōmai`.
- **The `gloss` field is a second leak surface.** Māori carries a per-drill interlinear
  `gloss` on 240/240 drills, shown to the learner. It must never spell the answer
  and must be *correct*: `Kei te {{answer}} ngā pukapuka.` ("The books are on the table.") is
  glossed `PRESENT · ___ · the(pl) · book`, but `kei te` there is locative "at the", not the
  present-tense marker. A wrong gloss teaches a wrong parse.

  **Māori being the only fully glossed course is not a fact about Māori.** Measured 18 Aug:
  374 of 8,049 drills across all 27 courses carry a gloss — Māori's 240, Swahili's 134, and
  nothing else. On the sentence side only Swahili's curated bank has any (461 rows), and the
  Tatoeba builder has no gloss column to write at all. Meanwhile
  `frontend/src/features/review/hintLayers.ts` gives NINE courses a gloss step, and puts
  `mi, sw, yo, xh, ha` on `GLOSS_FIRST` — so `yo`, `xh` and `ha` open their hint ladder on a
  layer that is empty, and drop straight to English. Treat this page's gloss rules as the
  **standard the other courses have yet to reach**, not as a Māori peculiarity to police; see
  `docs/plans/quality-parity.md` D2c and Phase 2c.
- Possession drills must make the a/o choice **forced** by the sentence. `Ko tāku pukapuka
  tēnā.` works because a book is a-category; a parent or body part would demand `tōku`, and the
  hint must say which category and why. Keep `taku`/`tāku` deliberate — both are real words, so
  a slip reads as a teaching choice, and today `tāku` appears 3× and `taku` 4× with no stated
  difference.

## Translation & definition standards

- No bare one-word gloss for a polysemous item. `roto` is "interior; lake"; `whenua` is "land;
  country" (and "placenta"); `iwi` is "tribe, people" as well as "bone". Sense splits go in the
  definition, separated by `;`.
- No gender or noun class to mark. Mark **particle class and possessive category** instead: a
  pronoun row says dual vs plural and inclusive vs exclusive, a possessive says a- or
  o-category. Neither survives an English gloss.
- **Macrons in vocabulary are non-negotiable and the single largest debt** (see below). Register
  consistency: whakataukī, mihi and formal-greeting material must be labelled as such, so a
  learner never drops `Tēnā koutou katoa` into a text message.

## Current measured state

Counted directly from `data/grammar/mi_grammar.json`: **40 points, 240 drills**, every point
`source: "contributor"`, **12 reviewed, 28 not**; levels A1 12 / A2 10 / B1 7 / B2 6 / C1 3 /
C2 2. Footprint: `data/mi_sentences.tsv` 259 rows, curated `data/sentences/mi_sentences.tsv` 93,
`data/mi_frequency.tsv` 781 rows, **no `data/mi_morphology.json`**, **no `data/gym/mi.json`**.

| Rule | Count | Share of drills |
| --- | --- | --- |
| `leak_hard` — answer whole-word in its own hint (all 9 `construction_quote`) | **9** | 4% |
| `giveaway_by_gloss` — ≤3-word hint verbatim in the translation | **25** | 10% |
| `duplicate_hint` — one hint, two answers in a point | **1** | — |
| `self_answering` / `empty` / `vague_translation` | 0 | — |
| one-word hints (warn); plus 1 in-word blank (structural) | 30 | 12% |

**Correction to the crawl.** Its "duplicate hints 1" matches the file, but a naive
case-sensitive scan finds four — the extra three are sentence-initial capitalisation of one
answer (`Ki`/`ki`, `Hei`/`hei`, `Nō`/`nō`). Grading lowercases; casefold before comparing.

Worst offenders, verbatim:

1. `"sentence": "Hō{{answer}} te kai ki a au."`, answer `mai`, hint `towards me (hōmai)` — the
   blank splits a lexeme *and* the hint prints the whole word, yet the leak scan misses it
   because `ō` is a word character, so `(?<!\w)mai` never matches inside `hōmai`.
2. **`data/mi_frequency.tsv` has zero macrons on headwords.** Six of 781 rows contain a macron
   anywhere and all six are inside the English definition, so two high-frequency rows are
   glossed as the wrong lexeme: rank 23 `tona` → `wart, corn, nodule` (the frequent word is
   `tōna` "his/her", spelled correctly 3× in the grammar file) and rank 29 `ra` → `Ra (Egyptian
   god of the Sun)` (the frequent word is `rā`, macronised 24× in the grammar file). Rank 7
   documents the defect against itself: `nga | article | macronless spelling of ngā`. Trust the
   grammar file; re-macronise the TSV against Te Aka.
3. `Kei te {{answer}} ngā pukapuka.` / "The books are on the table." / hint `table` / gloss `PRESENT · ___ · the(pl) · book` — a giveaway gloss and a mis-glossed particle in one drill.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language mi
.venv/bin/pytest backend/tests/test_nlp_latin.py -q -k Maori
.venv/bin/pytest backend/tests/test_content_quality.py -q
```

There is no `test_nlp_maori.py` — Māori grading lives in `TestMaori` inside
`backend/tests/test_nlp_latin.py`, alongside `TestFoldDiacritics::test_strips_macrons`
(`kēkē` → `keke`), the macron-tolerance guard. Not in `TRANSLIT_LANGS`, so no translit suite.

A human reviewer pulls 10 random drills and rejects any that: parenthesise the construction
containing the answer; hint a content word with a gloss already printed in the translation;
blank part of a word; carry a `gloss` that mislabels a particle or spells the answer; use a
macron-contrastive form with no hint separating it from its pair; ask for an a/o possessive the
sentence does not force; or — the one no command catches — drop a macron anywhere. Then check
five vocabulary rows against Te Aka; today that fails on the first row needing a macron.
