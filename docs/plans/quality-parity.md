# Quality & parity: every language to the same bar

The owner's report, from two screenshots and a sentence: English "be" is
defined as *"a light strong brittle grey toxic bivalent metallic element"*
(that is beryllium, Be), the German course defines a headword `s` as a letter
of the alphabet, and "English is lacking sentences in a way that is a
problem." The ask: fix quality and parity across all 27 languages — gym,
sentences, lessons, reviews, everything — with a maker–checker pass over
anything new.

Measured 17 Aug 2026 against the tree. The standard is §3b of the ROADMAP;
per-language rules live in `docs/quality/<code>.md` and win over anything
general here.

## Ground rules for this program (owner decisions, 2026-08-17)

1. **No API spend.** All extraction, generation, and checking runs in the
   local Claude Code session — never the owner's `ANTHROPIC_API_KEY`.
   extra-agent's schema, validation, and emit-merge machinery are still used
   (they are offline); only its API-calling extractor is not.
2. **Facts ship; sentences are regenerated.** From commercial course
   material (see `docs/extraction-sources.md`): vocabulary, grammar
   structure, paradigms, sequences, and pitfalls may ship. Verbatim course
   sentences and drills may NOT — every example sentence and drill sentence
   is freshly written and checker-verified. This amends the old
   calibration-only rule and also applies retroactively: the verbatim
   commercial sentences already shipped (sw, ko — see Phase 2) get replaced.
3. **Everything authored gets an adversarial check.** Maker and checker are
   separate passes (separate subagents in-session); a batch that the checker
   cannot defend is rejected, not filed.

---

## What is actually wrong (diagnosis, three agents deep)

### D1 — Wrong-sense definitions (the screenshots). Three causes:

- **English course** (`seed_english.py:151`): definitions come from WordNet
  `synsets[0]`, which returns nouns first. `be` → beryllium; rank 29 `don`,
  `up`, `well`, `there`, `one` all wrong-sense. 161 of 183 words of length
  ≤2 (794 of length ≤3) fall through the 51-entry hand guard. Tokenizer
  shrapnel (`re`, `ll`, `ve`, `e`, `lf`, `th`, `wh`…) seeds as words.
- **kaikki languages** (`source_data.py:297-357`): the first dictionary
  entry with any usable gloss wins — no POS ranking — so `name`/`symbol`/
  `character` entries beat the real word. Live today: fr rank 15 `ne` →
  an ISO canton code; fr rank 36 `y` → "a letter in the French alphabet";
  de `ne` → canton code. The `alt_of` filter also kills correct
  "abbreviation of" senses.
- **Stale committed TSVs** (tr, yo, sw, xh): predate the current filters.
  Yoruba ranks 1–12 are almost all letter-name glosses; Turkish rank 4 `ve`
  ("and") is glossed as the letter V. 266 rows the current code could never
  emit, 58 in the top-500 band. The German `s` card is a stale DB row —
  current code drops it; the refeed clears it.

### D1b — The larger definition problem behind the screenshots (measured 17 Aug)

The wrong-sense class the owner photographed is the *small* half. Sweeping
every committed frequency TSV over the top-1000 band found **2,156 unique rows
carrying at least one definition defect**, in six classes:

| Class | Rows | Example |
| --- | --- | --- |
| Dictionary jargon, often with an inline romanization | 1,912 | ru `мне` → "dative/prepositional of я (ja)" |
| Truncated — gloss ends in `:` and the senses it promised are gone | 925 | ru `от` → "from, away from, of, with (in the following senses):" |
| Raw MediaWiki markup | 151 | **sw rank 2** `ya` → `[[Appendix:Swahili_noun_classes#N class\|n class_((IX))]] i` |
| Wrong sense (letter name / ISO code / sound-of-letter) | 60 | fr rank 15 `ne` → "ISO 3166-2:CH code of Neuchâtel" |
| Bracket with no definition at all | 6 | **ru rank 4** `в` → "[with prepositional]" |
| "See X" stub | 3 | ar `الخاصة` → "See خَاصَّة (ḵāṣṣa)" |

Worst languages by unique affected rows: sw 289, hi 270, nl 174, de 160,
it 142, pt 135, ca 134, fr 128, ru 127, es 115, ro 114, el 109.

Two of these are worse than they look. Swahili's rank 2 and Russian's rank 4
are among the first words either course teaches, and both currently render as
markup or an empty bracket. And the jargon class is where the owner's "ia for
я" report comes from: kaikki writes cross-references as `word (romanization)`,
so a learner meets rank 15 and is told it is the dative of something rather
than that it means "(to) me".

**Where the fix has to land.** `review_hints.py` already targets the jargon
class (its `SUSPICIOUS` regex catches 1,912 of the 2,156), but it writes
`translations.definition` in the DATABASE, and these definitions are seeded
from the committed TSVs — so a re-seed silently reverts the repair. That is
the same self-undoing trap `docs/quality/running-locally.md` §7 names for
drills. **Definitions are therefore fixed in the committed TSVs**, where they
are reviewable in git and a fresh environment inherits them, and
`review_hints` is used only for what is already deployed.

Two sub-classes need different treatment, which is what the checker is for:
a row whose parser simply picked the wrong sense is fixed for free by the
part-of-speech ranking below, on regeneration; a row whose word genuinely IS
an inflected form (`мне` really is the dative of `я`) needs its gloss
**written** — "(to) me, for me" — and a plausible-but-wrong case label is
exactly the error that reads fine and teaches wrong.

### D1c — Polysemy: one headword, several words (measured 18 Aug)

The owner's Portuguese card is the clearest statement of the problem. It
teaches `a`, gives one meaning, and then drills three sentences — "O que ele
está **a** fazer?" — in which `a` is neither the article nor the pronoun but
the **preposition** of the European progressive. The definition and the
exercise are about different words that happen to be spelled the same.

This is not the wrong-sense bug of D1. There the parser picked a bad sense
when a good one existed. Here **every** sense is real and the card has room
for one:

| Portuguese `a` (rank 2) | |
| --- | --- |
| definite article | the (feminine singular) |
| preposition | to, at — and `estar a` + infinitive, the progressive |
| object pronoun | her, it |

Three high-frequency words, one card, one gloss. Whichever is chosen, two
thirds of the sentences the learner meets illustrate something the card did
not teach. The same shape sits on `o`, `de`, `da`, `no`, `le`, `la` across
every Romance course, on Russian `с`/`в`, on German `sie`.

