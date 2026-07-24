# Review workflow: how content gets checked, approved, and audited

This is the end-to-end story of how a piece of content — a grammar
explanation, a drill, an example sentence, a vocab level — travels from
"drafted or AI-generated" to "learners can see it", who signs off, what the
AI check actually does, and how every change is logged so you can roll it
back.

If you only remember one thing: **nothing an AI writes reaches a learner
until a human with the reviewer role approves it** (the one exception is a
language an admin has explicitly opted into `ai_ok`, below). Everything else
is about making that human's job fast and reversible.

---

## The short version

```
                    ┌─────────────────────────────────────────────┐
   draft / generate │  reviewed = false  — hidden from learners    │
   ─────────────────▶  (contributor draft, or AI-generated content) │
                    └───────────────────────┬─────────────────────┘
                                            │
                     (optional) AI check ───┤  advisory: pass / concerns
                     (optional) flag issue ─┤  parks a problem for a human
                                            │
                                            ▼
                    ┌─────────────────────────────────────────────┐
   human sign-off   │  reviewer (or admin) approves                │
   ─────────────────▶  reviewed = true, reviewed_by = them          │
                    └───────────────────────┬─────────────────────┘
                                            │
                                            ▼
                          learners see it in the learnable path

   every step above is written to content_change_log ── roll back any of it
```

There is **one** approval, by **one** reviewer (or admin) — there is no
multi-reviewer consensus vote before publishing. The vote mechanisms that
exist (change-request votes, trial-reviewer recommendations) are *advisory
inputs to that one reviewer*, not a gate. This was a deliberate choice: a
single accountable sign-off, made safe by a full audit trail and one-click
rollback, rather than a quorum that stalls.

---

## Who can do what

Roles live in `contributor_roles` (user, role, optional `language_id` scope;
`language_id NULL` means all languages). A user with no row is a **learner**.

| Capability | learner | contributor | trial_reviewer | reviewer | admin |
|---|:---:|:---:|:---:|:---:|:---:|
| Study, leave card feedback | ✅ | ✅ | ✅ | ✅ | ✅ |
| Draft explanations, create points, add/delete drills | | ✅ | | ✅ | ✅ |
| **View** the review queue / Review Inbox | | | ✅ | ✅ | ✅ |
| **Recommend** (advisory ✓/✗) on pending items | | | ✅ | ✅ | ✅ |
| **File a review note** on a card (advisory) | | ✅ | ✅ | ✅ | ✅ |
| **Approve** → flips `reviewed = true`, exposes to learners | | | | ✅ | ✅ |
| Edit / delete published content | | | | ✅ | ✅ |
| **Roll back** a logged change | | | | ✅ | ✅ |
| Run generation, bulk-approve, set review policy | | | | | ✅ |
| Grant/revoke roles, view the per-language audit feed | | | | | ✅ |

The three gate helpers in `backend/repositories/contributor.py` encode this
exactly:

- `can_contribute(roles, language_id)` — admin anywhere; contributor or
  reviewer for that language. (A reviewer can draft fixes to what they
  review.)
- `can_review(roles, language_id)` — admin anywhere; reviewer for that
  language. **This is the publish gate** and the rollback gate.
- `can_trial_review(roles, language_id)` — anyone who can review, **plus**
  trial reviewers for that language. Grants *view + recommend*, never
  publish.

A **trial reviewer** is the on-ramp: they reach the Review workspace, see
everything a reviewer sees, leave advisory ✓/✗ recommendations, and **file
written review notes** on a card — but they cannot publish or delete.
(Notes are exactly where their judgement shows, which is what you promote
on.) Promote a trial reviewer to reviewer once you trust that judgement. Grant either role
from **Contribute → Roles** (admins) or **Manage accounts** (both panels
offer `trial_reviewer` and `reviewer`).

---

## The two kinds of "AI review" — and where you see the flags

People say "AI review" to mean two different things. They are separate:

### 1. The generation checker (automatic, at creation time)

