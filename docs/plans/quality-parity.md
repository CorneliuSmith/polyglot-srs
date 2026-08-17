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
4. **Regenerate the frequency TSVs** from the local raw cache, worst-first:
   sw, hi, nl, de, it, pt, ca, fr, ru, es, ro, el, then the tail.
5. **Author what regeneration cannot fix** — the rows whose word genuinely is
   an inflected form, and the yo top-12 where kaikki has nothing good. Maker
   writes, an adversarial checker verifies, and the fix lands in the TSV.

Definitions are fixed **in the committed TSVs, never only in the database** —
a DB-only repair is reverted by the next re-seed.

### Phase 2 — Sentences to parity

- **The English locale fix goes first**, because it is code rather than
  authoring and it unblocks 112,648 sentences that already exist. Serve the
  English course's own sentences to a learner whose support locale is `en`
  (and to the thirteen locales with no translations yet) without demanding a
  `translation_locale='en'` row that, per `docs/quality/en.md`, should not
  exist. Regression test: an English learner with support locale `en` gets a
  non-empty "in context" line.
- Tatoeba builds (`source_data --sentences`) for la, id, he, fa, tl; top-ups
  where the corpus has more (th, ca, hi, ko, sw).
- Session-generated sentences for the top-500 gaps that corpora cannot
  fill (xh, yo, mi, ha + low-resource leftovers): maker writes against the
  word's gloss/level with structural-diversity constraints; adversarial
  checker verifies naturalness, level, word-sense fit; lands as
  `source='ai'` so it queues in the Review Inbox. Nothing auto-approved.
- **Replace shipped verbatim commercial sentences** (policy rule 2): the
  sw (bk_inno) and ko (HTSK) extracted sentence rows get regenerated
  originals; same word coverage, fresh text.
- mi frequency repair: macronised headwords, correct glosses.

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