**No ranking rule resolves this**, which is worth stating because it is
tempting to keep tuning one. Turkish `bir` needs a numeral sense to beat an
adverb; Spanish `a` needs a preposition to beat a noun ("bishop"); French `a`
needs a verb ("has") to beat a pronoun. Any ordering that fixes one breaks
another — verified by building all three orderings and diffing the output.
The signal that would settle it is *sense frequency*, and Wiktionary does not
carry it.

So polysemy is handled three ways, in this order:

1. **Multi-sense glosses for the top band.** A word a learner meets in their
   first month should show its senses, the way a dictionary does — "the
   (feminine singular); to, at (with an infinitive); her, it". This is
   authoring, not selection, and it lives in `data/gloss_overrides.tsv`
   (mechanism shipped; applied in `build_language` after the merge, correcting
   only words the corpus already ranked, never inventing entries).
2. **A detector for under-glossed polysemy.** A top-band word whose kaikki
   extract carries entries under three or more distinct parts of speech, but
   whose committed gloss states one sense, is a card that will mislead. That is
   computable from the files already on disk and belongs beside the other
   audits.
3. **Example-sense agreement, reported not gated.** The sentence bank matches
   on surface form with no sense check, so a card can be illustrated entirely
   by a different word. Full sense-tagging is out of scope; what is in scope is
   flagging the case the owner hit — a card whose gloss names one part of
   speech while its examples overwhelmingly use another.

**Measured 18 Aug** by `backend/services/seeder/audit_polysemy.py`: across the
twenty cached languages, **1,293 top-band words carry three or more word-class
senses and are glossed with fewer**, and 104 more record a part of speech the
dictionary does not carry at all. Concentrated where the owner found it —
pt 149, it 139, es 122, ar 108, nl 102, th 90 — and at the very top of each
list, because a word earns rank 2 partly BY being several words.

#### What this means for sentence work (the second half of the goal)

Both halves have to move together. A multi-sense gloss with single-sense
examples still teaches the wrong thing; sense-correct examples under a
one-sense gloss are just as confusing.

**Selecting** from the harvested corpus: prefer sentences whose use of the word
agrees with the sense being taught. The per-language NLP backends already
lemmatize and, for several languages, can distinguish a form's function, which
is enough for the case that actually bites — `a` before an infinitive is the
preposition, not the article. Where the language has no such signal, report
rather than guess.

**Generating** (Phase 2, where sentences are authored for uncovered words):
sense is a required input, not an accident. For a word the polysemy audit
flags, the generator writes one sentence per major sense and states which sense
each carries; the adversarial checker's job is to confirm the sentence uses
THAT sense and reject it otherwise. This is cheap to add because the prompt is
ours, and it is the only point in the pipeline where sense is known for certain
at the moment the sentence is written.

**Ordering**: the audit ships first (done), the multi-sense glosses next, and
sentence selection last — because a sense-aware selector has nothing to select
against until the card states which sense it is teaching.

#### Decision: one card per word, not one per sense

The owner left this open. The answer is **one card**, and the reasons are
worth writing down because the alternative is superficially attractive.

Splitting `a` into three rows — article, preposition, pronoun — would let each
card teach one thing and carry only its own examples. It also breaks the
natural key the entire pipeline is built on. `vocabulary` is
`UNIQUE (language_id, word)` (migration 20260314000000); the vocabulary seeders
upsert `ON CONFLICT (language_id, word)`, and `seed_sentences` attaches every
example by `JOIN vocabulary v ON v.language_id = $1 AND v.word = u.word`. With
three rows spelled `a`, that join has no way to choose, so every example would
either fan out to all three senses or need a sense key the corpus does not
carry. Frequency rank has the same problem: rank is measured on the surface
form, so three cards would have to share one rank or invent three.

The learner-facing argument is stronger still. These are homonyms, not just
homographs — Portuguese `a` is pronounced the same in all three uses. Three
cards would be identical in text AND in audio, differing only in a label, and
a spaced-repetition queue that shows the same-looking prompt three times
teaches the learner to answer from position rather than from meaning.

So: one row, a gloss that names the senses, and examples labelled with the
sense they show. The example label is the part that does the real work — it is
what turns "O que ele está a fazer?" from a contradiction into an illustration
of the preposition sense the gloss already mentions. It is also additive: a
nullable column or an existing JSON field, which degrades to today's behaviour
when the migration has not landed, per the repo's standing rule.

One case would justify revisiting this: a true homograph with a DIFFERENT
pronunciation, where one card cannot carry both audio clips. None of the
1,293 words measured is that case, so it stays out of scope until one is.

### D1d — The homonym gap: one row per spelling hid whole words (19 Aug)

D1c decided one card per written form, with the gloss naming the senses. The
owner's follow-up exposed the assumption underneath: treating a spelling as one
word doesn't only merge senses — **it dropped the other words entirely**. The
frequency pipeline emits one row per surface form, so wherever two lemmas
shared a spelling (or shared one because the source carried no marks), only the
corpus-dominant lemma got a row.

Measured in Latin the moment macronisation made it visible: `hic` "this" has a
row, `hīc` "here" does not — while `ibi` and `ubi` do, so the adverb slot
plainly exists in the course. `lātus` "wide" present, `latus` "side" absent.
`malum`/`mālum` both absent.

This scales with the orthography debt. `es`/`fr` mostly carry both members
(`el` and `él` are separate rows) because their corpora distinguish them. But
**toneless `yo` means every tone-distinguished set is one skeleton row** — the
lexicon is missing the non-dominant member of every such set, and nobody can
count how many until the tone repair happens. Same shape in `mi` pre-repair,
and behind spelling rather than diacritics in `ar`/`he`/`fa` (unvocalised) and
`th`.

**So Phase 2a gains a rule: re-marking is not decoration.** Each unmarked row
may stand for several words. The re-marking pass must decide which word the
rank belonged to, and whether the others merit rows of their own — and the
post-repair sweep for missing high-frequency members (the Latin sweep is the
model) is part of the repair, not optional follow-up. CHECKS.md §8.

### D2 — Sentence parity. Two separate problems, and one is not what it looked like.

**English (corrected 17 Aug — the first reading was wrong).** The sentences
are not missing and it is not only a deployment gap. `data/en_sentences.tsv`
holds 112,648 distinct English sentences over 9,073 headwords, 99.1% of the
top 1,000. But **zero of its 202,772 rows carry `translation_locale='en'`** —
every row is an English sentence translated *into* one of thirteen other
languages. The card query (`backend/repositories/cards.py:193`) selects
`WHERE es.translation_locale IN ($support_locale, 'en')`, so:

