# Every check, and which languages it applies to

**This file exists because the checks kept being written for one language.**

Each one below was found by looking at a single course — English's beryllium
definition, Portuguese's `a`, Latin's macrons, Māori's gloss — and each turned
out to be a *class* present in others that nobody had looked at. A check that
lives only where it was discovered is not a check; it is an anecdote.

**The rule: a check is not finished until its applicability to all 27 courses
is decided and written in this table.** "Applies everywhere", "applies to these
eight for this reason", and "applies only here, because X" are all acceptable
answers. Silence is not — an undecided language is an unchecked language.

The 27: `ru ar en sw tr yo ha xh es it fr de ca mi ro el pt hi jam nl th ko la
id tl he fa`.

---

## Status legend

| | |
| --- | --- |
| **all** | runs on every course, no per-language configuration |
| **parameterised** | runs everywhere, but needs a per-language value (which mark, which policy) |
| **scoped** | deliberately limited, with the reason stated — the limit is a decision, not an omission |
| **UNDECIDED** | found, not yet generalised. **This is debt.** |

---

## 1. `circular_gloss` — a definition that explains the word with the word

`have` → "have or possess"; `paint` → "make a painting". 80 of English's first
1000 were circular; all rewritten.

**Status: scoped — English only, and the scope is load-bearing.** Everywhere
else the gloss is in a *different language* from the headword, so a headword
inside its own gloss is either a deliberate collocation example (`na` — "and;
with (kuwa na, to have)") or a loanword that honestly glosses to itself
(`hotel`, `internet`). Measured across the other 26: 500+ hits, none a defect.
Content-word POS only — a preposition cannot be glossed without being used.

**The analogous check for the other 26 is different and is NOT yet built:** does
the English gloss actually *gloss*, rather than restate the foreign word in
transliteration? See `wrong_sense_gloss` for the part of this that is covered.

---

## 2. `wrong_sense_gloss` — the gloss describes the wrong thing entirely

A top-1000 word glossed as a letter of the alphabet or an ISO region code —
French `ne` glossed as a Swiss canton.

**Status: all 27**, top-1000 band, first sense only.

---

## 3. Grader collisions — two cards, one gradable answer

Two different vocabulary rows that normalise to the same string under **that
language's own grader**, so the learner is graded on a word the card is not
teaching. Found in Latin (40 pairs); measured with each real NLP class it was
**2,122 cards across 11 languages** — `fr` 511, `ro` 502, `es` 270, `ar` 199.
Typing `el` (the) against `él` (he) returned **`CORRECT_SLOPPY`** — full
credit — and the SRS scheduled the card as known.

**The policy (settled by a 10-language triage, 19–20 Aug 2026): a fold may
excuse a mark; it may never launder a word.** A match that succeeds only under
a lenient fold earns credit only if what was typed is NOT itself another
course word. When it is, the grader returns `WRONG_FORM` naming the collision.
Triage: **1,098 contrastive pairs** (different words) vs 923 incidental across
the ten; the marks are not decorative anywhere it matters — the Spanish acute
is the *tilde diacrítica* (its only job is separating homographs), Romanian's
five diacritics and German umlauts are letters, Greek tonos is phonemic
stress, Arabic hamza variants are letters. Dutch is the one genuinely
prosodic-optional mark, and the same guard is still right there: only its
lexicalised pairs (`hé`/`hè`) trigger it.

**Status: all 27 — implemented and ratcheted.** The guard lives server-side in
`BaseNLP` (layers 2.5/2.6) and `AccentFoldingNLP` (fold level, for marks NFD
cannot strip: ș, ț), keyed by the committed vocabulary — never by
client-supplied `card_context`. `test_nlp_collisions.py` freezes per-language
ceilings so no course grows the class silently; a zero-collision course is
asserted at zero.

**Follow-ups, in order:**

1. ~~**`ar` normalize surgery.**~~ **DONE 20 Aug 2026.** The alef fold moved
   out of `ArabicNLP.normalize()` into `fold_lookalikes`, where the guard sees
   it: **199 → 79** cards graded as another card, and rank 1 `أن` is no longer
   the same card as `إن` ("if") and `آن` ("time"). Two carve-outs: the
   alphabet deck (a one-letter answer has no word to confuse it with) and
   Check 0, widened to fire on `CORRECT_SLOPPY` so vocalized form drills still
   fail a bare answer. 11 junk twin rows deleted. The yeh fold (ى/ي) followed on the
   owner's ruling once the cost was measured: the green ruling rested on
   Egyptian convention, which `ar.md` puts explicitly out of scope, and in MSA
   word-final ى is /aː/ against ي /iː/. Moved to the coaching layer as well —
   **79 → 1**. `ArabicNLP.normalize()` now strips tashkeel and tatweel and
   nothing else. The 1 residual is `ه` vs the kashida-written hijri
   abbreviation `هـ` at rank 5634, left deliberately.
2. **Data repairs the triage verified but that need human judgment:** `el`
   twins (Greek monosyllable tonos cuts the other way — a mechanical
   keep-the-marked rule was tried and reverted), `hi` nuqta variants, `de`
   ß/ss duplicates, `fr` 1990-reform pairs (both spellings official — merge
   and accept either as fully CORRECT), `es` broken twin glosses (`creo`
   glossed as crear, `llegue` "stab", `pagué` "cinchweed", `mío` "meow").
3. ~~**`de` digraph acceptance.**~~ **DONE 20 Aug 2026.** `GermanNLP.fold_lookalikes`
   now accepts the Duden substitution (ä→ae, ö→oe, ü→ue, ß→ss), so `schoen`
   for `schön` is amber instead of WRONG, while `schon` stays failed as
   another card. 24 rows removed (Swiss variants, identical-gloss twins, 9
   pre-1996 spellings, 2 digraph duplicates) plus `strasse` excluded. de
   strip-key collisions 128 → 127, fold-key 152 → 129.

**Done mechanically (103 + 4 rows):** self-identifying "misspelling of X"
rows deleted in 8 languages; ru ё-twins and Romance accent-twins with
identical glosses merged; four typo-mass artifacts (`citta` "Tuscan girl",
`envoye` "slowworm", `tete`, `voila`) deleted AND recorded in
`data/vocab_exclusions.tsv` — a TSV-only deletion is undone by the next
regeneration, exactly the way a DB-only fix is undone by a re-seed.

## 3b. Wrong-lexeme glosses — the frequency is one word, the gloss is another

A row's rank is carried by a form of one word while its gloss was taken from a
different word that happens to share the spelling. The same failure that made
English rank 3 `be` the element beryllium, arriving through accent collisions.

Confirmed across nine accent-carrying courses (20 Aug 2026), 19 rows reglossed:

| | rank | said | is |
| --- | --- | --- | --- |
| `pt` | 286 | `ia` — "AI (artificial intelligence)" | imperfect of *ir* |
| `pt` | 143 | `pelo` — "hair; fur" | the contraction *por + o* |
| `pt` | 606 | `irá` — "meliponine" (a stingless bee) | "will go" |
| `ca` | 924 | `soc` — "stump (of a tree)" | **"I am"** |
| `fr` | 235 | `dû` — "what is owed" | past participle of *devoir* |
| `fr` | 1099 | `fut` — "post-1990 spelling of fût" (a cask) | passé simple of *être* |
| `it` | 3033 | `dì` — "day; daytime" | the *tu* imperative of *dire* |
| `es` | 2810 | `mato` — "bushes" | "I kill" |

**Catalan had no correct card for "I am."** `soc` (rank 924, the post-2016 IEC
standard spelling) read "stump of a tree", while `sóc` at rank 63 carried only
a pointer calling itself superseded. Both cards, neither meaning.

**The detection is judgment, not a heuristic — two mechanical detectors were
built and both discarded.** Ranking a frequent surface against a rarer stated
lemma flags 530 rows across 27 courses, almost all correct (`puedo` really is
"of *poder*"; an inflected form outranking its infinitive is normal). Flagging
accent-twins whose glosses share no vocabulary gives 367, almost all
legitimate contrastive pairs (`de`/`dé`, `schon`/`schön`) that the collision
guard exists to protect. What actually separates the classes is asking
**"would anyone write this word this often, meaning that?"** — cinchweed at
rank 5192, a stingless bee at 606 — and that is a maker–checker question.

**The card's own sentences are the strongest evidence, and they are free.**
`es mato` was glossed "bushes" above three attached sentences all reading
*"I'll kill you"*; `it dì` was glossed "day" above three that all mean
*"say/tell"*. This is the D2c2 join (definition against examples) paying off
before the mechanical detector for it exists.

### A mechanical screen now exists, and it changed the size of this problem

The paragraph above said detection was judgment, not a heuristic, after two
detectors were built and discarded. A third works, and the reason it works is
one condition the earlier two lacked.

kaikki marks the distinction itself: an inflection carries `form-of` in its
sense tags plus a `form_of` lemma; contractions and abbreviations carry their
own. A candidate is a row where kaikki lists **both** a grammatical and a
lexical sense, the committed gloss matches the lexical one, **and the
grammatical sense points at a lemma this course also teaches**. That last
condition is load-bearing: without it the query returns 1,227 rows of mostly
noise (Xhosa `uku-` infinitives really are nouns; Indonesian `api` is "fire"
whatever else kaikki lists). With it, 351.

`backend/services/quality/audit_wrong_lexeme.py`. It needs
`data/raw/<code>_kaikki.jsonl`, which is gitignored — 8 GB of extracts — so it
is a **local maintenance tool, not a CI check**, and it screens rather than
judges. About 70% of its candidates were real.

**Swept the top 2000 of all 16 well-resourced courses (25 Aug 2026): 1,247
candidates generated, 1,217 decided, 781 repaired, 420 correctly kept, 16
rejected by reviewers. 425 fatal** — meaning the card named a genuinely
different word. (30 candidates were generated but not returned by an agent;
they are unreviewed, not cleared.)
Split by band: the top 500 gave 351 candidates and 248 repairs (130 fatal);
ranks 501-2000 gave 896 candidates and 533 repairs (295 fatal).

**The keep rate rises with rank, and that is the check on the pass**: roughly
30% of candidates were kept in the top 500 against about 50% below it. Deeper
in a frequency list the lexical sense genuinely is more often the right one, so
a pass that kept rewriting at the same rate would be rewriting on sight.

| | rank | said | is |
| --- | --- | --- | --- |
| `ca` | 66 | `estic` — "hockey stick" | **"I am"** |
| `ca` | 210 | `som` — "shallow" | **"we are"** |
| `ca` | 381 | `sou` — "salary, wage" | **"you are"** |
| `fr` | 55 | `va` — "version anglaise", a film-dubbing term | "goes" |
| `fr` | 57 | `as` — "ace (card of value 1)" | "you have" |
| `nl` | 41 | `kan` — "jug; pot" | "can" |
| `nl` | 78 | `kom` — "bowl; basin" | "come" |
| `pt` | 37 | `estou` — "hello (answering the telephone)" | **"I am"** |
| `it` | 46 | `era` — "age, epoch, period" | "was" |
| `ro` | 53 | `pot` — "pot" | "I can" |
| `ru` | 34 | `есть` — "to eat" | "there is; I have" |

**Catalan's whole core present tense was affected**, not one row: `estic`,
`som`, `sou`, `vas`, `va`, `fa`, `pot`, `tens`, `dic`, `faig`, `fem`. The
`soc` case recorded above was not an outlier, it was a sample.

**Two of the Dutch rows were already named in `nl.md`** — "`wil` → will (also
he/she wants)", "`meer` → lake (also the everyday more)" — and nothing had
acted on them. A finding recorded and not executed is not a finding; see the
`la` macron policy and the `jam` Cassidy policy for the same shape.

