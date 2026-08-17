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

### D2 — Sentence parity. English is fine; five languages have nothing.

`data/en_sentences.tsv` holds 202,772 rows, 98.8% top-500 coverage — the
missing English sentences in the app are a **deployment gap** (the DB
predates the `translation_locale` seeder fix, #264); the refeed fixes it.
The real crisis: **la, id, tl, he, fa have zero sentences**; xh 21%, yo 23%,
mi 38%, ha 46% top-500 coverage. Also: `data/mi_frequency.tsv` has zero
macrons, so rank 23 `tona` is glossed *wart* and rank 29 `ra` as the
Egyptian sun god. The thin/monotone problem inside covered words is already
scoped by `docs/plans/example-diversity.md` (2,090 words, top-1000 band).

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
`en.md` and the README lag the `agreement_feature` rule.

### D5 — Idle extraction assets; extractor gaps.

extra-agent's emit now **merges** (sidecar ownership; existing wins on
collision). Sitting unemitted: ~2,518 validated Russian vocabulary entries,
19 grammar points, 218 sentences (`out/Russian.parts`); an English grammar
book (156 vocab / 149 grammar / 32 sentences). he/fa/la/id/tl have **no
LanguageProfile** in the extractor (Hebrew/Persian would extract with wrong
tuning). Frequency lists are thin where sentences are thin too: tl 90 rows,
id 581, fa 584, la 595, mi 781, he 929.

---

## The plan — six phases, one PR each

### Phase 0 — Instruments first (measure before touching)

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

### Phase 1 — Definitions (the named complaint)

- `seed_english.py`: POS-aware synset selection (function words prefer
  their function-word sense; frequency rank informs expected POS), expanded
  curated guard for the top band, shrapnel filter. Tests.
- `source_data.py`: kaikki sense ranking — prefer lexical POS
  (pron/det/verb/particle/conj/prep/adv) over `name`/`symbol`/`character`;
  keep the letter-name filters; tests pinning fr `ne`/`y`, de `ne`, tr `ve`.
- Regenerate frequency TSVs from the local raw cache: tr, yo, sw, xh first
  (stale rows), then the wrong-sense tail (fr, de, nl, es, ca, hi, el, ro,
  pt, it, ko, ru).
- Maker–checker workflow over every changed top-500 gloss; curated
  overrides where kaikki still has nothing good (yo top-12 especially).

### Phase 2 — Sentences to parity

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