| Learner's support language | English example sentences served |
| --- | --- |
| es fr de it ru tr ar el ro ca sw pt hi | 20k+ each — work after a re-seed |
| **en** (the default when the UI is English) | **zero** |
| ko nl th he fa yo ha xh mi jam la id tl | **zero** |

That is the owner's screenshot: an English speaker's support locale resolves
to `en`, and the English bank has no `en` rows because English is the one
course where the target language and the metalanguage can coincide. More than
half of the possible support locales get nothing.

The fix is code, not authoring. `docs/quality/en.md` already settles the
design question — the English course's `translation` field is *a usage note
by design*, not a translation — so the self-pair must serve the sentence
without requiring a translation row that should not semantically exist. The
same change covers the other thirteen uncovered locales, whose translation
line then fills in on demand through `auto_translate.py`.

**The real authoring crisis is elsewhere.** `la, id, tl, he, fa` have zero
sentences of any kind; xh 21%, yo 23%, mi 38%, ha 46% top-500 coverage. And
Phase 0's measurement sharpened this: separating "no example at all" from
"only one" shows **6,863 top-band words with no example**, against 2,745
needing more variety. The earlier scoping treated this as a diversity problem
(~2,090 words); it is four times that and mostly a **sourcing** problem, which
needs a corpus or an author rather than a better prompt. Also:
`data/mi_frequency.tsv` has zero macrons, so rank 23 `tona` is glossed *wart*
and rank 29 `ra` as the Egyptian sun god.

### D2b — The sentence crisis is a VOCABULARY crisis (measured 18 Aug)

Phase 2 was scoped as an authoring problem: nine courses need sentences, so
author sentences. That scoping was wrong, and building on it would have
wasted the most expensive work in the program.

Every one of the nine low-coverage courses has a **word list that is not fit
to hang sentences on**. Measured directly against the committed files:

| | measured | what it means for a learner |
| --- | --- | --- |
| yo | 1,638 of 1,644 headwords carry **no tone mark** (99.6%) | Yoruba tone is phonemic. The card fronts are toneless skeletons — not words |
| mi | **791 of 791** carry no macron | the macron is the sixteenth letter of the alphabet, not decoration |
| la | 285 macronised vs 310 not, **40 collision groups** | 40 duplicate card pairs; `AccentFoldingNLP` grades both identically, so no test can see it |
| xh | top ranks are `uthixo`, `unyana`, `uyesu`; `molo`, `enkosi`, `phi`, `nini`, `ngubani` all **absent** | it is a Bible-corpus frequency list. The learner never meets "hello" or "thank you" |
| ha | the high-frequency grammatical spine is missing | |
| he | 929 rows, but `rank` is a thematic syllabus, not a frequency ranking | |
| fa | 584 hand-built entries, 92 un-matchable by the sentence pipeline | the builder attributes sentences by exact token match, so those words can never receive one |
| id | 581 rows, a thematic syllabus with 24 duplicate lexemes | |
| tl | **90 rows** | too few to be a course |

Authoring example sentences over toneless Yoruba or macronless Māori produces
thousands of sentences that teach the wrong words, in a file that grades
green because the graders fold exactly the marks that are missing.

**So the order inverts: vocabulary repair comes before sentence authoring, per
language.** The two are not independent phases — sentences are downstream of
the word list, and the word list is downstream of orthography.

One correction to the assessment that produced this table: it was generated by
nine agents, each told that a short frequency file is a vocabulary problem
rather than a sentence problem, and all nine returned "fix vocabulary first" —
a unanimity that is at least partly the question's doing. Every number above
was therefore re-measured by hand against the files. They hold, with one
exception: the tl assessment claimed the 90-word list "omits the closed-class
words its own grammar syllabus drills", and it does not — `ang`, `ng`, `sa`,
`na`, `at`, `ako`, `ikaw` are all present, and only `ay` is missing. Tagalog's
90 words are a sound core. The problem is that there are ninety of them.

### D2c — The interlinear gloss: a hint layer built for nine courses, filled for one

`frontend/src/features/review/hintLayers.ts` gives nine languages a **gloss**
step in the hint ladder — `ru, ar, el, hi` reach it after romanization, and
`mi, sw, yo, xh, ha` open on it (`GLOSS_FIRST`), because their syntax does not
map onto English word order and the word-by-word gloss shows how the sentence
is *built* rather than what it means.

It is populated almost nowhere:

| surface | coverage |
| --- | --- |
| grammar drills | mi **240/240**, sw 134/442, the other 25 courses **zero** — 374 of 8,049 drills, **4.6%** |
| curated sentence banks | sw 461 rows (92%), every other bank **zero** |
| Tatoeba-built banks | **nobody** — `write_sentences_tsv` has no gloss column to write |

Nothing in the pipeline *generates* a gloss. `seed_sentences.py` and
`seed_grammar.py` only read the column; it is hand-authored or it is absent.

Two consequences, and the second is the one that matters:

1. Seven of the nine languages declare a layer they cannot fill. The ladder
   degrades quietly (`hintLayers.ts` skips absent layers), so nothing looks
   broken.
2. **`yo`, `xh` and `ha` are `GLOSS_FIRST` with zero glosses.** The disclosure
   order built specifically for them opens on an empty layer, so they fall
   straight through to the English translation — the exact scaffold they were
   given the ordering *for*, and the one class of learner least served by
   jumping to English, gets nothing.

`docs/quality/mi.md` records this as a Māori quirk — "Māori is the only course
with a per-drill interlinear `gloss`" — and treats it purely as a leak surface
to police. That framing is the flaw: being the only course with a gloss is not
a property of Māori, it is **debt in the other twenty-six**. The gloss should
be available to most courses, and the guidelines should say so.

### D2c2 — A card's definition and its examples are fixed independently, and nothing joins them

`audit_polysemy` was written for a Portuguese card: `a`, one meaning, drilled
"O que ele está a fazer?" three times, where `a` is the progressive preposition
and not the article the card defined. That diagnosis is in its docstring.

**The gloss has since been repaired. The sentences have not.** Measured
19 Aug 2026, rank 2 `a` now reads "the (feminine singular); to, at — also
estar a + verb (is doing); her, it" — three senses, so the under-glossed rule
is satisfied and `audit_polysemy` reports it clean. Its three example
sentences are still, all of them, `está a fazer`. A learner is told the word
means "the" and shown it working as a progressive marker three times.

