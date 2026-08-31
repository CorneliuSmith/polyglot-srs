---
name: quality-rules
description: The working rules of the language-quality program. Load before any content, definition, sentence, gloss, grammar, or guideline work on any course — they encode every failure this program has already paid for once.
---

# Quality program rules

The long forms live in `docs/quality/CHECKS.md`, `docs/quality/README.md` and
`docs/plans/quality-parity.md`. This is the digest to hold in context while
working. Each rule exists because its absence already shipped a defect.

## Scope — the rule the owner has had to repeat

1. **Every check applies to all 27 courses until decided otherwise.**
   A defect found in one language is a *class*; measure the other 26 before
   fixing one. A check is not finished until its row in `CHECKS.md` says
   all / parameterised / scoped-with-reason. (English's circular glosses,
   Latin's collisions, Māori's gloss were each "one language's quirk" — none
   was.)
2. **Fix the class, not the example the owner happened to screenshot.**
3. **A finding is not shipped until the guidelines say so.** Every fix updates
   `docs/quality/<code>.md` for each language it touched, `CHECKS.md` (status
   row), and the plan. Record what was measured, what changed, and what it
   COST — including decisions you did not take. A repair whose reasoning lives
   only in a commit message is invisible to the next session and to the owner.
   When a fix reveals that a standing owner decision has a price (the ar yeh
   fold merging 84 cards), write the price into the doc and leave the decision
   alone — surfacing it is the job, overruling it is not.

## Order of work (owner decision, 20 Aug 2026)

**Low-frequency courses first — clean AND populate** (`mi` step c, `ha`, `xh`,
`yo`, `jam`, `id`, `tl`, `he`, `fa`). Several are not yet real courses: `tl`
has 90 rows, `jam` 384. **Then** the deep pass on the well-resourced courses
to `en`/`la` standard. **Then** sentences, for all 27 at once — no course
reaches the sentence stage ahead of the others.

The expectation is that the deep pass will be lighter on the big courses
because their data is better. Treat that as a prediction to test, not a fact:
`ca` had no correct card for "I am" with 9,996 rows, and `es` had rank 79
`creo` glossed as the wrong verb. If the deep pass finds defects at English's
rate, say so — that result matters more than the phase closing quietly.

## Content

4. **One card per written form; the gloss names the senses** (D1c) — but where
   orthography CAN distinguish (macron, tone, accent), distinct words get
   distinct rows. **Re-marking is not decoration**: an unmarked row may stand
   for several words; decide which owns the rank, add rows for the rest, sweep
   for missing members after (D1d, CHECKS §8).
