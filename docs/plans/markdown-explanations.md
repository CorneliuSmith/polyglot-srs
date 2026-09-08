# Markdown pass over the seed explanations — plan (4 Sep 2026)

**Status: TEN COURSES DONE (7 Sep 2026)** — fr, es, it, pt, de, nl, ca,
ro, el, ru. 272 of 438 explanations render as markdown and **576 content
defects** were corrected on the way through (`2026-09-07-fr-markdown-pass.md`,
`-batch-2.md`, `-batch-3.md`). 17 courses to go.

**Status was: FIVE COURSES DONE (7 Sep 2026) — fr, es, it, pt, de. 124 of 216
explanations now render as markdown and **164 content defects** were
corrected on the way through (`2026-09-07-fr-markdown-pass.md`,
`2026-09-07-markdown-batch-2.md`). 22 courses to go.**

**Status was: FRENCH IS DONE (7 Sep 2026) — 20 of 42 explanations now render
as markdown and 13 content defects were corrected on the way through
(`docs/decisions/2026-09-07-fr-markdown-pass.md`). 26 courses to go, in the
order below. The tooling is built.**

**Status was: the tooling is built; the editorial pass has not
started.** `scripts/apply_grammar_explanations.py` is the export/apply pair
the corrections below call for, and `test_content_markdown_guard.py` has
been reshaped so a formatted explanation is legal while a construct the card
cannot render is not (see "The gate", below). What remains is the read
itself: 27 in-session runs over 1,378 texts, in the order this plan sets.

**Status was:** planned, not started. Reviewed against the code on 6 Sep 2026
(a workflow agent, every claim cited to file:line) and corrected below;
the sections that follow are the original design with the wrong lines
struck. **Placement: `docs/plans/quality-parity.md` Phase 3, as its closing
per-language step** — see "Where it sits" at the end.

## Corrections, 6 Sep 2026

1. **Scope is `explanation` only.** `culture_note` and `function_note`
   render as plain `<p>` on every surface (`GrammarPathPage.tsx`,
   `LearnPage.tsx`, `ReviewDetail.tsx`); only `explanation` reaches
   `ExplanationView` → `CardMarkdown`. A `**` in a culture note prints
   literally. The guard exemption must therefore cover `explanation` only
   — and the guard's `function_note` field is vacuous today because the
   seed key is `function` (`seed_grammar.py`), which the pass must never
   touch: it is what `REFERENCE.md` renders from.
2. **No API key.** The programme's ground rule and the owner's directive:
   maker–checker runs in-session. The script splits like the two the repo
   already has (`scripts/apply_drill_glosses.py`,
   `scripts/apply_authored_sentences.py`): an EXPORT half writes each
   point's task input (title, explanation, language brief, house style);
   an APPLY half reads the workflow journal / task output, runs
   `clean_markdown`, the typesetter-safety split and the idempotence
   check, writes the reviewer diff, and only then the grammar file. The
   `--model` flag, the cost table and "needs `ANTHROPIC_API_KEY`" go.
3. **The corpus is 1,262 points and 1,378 non-empty texts**, not 3,786
   (that was 1,262 × 3 fields including empties) — 27 in-session runs of
   roughly 40–50 points (ko 156, sw 64, ru 55, the rest 32–47).
4. **Delivery is `docs/quality/refeed.md` step 4** (`seed_grammar -l
   <code>`), per course, owner-run, no rollback file — revert is the
   previous commit's JSON. The 26 Aug gate this plan tied itself to was
   released on 30 Aug (CLAUDE.md).