This is a **join** that no check performs. `audit_polysemy` measures the gloss
against the dictionary. `audit_examples` measures how many sentences exist and
how varied they are. Neither asks the one question that matters here: *does
this card's example set demonstrate the sense its gloss leads with?* Repairing
definitions (Phase 1) and sourcing sentences (Phase 2b) are separate passes on
separate files, so a card can pass both and still teach one thing while showing
another.

It cannot be measured today because nothing records what a word is *doing* in
its sentence — which is precisely what a gloss records. Hence the process in
Phase 2c: glossing is where this gets caught, and the gloss is what finally
makes the check mechanical.

### D2d — The scrutiny is not evenly spread, and the gap is large (19 Aug)

Asked directly whether every language is getting the depth English and Latin
got, the answer is **no**, and the asymmetry should be visible in the plan
rather than discovered later.

**Deep repair — 2 of 27 courses:**

| | what it received |
| --- | --- |
| `en` | 99 definitions rewritten maker–checker; glosses committed so an audit can see them; new `circular_gloss` rule; the sentence-locale fix |
| `la` | all 557 headwords + 189 drills + gym macronised; 40 duplicate cards removed; policy reversed; 5 guards |

**Everything else has had three shallow passes**, all real, none deep:

- the `source_data` sense-ranking rewrite, which took defective glosses from
  2,150 to 944 across 26 languages;
- `data/gloss_overrides.tsv` — **527 rows across 27 languages, ~20 each.** For
  `fr`, `de`, `es`, `ru` that means roughly the top 20 words are hand-verified
  and **the remaining 9,980 are not**;
- diagnosis only, for the nine in D2b.

**The measured gap, 19 Aug 2026:**

- **920 audit findings open**, unchanged except Latin's zero — `tl` 152,
  `id` 121, `el` 59, `ro` 51, `ar` 51, `de` 49, `fr` 46, `jam` 46.
- **Glosses: 374 of 8,049 drills (4.6%)** — `mi` 240, `sw` 134, and
  twenty-five courses at zero.
- **7,243 top-band words with no example sentence**; five courses with no
  sentence bank at all.
- Of the 118 guideline defects in D2e, roughly 8 were applied and the rest
  deliberately left.

Two things make this worse than the table suggests. **Latin was only reachable
at that depth because it is 557 words** — `fr` and `de` are 10,000 each, so the
same treatment is roughly 18× the work per language. And **the deep passes keep
finding defects the shallow passes could not see**: the four wrong macrons, the
rank-misalignment bug, the eight richer glosses a naive dedup would have
deleted. That is evidence the other 25 hold comparable defects nobody has
looked for, not evidence they are clean.

**How the depth was chosen so far is the problem: it was reactive.** English got
it because a screenshot pointed there; Latin because a question did. The
correction, in priority order:

1. **Finish Phase 2a** — the nine broken word lists, since sentences *and*
   glosses are both downstream of orthography. `mi` next (791/791 missing
   macrons), then `yo` (1,638/1,644 missing tone).
2. **Raise the floor everywhere before deepening anywhere else.** Extend
   `gloss_overrides` from ~20 to the top 200 per language — the band a learner
   actually reaches — and burn down the 920 audit findings worst-first
   (`tl` and `id` alone are 273 of them).
3. **Prefer rules to hand-authoring wherever a rule can carry the load.**
   `circular_gloss` found 99 English defects in a single pass and now blocks
   the class permanently. Rules generalise across 27 courses; authored rows do
   not.

### D2e — The guidelines assert 118 things that are not true (19 Aug)

A claim audit checked every falsifiable statement in all 27
`docs/quality/<code>.md` files against the data it describes: **118 defects —
45 outright false, 52 stale, 18 true-but-misleading.**

Two failure modes, both costly. **Undercounting live debt:** `sw.md` says "50
grammar points, 308 drills" against a real 64 and 442; `ko.md` says "verified
on disk: 40 points, 240 drills" against **156 points and 1,217 drills**. Anyone
scoping from those pages plans a third of the job. **Describing defects already
fixed:** `el.md`, `hi.md`, `th.md`, `es.md`, `ca.md` each still name rows or
grading bugs since repaired, so a reader who checks the example finds it clean
and stops trusting the page.

Four files also contradict the tool outright — `fr.md` and `it.md` assert
`leak_hard: 0` where the audit prints 10 and 3; `ro.md` says 2 against 11;
`pt.md` 2 against 7; `en.md` totals 13 against 17. In every case the audit and
`data/quality/baseline.json` agree with each other and the doc is the outlier.

Shipped in the guideline-claim-audit PR: the misleading ones corrected, plus
the rule that stops the class — **never freeze a count the audit computes**,
cite the rule name; any other number carries its date and measurement; and
"verified" must name every file the claim covers, which is exactly what
`la.md` failed to do.

**Deliberately not applied: the findings that did not reproduce.** The audit
claimed `de.md` undercounts case+gender hints at 10 against 30, and `tr.md`
harmony hints at 3 against 8; re-measuring gave 2 and 4. Three of five sampled
figures reproduced exactly, two did not, so nothing from that class was written
in. Replacing a wrong number with a differently wrong number is the failure
being fixed.

### D3 — Gym. Already scoped by `docs/plans/gym-coverage.md`:

411 drilled points hidden from pickers (en shows 12 of 43), 1,578-drill
depth deficit in the thin five, and **seven languages with no manifest at
all** (sw, yo, ha, xh, mi, jam, th) — sw being a language whose entire
difficulty is paradigms.

### D4 — Grammar debt. 920 baselined findings; the worst are documented but unexecuted.

id (121) and tl (152) have mechanical rewrite rules written in their own
quality docs, never run. `giveaway_by_gloss` is the biggest cross-language
class (ar 48, jam 41, el 37, th 29, ro 29…). Korean carries duplicate
same-topic points (`ai` vs `pending` pairs — an emit-merge same-title
artifact). Nine languages are 0% human-reviewed. Fixable held items:
fr elision convention (2 drills), ar tashkeel-ungradeable drills (10),
ru transliteration scheme mismatch (5 drills), th Thai-script stage
directions (19) and romanization-unreachable answers (30 of 96 distinct).
`docs/quality/ko.md` and `sw.md` are stale against the tree (~5× growth);
`en.md` still lags the `agreement_feature` rule (the README was fixed in
Phase 0). The baseline is 980 after Phase 0 added `wrong_sense_gloss`.

Several per-language docs also report `leak_hard` net of
`construction_quote`, while the code counts construction quotes *inside*
`leak_hard` — ro says 2 against a real 11, pt 2 against 7, de 18 against 17,
ar 1 against 2. That is one normalising pass over the docs, not 27 edits to
the content, and it should happen before anyone uses those numbers to
prioritise.