The maker-checker generator (`services/generate.py`, `translate.py`,
`define.py`, driven by `scripts/generate_content.py`) runs a **checker pass
on every item it makes** before it's even stored. A sentence that fails the
checker isn't saved. The `--recheck` flag additionally audits *existing* content — vocab example
sentences (`-k vocab --recheck`) **and grammar drills**
(`-k grammar --recheck`) — and can:

- **flag** a bad item (`flagged = true` + a `flag_reason` on
  `example_sentences` / `drill_sentences`) — the red "flagged" chip a
  reviewer sees on the example or drill;
- **suggest** a better translation on an example (`suggested_translation` +
  `suggestion_reason`) — the Accept/Dismiss box;
- **generate alternatives** to heal the item back to target, marked pending
  review.

All of this output lands as `source = 'ai'`, `reviewed = false` — **still
behind the human gate**. The checker never publishes; it only prepares work.

### 2. The semantic check (manual, advisory, on demand)

On a grammar point **or a vocabulary word**, a reviewer can click **"Run AI
check"**. That calls `services/semantic_check.py`
(`semantic_check_point` / `semantic_check_vocab`), which returns a verdict
stored on the entity:

- `ai_check_status` = `pass` or `concerns` (on `grammar_points` / `vocabulary`)
- `ai_check_notes` = the model's reasoning

For grammar it checks the explanation and every drill; for a word it checks
the definition/gloss and every example sentence. You see it in the
**PointEditor → "Checks" box** (grammar) or the vocab card's **"AI check"
box**. Only contributors/admins can *run* it (it costs an API call); any
reviewer can *see* the result. It is purely advisory —
a second opinion to help the human decide. Under the default `strict`
policy it changes nothing about what learners see; it does **not** approve
anything. **Where do concerns show up?** Right on the point in the Review
tab, in that Checks box — that is the single place to look.

### `ai_ok`: the opt-out, per language

An admin can set a language's `grammar_review_policy` to `ai_ok`
(Review-policy control, admin only). For that language, AI-passed drafts are
surfaced to learners **without** waiting for a human approval. Use it only
for languages where you trust the pipeline. The default is `strict` (human
gate on).

---

## The unified Review Inbox

Reviewers used to hunt across ~10 scattered panels to find what needed
attention. The **Review Inbox** (top of the Review tab) is a single roll-up
per language: it shows only the non-empty queues with a count, and a running
total, or "All clear".

It counts (via `review_inbox_counts()`, `GET /review/inbox`):

| Queue | What it is | Panel that acts on it |
|---|---|---|
| Grammar points | drafted, pending review | Contribute list |
| Generated drills | AI drills awaiting approval | Generated drills panel |
| Flagged drills | `--recheck` flagged as bad | Point drills (flagged chip) |
| Generated examples | AI example sentences pending | Word examples |
| Flagged examples | `--recheck` flagged as bad | Word examples (flagged chip) |
| Translation fixes | suggested-translation boxes | Word examples (Accept/Dismiss) |
| AI vocab levels | provisional CEFR levels | AI levels panel |
| Change requests | learner/contributor requests | Change-requests board |
| Content suggestions | proposed definition edits | Suggestions panel |
| Review notes | open notes on a point | Point review notes |
| Learner feedback | open card feedback | Feedback panel |

The Inbox is **counts only** — it doesn't act. It's the "what needs my
attention, and how much" view; you still act in the panel below it. Open to
anyone who can trial-review the language.

---

## Change requests & recommendations — the advisory inputs

These do **not** publish anything. They feed the one reviewer's decision:

- **Change requests** (`card_change_requests`) — anyone with a role can
  raise "this card is wrong" with an issue + optional suggestion, and role
  holders vote (`card_change_request_votes`). Only an admin
  accepts/rejects (server-enforced). The votes are a signal, not a gate.
- **Trial-reviewer recommendations** — a trial reviewer's ✓/✗ on a pending
  drill or example. Shown as a tally next to the item so the reviewer who
  *does* publish can weigh it.
