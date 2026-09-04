# Markdown pass over the seed explanations — plan (4 Sep 2026)

**Status:** planned, not started. Owner-scheduled. Runs from any Claude Code
session on a checkout of this repository — the local one included — see
"Where this can run" at the end.

## What it is, and what it is not

Since PR #394 an explanation, culture note or function note that carries
markdown syntax renders as markdown ("like Anki"): bold, lists, tables,
inline code, links. The 3,786 texts in `data/grammar/*_grammar.json`
carry none. They render fine today: `components/ExplanationView.tsx`
typesets the three plain-text shapes they use (term/gloss tables, arrow
derivations, `label: forms` chips).

So this is **not a format migration**. Nothing mechanical turns prose
into good markdown. It is an **editorial pass**: per explanation, decide
what deserves bold, which enumerations become lists, which paradigms
become tables — and, while every text is being read anyway, fix what is
wrong in it. That second half is the comprehensive grammar-concept review
the production push is gated on (`docs/decisions/2026-08-26-owner-decisions.md`).
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

1. `scripts/markdown_explanations.py <code> [--apply] [--model MODEL]
   [--only TITLE…]` — one language at a time.
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

**Cost:** each point is one call of roughly 1–2k tokens in and out; 27
languages × ~140 points ≈ 4,000 calls, a few dollars on the summary tier,
tens on the chat tier. Use the chat tier: this is judgement, not
summarising.

## Delivery to production

Seed files reach the live database through the seeder sequence, which
the owner runs and which waits on the Gym level and this very review
(`CLAUDE.md`, "Production pushes are GATED"). Until that push the live app
keeps plain text; the repo and the local dev app show markdown. A point a
reviewer edited in the app is not overwritten by the re-seed — the seeder
files a suggestion for it instead (`seed_grammar.py`, the proposal
branch), so the pass cannot stomp a correction made in production.

## Rollback

Per language, `git revert` the pass commit and remove the code from
`MARKDOWN_LANGUAGES`. The renderer needs no change: plain text is still
typeset exactly as before.

## Where this can run

Anywhere with a checkout and an `ANTHROPIC_API_KEY` in `backend/.env` —
the local Claude Code session is the better place, not the cloud one:
the model pass needs the key (the cloud session has none), the
spot-check needs `npm run dev` in a browser, and the seeder step needs
the production database URL. Everything the script needs is in the
repository; nothing depends on this session's state. Point the local
session at this file.

## Done when

- [ ] `scripts/markdown_explanations.py` exists with tests for the
      typesetter-safety split and idempotence.
- [ ] `MARKDOWN_LANGUAGES` replaces `ALLOWED` in the guard test.
- [ ] French passed, reviewed, merged.
- [ ] Remaining languages, in the order above, each signed by a reader.
- [ ] `jam.md` and the quality-rules skill updated.
- [ ] Production push (gated; owner).