### D5 — Idle extraction assets; extractor gaps.

extra-agent's emit now **merges** (sidecar ownership; existing wins on
collision). Sitting unemitted: ~2,518 validated Russian vocabulary entries,
19 grammar points, 218 sentences (`out/Russian.parts`); an English grammar
book (156 vocab / 149 grammar / 32 sentences). Frequency lists are thin where
sentences are thin too: tl 90 rows, id 581, fa 584, la 595, mi 781, he 929.

The missing he/fa/la/id/tl `LanguageProfile`s — which had Hebrew and Persian
extracting as left-to-right Latin — were fixed in extra-agent #8, along with
a structural gap that generalises: a profile's `guidance` reaches only the
extraction prompt, so an orthography rule stated there held while a document
was read and was dropped when the fill pass wrote a new drill. Any rule that
must hold in every emitted string now goes in the new `orthography` field,
which is injected into the maker *and* the checker.

Two residual extractor caveats to design around rather than trip over: a
same-title grammar point silently drops the new content (existing wins on
key collision), which is why Korean carries `ai`/`pending` duplicate pairs;
and `ERRORS.extracted.md` is still replaced wholesale rather than merged.

---

## The plan — six phases, one PR each

### Phase 0 — Instruments first (measure before touching) — SHIPPED (#292)

Delivered: `audit_examples.py`, `audit_gym.py`, the `wrong_sense_gloss`
fail-level rule with 60 rows baselined, the README rule-table drift fixes, and
`LanguageProfile` entries for he/fa/la/id/tl in extra-agent (#8).

What the instruments then found, which reshaped Phases 1 and 2 above:
6,863 top-band words with no example at all; 2,156 rows with a definition
defect; and the English locale-filing bug. `audit_gym` reconciles exactly with
the gym plan (en 12 shown / 31 hidden, 435 forms repo-wide) and adds the 298
drilled points in the seven languages that have no manifest at all.

One known gap in the new rule, recorded rather than hidden: its letter-name
pattern misses `а` → "The sound expressed by the letter A" (ru rank 22),
which uses different phrasing. Phase 1 widens the pattern when it regenerates
the Russian list.

Original scope, for the record:

- `backend/services/seeder/audit_examples.py` — thin/monotone/coverage
  report per language (example-diversity Stage 1, TSV-backed; DB query
  shipped for the owner to run).
- `backend/services/seeder/audit_gym.py` — breadth/depth/copy fullness
  (gym-coverage Stage D), wired into CI as a floor check.
- **New fail-level audit rule** in `audit_content.py`: wrong-sense gloss
  detection over frequency TSVs and vocabulary CSVs (letter-name, symbol,
  ISO-code, chemistry-element, wrong-language patterns), baselined like
  every other rule so it can never regress silently.
- extra-agent: `LanguageProfile` entries for he, fa, la, id, tl.
- `docs/extraction-sources.md` (shipped with this plan) — the owner's
  source library mapped per language with the facts-only policy attached.

### Phase 1 — Definitions (the named complaint, and the 2,156 behind it)

**Status: shipped, in four PRs.** Steps 2–5 landed in #296/#298/#301/#304
(2,150 → 944 defective glosses, no word lost from any top-50) and #305
(WordNet sense selection by tagged-corpus count). What closed it out:

- **English's glosses are committed.** `data/en_frequency.tsv` now carries
  `pos` and `en` columns like the other 26 courses, written by
  `python -m backend.services.seeder.emit_english_glosses`, and the seeder
  reads them. English was the one course no audit could see, which is how
  rank 3 `be` shipped as beryllium.
- **English reaches `data/gloss_overrides.tsv`.** It could not before: its
  definitions are built at seed time from WordNet rather than read from a
  gloss column, so the shared override table had no way in. 99 English rows
  now sit in the same file as the other 26 languages'.
- **`circular_gloss`, a new fail-level rule.** A definition that explains the
  word with the word teaches nothing — `have` → "have or possess", `paint` →
  "make a painting", and rank 6 `a` defined as an ångström. 80 of the first
  1000 English definitions were circular; all 80 were rewritten maker–checker
  and the top band is now at zero.

  The rule is English-only and content-words-only, both deliberately.
  Elsewhere the gloss is in a different language from the headword, so a
  headword inside it is a collocation example (`na` — "and; with (kuwa na, to
  have)") or a loanword that honestly glosses to itself (`hotel`,
  `internet`); running it on the other 26 courses reports 500+ findings and
  not one is a defect. And a preposition cannot be glossed without being
  used — "in exchange for" IS the teaching.

  **Remaining debt, outside the audited band:** 106 circular definitions in
  ranks 1001–3000 and 277 in 3001–10000. The rule measures the top 1000 only,
  matching `wrong_sense_gloss`; widening the band is a later pass, not a
  silent gap.


Rescoped after D1b. This is no longer "fix 60 letter-name glosses"; it is the
text under every vocabulary card in 21 languages.

1. **Offline mode for the repair tool, first.** Port `review_translations`'
   `--export` / `--apply` round-trip (about 120 lines, including the
   one-file-round-trips stale check) to `review_hints.py`, so definitions can
   be judged in-session at no API cost. `review_hints` is strictly simpler
   than the pass that already has the feature — no derived-row deletes, no
   file mirror — and the shared machinery gets lifted out rather than copied
   a third time.
2. **`source_data.py`: kaikki sense ranking.** Prefer lexical parts of speech
   (pron/det/verb/particle/conj/prep/adv) over `name`/`symbol`/`character`;
   descend into the nested sense structure rather than emitting the "in the
   following senses:" preamble; strip MediaWiki markup; keep the letter-name
   filters. Tests pinning fr `ne`/`y`, de `ne`, tr `ve`, sw `ya`, ru `от`.
3. **`seed_english.py`: POS-aware synset selection** (function words prefer
   their function-word sense; frequency rank informs expected POS), expanded
   curated guard for the top band, shrapnel filter (`re`, `ll`, `ve`, `e`,
   `lf`, `th`, `wh`). Write the result to a **committed** gloss file so
   English joins `wrong_sense_gloss` and stops being the one course whose
   definitions no audit can see.
4. **Verify the top band BEFORE regenerating.** A first regeneration was built
   and thrown away because of exactly this: it fixed 1,300 defective glosses
   and simultaneously turned Spanish rank 4 `a` into "bishop", French rank 14
   `a` into "she" and Romanian rank 5 `o` into "oh". Net-positive by count and
   badly negative on the words every learner meets. So the order is: author
   the overrides, then regenerate, then diff the top 200 of every language by
   hand before committing — not the reverse.