5. **Use the repo's serializer** — `json.dumps(ensure_ascii=False,
   indent=<detected>)` as `apply_drill_glosses.py` does; all 27 files
   round-trip byte-identically through it, which is what lets a gloss PR
   and an explanation PR to the same file merge cleanly.
6. **Korean after its Phase 3 dedupe** (156 points in the file, 40 in
   production): formatting a point that is then merged away is wasted
   reviewer time.
7. **Locale explanations do not follow.** `explanation_translations` are
   generated only where no row exists, and the card prefers the locale
   row — so a formatted English explanation leaves every existing
   Spanish/Portuguese/Russian rendering plain. Not breakage; say so in
   the reviewer diff, and queue those locales for regeneration when the
   translation lane has capacity.
8. **`REFERENCE.md` is a check, not a regeneration**, for an
   explanation-only pass (`render_reference` reads title, function, level,
   display_order). Run `python -m backend.services.tutor_reference` and
   expect no diff.
9. **`seed_grammar.py` does not call `clean_markdown`** (the editor and
   the AI generator do). The apply step's own call is the only cleaner
   between the file and production; it stays.

## The gate (built 7 Sep 2026)

```bash
.venv/bin/python -m scripts.apply_grammar_explanations --export tr --out tr.json
.venv/bin/python -m scripts.apply_grammar_explanations --apply tr.edited.json --dry-run
```

The export half writes one task per non-empty explanation (index, title,
level, function, text). The apply half refuses anything the card cannot
render, and only that — taste stays with the reader:

| refused | because |
|---|---|
| a heading | `CardMarkdown`'s sanitiser has no `h1`-`h6`; the card title is the heading |
| an image, a horizontal rule, raw HTML, a non-http link | not in the allow-list — dropped silently or printed literally |
| a table whose rows disagree with its header | GFM renders it as a paragraph of pipes, worse than the prose it replaced |
| `___` inside a markdown block | that is how cards write a blank; inside markdown GFM reads it as emphasis |
| a text sharing no word with the one it replaces | what an off-by-one in the round trip looks like |
| a text past 3x or under 40% of the original | formatting does not triple a paragraph, and truncation is otherwise silent |

Tested against the corpus it governs (rule 47): every one of the 1,378
shipped texts passes its own gate, and a test pins that none carries
markdown yet, so the first formatted course shows as a real change rather
than as drift. `has_markdown` mirrors `ExplanationView.hasMarkdown`, and a
test reads the TSX to keep the two in step.

**The old guard could not have survived this pass.** It forbade markdown in
`explanation` outright with an ALLOWED set of exceptions — 1,378 lines of
exceptions, one per text, and a list that long is not read. It now checks
the renderer-supported subset instead, and keeps the zero rule for the
fields that render plain (`culture_note`, `function`). It had been naming
`function_note`, which is not the seed key, so that field was never
actually guarded — correction 1 in this plan, now fixed.

## What it is, and what it is not

Since PR #394 an explanation that carries markdown syntax renders as
markdown ("like Anki"): bold, lists, tables, inline code, links. (~~culture
note or function note~~ — correction 1: those render plain.) The 1,378
non-empty texts in `data/grammar/*_grammar.json` carry none. They render fine today: `components/ExplanationView.tsx`
typesets the three plain-text shapes they use (term/gloss tables, arrow
derivations, `label: forms` chips).

So this is **not a format migration**. Nothing mechanical turns prose
into good markdown. It is an **editorial pass**: per explanation, decide
what deserves bold, which enumerations become lists, which paradigms
become tables — and, while every text is being read anyway, fix what is
wrong in it. That second half is the editorial read Phase 3 of
`quality-parity.md` owes each language's grammar file (~~the review the
production push is gated on~~ — correction 4: the gate is gone).
**Do both in one pass.** Done apart, the corpus gets read twice.

## House style for card markdown

The renderer's allow-list (`components/CardMarkdown.tsx`) and the server's
cleaner (`services/markdown.py`) already refuse everything else, so the
rules are about taste, not safety:

- **Bold** the form being taught the first time it appears, and nothing
  else. One bold per paragraph at most.
- **A list** when the prose enumerates three or more parallel cases
  ("with être: movement verbs, reflexives, …"). Two cases stay in prose.
- **A table** for a paradigm (person × form, case × ending). Header row
  in the learner's language; cells hold forms only, no commentary.
- **Inline code** for an ending or affix quoted as a string (`-er`,
  `ndi-`). Not for whole words.
- **Never**: headings (the title is the heading), images, raw HTML,
  links inside the body (references have their own field), emphasis by
  underscore (blanks are written `___`), nested lists.
- **Keep the three typesetter shapes as they are** when they already do
  the job. A term/gloss line pair renders as a table today; rewriting it
  as a markdown table changes nothing the learner sees. Convert a block
  only where markdown says something the typesetter cannot.
- **Content changes are the review, not a side effect.** A rewrite that
  changes what the explanation claims must be flagged as such in the
  diff — that is what the reviewer reads for.

## Tooling to build (about a day)

1. `scripts/markdown_explanations.py <code> [--export | --apply RUN]
   [--only TITLE…]` — one language at a time; ~~`--model MODEL`~~
   (correction 2: export/apply around an in-session run).
   - Reads `data/grammar/<code>_grammar.json`.
   - For each point sends `title`, `explanation`, `culture_note`,
     `function_note` and the language brief
     (`quality_rules.language_brief`) to the model with the house style
     above and the instruction *"reformat; correct only what is wrong;
     list every content change you made"*. Structured output:
     `{explanation, culture_note, function_note, changes: [str]}`.
   - Runs `services/markdown.clean_markdown` on the result, then the
     typesetter-safety check: a block flagged by `hasMarkdown` must not
     also contain a term/gloss or arrow shape (mixed blocks lose the
     typeset half — split them).
   - Without `--apply`: writes `data/grammar/<code>_grammar.markdown.json`
     and a unified diff + the per-point `changes` list to
     `docs/quality/<code>.markdown-pass.md` for the reviewer. With
     `--apply`: writes the grammar file in place.
   - Idempotent: a point whose texts already carry markdown is skipped
     unless `--only` names it.
2. `backend/tests/test_content_markdown_guard.py`: replace the empty
   `ALLOWED` set with `MARKDOWN_LANGUAGES: set[str]`; a language in that
   set is exempt from the zero-marker rule for explanations and notes
   (glosses stay at zero backticks everywhere). Add a code there when its
   pass is accepted.
3. `python -m backend.services.tutor_reference` after each apply — the
   REFERENCE.md test fails otherwise (titles do not change, but run it).
4. `docs/quality/jam.md` and the quality-rules skill: say that
   explanations render markdown; glosses still print literally.

## Procedure, per language

1. `scripts/markdown_explanations.py fr` → read
   `docs/quality/fr.markdown-pass.md`. Reject the pass outright if the
   `changes` lists are long: the model was rewriting, not reformatting.
2. Spot-check ten points in the app: `npm run dev`, open the Workshop
   editor on each, the preview shows the learner view.
3. `--apply`, add `fr` to `MARKDOWN_LANGUAGES`, run the backend suite,
   `npm run build`, `npx vitest run`.
4. Commit per language ("Markdown pass: French"), one PR per language or
   per batch. The reviewer for that language signs the PR.

**Order:** French first (the best-documented standard, the owner reads
it), then the languages testers are using, then the rest.

**Cost:** ~~4,000 API calls~~ — 27 in-session workflow runs of 40–50
points each (correction 3), the checker one tier up as for glosses. No
key.

## Delivery to production

Seed files reach the live database through `docs/quality/refeed.md`
step 4, `seed_grammar -l <code>`, which the owner runs per course
(~~waits on the Gym level and this very review~~ — correction 4). Until
that run the live app keeps plain text; the repo and the local dev app
show markdown. A point a
reviewer edited in the app is not overwritten by the re-seed — the seeder
files a suggestion for it instead (`seed_grammar.py`, the proposal
branch), so the pass cannot stomp a correction made in production.

## Rollback

Per language, `git revert` the pass commit and remove the code from
`MARKDOWN_LANGUAGES`. The renderer needs no change: plain text is still
typeset exactly as before.

## Where this can run

The local Claude Code session: the in-session maker–checker run
(correction 2 — no key anywhere), the spot-check needs `npm run dev` in a
browser, and the seeder step is the owner's, from `refeed.md`. Everything
the script needs is in the repository. Point the local session at this
file.

## Where it sits

`quality-parity.md` Phase 3 — Grammar & hint debt burn-down — as its
closing per-language step, run in the SAME PR as that language's Phase 3
grammar-file work: the pass edits `points[].explanation`, the gloss and
hint passes edit `drills[]`, and Phase 3's ko dedupe is the only other
work on `points[]` itself. One PR and one `seed_grammar` run per course
instead of two. French first (Phase 3 owes it nothing, and the owner
reads it), ko after its dedupe, ru/en topped up after Phase 5's emit
(the pass is idempotent, so a top-up costs only the new points). Never
ahead of items 1–8 of `docs/decisions/2026-09-06-review-pass.md`, which
own the learner-facing defects; before Phase 7. Phases 7 and 8 touch no
grammar JSON, so ordering against them is free.

## Done when

- [ ] `scripts/markdown_explanations.py` exists with tests for the
      typesetter-safety split and idempotence.
- [ ] `MARKDOWN_LANGUAGES` replaces `ALLOWED` in the guard test — for
      `explanation` only; `culture_note` stays at zero markers.
- [ ] French passed, reviewed, merged.
- [ ] Remaining languages, in the order above, each signed by a reader.
- [ ] `jam.md` and the quality-rules skill updated.
- [ ] `seed_grammar -l <code>` per passed language (owner, refeed.md).