**Status: all 27 for the sweep. Nine accent-carrying courses done by hand;
the top 500 of all 16 well-resourced courses done by screen + review.** The
nine accent-carrying courses were triaged by hand; `ru`, `ar`, `hi`, `th`,
`ko`, `tr` and `nl` were swept by the screen on 25 Aug and reviewed. All 16
well-resourced courses are now covered **to rank 500**.

**Final state of the sweep (25 Aug 2026): 911 rows repaired across 23 courses,
485 fatal, from 1,594 decided candidates (664 kept, 19 rejected).** Every
course with a kaikki extract is covered to rank 2000.

Three gaps, stated so they are not mistaken for coverage:

1. **Below rank 2000 is not swept.** That band is 48,363 of 170,948 rows — so
   **72% of all vocabulary has never been checked for this class.**
2. **`en`, `la` and `jam` cannot be screened this way** — they have no kaikki
   extract. `jam` has none at all; `en` builds its glosses from WordNet at seed
   time and `la` from its own source.
3. **30 candidates were generated but never returned by an agent** — unreviewed,
   not cleared.

**Arabic needed a different filter entirely, and this is the transferable
lesson.** In an unvocalised or unspaced script a written string is not one word
inflected — it is several DIFFERENT words sharing a skeleton, so nothing carries
a `form_of` tag and this screen sees nothing. Arabic scored 1 candidate in the
top 500 and was in fact carrying `نعم` "yes" glossed "to live in comfort",
`رجل` "man" glossed "to go on foot", and `بعد` "after" glossed "to be distant".
The filter that worked there was the defect's own signature: a row tagged
`verb` whose gloss opens "to …". It found 51 Arabic repairs — and, importantly,
**0 in Hebrew from 45 candidates and 0 in Persian from 56**, because every `ל-`
infinitive and `می-` present form really is "to …". A filter that had produced
fixes in those two would have been the tell that it was manufacturing them.