5. **Author what regeneration cannot fix** — polysemous top-band words (D1c),
   rows whose word genuinely is an inflected form, and the yo top-12 where
   kaikki has nothing good. Maker writes, an adversarial checker verifies, and
   the fix lands in `data/gloss_overrides.tsv` or the TSV.
6. **Ship the two detectors from D1c** (under-glossed polysemy; example-sense
   disagreement) so the class cannot silently return.

Definitions are fixed **in the committed TSVs, never only in the database** —
a DB-only repair is reverted by the next re-seed.

### Phase 2 — Sentences to parity

- **The English locale fix — SHIPPED.** All four sentence-selection queries in
  `backend/repositories/cards.py` demanded a row whose `translation_locale`
  was the learner's or `en`. The English bank has zero `en` rows by design —
  every one of its 202,772 rows translates English INTO another language — so
  an `en`-locale learner of English matched nothing and saw no example
  sentences at all. That is the default locale, so it was most of them.

  A sentence already written in the language the learner reads needs no
  translation, so the queries now also accept `es.language_id IN (SELECT id
  FROM languages WHERE code = $locale)` and null the translation and its
  locale for those rows — the learner gets the cloze with no translation
  line, never a Turkish gloss under an English sentence. Covered by
  `test_english_support_locale_localizes_cards`.

  Still open: the thirteen locales *with* translations are covered, but a
  learner in a locale outside those thirteen (ko, ja, id…) gets the sentence
  with no translation rather than one in their language. That is the
  `translate_english` runner's job, not this fix's.
**Restructured 18 Aug after D2b.** Sentence authoring is now the SECOND half
of this phase; the first half is repairing the word lists it depends on. The
order below is the order the work must happen in, per language.

**2a — Orthography and word-list repair (blocks everything downstream).**

| | fix | kind |
| --- | --- | --- |
| la | strip macrons per la.md's all-or-nothing policy; merge the 40 collision groups | mechanical — no authoring, the policy decides |
| mi | **not a macron pass** — restore the missing high-frequency words, re-gloss the bare-homograph rows, then mark | measured 20 Aug: `tēnei`, `kāore`, `mātou`, `whānau`, `kōrero` are all ABSENT; a macronisation pass was authored and discarded (see `mi.md`) |
| yo | top band from in-repo evidence, tail still needs a source | **partly unblocked** 20 Aug: the drills are 65% tone-marked against the vocabulary's 0.4%, giving 130 attested top-band forms + 17 rows that state their own tone. The tail (~1,491) still needs an external source. Attested ≠ correct for the row — see `yo.md` |
| xh | replace the Bible-corpus frequency list, or author a core over it | sourcing |
| ha | add the missing grammatical spine | authoring |
| he, fa, id | rebuild `rank` as a frequency ranking; dedupe | sourcing + mechanical |
| tl | grow 90 rows into a course | sourcing |

Latin is first because its quality doc makes it deterministic: "no macrons,
anywhere, all-or-nothing" decides every case, so nothing needs authoring — but
see the homograph note below, which the strip *creates*.

**The macron strip collapses genuine minimal pairs.** `liber` (book) /
`līber` (free) and `os` (bone) / `ōs` (mouth, face) are not duplicates; length
is the only thing that ever kept them apart. Under D1c's settled rule — one
card per written form — each becomes a single card whose gloss must carry both
senses, because the spelling no longer can. `la.md` anticipated exactly this:
the policy's cost "is real and is paid in the hint".

**2b — Sentences, once 2a lands for that language.**

- Tatoeba builds (`source_data --sentences`) for la, id, he, fa, tl; top-ups
  where the corpus has more (th, ca, hi, ko, sw). These five have no bank for
  a five-line reason, not a data one: `TATOEBA_ISO3` and the `--language`
  choices in `source_data.py` simply do not list them. All five banks exist
  and are substantial — heb 2.4 MB, tgl 954 KB, lat 738 KB, pes 468 KB, ind
  328 KB, with English link tables for each. Persian's English links are thin
  relative to its sentence count (53 KB against 468 KB), so expect its
  coverage to land below the others. Adding a code also needs an entry in
  `nlp_by_lang`, or the build dies on a bare `KeyError`.
- Session-generated sentences for the top-500 gaps that corpora cannot
  fill (xh, yo, mi, ha + low-resource leftovers): maker writes against the
  word's gloss/level with structural-diversity constraints; adversarial
  checker verifies naturalness, level, word-sense fit; lands as
  `source='ai'` so it queues in the Review Inbox. Nothing auto-approved.
- **Replace shipped verbatim commercial sentences** (policy rule 2): the
  sw (bk_inno) and ko (HTSK) extracted sentence rows get regenerated
  originals; same word coverage, fresh text.
- mi frequency repair: macronised headwords, correct glosses.

### Phase 2c — The interlinear gloss, for most courses (new, from D2c)

Today 4.6% of drills carry a word-by-word gloss: Māori 240/240, Swahili
134/442, everyone else zero. Nine courses are wired for the layer and one and
a half can fill it.

- **First, the three that are actively broken:** `yo`, `xh`, `ha` are
  `GLOSS_FIRST` with no glosses at all, so their hint ladder opens on an empty
  layer and drops to English. They get glosses before anyone else, because
  they are the courses the ordering was designed for.
- Then `sw` to 100%, and `ru, ar, el, hi` — already wired, glossed after
  romanization.
- Then extend the layer beyond the current nine. A word-by-word gloss is not
  only for non-English word order; it is the cheapest way to show *how a
  sentence is built* in any language. Widening `LAYER_ORDER` is a small
  frontend change; the content is the work.
- **`write_sentences_tsv` needs a gloss column** so Tatoeba-built banks can
  carry one at all. Today it writes word/sentence/translation/difficulty_rank
  and nothing downstream can add a gloss to those rows.
- Authored maker–checker against each language's own `docs/quality/<code>.md`,
  and every gloss is subject to the same leak rule `mi.md` already sets out:
  **a gloss must never spell the answer.** That rule is why Māori's gloss is
  policed today; it becomes a rule for every course that gains one.

Sequenced after 2a because a gloss over a toneless or macronless headword is
wrong in the same way the sentences would be.

**No — a gloss will NOT exist for every sentence, and that is the design, not a
shortfall.** Measured 19 Aug 2026:

| | sentence rows | gloss policy |
| --- | --- | --- |
| `mi sw yo xh ha` (`GLOSS_FIRST`) | **4,974** | **every sentence a learner meets.** This is the tractable, high-value job |
| `ru ar el hi` (`SCRIPT_FIRST`) | 63,183 | top-1000 band only — romanization is their primary scaffold, gloss is the second layer |
| the other 18 courses | 416,597 | **none, by design.** Their ladder is `translation → hint`; no gloss layer is wired and none is wanted |
| **total** | **484,754** | |

Hand-authoring Leipzig-style glosses for 484,754 rows is not on the table and
never was. The number that matters is **4,974** — the five courses whose hint
ladder *opens* on the gloss, three of which (`yo`, `xh`, `ha`) currently have
zero. That is the whole of the urgent work, and it is a few thousand rows, not
half a million.

**And it cannot be generated mechanically at the quality the authored ones
set.** Swahili's 461 glosses are true interlinear morpheme analyses —
`tu-ta-on-ana (1PL-FUT-see-RECIP)`, `ni-li-jaribu (1SG-PAST-try)`, noun classes
`CL1`/`CL9`/`CL10`, `LOC`, `REL`. A dictionary lookup cannot segment
`tutaonana` into its morphemes or name their categories.

What the repo has is **not** a morphological analyser: `data/<code>_morphology.json`
(14 languages, including `sw`, `xh`, `yo` but not `mi` or `ha`) holds *paradigm
chips* — surface forms tagged with a label, `kuabudu` = Infinitive of `abudu`.
That supports a reverse lookup ("this token is the infinitive of that lemma")
and so a **weak** gloss, but not `tu-ta-on-ana (1PL-FUT-see-RECIP)`.

So the rule: **a mechanical gloss may fill a gap, never overwrite an authored
one, and never for a `GLOSS_FIRST` course**, where the gloss is the primary
scaffold and a wrong parse is worse than no gloss at all (`mi.md`'s standing
rule). If the weak form is used anywhere it is marked as such, so nobody reads
a paradigm lookup as an analysis.


**Glossing is a sense audit, and that is half its value.** Writing a
word-by-word gloss forces you to say what each token is *doing* in that
sentence. The moment you write it down, a card whose examples exercise a
different sense than its definition becomes obvious — you cannot gloss
Portuguese `a` in "está a fazer" as "the (feminine)" without noticing.

This is live, measured 19 Aug 2026, and it is the owner's own example:

| | |
| --- | --- |
| card | `a` — rank 2 — "**the (feminine singular)**; to, at — also estar a + verb (is doing); her, it" |
| its sentences | "O que ele está **a** fazer?" / "Que está ela **a** fazer?" / "Que está ele **a** fazer?" |

All three show the **third** sense. Not one shows the article the gloss leads
with, and a learner drilling this card meets `a` as a progressive marker three
times while being told it means "the". A sentence like *a menina é boa* would
teach the leading sense; *vou ao mercado* would not.

Note what this is NOT: the gloss is already correct and complete — it names all
three senses, so `audit_polysemy`'s under-glossed rule is satisfied. **The
definition was repaired and the examples were never rechecked against it.** The
two were fixed independently and nothing joins them, which is exactly why this
survives every existing check.

**So the process, whenever a sentence is glossed:**

1. Gloss the sentence, naming the target word's actual role in it.
2. Compare that role against the sense the card's gloss leads with.
3. On a mismatch, decide which is wrong — and it may be either:
   - **the sentence** — swap it for one that shows the leading sense, or demote
     it behind one that does;
   - **the gloss order** — if the corpus really shows this sense most, the
     gloss is leading with the wrong one and should be reordered;
   - **the coverage** — if two senses are both common, the card needs both
     named *and* at least one example per named sense.
4. Record the correction where it belongs: `data/gloss_overrides.tsv` for the
   definition, the sentence bank for the example. A fix in one is not a fix in
   the other.

**The instrument this earns.** Once a sentence carries a gloss, the comparison
is mechanical: the gloss states the role, the frequency row states the leading
sense, and a card whose entire example set disagrees with its own first sense
can be reported without a human reading it. That is the "example-sense
disagreement" detector Phase 1 step 6 listed and never built — it was not
buildable before, because nothing recorded what a word was doing in its
sentence. Glossing is what makes it possible.

Until it exists, step 2 is done by the checker in the maker–checker pass, and
the checker is told to reject a gloss whose sentence does not exercise the
card's leading sense rather than silently glossing what is in front of it.

### Phase 2 — the running order (owner decision, 20 Aug 2026)

Asked which courses had actually been reviewed, the measured answer was that
the well-resourced ones have had **broad** repair — the collision guard,
junk-twin removal, wrong-lexeme reglosses, 60+ row exclusions across `pt`,
`fr`, `es`, `ro`, `ca`, `el` — while only `en`, `la` and `mi` have had the
**deep** pass. Five courses had had nothing at all: `jam`, `id`, `tl`, `he`,
`fa`. Two of those, `id` (121) and `tl` (152), hold **273 of the 920**
remaining audit findings between them.

**The owner's decision on sequencing, and it is not "biggest first":**

1. **Finish the low-frequency courses — clean AND populate.** `mi` step (c),
   then `ha`, `xh`, `yo`, `jam`, `id`, `tl`, `he`, `fa`. These are the courses
   that are *far behind*, and several are not yet real courses: `tl` has 90
   rows, `jam` 384, `la` 559. Populating is part of the job, not just
   repairing what is there.
2. **Then the deep pass on the well-resourced courses**, to the standard `en`
   and `la` received — definitions verified against the corpus, homonym gaps
   filled, glosses committed and audited.
3. **Then sentences for everyone at once** (Phase 2b), which is the owner's
   standing instruction: no course reaches the sentence stage ahead of the
   others.

**A prediction worth recording, because it is testable.** The owner expects
step 2 to be *lighter* than `en` and `la` were, on the grounds that the
well-resourced courses have better source data. That is plausible — their
corpora are larger and their kaikki entries richer. But it is a prediction,
not a finding, and this program has already seen the opposite twice: `es` had
`creo` at rank 79 glossed as the wrong verb, and `ca` had **no correct card
for "I am"**, both in 10,000-row courses with good data. **If the deep pass on
Spanish or French turns up defects at English's rate, say so plainly** — that
result is more valuable than the phase completing quietly, and it would mean
row count is not a proxy for quality.

### Phase 2d — Raise the floor on all 27 before deepening any further (from D2d)

