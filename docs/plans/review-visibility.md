# Review visibility: four streams, one map

Owner (2026-08-20): "A key issue that I am experiencing is visibility of
feedback. There are reviews submitted by users, general reviews, ai that
needs to be reviewed, and contributions by humans that need to be reviewed —
they should be parsed by language but it should be easy to change the
language with good visibility on the type of review and who sees it and
where."

## The problem, located precisely

The pieces mostly exist. What's missing is that they don't say what they
are, and one stream is missing from the map entirely:

| Stream (owner's words) | What it is here | Where it lives today | Gap |
|---|---|---|---|
| "reviews submitted by users" | card feedback, review notes, tester recommendations | Review tab panels, counted in the inbox | Indistinguishable from the other 11 tiles — no grouping, no "who sees this" |
| "general reviews" | `app_feedback` (the home-page feedback button) | Triaged on `/feedback` and in Settings — **not** in the Contribute workspace, **not** in the per-language inbox, not language-filterable in its own panel | The one stream that never appears on the per-language map at all. The bell's "Open the feedback queue" even navigates to a page that doesn't host the queue |
| "ai that needs to be reviewed" | generated drills/examples, AI translations, AI levels, audit flags, overlaps | Review tab panels, counted in the inbox | Same flat-tile anonymity; two queues are admin-only and nothing says so |
| "contributions by humans" | pending grammar points, content suggestions, change requests | Contribute/Review tabs, counted in the inbox | Same |

And one real correctness bug the audit surfaced: the cross-language totals
(the inbox strip, the bell badge) include **admin-only queues in a
reviewer's numbers** — a reviewer can be shown "9 waiting" of which 3 are
AI translations they cannot open. A count you cannot clear is the badge
version of a lie.

## Contracts

- **C1 — complete map.** Every stream, including general feedback, appears
  in the per-language roll-up and the per-language bell counts. General
  feedback that names no language is a first-class bucket, never dropped
  and never mis-filed under a course.
- **C2 — self-describing tiles.** The inbox groups by origin (reports from
  learners & testers / general feedback / AI awaiting review / human
  contributions), and every tile carries who can see it and where it is
  acted on. The taxonomy is defined once (`lib/reviewTaxonomy.ts`) and the
  inbox, the bell, and any future badge all read it.
- **C3 — honest counts.** No total shown to a viewer includes work they
  cannot act on. Admin-only queues are stripped server-side from every
  cross-language number a non-admin receives.
- **C4 — act where you look.** The general feedback queue is triageable
  inside the Review workspace, scoped by the same language picker as
  everything else, with three scopes: this language / not about one
  language / all. The bell's feedback rows land somewhere that can act.

## Changes

**Backend**
1. `_INBOX_QUEUES` gains `app_feedback` (open rows for the language), so
   C1 holds with no new endpoint — the roll-up, the strip, and the bell
   all inherit it.
2. `ADMIN_ONLY_QUEUES = ("ai_translations", "app_feedback")` declared next
   to the queue table; `/review/inbox`'s other-languages strip and
   `/notifications` zero those counts and recompute totals for non-admins
   (C3). Languages whose total falls to zero drop out.
3. `/notifications`' separate `feedback` list narrows to the no-language
   rows only — the per-language rows now ride inside each language's
   counts, and reporting them twice would double the badge.
4. `list_feedback` gains `unassigned` (language IS NULL); router +
   client pass it through (C4).

**Frontend**
5. `lib/reviewTaxonomy.ts`: one table — key → label, origin, audience,
   where-acted-on, cap. `ReviewInbox` and `StaffNotifications` both read
   it (C2).
6. The inbox renders four origin sections with subtotals; every tile shows
   an audience chip ("reviewers" / "admins only") and its destination.
7. Bell rows describe each language by origin ("3 reports · 4 AI · 2
   contributions") instead of a bare total.
8. `FeedbackQueuePanel` grows a scope control (this language / not about
   one language / all) and mounts in the Review tab for admins.
9. `docs/review-workflow.md` gains the who-sees-what-where matrix.

## Test matrix

| # | Case | Expected |
|---|---|---|
| 1 | app_feedback rows exist for a language | Inbox counts and bell counts include them; admin sees the tile |
| 2 | Reviewer (non-admin) opens the inbox | No app_feedback / ai_translations tile; strip totals exclude both |
| 3 | Reviewer's bell | Language totals exclude admin-only queues; a language with only admin-only work doesn't appear |
| 4 | Admin's bell | Full totals; feedback section lists only "not about one language" |
| 5 | Feedback with no language | Counted once (bell bucket), never under a course |
| 6 | Panel scope = "not about one language" | Query sends `unassigned`, list shows only null-language rows |
| 7 | Panel scope = this language | Query sends the workspace language id |
| 8 | Inbox grouping | Four sections, subtotals, audience chips on admin-only tiles |
| 9 | Migration 20260906/20260930 absent | Everything above degrades to zero/absent, never a 500 |