**61 of the 70 proposed row exclusions applied; 9 vetoed.** Each was read
against its accented twin before the call, not taken from the triage summary.
What went:

- **13 pointer glosses** — the row names another spelling and carries no
  meaning of its own (`pt idéia` "pre-reform spelling", `el οχι` "misspelling
  of όχι", `ca cóm` "superseded spelling of com").
- **38 rank-impossible rows** — the meaning is real but cannot carry the rank,
  because the frequency is unaccented typing of the twin. `es tenia`
  "tapeworm" at rank 2118 against `tenía` at 174; `pt nao` "carrack" at 504
  against `não` at 4; `ro inca` "Inca" at 585 against `încă` at 130.
- **7 post-1990 French rectification spellings** (`boite`, `maitre`,
  `connaitre`…) — official variants of the same word, so one card, not two.
  **The grading nicety is still open:** both spellings are fully correct
  French, so typing `boite` for `boîte` should be `CORRECT`, and today it is
  amber. That needs an alternatives mechanism, not a row deletion.
- **3 voseo forms** (`callate`, `mirá`, `sabés`) — `es.md` makes the course
  peninsular.

**Vetoed, because deleting a real word is worse than leaving an odd one:**
`el μία` (the full spelling of "one", and its gloss is correct), `el τί/τίς/δέ/ά`
(polytonic and abbreviation rows that need an `el.md` ruling rather than a bulk
delete), `de scheiss`, `nl client`, `pt pa`, `ro pă`.

**Three exclusions genuinely lose a sense**, recorded in
`data/vocab_exclusions.tsv` so they can return at a rank their meaning
justifies: `ro in` (flax), `es paris` (the Trojan prince), `pt nao` (a carrack).

Ceilings retightened after the deletions — `ar` 200 → 116 (the yeh move),
`pt` 130 → 108, `es` 247 → 230, `fr`/`ro` 500 → 491.



## 4. Orthography policy compliance — across every file the policy covers

`la.md` declared "no macrons, anywhere, all-or-nothing" **verified**, having
checked only `data/grammar/la_grammar.json`. Nobody re-checked
`data/la_frequency.tsv`, which had gone 48% non-compliant and seeded 40
duplicate cards.

**Status: parameterised — every course with an orthography policy, over every
file it covers** (`<code>_frequency.tsv`, `grammar/<code>_grammar.json`,
`gym/<code>.json`, both sentence banks).

Known policies and their state:

| | policy | state |
| --- | --- | --- |
| `la` | macrons everywhere, all-or-nothing | **compliant**, 5 guards |
| `mi` | macrons are the 16th letter, non-negotiable | **compliant** — 0 out-of-inventory chars (25 Aug) |
| `yo` | tone is phonemic, Standard Yoruba fully marked | **top band done** — 120 of 1,650 marked, was 6 of 1,644; tail blocked on an external source |
| `jam` | Cassidy–JLU, declared here and in `JamaicanNLP` | **12 → 2 non-compliant headwords** (25 Aug); the 2 are deliberate keeps |
| `xh` | Latin basic, no diacritics | **compliant** — 0 out-of-inventory chars (25 Aug) |
| `ha` | Boko incl. hooked `ɓ ɗ ƙ ƴ` | compliant for grading — 2 rows use U+02BC, which `HausaNLP.normalize` folds |
| `ar` `he` `fa` | vocalisation marks | not yet stated as a testable policy |
| others | — | **UNDECIDED — needs a policy statement before it can be checked** |

**A letter-inventory gate is the cheap half of this and it generalises**: express the
policy as a character set and the violations fall out. Measured 25 Aug across the five
courses with a tight declarable inventory — `mi` 0, `xh` 0, `yo` 0, `ha` cosmetic-only,
`jam` 6. So the class is real but currently **Jamaican-scoped**, which is a measured
decision rather than an omission.

It is **necessary, not sufficient**: `friend` breaks no Cassidy letter rule and is still
the English spelling, and `mangguus` trips a doubled-consonant regex where the `gg` is
really `ng` + `g`. A gate proposes; a reviewer disposes.

### 4b. `alt`-column laundering — a variant that is another word's headword

Only `jam` has an `alt` column (347 of 384 rows). It is deliberate leniency — a learner
typing `him` for `im` should pass. But **5 entries listed another row's HEADWORD** as a
variant: `di` (the) claimed `de` (to be at), `nuo` (know) claimed `no` (the negator), `wi`
claimed `we` (where). That is the fold rule ("a fold may excuse a mark; it may never launder a word") inverted — the leniency stops excusing a spelling and
starts laundering a word, on some of the commonest words in the language.

**The collision ratchet cannot see this**: `_collision_surfaces()` reads only the `word`
column. Checked separately; **0 clashes remain** (25 Aug).

**Status: scoped — `jam` only, because no other course has an `alt` column.** Any course
that gains one inherits this check.

---

## 5. Definition ↔ example sense agreement

Does a card's example set demonstrate the sense its gloss *leads with*?

Portuguese rank 2 `a` is glossed "**the (feminine singular)**; to, at — also
estar a + verb; her, it" and all three of its sentences are `está a fazer` —
the third sense. The gloss was repaired and the examples were never rechecked
against it.

**Status: all 27 — and NOT YET BUILT.** `audit_polysemy` compares the gloss to
the dictionary; `audit_examples` counts and varies sentences; neither joins the
two. It becomes mechanical once sentences carry glosses (a gloss states the
word's role), which is why it is sequenced with the gloss work. Until then the
maker–checker performs it by hand, on every language, not only the ones with a
reported example.

---

## 6. Interlinear gloss coverage

**Status: scoped — the 9 courses wired for the layer** in
`frontend/src/features/review/hintLayers.ts`: `mi sw yo xh ha` open on it,
`ru ar el hi` reach it after romanization. The other 18 have no gloss step and
need none.

374 of 8,049 drills carry one (4.6%) — `mi` 240, `sw` 134, everyone else zero.
`yo`, `xh`, `ha` are GLOSS_FIRST **with zero glosses**, so their ladder opens on
an empty layer and drops to English.

Not every sentence gets one, by design: 4,974 rows in the GLOSS_FIRST courses
are the target, out of 484,754 total.

---

## 7. Frozen counts in the guidelines

Never assert a number the audit already computes. 118 defects found across the
27 files — 45 outright false.

**Status: all 27.** Rules in `README.md`.

---

## 8. The homonym lexicon gap — the other word is not merely under-glossed, it is ABSENT

The frequency pipeline builds **one row per surface form**. When two words share
a spelling — or shared one because the source text carried no marks — only the
corpus-dominant word got a row. The other is not a missing sense on a card; it
is **a missing word in the lexicon**.

Measured in Latin (19 Aug 2026), immediately after macronisation made the gap
visible: `hic` "this" present, `hīc` "here" **absent** — while `ibi` "there"
and `ubi` "where" both have rows, so the slot plainly exists; `lātus` "wide"
present, `latus` "side" absent; `populus` "people" present, `pōpulus` absent
(fine — poplar is not first-year); `malum`/`mālum` both absent.

**Where it concentrates: exactly the courses whose marks were stripped or never
present.** In accent-keeping courses the corpus distinguishes the pair, so both
usually have rows (`es` has `el` AND `él`, `fr` has `a` AND `à`). But `yo` is
1,638 toneless rows in a language where tone separates whole lexemes — so each
skeleton row potentially stands for SEVERAL words, and the lexicon is missing
every non-dominant member. Same for `mi` before its macron repair.

**The rule this adds to every orthography repair (Phase 2a): re-marking is not
decoration.** When a row gains its marks, the pass must decide *which word the
rank belonged to* and whether the other members of the collapsed set merit rows
of their own. A re-marking pass that just decorates the existing row with one
mark pattern silently keeps the gap.

**Status: all 27.** Concretely: after any orthography repair, sweep for
high-frequency homonym members with no row (the Latin sweep is the model);
in unmarked-script courses (`th`, no spaces; `ar`/`he`/`fa`, unvocalised) the
same gap hides behind spelling rather than diacritics and needs the
dictionary's homograph entries checked against the file.

## 9. The six layers of a card — measured per layer, not per course

**The standard each layer must meet is `docs/quality/card-layers.md`** — the
Leipzig Glossing Rules for the interlinear line, the romanisation policy, and
the per-course sentence sourcing. This section is the measurement; that file is
the requirement.

**Owner directive, 25 Aug 2026:** check hint, sentence, translation,
interlinear gloss, and — for non-Roman scripts — the romanisation. Plus the
definition, which is the layer the wrong-lexeme sweep repaired. A course is not
"done" because one layer is.

**Name them precisely — "gloss" means THREE things in this repo:**

| written as | actually means |
| --- | --- |
| `data/gloss_overrides.tsv` | **definitions** (`ar أن → "to, that…"`) |
| a drill's `gloss` field | the **interlinear** word-by-word line (`a · student · ___`) |
| audit rule `giveaway_by_gloss` | a **hint** that repeats its own translation |

**What that cost, stated accurately.** It did not cause the Māori
interlinear defect — that line was wrong in `mi_grammar.json` regardless, and a
definitions pass reads different files and would never have looked at it. What
the ambiguity did was make the REPORTING wrong: "911 gloss fixes" reads as
though the word-by-word layer had been repaired when nothing had touched it,
and the owner found the defect from a screenshot rather than from any status
this program produced. The failure is a claim that overstated its own coverage,
which is the same failure as "audit PASS" reading as though it described
production.

Measured 25 Aug 2026:

| layer | state |
| --- | --- |
| hint | present on 100% of drills in all 27 — but presence is not quality; `audit_content` still carries 920 hint findings (`id` 121, `tl` 152) |
| sentence | present for 22; **`la`, `id`, `tl`, `he`, `fa` have ZERO**. Range 63 (`yo`) to 202,772 (`en`) |
| translation | 100% wherever a sentence exists |
| interlinear gloss | **`mi` 100% of drills, `sw` 30% of drills / 91% of bank, every other course 0%** — this is D2c, "built for nine courses, filled for one" |
| romanisation | see below |

### Romanisation is the worst-covered layer, and two courses have none at all

Only the eight non-Roman courses need it. Splitting drills from sentence banks,
because they are filled independently:

| | drills | sentence bank |
| --- | --- | --- |
| `ar` `el` `fa` `he` `ru` | 100% | `el` 100%; `ru` 0%, `ar` 0%; `he`/`fa` have no bank |
| `ko` | 78% (949/1217) | 18% |
| **`hi`** | **0%** | **0%** (8,130 sentences) |
| **`th`** | **0%** | **0%** (4,037 sentences) |

**`hi` and `th` have no romanisation anywhere.** Devanagari and Thai are the two
scripts in this repo a beginner is least able to decode cold — Thai has no
spaces between words — and both ship with none. `ru` and `ar` have romanised
drills but 348 and 14,671 unromanised sentences respectively.

**Status: all 27 for the check; per-layer for the fix.** The sentence-bank
columns are themselves inconsistent (`ru` has no `transliteration` column at
all, `ko` does), so filling this starts with agreeing the schema.

---

## 10. Unanswerable cards — a definition that cannot reach its word

`ha` rank 119 `abubakar` is defined, in full, as **"a male given name"**. So is
`de` rank 870 `mike`, `nl` rank 606 `sam`, `fr` rank 930 `mike`. The gloss is
accurate and the card is impossible: the prompt gives a learner no route to the
answer, and dozens of rows in the same course share the identical prompt.

**1,164 rows across 20 courses** whose ENTIRE definition is "a male given
name", "a female given name" or "a surname" (measured 25 Aug 2026):

`de` 220, `fr` 141, `pt` 119, `nl` 100, `es` 91, `ro` 82, `it` 70, `tr` 69,
`ru` 60, `ar` 47, `ha` 38, `hi` 28, `ca` 27, `el` 22, `yo` 22, `mi` 18,
`sw` 6, `th` 2, `ko` 1, `xh` 1.

**This is NOT the wrong-lexeme class** (§3b) and must not be counted with it.
Those cards name a different word; these name the right word uselessly. Two
different repairs:

- where the name is one a learner genuinely meets (`ha abubakar` at rank 119,
  `yo adebayọ` at 545 — these are common Nigerian names in running text), the
  row needs REAL content: the English equivalent, the bearer, or what the name
  means. "Michael — a male given name" is unanswerable; "Michael — the English
  equivalent of Michel" is not.
- where the name only earned its rank from corpus noise (`de mike`, `nl sam`,
  `fr max` — English names inside foreign-language text), the row belongs in
  `data/vocab_exclusions.tsv`, not on a card.

**A separate, smaller class hides in the same query**: a proper-noun row glossed
with an unrelated COMMON noun — `it svizzera` "hamburger" for Switzerland,
`it roma` "a type of rice" for Rome, `pt charles` "rabona". Those ARE §3b and
are being repaired by the db-vs-file pass.

### Resolved (owner decision, 25 Aug 2026): 645 retired, the rest kept

**A card asks the learner to PRODUCE a word from its definition.** Nobody can
produce `Abubakar` from "a male given name", and dozens of rows in one course
carry that identical prompt — so those are not hard cards, they are impossible
ones, and frequency does not rescue them (`ha abubakar` is rank 119).

But the class is not uniform, and only one third of it is unanswerable:

| | | |
| --- | --- | --- |
| **645** | "a male given name" with NO English equivalent named | **retired** |
| 189 | names an equivalent AND the form differs — `ca isabel` → Elizabeth, `júlia` → Julia, `antoni` → Anthony | kept: answerable, and it teaches the difference |
| 160 | names an equivalent, form identical — `ca robert` = Robert | kept |
| 822 | **place names** | kept **even when identical to English** |

**Place names stay whatever the spelling**, on the owner's reasoning: a learner
studying several languages needs to recognise that the word is the same but
*said* differently. That is delivered — `ReviewSessionPage.tsx:517` falls back
to speaking `correct_answer` on a correct answer for non-cloze cards, so a
Spanish card for `Sydney` plays the Spanish pronunciation. 17 courses have TTS.

Retired rows are removed from the TSV **and** recorded in
`data/vocab_exclusions.tsv` (78 → 723 rows), which is the convention the
existing exclusions follow — a TSV-only deletion is undone by the next
regeneration.

**Status: all 27, measured and resolved.**

---

## 11. Romanisation must mark the blank, not spell it

**Measured 26 Aug 2026: 926 romanisations handed the learner the answer.**
`hintLayers.ts` reveals romanisation FIRST for non-Latin scripts — before the
gloss, before the translation — so a romanisation of the COMPLETE sentence is
an answer key on the first hint press.

| | leaking, before | after |
| --- | --- | --- |
| `he` | **191 of 191** — every drill | 0 |
| `fa` | **188 of 188** — every drill | 0 |
| `ko` | 547 of 1,213 | 0 |
| `hi` `th` `ru` `ar` `el` | 0 | 0 |

    {{answer}} איש טוב.   answer הוא   ->  "hu ish tov."

**Two blank conventions are in use and both are accepted.** `ru`, `ar`, `el`,
`he`, `fa` write `___`; `ko` writes `{{answer}}`, which it needs because its
blanks sit INSIDE a word (`저{{answer}}` — a bare `___` would not show the
particle attaching). `hi` and `th` were filled following `ko`'s form.
**Settling on one is undone**, and deliberately not forced by the test:
churning 750 rows over a cosmetic choice is not the same as fixing a defect.

672 rows were repaired mechanically (whole-token blank, aligned token counts),
252 by review, and **2 by hand because no rule could place them** — Korean time
expressions where the answer's romanisation occurs twice:

    12 시 50 분은 {{answer}} 오십 분이에요.   answer 열두 시
      yeoldu si osip buneun yeoldu si osip bunieyo.
      -> the SECOND occurrence is the blank; the first romanises the literal 12 시

**Status: all 8 non-Latin courses, enforced.**
`test_the_romanisation_keeps_the_blank` in `test_orthography.py`.

---

## 12. A layer needs a write path, and three did not have one

Three separate times this programme filled something that could not reach a
learner. The class is worth naming because it is invisible to every content
check: the DATA is right, the PIPE is missing.

| what | how it failed | found |
| --- | --- | --- |
| `transliteration`, `gloss` | `load_example_sentences` never wrote the columns. `ko`'s TSV carried romanisation since it was built; production read 18%. Interlinear gloss read 0% in production for **all 27**. | 25 Aug |
| collision guard | `.dockerignore` excluded `data/*`, so `_collision_surfaces()` caught `OSError` and returned an empty set — the guard was OFF in production while 37 tests passed locally | 25 Aug |
| macron policy | the guard listed the frequency, grammar and gym files but **not** the sentence bank, so 504 unmacronised rows would have passed | 26 Aug |

**The check that generalises: follow a layer end to end before filling it** —
file → loader → column → renderer — and write a test at the weakest joint.
`test_runtime_data_ships.py` does this for the image; the loader now carries
both columns; the macron guard now lists the sentence bank.

**Still open, and it blocks the romanisation work from ever being seen:**
`load_example_sentences` uses `ON CONFLICT ... DO NOTHING`, so an EXISTING row
does not gain the new columns on a re-run. The ~28,000 sentences harvested on
25–26 Aug are already-written rows. **Backfilling them is reconciler work and
is not built.**

---

## Adding a check

1. Measure it on the language that surfaced it.
2. **Run the same measurement on the other 26 before writing any fix.**
3. Decide the status: all / parameterised / scoped — and if scoped, state why,
   with the measurement that justifies the limit.
4. Add a row here. A check absent from this file does not exist.

---

## §13 A green assertion can be a crash — check the path ran

`test_generates_and_draws_one_message` asserted the Gym charges one message
per form topped up. It was green in CI and red on a developer machine, which
reads like flake and is not.

WP45 (`672ecb2`) added a second charge — one message per new word charted —
so the honest answer became 3. The test kept reading 1 because it left
`generate_chart` unpatched: with `TUTOR_DEV_MOCK` unset, `make_chart` builds
a live Anthropic client, the keyless call raises, and the router's
`except: break` skips both chart charges. **CI passes because the feature
crashes.** Turn the dev mock on — i.e. make the code actually work — and the
test fails.

Three things this establishes, all now enforced rather than remembered:

1. **Check the path RAN before trusting a green assertion.** Any assertion
   about a code path that calls outward can be satisfied by that call
   failing. Assert the call happened (`mock.assert_not_awaited()` /
   `await_count`), not only the number that came out the end.
2. **No test may construct a live model client.** `never_reach_a_live_model`
   (autouse, `backend/tests/conftest.py`) raises on any `AsyncAnthropic`
   construction with a message naming the fix. With a key present the old
   behaviour would have SPENT it — two calls per run of one test — against a
   standing owner directive not to. The full suite passes with the guard in
   place, so nothing else was reaching out.
3. **When CI and local disagree, find out which one is executing the real
   path.** Here the greener environment was the broken one. Run both
   (`TUTOR_DEV_MOCK=false .venv/bin/pytest …` reproduces CI) before deciding
   which result to believe.

Verified 26 Aug: 2,162 pass with the mock ON and 2,162 with it OFF — the
suite no longer depends on the setting.

---

## §14 The answer-leak class, third instance — and how it hides

A support layer exists to help the learner recall the answer. Three times now
one has printed the answer instead:

| layer | scale | how it looked |
| --- | --- | --- |
| romanisation | 926 rows (`he` 191/191, `fa` 188/188) | the reading spelled the blank |
| Hebrew hint | 191 of 191 drills | the hint was the answer |
| interlinear gloss | **134 of 134 Swahili drills** | `Utarudi {{answer}} ...` glossed `... lini (when) ...` where `lini` IS the answer |

Nobody reports these, because the only people who read a support layer are
the people who cannot check it. `backend/tests/test_gloss_layer.py` and the
romanisation guards now run over every course. **A new layer gets its leak
test before it gets content.**

### Two audit mistakes this cost, both worth not repeating

**Search the folded form.** The first Swahili audit found 71 and reported
them. It missed 62 more — nearly half — because the gloss writes the head
with morpheme boundaries (`i-ko`) while the answer is written without them
(`iko`). A word-boundary regex sees two different strings; a learner sees the
answer. Normalise hyphens, spaces and case away before comparing. A third
form hid again by spanning two cells (`ku-to-kata tamaa`).

**Compare tokens, not substrings.** Loosening to a substring match to catch
the above then flagged 32 clean lines: `na` occurs inside `ni-na`, and Māori
`I` is both the past-tense marker and the English gloss of `au`. Every one was
a phantom. The leak test is therefore scoped to the self-labelling format —
the only one whose gloss line carries target-language words at all — because
a positional gloss (`CONT · live · ___ · to · Wellington`) holds nothing but
English and category labels, so there is no target word in it to leak.

## §15 Build it and measure it; do not predict it

Three romanizers went through identical adversarial verification — two
lenses over 60 corpus sentences biased toward the risky construct, every
claimed defect put to independent refuters, then a second round on 60 fresh
sentences.

| | prediction | result |
| --- | --- | --- |
| `el` | risky — digraphs, voicing | **1** systematic defect (`γκ`), round two clean → shipped |
| `ko` | risky — assimilation across every boundary | **1** systematic defect (`ㄹ`+`ㄹ`), round two clean → shipped |
| `th` | buildable, once a segmenter exists | **38** defects in 7 classes; 6/18 on the confirmed set → **not shipped** |

Both defects that shipped were the same shape: a table with a rule's
neighbours filled in and the rule itself absent, passing every example I
chose by hand. Thai's were spread across silent leading consonants, dropped
linking syllables in Pali compounds, mid-word segmentation, and a repetition
mark the engine hallucinated a syllable from — and they land on ordinary
words (`สุขภาพ` health, `ฝรั่งเศส` France, `ไหม` the question particle).

The ranking was not predictable from what the scripts look like. Build the
romanizer, run it over the real corpus, and let the number decide. Recording
a rejection is a result: `test_thai_reading_is_not_ready.py` pins each known
failure so the day one starts passing is visible.

---

## §16 The translation pipeline re-runs the guards on its own output

A Spanish speaker learning English reads the auto-translate loop's output on
every card, so the loop now carries the same mechanical guards as the content
it conveys (`backend/services/translate_checks.py`, gated inside
`generate_sentence_translations` / `generate_text_translations`, proven in
mock mode by `test_translate_gates.py`):

* **A translated hint must not contain the drill's answer.** The label
  charter's own — correct — instruction to copy quoted course-language
  material unchanged is precisely how an English hint that quotes its answer
  (`be — bare`) carries the leak verbatim into every locale. The render guard
  would blank it, the learner would get no hint, and COALESCE would keep the
  row "done" forever. The gate withholds instead, so the sweep retries after
  the source is fixed. The drill's TRANSLATION field is deliberately not
  answer-gated: an English answer `no` would veto every Spanish sentence
  containing the Spanish word `no` (rule 19's homograph phantom).
* **Model-controlled indexes are validated.** `rows[res["i"]]` with `i = -1`
  filed a rendering under the LAST row with no error — the luna/stella class.
  `safe_row` drops anything not an in-range int; no raw lookups remain.
* **Identity echoes, altered cloze blanks, and missing Spanish inverted
  punctuation are withheld** rather than stored (examples land
  `reviewed=true`, so nothing downstream re-examines them).
* **Folding strips Unicode category `M*`, not `combining()>0`.** Python's
  `\w` drops the Devanagari vowel sign ी (Mc, combining class 0) exactly as
  JS `\p{L}` did, so रही tokenised as रह and slipped the guard. Same bug,
  second language, now one fold on both sides.
* Sentences are graded by their own checker charter naming the caught
  classes (wrong language outright — the TRADUCCIÓN incident —
  part-translation, meaning drift), not the word-gloss charter's
  "right part of speech".

Also fixed at the source: ten `en` hints named their own answer as a folded
token and rendered blanked; all ten rewritten leak-free (checked against the
same fold before writing).

---

## §17 Where the interlinear gloss renders — and the one surface that drops it

Traced end to end 30 Aug 2026, before authoring at scale (rules 13 and 22):

| surface | path | gloss? |
| --- | --- | --- |
| vocabulary review card | `cards.py` `es.gloss` → `example_glosses` | **yes** |
| grammar review card | `cards.py` `d.glosses` → `drill_glosses` | **yes** |
| grammar LESSON view | `curriculum.py:269` `examples[]` | **no** |

So the layer is live on both SRS surfaces — the ones a learner actually
drills — and authoring is not into a dead route. The lesson view is the
exception: its query selects only sentence/answer/translation/hint, and it
computes `reading` on the fly rather than reading the stored romanisation.

**Adding gloss there is not a one-line select.** The lesson view fills the
answer INTO the sentence (`ANSWER_MARKER` → `d["answer"]`), while the stored
gloss carries `___` at that position by construction. A filled sentence over
a blanked gloss cell is a mismatch a learner would notice, and nothing stores
the answer's own gloss cell to substitute. Options, undecided: substitute the
answer's cell (needs a new field), drop the `___` cell from the lesson
rendering, or leave the lesson view glossless and let the layer be an SRS
feature. Left alone deliberately — surfacing it is the job.

Sentence-bank status the same day: `gloss` column present and populated only
in the five gloss-first banks (`ha`/`mi`/`sw`/`xh`/`yo`); the other 22 TSVs
have no gloss column at all. 6,627 of 375,004 sentence rows glossed (2%);
1,439 of 8,874 drills (16%). The write path (`seed_sentences.py`,
`seed_grammar.py`, migration 20260707) carries both gloss and
transliteration, so this is a content gap, not a plumbing one.

---

## §18 A curated file does not reach a learner by itself (30 Aug 2026)

The owner opened the English card for `I` and was shown **"I am."**,
**"I am you."** and **"I am!"** — while `data/en_sentences.tsv` holds
"I think he did it." and "Just do what I say." for that word.

None of those three is in any committed file. They are rows the curation cut
that stayed live, because `seed_sentences` inserts `ON CONFLICT DO NOTHING`
and can therefore only ever ADD. Production held **196,004** English
sentences against a curated **70,975**, and the review card picks at random
from everything present — so thinning the file changed nothing a learner saw.
This is the sentence-layer twin of §16's rule: a fix that lands in a file is
not a fix in production until something carries it there.

Two mechanisms now exist, and they are NOT the same job:

* `seed_sentences -l <code>` — additive, safe, idempotent. Fixes "the file
  has content production lacks". Five courses had sentences on disk and
  **zero** in the database (`he` 7,483, `id` 5,219, `tl` 4,749, `fa` 4,003,
  `la` 1,136); 26,471 rows were loaded on 30 Aug.
* `prune_sentences -l <code> --apply` — subtractive, gated behind a rollback
  file. Fixes "production has content the file rejected". This is the only
  thing that makes a thinning decision real.

**Measured 30 Aug, all 27:** 147,246 tatoeba rows are no longer endorsed by
any committed bank (English alone 127,363), 30,938 rows are exempt as
`curated`/`ai`, and 1,131 words would be stranded and are therefore left
alone. See §18a for why the match key is not the obvious one.

### §18a The prune's match key is (word, SENTENCE), never the locale

The committed bank keeps one row per sentence; the database keeps that
sentence once per translation locale. Keying the prune on
`(word, sentence, translation_locale)` — the same key the INSERT conflicts
on — would delete the German translation of a sentence the bank endorses
merely because the file happened to store that sentence with its Spanish
one. Modelled before running: keying on the sentence keeps 66,258 English
rows across all locales; keying on the locale would have kept far fewer and
silently cost every non-file locale.

Three invariants are tested rather than trusted (`test_prune_sentences.py`):
`curated`/`ai` are never candidates, a word is never stranded with zero
sentences, and **an empty or missing TSV refuses outright** — the file
endorsing nothing must not mean "delete the entire corpus", so `survey()`
does not even issue the query.

---

## §19 A conjugation cue is not an answer leak (30 Aug 2026)

A sweep for "hints that name their own answer" flagged 96 drills; 12 of them
were correct as written and the fix broke them.

A conjugation/declension drill — one carrying a `cell` — is cued by
`<base form>, <person>` in the TARGET language (`test_grammar_hints.py` locks
this for es/fr/it/ca/ro/de/ru/nl). Naming the base form is the exercise's
PREMISE: "conjugate *haben* for *wir*" is the task, and German 1PL happens to
coincide with the infinitive. The learner is not being handed the answer;
they are being handed the input.

Two ways the sweep manufactures a false positive here:

* **Coincidence.** German 1PL/3PL *haben* = infinitive *haben*, Romanian `tu`
  imperative *deschide* = stem of *a deschide*. Real forms, real convention.
* **The fold.** Romanian `a cânta` → `cântă` differ ONLY in the diacritic the
  folded comparison strips. The mark IS the grammatical content being tested,
  so folding the two together invents a leak. This is rule 10 from the other
  side — a fold may excuse a mark, but where the mark is the answer, the fold
  must not be applied at all.

**So: exclude drills with a `cell` from the answer-leak sweep**, and check
them against the conjugation convention instead. A `cell` drill whose hint is
NOT a base-form cue is still fair game — `nl` had two whose hint was the bare
string `is` for the answer `is`, which is a leak by any reading; those were
put on the convention as `zijn, het` / `zijn, dat` (Dutch has an infinitive,
and *zijn* ≠ *is*).

Count after the pass: 0 non-conjugation hints name their answer, across all
27 courses, down from 84.

---

## §20 "Same hint, different answer" is mostly capitalisation (30 Aug 2026)

A sweep for drills sharing a hint across different answers returned **121**
across 16 courses, each supposedly unanswerable — a learner types a correct
word and is marked wrong. Only **45** were real.

The other 76 were the SAME answer, capitalised because one drill's blank
opens its sentence: Catalan `Hi` / `hi`, Spanish `la` / `La`, Jamaican
`Di` / `di`, Romanian `este` / `Este`. Those drills are supposed to share a
hint. Fold the answer before comparing, exactly as the leak sweep does.

Two further shapes look like the defect and are not:

* **A rule that the learner applies.** Turkish `mı / mi / mu / mü` all share
  "question particle — harmonize with the last vowel", which is the complete
  and correct cue: deriving which vowel is the exercise. Compare §19's
  conjugation cue — naming the input is not giving the answer.
* **A repeated answer inside a genuinely mixed group.** Greek point 34 has
  three drills, two answering `ότι` and one `πως`. The two `ότι` drills must
  keep the SAME hint. So the rule is not "all hints in a group are distinct"
  — it is **hints differ wherever answers differ, and match wherever answers
  match**. A first pass demanding all-distinct rejected the correct fix.

After the pass: 1 shared-hint group remains, the Turkish harmony set, and it
is correct as written.

---

## §21 An example sentence must let the learner determine the use (30 Aug 2026)

Owner requirement, from three production cards: *"Sentences need to allow
context to be given and determined."*

`Да.` for **да**, `И?` for **и**, `Что?` for **что** — the sentence is only
the word, so it demonstrates nothing about how the word behaves. **2,671
such rows across 24 courses**, English included after its prune (306, the
largest single count). Measured by stripping punctuation and comparing the
remainder to the headword, which is script-independent — a whitespace token
count is not, and reports nonsense for Thai and Korean.

Two neighbouring rules the same cards exposed:

* **The sentence must contain the word it teaches, in the form it teaches
  it.** 1,027 rows contain a different written form — Arabic `أنت` taught
  with `أنتِ` in the sentence (masculine vs feminine *you*), Latin `hic`
  taught with `hīc` used, Yoruba tone pairs. Case differences are NOT this
  defect: 53,813 rows differ only by a sentence-initial capital and are
  correct. Fold case, never marks — the mark is the word.
* **The example must exercise the sense the definition leads with** (D2c2).
  The `ё` card glosses "yeah!, yo!, oh yeah!" and its sentence uses `-е` as
  an ordinal ending. Nothing checks this today; it needs a rule before it
  can be counted.

Measurement note, third time in one day: Python's `\w` drops Mn/Mc marks, so
`नहीं` tokenises as `नह` and `ใช่` as `ใช`. A first pass reported 1,713
form-mismatches, 1,299 of them phantoms from that. Tokenise on
letters-plus-marks, or the Indic and Thai numbers are fiction.

---

## §22 An unspaced script cannot be gloss-checked by whitespace (30 Aug 2026)

The interlinear gloss's contract is one cell per token, joined by ` · `. That
assumes tokens are whitespace-delimited. **Thai writes without spaces**, so a
whole drill sentence is ONE token — 205 of Thai's 271 — and a correct
three-cell gloss of `ผม{{answer}}ข้าว` (`1SG.M · ___ · rice`) reads as a
count error. The first pass rejected 100 correct Thai glosses that way and
landed Thai at 19% while every other course in the batch cleared 99%.

`apply_drill_glosses.tokenize` now segments unspaced scripts by borrowing the
**reading pipeline's own segmentation** — the romaniser emits space-separated
words and passes `{{answer}}` through as a unit, so it divides the sentence
the way the learner sees it divided. Thai went 19% → 44%.

**The remaining 105 are not wrong glosses.** They are two segmenters
disagreeing: the dictionary longest-match segmenter and the author divide
unspaced text differently, both defensibly. At that point the gate is
measuring *"do two segmenters agree"*, not *"is this gloss right"*, and it
should not be read as a defect count.

The real fix is to store the segmentation WITH the gloss so the renderer
aligns cells to the same units the author used — a schema question, not an
authoring one. Until then Thai's drill gloss is capped around 44% and that
ceiling is a known limitation, not a backlog item to grind at.

Applies to any future course written without word spaces (Japanese, Chinese,
Khmer, Lao). Check the writing system before setting a coverage target.

---

## §23 The complexity bar for an example sentence (owner, 30 Aug 2026)

§21 set the floor — a sentence may not be only the word it teaches. This is
the ceiling, and it is the more demanding half: **a sentence must carry a
scene, because that is the mechanism by which a learner remembers.**

Grammatical is not the standard. *Я живу в Москве* is correct, natural, and
nearly worthless as a card — there is nothing to picture, so nothing to
attach the word to. *Я живу в Москве уже пять лет, но до сих пор путаюсь в
метро* teaches the same word and is memorable, because it has a duration, a
complication and a feeling.

The bar, applied when authoring and enforced when checking:

* **7–14 words.** Below seven there is rarely room for a scene; above
  fourteen it stops being memorable.
* **A finite verb and a real predicate** — not a label, list, or bare noun
  phrase.
* **The target word does work.** Remove it and the sentence should lose
  meaning. A preposition or particle must sit in the construction that
  actually teaches its use.
* **Three sentences per word, differing in KIND** — one domestic, one social
  or working, one carrying feeling or opinion. Three frames with swapped
  nouns count as one sentence.
* **Native settings.** A dacha, a marshrutka, Ramadan, a souq — not English
  scenery with the nouns changed.
* **Meaning-for-meaning translations**, never word-for-word.

**Measured before the first pass (30 Aug):** 21% of Russian and 31% of
Arabic sentences were three tokens or fewer. 151 Russian and 228 Arabic words
inside the top 2,000 had NO sentence longer than three tokens — including
`я` (rank 0, best example "Не я."), `не`, `и`, `что`, `كان`, `لا`, `هذا`.
The highest-frequency words had the thinnest examples, which is the worst
possible distribution: they are what a learner meets first.