Two courses have been repaired to a standard the other 25 are not held to, and
the depth was chosen reactively — a screenshot pointed at English, a question
pointed at Latin. Before any third course gets that treatment:

- **`gloss_overrides` from ~20 rows per language to the top 200.** 527 rows
  across 27 languages today; the top 20 of a 10,000-row file is not coverage.
  200 is the band a learner actually reaches in the first months.
- **Burn down the 920 audit findings worst-first.** `tl` 152 and `id` 121 are
  273 between them — nearly a third of the total in two of the smallest
  courses.
- **Reach for a rule before reaching for an author.** `circular_gloss` found 99
  English defects in one pass and blocks the class permanently; that is worth
  more than any number of hand-authored rows, and it generalises to courses
  nobody has looked at yet.

The test of this phase is not "is any language excellent" but **"is any
language far behind"** — today `tl` (90 words, 152 findings) and `id` (581
rows, 121 findings) are, and no amount of further English polish changes that.

### Phase 2e — Grader collisions: shipped guard, queued repairs (from CHECKS §3)

The collision guard is live: a fold-only match grades `WRONG_FORM` when what
was typed is itself another course word (`el`/`él`, `все`/`всё`,
`liber`/`līber`), with per-language ceilings ratcheted in
`test_nlp_collisions.py`. 103 junk twin rows deleted mechanically; four
typo-mass artifacts excluded durably via `data/vocab_exclusions.tsv` (new
mechanism — a TSV deletion alone is undone by regeneration).

Remaining, in order:

1. ~~**`ar` normalize surgery**~~ — **DONE.** Alef fold moved into
   `fold_lookalikes`; 199 → 79 cards graded as another card; 11 junk twins
   deleted. The yeh fold followed once its cost was
   measured (84 cards, `على`/`علي` at ranks 8/144): green rested on Egyptian
   convention that `ar.md` excludes, and MSA distinguishes /aː/ from /iː/
   word-finally. Now amber. **199 → 1** across both moves.
2. **Judgment repairs** the mechanical rules could not make: `el` tonos twins
   (keep-the-marked was tried and REVERTED — Greek monosyllables are standard
   unmarked), `hi` nuqta variants, `de` ß/ss, `fr` 1990-reform merges (accept
   both spellings as CORRECT), `es` broken twin glosses (`creo`→creer,
   `llegue`, `pagué`, `mío`, `parís`, `dólares`).
3. ~~**`de` digraphs**~~ — **DONE.** Duden substitution accepted in the
   coaching layer; 24 junk/obsolete rows removed, `strasse` excluded.
4. The ~900 incidental same-lemma inflection twins ride the per-language
   deep passes, not this phase.

### Phase 3 — Grammar & hint debt burn-down

- Execute the documented id/tl hint rewrite rules (≈270 findings).
- `giveaway_by_gloss` burn-down worst-first (ar, jam, el, th, ro, yo, ha…),
  each language judged against its own `docs/quality/<code>.md`.
- ko: dedupe same-topic point pairs; register/hint fixes from ko.md.
- Fixable held items: fr elision (2), ar tashkeel drills (10), ru translit
  normalization (5), th stage-directions (19). Anything needing a native
  speaker stays held and stays written down.
- Refresh stale docs (ko.md, sw.md, en.md, README agreement_feature row).
- Baseline ratchets DOWN with each fix; never up.

### Phase 4 — Gym parity

- Exposure pass: en first (12 → ~43 forms, new columns, house-style copy),
  then the other legacy languages.
- New manifests for the seven languages without one (updating
  `test_load_manifest_none_for_uninflected_language`, which pins sw=None).
- Copy pass on early manifests to the later house style.
- `-k drills-topup` CLI implemented and tested (the DB run itself is the
  owner's, in the runbook).

### Phase 5 — Extraction leverage (session-only, facts-only)

- Emit the Russian backlog: vocabulary + grammar structure merge in;
  the 218 Red Kalinka sentences do NOT — regenerated instead.
- English grammar book: vocabulary/structure only (en grammar is
  contributor-only by test; sentences regenerated).
- Targeted in-session extraction from `docs/extraction-sources.md`
  (Innovative Language books per language, Arab Academy structure, HTSK
  units for ko depth): vocabulary, grammar points, paradigms, pitfalls —
  sentences and drills always freshly written. Validated offline against
  the interchange schema, emitted through emit-merge.

### Phase 6 — Verification & the refeed runbook

- Full gates: audit (baseline equal-or-down), backend tests, ruff,
  frontend build + vitest, adversarial QA sweep over all new content.
- `docs/quality/refeed.md` + chat summary: exact per-language reseed
  order (`seed_english` → `run.py` → `seed_sentences` → `seed_grammar` →
  `morphology_charts` → `seed_alphabet`), which DB-side passes to run
  afterwards (`review_translations` offline mode, `review_hints`,
  gym top-up, example diversity) and what each costs.

## What this deliberately does not do

- **No auto-approval.** Generated sentences/drills land unreviewed in the
  Review Inbox queues, per the standing rule.
- **No API spend.** If a pass would need the paid API, it goes in the
  runbook as an owner decision instead.
- **No native-reviewer bypass.** Languages gated on a named native reviewer
  (sw/yo/ha/xh/mi and the 0%-reviewed nine) stay `reviewed: false`; this
  program improves the drafts, not the trust label.
- **No whole-corpus regeneration.** Top-500/top-1000 bands first,
  per the example-diversity plan's cost argument.

## Open items the owner may want to weigh in on later

1. Whether the regenerated sw/ko sentence replacements should retire the
   old rows immediately or run through the Review Inbox first.
2. Gym floor (10 drills/form, 12 for A1) — inherited from the gym plan.
3. The thin five's frequency lists (tl 90 rows!) — Tatoeba/kaikki can grow
   id/he/fa/la substantially; tl needs a source decision.
4. Tagalog's interlinear gloss. It has the best linguistic claim to one of
   any unglossed language — verb-initial with a focus system, so `ang/ng/sa`
   are hard to parse without it — but `hintLayers.ts` renders a gloss only
   for mi/sw/yo/xh/ha, so requesting one today produces data nothing shows.
   Enabling it is an app-side change first (`hintLayers.ts`, ROADMAP §3b,
   `docs/quality/tl.md`), then the extractor flag. Recorded in the test that
   pins the flag off, so it cannot be lost.
5. Whether English's regenerated glosses should be a committed file (the
   Phase 1 assumption, which is what lets any audit see them) or stay
   generated at seed time. Committing 10,000 rows makes English reviewable
   like every other language; it also puts WordNet output in git.