- **Content suggestions** (`content_suggestions`) — proposed definition /
  usage-note edits, approved or rejected by a reviewer.
- **Review notes** (`point_review_notes`) — freeform "look at this" notes
  parked on a **grammar point or a vocabulary word** ("this gloss is
  regional", "the B1 level looks high"), filed from the card's *Flag an issue*
  box (grammar list / vocab card) and resolved by a reviewer. They collect in
  the amber **Open issues** panel, each tagged *grammar* or *word*.

---

## Audit trail & rollback

**Every content mutation is logged** to `content_change_log` with a
before/after snapshot, so you can see who changed what and undo it.

### What's logged

The instrumented mutators in `contributor.py` write a row on: example edits,
example flags, example/drill approvals and rejections, vocab-level
confirmations, drill updates, explanation saves, and explanation approvals.
Each row carries:

- `entity_type` (`grammar_point` / `drill` / `example_sentence` /
  `vocabulary` / `translation`) and `entity_id`
- `actor_id` (who — `NULL` for the automated CLI recheck), `action`
- `before` / `after` JSONB snapshots, an optional `note`
- `seq` — a monotonic counter so the timeline is unambiguous even when two
  changes share a timestamp

Logging is **best-effort**: if the audit insert ever fails it never blocks
the real edit (the mutation still succeeds).

### Where you see it

- **Per card** — a collapsible **"History"** toggle on the card
  (`CardHistory` component, currently on example sentences) shows the
  timeline: who did what, when, before → after.
- **Per language** — admins get the full feed via `GET /admin/audit`
  (`list_recent_changes`), ordered newest-first.

### Rolling back

On a revertible logged change, a **reviewer or admin** sees a **"Roll back"**
button (`POST /review/revert/{log_id}`, gated by `can_review`). It:

1. restores the entity's columns from the `before` snapshot (only whitelisted
   columns in `_REVERT_COLUMNS` — sentence/translation, drill fields, the
   grammar `reviewed` flag, vocab level + source), and
2. appends a new `reverted` entry to the log — **the rollback is itself
   audited**, so an undo is never silent.

`revert_change` returns `ok` / `not_found` / `no_snapshot` /
`not_revertible`, so the UI can explain why a given entry can't be undone
(e.g. an approval with no captured prior state).

---

## End-to-end example

1. You run `generate_content.py --recheck` for Swahili vocab examples.
   The checker flags two weak sentences, suggests a better translation on a
   third, and adds three new alternatives. All land `reviewed = false`.
2. A reviewer opens the Swahili **Review tab**. The **Review Inbox** shows
   *Generated examples 3 · Flagged examples 2 · Translation fixes 1*.
3. In the Word examples panel they Accept the suggested translation, edit one
   flagged sentence and delete the other, and approve the three new ones.
   Every one of those actions is written to `content_change_log`.
4. A day later they realise the edited sentence read better before. They open
   its **History**, click **Roll back**, and it's restored — with a
   `reverted` entry recording the undo.
5. The admin audit feed (`/admin/audit`) shows the whole sequence, actor and
   timestamps included.

---

## Where this lives in the code

| Concern | Code |
|---|---|
| Role gates | `backend/repositories/contributor.py` — `is_admin`, `can_contribute`, `can_review`, `can_trial_review` |
| Generation + recheck | `backend/services/{generate,translate,define}.py`, `scripts/generate_content.py` |
| Semantic check | `backend/services/semantic_check.py`; verdict on `grammar_points.ai_check_status/notes` |
| Review Inbox | `review_inbox_counts()`; `GET /review/inbox`; `frontend/.../ReviewInbox.tsx` |
| Audit + rollback | `backend/repositories/audit.py`; `content_change_log` table; `frontend/.../CardHistory.tsx` |
| Endpoints | `backend/routers/contribute.py` — `/review/*`, `/admin/audit` |

See also **[accounts-and-roles.md](accounts-and-roles.md)** for granting the
roles named here, and **[content-generation-cli.md](content-generation-cli.md)**
for running the generator/recheck.