5. **A card has SIX layers; check every one, and name them precisely**
   (owner directive, 25 Aug 2026). **hint** (narrows the answer) · **sentence**
   (the example) · **translation** (its English) · **interlinear gloss** (the
   word-by-word line UNDER the sentence) · **romanisation** (non-Roman scripts
   only) · **definition** (the card's English meaning). **"Gloss" names THREE
   of these in this repo** — `gloss_overrides.tsv` holds definitions, a drill's
   `gloss` is the interlinear line, `giveaway_by_gloss` is about hints. The cost
   is overstated REPORTING, not a missed pass: "911 gloss fixes" reads as though
   the word-by-word layer was repaired when nothing had touched it. Say which
   layer you mean; a fix to one is not a fix to another. Measured
   25 Aug: interlinear gloss is 100% on `mi` drills, 30% on `sw`, **0%
   everywhere else**; romanisation is absent from `hi` and `th` ENTIRELY, and
   from the `ru`/`ar`/`hi`/`th` sentence banks (see `CHECKS.md` §9).
6. **Examples must exercise the sense the gloss leads with** (D2c2). Definition
   and sentences are fixed in different files by different passes — a fix in
   one is not a fix in the other. On mismatch: fix the sentence, the gloss
   ORDER, or the coverage — decide which.
7. **Orthography and word list before sentences; sentences before glosses.**
   Everything downstream of a toneless headword is wrong at birth.
8. **A gloss never spells the answer; a wrong gloss is worse than none.**
   Mechanical glosses never overwrite authored ones, never serve GLOSS_FIRST
   courses. Not every sentence gets a gloss — 4,974 GLOSS_FIRST rows are the
   target, not 484k.
9. **A declared policy that nothing checks is being violated — two for two.**
   `la.md` asserted "macrons everywhere, verified" while `la_frequency.tsv`
   was 48% non-compliant; `jam.md` asserted Cassidy–JLU while 12 headwords
   broke it, three of them words the doc names as drift itself. Express the
   policy as a character set and test it (`test_orthography.py`). Necessary,
   not sufficient: `friend` breaks no Cassidy letter rule and is still English.
10. **A fold may excuse a mark; it may never launder a word.** Settled and
   shipped: a fold-only match grades WRONG_FORM when the typed string is
   itself another course word, sloppy otherwise (`test_nlp_collisions.py`
   ratchets per-language ceilings). Before folding anything new, ask what the
   mark DOES in that language — and check the fold-image of the vocabulary.

## Sources & spend

11. **Check the PIPELINE before concluding a resource does not exist.** `la`,
    `id`, `tl`, `he` and `fa` were each queued for authoring "from nothing"
    while Tatoeba had an export for all five — they were simply missing from
    `TATOEBA_ISO3`. Five courses, one dict. Before authoring a corpus, curl the
    source and read the language map. (26 Aug 2026)
12. **A rebuild is not a replacement — merge.** `build_sentences` overwrote a
    committed bank with a smaller one twice in one day, destroying 393 authored
    rows the second time. Committed files carry hand-added content a generator
    cannot reproduce, so a rebuild that SHRINKS a file is a bug even when every
    row it writes is correct. Rebuild, then union with what was there.
13. **A layer with no WRITE PATH cannot ship, however well authored.**
    `load_example_sentences` silently dropped `transliteration` and `gloss`, so
    `ko`'s TSV carried romanisation production never saw and the interlinear
    gloss read 0% in production for all 27. Before filling a layer, follow it
    end to end: file → loader → column → renderer. Same class as the collision
    guard shipping with `data/*` gitignored, which silently graded every fold
    as a pass.
14. **A test that passes because something CRASHED is not a passing test.**
    Before trusting a green assertion on a path that calls out to anything,
    check that the path actually RAN. The gym top-up test asserted
    `charged == 1` and was green in CI for two releases because `make_chart`
    built a keyless client, threw, and the router's `except: break` skipped
    the two charges WP45 had added. The honest answer was 3. It failed only
    on a machine with `TUTOR_DEV_MOCK` on — so the environment where the code
    worked was the environment that looked broken.
15. **A test must not reach a live model.** Owner directive: this program
    does not spend the API key, and a unit test is the easiest place to break
    that by accident. Patch the generator, or patch `get_settings` for the
    dev-mock path. `never_reach_a_live_model` in `backend/tests/conftest.py`
    now fails loudly on any client construction. Absent a key it is worse
    than a spend — it silently exercises the exception branch instead of the
    behaviour, which is how rule 14 happened.
16. **When local and CI disagree, the failing one is usually right.** Green
    CI is not evidence the code works; it can equally mean CI is missing the
    setting that makes the code run at all. Reproduce both, and find out
    WHICH environment is exercising the real path before believing either.
17. **Every support layer gets the answer-leak test BEFORE it gets content.**
    Three times now a layer that exists to help has spelled out the word the
    card is testing: romanisation on 926 rows, the Hebrew hint on 191 of 191,
    the Swahili gloss on 134 of 134. The layer's whole audience is people who
    cannot check it, so nobody reports it. Write the guard first.
18. **Search the FOLDED form, not the written one.** A leak audit that
    respects the writing hid 62 of Swahili's 134: the gloss head is `i-ko`
    and the answer is `iko`, so a word-boundary regex misses it while a
    learner reads it off instantly. Normalise away hyphens, spaces and case
    before comparing, and check multi-token answers too — one more hid by
    spanning two cells.
19. **Compare TOKENS, not substrings, or you will report phantoms.** The
    same audit with substring matching flagged 32 clean lines: `na` sits
    inside `ni-na`, and Māori `I` is also the English gloss of `au`. Verify
    every hit before it becomes a number in a report — see rule 10.
20. **The adversarial pass is what tells buildable from not. You cannot
    predict it.** Greek and Korean looked risky (assimilation, digraphs) and
    each returned exactly ONE systematic defect. Thai looked buildable once a
    segmenter existed and returned 38 across seven classes, missing ordinary
    words like "health" and "France". Build the thing, measure it on the real
    corpus, and let the number decide whether it ships — reading about the
    script decides nothing.
21. **Before unifying a label, ask whether the language makes ONE
    distinction or several.** Hausa `ya` carried COMPL and PFV — one morpheme,
    two names, a defect; collapsed to the majority. Māori `i` carried OBJ, PST
    and "at" — one form, three functions; collapsing it would have destroyed
    the distinction, so it was disambiguated per sentence instead. The number
    of spellings tells you nothing about which case you are in. And a hedge
    like `PAST/OBJ` is not a gloss — it is the decision left unmade.
22. **Do not author into a route that does not exist.** Half the remaining
    gloss work (3,609 of 6,610 drills) is for courses whose `LAYER_ORDER` has
    no gloss slot, so nothing would ever show it. Check the consumer before
    the content — this is CHECKS.md §12 from the other end.
23. **A mechanical split is a guess. Verify it before you ship it.** Peeling
    clitics off Hebrew and Persian words looked like clean engineering and was
    wrong 20% and 91% of the time — producing DIFFERENT WORDS, not near
    misses: `מחברות` read as "from friends" when it is "notebooks". Anything
    that decomposes a word it does not know is guessing; send a sample to a
    checker before it reaches a learner, and delete it if the rate is bad.
24. **A coverage number going DOWN can be the correct outcome.** Removing the
    Hebrew peeler dropped sentence coverage from 80% to 64%. That is 16
    percentage points of confidently wrong readings leaving the corpus. Move
    the ratchet floor down and write the reason into the test, so the next
    person does not "fix" it by restoring the fault.
25. **Facts yes, sentences regenerated** — paradigms/vocab from licensed
   courses may inform; verbatim sentences may not ship.
26. **Never the API key.** Maker–checker runs in-session (Workflow tool).
27. **Fixes land in committed files** (`gloss_overrides.tsv`, TSVs, JSON) —
    a DB-only repair is undone by the next re-seed. Same logic one level up:
    a TSV-only deletion is undone by the next regeneration — durable
    deletions go in `data/vocab_exclusions.tsv` (typo-mass rows like `citta`
    "Tuscan girl", rank inherited from `città`).

## Verification

28. **Verify agent output mechanically before writing it back**: structural
    validators, spot-checks against known ground truth, and assembly by stable
    key, never by index (a rank drift once nearly filed `luna`'s gloss under
    `stella`). After writing a TSV, eyeball it: text containing `"` gets
    csv-escaped into `""..""` noise — reword the text instead.
29. **Re-measure any agent-reported number before acting on it** — two of five
    sampled claim-audit figures did not reproduce.
30. **State verification honestly**: "275 of 557 checker-verified, rest
    maker-only" — never round up to "verified".
31. **Never freeze a count the audit computes** — cite the rule name; the tool
    says the number. Hand counts carry date + method. "Verified" names every
    file the claim covers.
32. **Baseline ratchet**: equal is fine, worse needs `--update-baseline` and a
    written reason. Run `audit_content` before pushing content.

## Ship

33. Green = `npm run build` (not `tsc --noEmit`), `vitest`, backend pytest at
    baseline (7 known environment failures), `ruff`, audit PASS, CI green,
    then merge — standing authorization. Say plainly what was left out.
34. **When adding words to fill a homonym gap, add only members a learner
    meets** (`hīc`, `mālum` yes; `pōpulus` "poplar" no) and gloss each naming
    its false twin — "here (distinct from hic: this)".
35. **Nothing of value stays only on this machine** (owner directive, 20 Aug
    2026). After every merge — and before any long-running job — fast-forward
    `feat/phases` to the current head and push it:
    `git branch -f feat/phases HEAD && git push origin feat/phases`.
    This is a multi-week project on hardware that has already slept mid-run
    and killed a workflow; remote is the only durable copy. Workflow outputs
    and analysis scripts live in the session scratchpad under `/private/tmp`
    and do NOT survive — promote anything worth keeping into the repo.

36. **A pipeline that rewrites content re-runs the guards on its output.**
    The translate loop's charter correctly says "copy quoted course-language
    material unchanged" — which faithfully carries a hint's answer-leak into
    every locale. Gates now run inside generate_* (leak, identity echo, blank,
    locale punctuation, validated model indexes), in mock mode too, so tests
    prove them without a model. And Python's `\w` drops Mc marks exactly as
    JS `\p{L}` did (रही → रह) — fold on category M*, both sides. (CHECKS §16)

37. **An example sentence must carry a SCENE, not just be grammatical.**
    Owner requirement, 30 Aug 2026: a learner remembers a word through the
    situation it sat in, so a true-but-pictureless sentence ("I live in
    Moscow") is nearly as weak as a fragment. The bar: 7-14 words, a finite
    verb, the target word doing work the sentence would lose without it,
    three sentences per word differing in KIND rather than in swapped nouns,
    and settings native to the speakers rather than English scenery
    translated across. Fragments were the floor (CHECKS §21); this is the
    ceiling. (CHECKS §23)

## Maintaining this skill (owner directive, 19 Aug 2026)

This is a living document. When new work teaches a rule, **add it here in one
or two lines** — if it improves quality and does not bloat the digest. Keep it
small enough to load in every content session; long rationale goes in
`CHECKS.md` or the plan, with only the rule itself here. Prune a rule only
when the class it guards is mechanically checked everywhere.
