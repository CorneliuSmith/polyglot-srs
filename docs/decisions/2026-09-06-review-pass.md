# 6 September 2026 — old versus modern: the review pass, and the queue for implementation

The owner paused implementation ("low on tokens"), asked for the old cards to
be compared with the modern ones so that quality holds across the board,
and for the rest of the plan to be reviewed and the documents brought up to
date before implementation resumes on Opus. This is that record. Nothing in
it is built; every number was measured on 6 Sep on the committed files.

## 1. What "old versus modern" turned out to mean

Two screenshots: a vocabulary card, `human`, sentence "We are ___." — three
words, the old corpus shape; and a grammar card whose TRANSLATION line read
"do — the participle."

The first is not a supply problem. English's bank holds 15,350 sentences
for its top 2,000 words and 7,990 of them meet the §23 bar; `human` itself
has longer sentences on file. **The card draws by `difficulty_rank` then
`id`, every row of a word ties on the word's rank, and the old rows have
the lower ids.** So the old corpus wins the draw on every course where it
was inserted first — which is every course. 89% of English, 62% of German,
58% of Russian top-2,000 words that OWN a modern sentence still show an old
one. The Russian figure is the important one: 6,517 sentences were authored
to the bar on 31 Aug, every top-2,000 word has one, and the learner would
see almost none of them. CHECKS §26 has the table for all 26 spaced-script
courses.

The second is a label. The English course's drill `translation` holds a
usage note by documented convention, and the real translations sit in 19
locale files; an English-UI learner has no locale row, so the note renders
under "Translation". 266 of 266 English drills; 0 elsewhere; 11 of the 266
are the hint said twice. CHECKS §27.

**So: the modern content is at the bar, and the old content is what the
learner sees — by ordering, not by quantity.** Maintaining quality across
the board is a selection fix first and an authoring queue second.

## 2. The queue, in order, for when implementation resumes

1. **Draw order (CHECKS §26).** One ORDER BY in `backend/repositories/cards.py`
   (the LATERAL that builds `sentences`/`translations`/`glosses`/
   `transliterations` — all five arrays, same order), integration test:
   a word with a 3-word row at a lower id and a 9-word row at a higher id
   returns the 9-word row first; a Thai word keeps rank order. Flips
   ~9,500 top-2,000 cards across 26 courses at zero content cost. Do this
   before any authoring.
2. **`fix/en-symbol-glosses`** — pushed, unmerged. 37 English headwords to
   `vocab_exclusions.tsv`; data-invariant tests 249 passed / 9 WordNet
   skips; `audit_content` PASS at baseline. Needs the full CI run, then PR
   and merge. Note it does not remove the rows from production (item 4).
3. **English drill `context` (CHECKS §27).** Backend returns the note as
   `context` on the `en` course and `translation` only from the locale
   row; frontend label `card.context` in all six locales; the 11
   cue-shaped notes rewritten as scenes; a check in `test_grammar_hints.py`
   (`translation` not `^\S+\s+[—–-]\s+`, not fold-equal to the hint).
   Ship `path.practiseForms` / `path.drillCount` for ar/es/fr/pt/ru in the
   same change.
4. **A retire step for exclusions.** `vocabulary.retired_at` (migration,
   owner-applied, readers degrade per CLAUDE.md), set by `reconcile` from
   `vocab_exclusions.tsv`, filtered by the card draw and lesson intake
   while the learner's `user_cards` row is kept. Without it the `em` card
   outlives the merge. Then the owner runs `reconcile --apply` for `en`.
5. **English vocabulary the seeder skips** — the 8,600 cap: `what`, `how`,
   `because` absent from production. Gloss through `gloss_overrides.tsv`
   or lift the cap; the audit gates either.
6. **Phase 8 supply**, in the 20 Aug order after the owner's ru/ar: `mi xh
   yo` → `id tl he fa` → `en` → the well-resourced courses; queue sizes per
   course in `quality-parity.md` Phase 8 item 8; plus the 378 bare rows
   (item 1) and the 44 Tatoeba self-references (item 3). Method unchanged:
   in-session maker–checker, `apply_authored_sentences.py`, never the key.
7. **Then Phases 2d, 3, 5, and last 7**, as the plan orders them.

After any merged data change the owner runs `docs/quality/refeed.md` for
that course; after item 1 the owner runs nothing — it is code.

## 3. Documents changed in this pass

`CHECKS.md` §26, §27 · `quality-parity.md` Phases 3, 4, 6, 8 · `en.md` note
0 and rule 4 · `refeed.md` (new; Phase 6 had promised it since August) ·
`DEBT.md` (gate entry rewritten; five entries added) · `LEARN.md` (the
add-only pipeline and its gates) · `CLAUDE.md` (the gate paragraph, which
described a state the owner ended on 30 Aug) · the 26 Aug decision marked
superseded in practice · quality-rules skill, rules 43–44.

## 4. Two things this pass did not do, on purpose

No implementation, per the owner. And no re-run of the full backend suite:
the 5 Sep run reported `4 failed, 499 passed, 2541 errors` — an error
flood, which CLAUDE.md says to restart and re-run rather than report — so
the exclusion branch was verified on its data-invariant tests only; the
full gate is CI's job at PR time.
